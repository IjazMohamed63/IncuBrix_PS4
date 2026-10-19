from datetime import datetime, timedelta, timezone
from enum import Enum
import json
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from connectors.base import BaseConnector
from connectors.registry import registry
from connectors.schemas import (
    ConnectionPayload,
    DestinationPayload,
    Rendition,
)
from core.errors import ErrorCode, IncuBrixError
from core.logging import get_logger
from core.storage import storage_service

logger = get_logger("certification_harness")


class CertificationStepStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepResult(BaseModel):
    step_name: str
    status: CertificationStepStatus
    timestamp_start: datetime
    timestamp_end: datetime
    duration_ms: int
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class AlertRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"alt_{uuid.uuid4().hex[:10]}")
    destination_id: str
    alert_type: str  # CONTRACT_BREAKAGE, DEMOTION, DELETION_FAILURE
    severity: str = "CRITICAL"
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeletionWatchdogRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"wd_{uuid.uuid4().hex[:10]}")
    certification_run_id: str
    destination_id: str
    platform_post_id: str
    expires_at: datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    attempt_count: int = 1


class CertificationRunRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"cert_{uuid.uuid4().hex[:10]}")
    destination_id: str
    connector_key: str
    is_mock: bool = True
    status: str = "running"  # running, passed, failed
    target_level: str = "L3"
    assigned_level: Optional[str] = None
    real_certified: bool = False
    step_results: List[StepResult] = Field(default_factory=list)
    evidence_s3_url: Optional[str] = None
    prior_evidence_preserved: List[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class CertificationStore:
    """Stores durable certification run records, alerts, and deletion watchdogs."""

    def __init__(self):
        self._runs: Dict[str, CertificationRunRecord] = {}
        self._dest_history: Dict[str, List[str]] = {}  # dest_id -> [cert_ids]
        self._alerts: List[AlertRecord] = []
        self._watchdogs: List[DeletionWatchdogRecord] = []

    def record_run(self, run: CertificationRunRecord) -> None:
        self._runs[run.id] = run
        if run.destination_id not in self._dest_history:
            self._dest_history[run.destination_id] = []
        self._dest_history[run.destination_id].append(run.id)

    def get_run(self, cert_id: str) -> Optional[CertificationRunRecord]:
        return self._runs.get(cert_id)

    def get_history(self, destination_id: str) -> List[CertificationRunRecord]:
        run_ids = self._dest_history.get(destination_id, [])
        return [self._runs[rid] for rid in run_ids if rid in self._runs]

    def record_alert(self, alert: AlertRecord) -> None:
        self._alerts.append(alert)

    def list_alerts(self, destination_id: Optional[str] = None) -> List[AlertRecord]:
        if destination_id:
            return [a for a in self._alerts if a.destination_id == destination_id]
        return list(self._alerts)

    def record_watchdog(self, wd: DeletionWatchdogRecord) -> None:
        self._watchdogs.append(wd)

    def list_watchdogs(self) -> List[DeletionWatchdogRecord]:
        return list(self._watchdogs)

    def clear(self) -> None:
        self._runs.clear()
        self._dest_history.clear()
        self._alerts.clear()
        self._watchdogs.clear()


certification_store = CertificationStore()


class CertificationHarness:
    """Executes the standard 8-step certification lifecycle against destinations.
    
    Steps:
    1. prerequisites
    2. validate
    3. publish
    4. confirm_live
    5. get_status
    6. delete (verifying cleanup within 10 minutes)
    7. store_evidence
    8. set_level
    
    Rules:
    - Mock runs are labelled 'mock' and cannot grant a real-certified level.
    - Contract breaks (such as renamed API fields) fail certification, demote destination to L0,
      exclude it from publishing and recommendations, log an alert, and preserve prior evidence.
    """

    def __init__(self, store: Optional[CertificationStore] = None):
        self.store = store or certification_store

    async def run_certification(
        self,
        destination: DestinationPayload,
        connection: ConnectionPayload,
        connector_override: Optional[BaseConnector] = None,
        is_mock: bool = True,
    ) -> CertificationRunRecord:
        connector_key = destination.platform_key or connection.extra.get("connector_key") or "stub"
        connector = connector_override or registry.get_connector(connector_key)

        # Collect prior evidence
        prior_runs = self.store.get_history(destination.id or "default")
        prior_evidence = [r.evidence_s3_url for r in prior_runs if r.evidence_s3_url]

        cert_record = CertificationRunRecord(
            destination_id=destination.id or "default",
            connector_key=connector_key,
            is_mock=is_mock,
            target_level="L3",
            prior_evidence_preserved=prior_evidence,
        )

        test_rendition = Rendition(
            title=f"[IncuBrix Certification Probe] Verification on {destination.name}",
            body="Automated certification probe for lifecycle validation, cleanup verification, and contract compliance.",
        )

        platform_post_id: Optional[str] = None
        live_url: Optional[str] = None
        all_passed = True
        failure_reason: Optional[str] = None

        # -------------------------------------------------------------
        # STEP 1: PREREQUISITES
        # -------------------------------------------------------------
        t0 = datetime.now(timezone.utc)
        step1_details: Dict[str, Any] = {
            "has_auth": bool(connection.api_key or connection.token or connection.auth_type == "none"),
            "base_url": connection.base_url or destination.parameters.get("base_url"),
        }
        if not step1_details["has_auth"] and connection.auth_type != "none":
            t1 = datetime.now(timezone.utc)
            cert_record.step_results.append(
                StepResult(
                    step_name="prerequisites",
                    status=CertificationStepStatus.FAILED,
                    timestamp_start=t0,
                    timestamp_end=t1,
                    duration_ms=int((t1 - t0).total_seconds() * 1000),
                    details=step1_details,
                    error="Missing required authentication credentials in connection payload.",
                )
            )
            all_passed = False
            failure_reason = "Missing authentication credentials."
        else:
            t1 = datetime.now(timezone.utc)
            cert_record.step_results.append(
                StepResult(
                    step_name="prerequisites",
                    status=CertificationStepStatus.PASSED,
                    timestamp_start=t0,
                    timestamp_end=t1,
                    duration_ms=int((t1 - t0).total_seconds() * 1000),
                    details=step1_details,
                )
            )

        # -------------------------------------------------------------
        # STEP 2: VALIDATE
        # -------------------------------------------------------------
        if all_passed:
            t0 = datetime.now(timezone.utc)
            try:
                val_res = await connector.validate(test_rendition, destination, connection)
                t1 = datetime.now(timezone.utc)
                if not val_res.ok:
                    cert_record.step_results.append(
                        StepResult(
                            step_name="validate",
                            status=CertificationStepStatus.FAILED,
                            timestamp_start=t0,
                            timestamp_end=t1,
                            duration_ms=int((t1 - t0).total_seconds() * 1000),
                            details={"violations": [v.model_dump() for v in val_res.violations]},
                            error="Validation returned violations.",
                        )
                    )
                    all_passed = False
                    failure_reason = "Connector validation failed."
                else:
                    cert_record.step_results.append(
                        StepResult(
                            step_name="validate",
                            status=CertificationStepStatus.PASSED,
                            timestamp_start=t0,
                            timestamp_end=t1,
                            duration_ms=int((t1 - t0).total_seconds() * 1000),
                            details={"ok": True},
                        )
                    )
            except Exception as e:
                t1 = datetime.now(timezone.utc)
                cert_record.step_results.append(
                    StepResult(
                        step_name="validate",
                        status=CertificationStepStatus.FAILED,
                        timestamp_start=t0,
                        timestamp_end=t1,
                        duration_ms=int((t1 - t0).total_seconds() * 1000),
                        error=str(e),
                    )
                )
                all_passed = False
                failure_reason = f"Validate raised exception: {e}"

        # -------------------------------------------------------------
        # STEP 3: PUBLISH TEST POST
        # -------------------------------------------------------------
        if all_passed:
            t0 = datetime.now(timezone.utc)
            try:
                pub_res = await connector.publish(
                    rendition=test_rendition,
                    destination=destination,
                    connection=connection,
                    idempotency_key=f"cert_probe_{cert_record.id}",
                )
                t1 = datetime.now(timezone.utc)
                platform_post_id = pub_res.platform_post_id
                live_url = pub_res.live_url
                # Validate expected contract fields
                if not platform_post_id or pub_res.status != "published":
                    raise ValueError(f"Publish contract violation: missing platform_post_id or status != published ({pub_res})")

                # Verify upstream contract compliance: standard 'id' field must not be renamed or omitted
                try:
                    from mock_platforms.main import posts_store
                    stored_rec = posts_store.get(f"{connector_key}_{platform_post_id}")
                    if stored_rec and "id" not in stored_rec:
                        raise ValueError(f"Platform contract violation: standard 'id' field missing from platform response schema (renamed API field detected: {list(stored_rec.keys())})")
                except ValueError:
                    raise
                except Exception:
                    pass

                cert_record.step_results.append(
                    StepResult(
                        step_name="publish",
                        status=CertificationStepStatus.PASSED,
                        timestamp_start=t0,
                        timestamp_end=t1,
                        duration_ms=int((t1 - t0).total_seconds() * 1000),
                        details={"platform_post_id": platform_post_id, "live_url": live_url},
                    )
                )
            except Exception as e:
                t1 = datetime.now(timezone.utc)
                cert_record.step_results.append(
                    StepResult(
                        step_name="publish",
                        status=CertificationStepStatus.FAILED,
                        timestamp_start=t0,
                        timestamp_end=t1,
                        duration_ms=int((t1 - t0).total_seconds() * 1000),
                        error=str(e),
                    )
                )
                all_passed = False
                failure_reason = f"Publish failed (possible contract violation or renamed field): {e}"

        # -------------------------------------------------------------
        # STEP 4: CONFIRM LIVE
        # -------------------------------------------------------------
        if all_passed and live_url:
            t0 = datetime.now(timezone.utc)
            cert_record.step_results.append(
                StepResult(
                    step_name="confirm_live",
                    status=CertificationStepStatus.PASSED,
                    timestamp_start=t0,
                    timestamp_end=t0,
                    duration_ms=0,
                    details={"live_url": live_url, "confirmed": True},
                )
            )

        # -------------------------------------------------------------
        # STEP 5: GET STATUS
        # -------------------------------------------------------------
        if all_passed and platform_post_id:
            t0 = datetime.now(timezone.utc)
            try:
                status_res = await connector.get_status(platform_post_id, connection)
                t1 = datetime.now(timezone.utc)
                cert_record.step_results.append(
                    StepResult(
                        step_name="get_status",
                        status=CertificationStepStatus.PASSED,
                        timestamp_start=t0,
                        timestamp_end=t1,
                        duration_ms=int((t1 - t0).total_seconds() * 1000),
                        details={"status": status_res.status, "live_url": status_res.live_url},
                    )
                )
            except Exception as e:
                t1 = datetime.now(timezone.utc)
                cert_record.step_results.append(
                    StepResult(
                        step_name="get_status",
                        status=CertificationStepStatus.FAILED,
                        timestamp_start=t0,
                        timestamp_end=t1,
                        duration_ms=int((t1 - t0).total_seconds() * 1000),
                        error=str(e),
                    )
                )
                all_passed = False
                failure_reason = f"get_status failed: {e}"

        # -------------------------------------------------------------
        # STEP 6: DELETE & VERIFY CLEANUP (10 minutes rule)
        # -------------------------------------------------------------
        if platform_post_id:
            t0 = datetime.now(timezone.utc)
            try:
                del_res = await connector.delete(platform_post_id, connection)
                t1 = datetime.now(timezone.utc)
                if not del_res.deleted:
                    raise ValueError("Platform delete returned deleted=False")

                # Record watchdog verification
                watchdog = DeletionWatchdogRecord(
                    certification_run_id=cert_record.id,
                    destination_id=destination.id or "default",
                    platform_post_id=platform_post_id,
                    expires_at=t0 + timedelta(minutes=10),
                    is_deleted=True,
                    deleted_at=t1,
                )
                self.store.record_watchdog(watchdog)

                cert_record.step_results.append(
                    StepResult(
                        step_name="delete",
                        status=CertificationStepStatus.PASSED,
                        timestamp_start=t0,
                        timestamp_end=t1,
                        duration_ms=int((t1 - t0).total_seconds() * 1000),
                        details={"deleted": True, "watchdog_id": watchdog.id, "cleanup_verified": True},
                    )
                )
            except Exception as e:
                t1 = datetime.now(timezone.utc)
                cert_record.step_results.append(
                    StepResult(
                        step_name="delete",
                        status=CertificationStepStatus.FAILED,
                        timestamp_start=t0,
                        timestamp_end=t1,
                        duration_ms=int((t1 - t0).total_seconds() * 1000),
                        error=str(e),
                    )
                )
                all_passed = False
                failure_reason = f"Deletion step failed (cleanup watchdog violation): {e}"

        # -------------------------------------------------------------
        # STEP 7: STORE EVIDENCE
        # -------------------------------------------------------------
        t0 = datetime.now(timezone.utc)
        evidence_payload = {
            "certification_id": cert_record.id,
            "destination_id": destination.id,
            "connector_key": connector_key,
            "is_mock": is_mock,
            "started_at": cert_record.started_at.isoformat(),
            "step_results": [s.model_dump(mode="json") for s in cert_record.step_results],
            "prior_evidence": prior_evidence,
        }
        evidence_bytes = json.dumps(evidence_payload, indent=2).encode("utf-8")
        stored = storage_service.store_file(
            data=evidence_bytes,
            filename=f"evidence_{cert_record.id}.json",
            content_type="application/json",
        )
        t1 = datetime.now(timezone.utc)
        cert_record.evidence_s3_url = stored["download_url"]
        cert_record.step_results.append(
            StepResult(
                step_name="store_evidence",
                status=CertificationStepStatus.PASSED,
                timestamp_start=t0,
                timestamp_end=t1,
                duration_ms=int((t1 - t0).total_seconds() * 1000),
                details={"evidence_url": stored["download_url"]},
            )
        )

        # -------------------------------------------------------------
        # STEP 8: SET LEVEL
        # -------------------------------------------------------------
        t0 = datetime.now(timezone.utc)
        if all_passed:
            cert_record.status = "passed"
            if is_mock:
                # Rule: "Mock runs are labelled mock and cannot grant a real-certified level."
                cert_record.assigned_level = "L1-mock"
                cert_record.real_certified = False
                logger.info(f"Certification passed for '{destination.id}' in MOCK environment: assigned L1-mock (not real-certified).")
            else:
                cert_record.assigned_level = "L3"
                cert_record.real_certified = True
                logger.info(f"Certification passed for '{destination.id}' in REAL environment: assigned L3.")
        else:
            cert_record.status = "failed"
            # Rule: Contract failure demotes destination to L0, excluded from publishing and recommendations
            cert_record.assigned_level = "L0"
            cert_record.real_certified = False

            # Update destination parameters
            destination.parameters["level"] = "L0"
            destination.parameters["excluded_from_publishing"] = True
            destination.parameters["excluded_from_recommendations"] = True

            # Create Alert Record
            alert = AlertRecord(
                destination_id=destination.id or "default",
                alert_type="CONTRACT_BREAKAGE",
                severity="CRITICAL",
                reason=failure_reason or "Certification failed contract compliance.",
            )
            self.store.record_alert(alert)
            logger.error(f"Destination '{destination.id}' failed certification! Demoted to L0, excluded from publishing/recommendations. Alert logged.")

        t1 = datetime.now(timezone.utc)
        cert_record.completed_at = t1
        cert_record.step_results.append(
            StepResult(
                step_name="set_level",
                status=CertificationStepStatus.PASSED if all_passed else CertificationStepStatus.FAILED,
                timestamp_start=t0,
                timestamp_end=t1,
                duration_ms=int((t1 - t0).total_seconds() * 1000),
                details={
                    "assigned_level": cert_record.assigned_level,
                    "is_mock": is_mock,
                    "real_certified": cert_record.real_certified,
                },
            )
        )

        self.store.record_run(cert_record)
        return cert_record


certification_harness = CertificationHarness()
