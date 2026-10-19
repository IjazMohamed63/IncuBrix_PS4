from typing import Any, Dict
from fastapi import APIRouter, Body, Depends, Path
from connectors.registry import ConnectorRegistry, registry
from connectors.schemas import (
    BuildAssistPackRequest,
    BuildAssistPackResponse,
    DeleteRequest,
    DeleteResponse,
    FetchMetricsRequest,
    FetchMetricsResponse,
    GetStatusRequest,
    GetStatusResponse,
    PublishRequest,
    PublishResponse,
    RefreshAuthRequest,
    RefreshAuthResponse,
    ValidateRequest,
    ValidateResponse,
)
from core.errors import ErrorCode, IncuBrixError

router = APIRouter(prefix="/connector/v1", tags=["connector-contract"])


def get_registry() -> ConnectorRegistry:
    return registry


@router.post("/{connector_key}/{method}")
async def dispatch_connector_method(
    connector_key: str = Path(..., description="Key of the connector (e.g. discourse, lemmy, stub)"),
    method: str = Path(..., description="Connector method to invoke"),
    payload: Dict[str, Any] = Body(..., description="JSON payload conforming to method schema"),
    reg: ConnectorRegistry = Depends(get_registry),
) -> Any:
    """Dispatches requests according to the exact IncuBrix connector contract:

    POST /connector/v1/{connector_key}/{method}
    """
    connector = reg.get_connector(connector_key)

    if method == "validate":
        req = ValidateRequest.model_validate(payload)
        res = await connector.validate(req.rendition, req.destination, req.connection)
        return res.model_dump()

    elif method == "publish":
        req = PublishRequest.model_validate(payload)
        res = await connector.publish(req.rendition, req.destination, req.connection, req.idempotency_key)
        return res.model_dump()

    elif method == "get_status":
        req = GetStatusRequest.model_validate(payload)
        res = await connector.get_status(req.platform_post_id, req.connection)
        return res.model_dump()

    elif method == "delete":
        req = DeleteRequest.model_validate(payload)
        res = await connector.delete(req.platform_post_id, req.connection)
        return res.model_dump()

    elif method == "fetch_metrics":
        req = FetchMetricsRequest.model_validate(payload)
        res = await connector.fetch_metrics(req.platform_post_id, req.connection, req.since)
        return res.model_dump()

    elif method == "refresh_auth":
        req = RefreshAuthRequest.model_validate(payload)
        res = await connector.refresh_auth(req.connection)
        return res.model_dump()

    elif method == "build_assist_pack":
        req = BuildAssistPackRequest.model_validate(payload)
        res = await connector.build_assist_pack(req.rendition, req.destination)
        return res.model_dump()

    else:
        raise IncuBrixError(
            code=ErrorCode.NOT_FOUND,
            message=f"Method '{method}' is not supported by connector contract.",
            details={"valid_methods": [
                "validate", "publish", "get_status", "delete",
                "fetch_metrics", "refresh_auth", "build_assist_pack"
            ]},
            status_code=404,
        )
