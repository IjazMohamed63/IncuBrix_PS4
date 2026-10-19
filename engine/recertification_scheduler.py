from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from connectors.schemas import ConnectionPayload, DestinationPayload
from core.logging import get_logger
from engine.certification_harness import AlertRecord, CertificationHarness, certification_harness

logger = get_logger("recertification_scheduler")

MAX_CERTIFICATION_AGE_DAYS = 30


class RecertificationScheduler:
    """Automated 30-day recertification scheduler.
    
    Identifies destinations whose certification has lapsed beyond 30 days.
    Runs automated recertification probe; on failure or expiry, demotes destination
    to L0, excludes it from publishing and recommendations, and logs an alert.
    """

    def __init__(self, harness: Optional[CertificationHarness] = None):
        self.harness = harness or certification_harness

    async def scan_and_recertify(
        self,
        destinations: List[Dict[str, Any]],
        now: Optional[datetime] = None,
        is_mock: bool = True,
    ) -> Dict[str, Any]:
        current_time = now or datetime.now(timezone.utc)
        threshold_date = current_time - timedelta(days=MAX_CERTIFICATION_AGE_DAYS)

        inspected = 0
        recertified_passed = 0
        recertified_failed = 0
        demoted_and_alerted: List[str] = []

        for dest in destinations:
            dest_id = dest.get("id") or "dest_id"
            last_cert_str = dest.get("last_certified_at")
            last_cert_dt = None
            if last_cert_str:
                try:
                    last_cert_dt = datetime.fromisoformat(last_cert_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            is_overdue = last_cert_dt is None or last_cert_dt < threshold_date
            if not is_overdue:
                continue

            inspected += 1
            logger.info(f"Destination '{dest_id}' certification is overdue (>30 days). Triggering recertification.")

            dest_payload = DestinationPayload(
                id=dest_id,
                name=dest.get("name", "Destination"),
                platform_key=dest.get("platform_key", "stub"),
                parameters=dest.get("parameters", {}),
            )
            conn_dict = dest.get("connection") or {}
            conn_payload = ConnectionPayload.model_validate(conn_dict)

            try:
                run_rec = await self.harness.run_certification(
                    destination=dest_payload,
                    connection=conn_payload,
                    is_mock=is_mock,
                )
                if run_rec.status == "passed":
                    recertified_passed += 1
                    dest["last_certified_at"] = current_time.isoformat()
                    dest["level"] = run_rec.assigned_level
                    logger.info(f"Destination '{dest_id}' recertification PASSED: level {run_rec.assigned_level}")
                else:
                    recertified_failed += 1
                    dest["level"] = "L0"
                    params = dest.setdefault("parameters", {})
                    params["level"] = "L0"
                    params["excluded_from_publishing"] = True
                    params["excluded_from_recommendations"] = True
                    demoted_and_alerted.append(dest_id)
            except Exception as e:
                recertified_failed += 1
                dest["level"] = "L0"
                params = dest.setdefault("parameters", {})
                params["level"] = "L0"
                params["excluded_from_publishing"] = True
                params["excluded_from_recommendations"] = True
                alert = AlertRecord(
                    destination_id=dest_id,
                    alert_type="RECERTIFICATION_FAILURE",
                    severity="CRITICAL",
                    reason=f"30-day recertification failed: {e}",
                )
                self.harness.store.record_alert(alert)
                demoted_and_alerted.append(dest_id)
                logger.error(f"Destination '{dest_id}' recertification error: {e}. Demoted to L0 and alert raised.")

        return {
            "inspected": inspected,
            "passed": recertified_passed,
            "failed": recertified_failed,
            "demoted_destinations": demoted_and_alerted,
        }


recertification_scheduler = RecertificationScheduler()
