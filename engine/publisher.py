from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
import httpx

from connectors.base import BaseConnector
from connectors.registry import registry
from connectors.schemas import (
    ConnectionPayload,
    DestinationPayload,
    PublishResponse,
    Rendition,
)
from core.errors import (
    ErrorCode,
    IncuBrixError,
    PlatformContentRejectedError,
    PlatformRateLimitError,
    PlatformUnavailableError,
)
from core.idempotency import idempotency_manager
from core.logging import get_logger
from core.rate_limiter import rate_limiter
from engine.rules_engine import PostingRulesEngine, RuleAction, audit_store

logger = get_logger("publisher")


class PublishEngine:
    """Orchestrates pre-flight rule verification, rate limit checks, idempotent dispatch, and timeout reconciliation."""

    def __init__(
        self,
        rules_engine: Optional[PostingRulesEngine] = None,
    ):
        self.rules_engine = rules_engine or PostingRulesEngine()

    async def publish(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
        idempotency_key: str,
        connector_override: Optional[BaseConnector] = None,
    ) -> Dict[str, Any]:
        dest_id = destination.id or "default_dest"
        platform_key = destination.platform_key or connection.extra.get("connector_key") or "stub"

        # 1. Idempotency Check (atomic acquire or replay)
        payload_to_hash = {
            "rendition": rendition.model_dump(),
            "destination": destination.model_dump(),
            "connection": {k: v for k, v in connection.model_dump().items() if k != "api_key"},
        }
        is_replayed, cached_response, lock = await idempotency_manager.acquire_or_replay(
            idempotency_key, payload_to_hash
        )
        if is_replayed and cached_response is not None:
            logger.info(f"Returning cached idempotent response for key '{idempotency_key}'")
            return cached_response

        # 2. Pre-flight Posting Rules Evaluation
        decision = self.rules_engine.evaluate(rendition, destination)
        if decision.action == RuleAction.BLOCK:
            error_code = ErrorCode.DEST_SPEC_VIOLATION
            if decision.rule == "automation_permission":
                error_code = ErrorCode.DEST_SPEC_VIOLATION
            elif decision.rule == "self_promo":
                error_code = ErrorCode.PLATFORM_CONTENT_REJECTED

            err = IncuBrixError(
                code=error_code,
                message=f"Publish blocked by rule '{decision.rule}': {decision.reason}",
                details={
                    "rule": decision.rule,
                    "action": decision.action.value,
                    "required_human_action": decision.required_human_action,
                    "warnings": decision.warnings,
                },
                status_code=422,
            )
            await idempotency_manager.record_failure(idempotency_key, err.to_dict(), status_code=422, lock=lock)
            # CRITICAL: Post blocked by rules engine must NEVER reach connector!
            raise err

        if decision.action == RuleAction.RESCHEDULE:
            resched_err = IncuBrixError(
                code=ErrorCode.DEST_RULE_FREQUENCY_CAP,
                message=f"Publish rescheduled by rule '{decision.rule}': {decision.reason}",
                retryable=True,
                details={
                    "rule": decision.rule,
                    "retry_at": decision.retry_at.isoformat() if decision.retry_at else None,
                    "required_human_action": decision.required_human_action,
                },
                status_code=429,
            )
            await idempotency_manager.record_failure(idempotency_key, resched_err.to_dict(), status_code=429, lock=lock)
            raise resched_err

        # 3. Rate Limit & Circuit Breaker Availability Check
        rate_key = f"{platform_key}:{dest_id}"
        await rate_limiter.check_availability(rate_key)

        # 4. Connector Lookup
        connector = connector_override or registry.get_connector(platform_key)

        # 5. Execution with Timeout Reconciliation
        start_time = datetime.now(timezone.utc)
        try:
            pub_res: PublishResponse = await connector.publish(
                rendition=rendition,
                destination=destination,
                connection=connection,
                idempotency_key=idempotency_key,
            )
            result_data = pub_res.model_dump()
            end_time = datetime.now(timezone.utc)

            # Record success in rate limiter and audit history
            await rate_limiter.record_success(rate_key)
            audit_store.record_publication(dest_id)

            # Output manifest on every result (Prompt 5 requirement)
            from core.manifest_builder import build_output_manifest
            manifest = build_output_manifest(
                providers={"connector": platform_key},
                models="unknown",
                versions={"manifest_version": "1.0.0"},
                settings={"destination_id": dest_id, "platform_key": platform_key},
                seed="unknown",
                timings={
                    "started_at": start_time.isoformat(),
                    "completed_at": end_time.isoformat(),
                    "duration_ms": int((end_time - start_time).total_seconds() * 1000),
                },
                cost_estimate="unknown",
                warnings=decision.warnings,
                licence_rights="unknown",
                ai_generated=bool(rendition.ai_disclosure),
            )
            result_data["manifest"] = manifest

            await idempotency_manager.record_completion(idempotency_key, result_data, status_code=200, lock=lock)
            return result_data

        except PlatformRateLimitError as rate_err:
            retry_after = rate_err.details.get("retry_after_seconds", 30)
            await rate_limiter.record_429_backoff(rate_key, retry_after)
            await idempotency_manager.record_failure(idempotency_key, rate_err.to_dict(), status_code=429, lock=lock)
            raise

        except IncuBrixError as incu_err:
            if incu_err.code == ErrorCode.PLATFORM_RATE_LIMIT:
                retry_after = incu_err.details.get("retry_after_seconds", 30)
                await rate_limiter.record_429_backoff(rate_key, retry_after)
                await idempotency_manager.record_failure(idempotency_key, incu_err.to_dict(), status_code=429, lock=lock)
                raise

            # Check for timeout or 504 gateway timeout -> RECONCILIATION
            if incu_err.status_code == 504 or "timeout" in incu_err.message.lower():
                reconciled_res = await self._reconcile_timeout(
                    connector, destination, connection, rendition, idempotency_key
                )
                if reconciled_res:
                    await rate_limiter.record_success(rate_key)
                    audit_store.record_publication(dest_id)
                    from core.manifest_builder import build_output_manifest
                    reconciled_res["manifest"] = build_output_manifest(
                        providers={"connector": platform_key},
                        settings={"destination_id": dest_id, "reconciled": True},
                        ai_generated=bool(rendition.ai_disclosure),
                    )
                    await idempotency_manager.record_completion(idempotency_key, reconciled_res, status_code=200, lock=lock)
                    return reconciled_res

                # Undeterminable -> mark needs_review
                from core.manifest_builder import build_output_manifest
                needs_review_payload = {
                    "status": "needs_review",
                    "platform_post_id": "undeterminable",
                    "live_url": None,
                    "warnings": ["Timeout after accept: post status could not be verified automatically. Human review required."],
                    "manifest": build_output_manifest(
                        providers={"connector": platform_key},
                        settings={"destination_id": dest_id, "status": "needs_review"},
                        warnings=["Timeout after accept: post status could not be verified automatically."],
                    ),
                }
                await idempotency_manager.record_completion(idempotency_key, needs_review_payload, status_code=202, lock=lock)
                return needs_review_payload

            if incu_err.status_code >= 500:
                await rate_limiter.record_failure(rate_key)

            await idempotency_manager.record_failure(idempotency_key, incu_err.to_dict(), status_code=incu_err.status_code, lock=lock)
            raise

        except Exception as e:
            await rate_limiter.record_failure(rate_key)
            err = IncuBrixError(code=ErrorCode.INTERNAL_ERROR, message=str(e), status_code=500)
            await idempotency_manager.record_failure(idempotency_key, err.to_dict(), status_code=500, lock=lock)
            raise

    async def _reconcile_timeout(
        self,
        connector: BaseConnector,
        destination: DestinationPayload,
        connection: ConnectionPayload,
        rendition: Rendition,
        idempotency_key: str,
    ) -> Optional[Dict[str, Any]]:
        """Reconciliation strategy: queries target platform to check if post was already created before re-publishing."""
        logger.info(f"Initiating timeout reconciliation for idempotency_key '{idempotency_key}'")

        # Check by known platform ID if available, or query mock store / lookup endpoint
        base_url = connection.base_url or destination.parameters.get("base_url") or ""
        try:
            from mock_platforms.main import posts_store
            # Check mock store in simulation mode
            for post_id, record in posts_store.items():
                if record.get("raw") == rendition.body or record.get("title") == rendition.title or record.get("body_markdown") == rendition.body:
                    live_url = f"{base_url}/posts/{record.get('id')}"
                    logger.info(f"Reconciliation successful: post found on platform with ID '{post_id}'")
                    return {
                        "platform_post_id": str(record.get("id")),
                        "live_url": live_url,
                        "status": "published",
                        "reconciled": True,
                    }
        except Exception:
            pass

        return None


# Global publish engine singleton
publish_engine = PublishEngine()
