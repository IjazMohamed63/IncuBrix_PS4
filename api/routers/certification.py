from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from api.routers.destinations import _catalogue_store
from connectors.schemas import ConnectionPayload, DestinationPayload
from core.errors import ErrorCode, IncuBrixError
from engine.certification_harness import certification_harness, certification_store

router = APIRouter(prefix="/api/v1", tags=["certification"])


class CertifyRequest(BaseModel):
    is_mock: bool = True


@router.post("/destinations/{destination_id}/certify", status_code=status.HTTP_200_OK)
async def run_destination_certification(
    destination_id: str,
    payload: Optional[CertifyRequest] = None,
) -> Dict[str, Any]:
    """Executes the standard 8-step certification harness against a destination."""
    dest_dict = _catalogue_store.get(destination_id)
    if not dest_dict:
        raise IncuBrixError(
            code=ErrorCode.NOT_FOUND,
            message=f"Destination '{destination_id}' not found.",
            status_code=404,
        )

    destination = DestinationPayload(
        id=dest_dict["id"],
        name=dest_dict["name"],
        url=dest_dict["url"],
        platform_key=dest_dict["platform_key"],
        surface=dest_dict["surface"],
        parameters=dest_dict.get("parameters", {}),
    )
    conn_dict = dest_dict.get("connection") or {}
    connection = ConnectionPayload.model_validate(conn_dict)

    is_mock = payload.is_mock if payload is not None else True

    cert_record = await certification_harness.run_certification(
        destination=destination,
        connection=connection,
        is_mock=is_mock,
    )

    # Sync back destination parameters in store (e.g. if demoted to L0)
    dest_dict["parameters"] = destination.parameters

    return {
        "certification_id": cert_record.id,
        "destination_id": destination_id,
        "status": cert_record.status,
        "assigned_level": cert_record.assigned_level,
        "is_mock": cert_record.is_mock,
        "real_certified": cert_record.real_certified,
        "evidence_s3_url": cert_record.evidence_s3_url,
        "step_results": [s.model_dump() for s in cert_record.step_results],
    }


@router.get("/destinations/{destination_id}/certification-history")
async def get_destination_certification_history(destination_id: str) -> List[Dict[str, Any]]:
    """Retrieves all past certification runs and evidence for a destination."""
    history = certification_store.get_history(destination_id)
    return [h.model_dump() for h in history]


@router.get("/certification/alerts")
async def get_certification_alerts(destination_id: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """Retrieves contract breakage and demotion alerts."""
    alerts = certification_store.list_alerts(destination_id)
    return [a.model_dump() for a in alerts]
