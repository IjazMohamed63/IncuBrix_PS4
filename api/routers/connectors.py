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


@router.get("", status_code=200)
async def list_connectors(reg: ConnectorRegistry = Depends(get_registry)) -> Dict[str, Any]:
    """Lists all registered connectors with manifests, capabilities, rate limits, and kill-switch states."""
    manifests = reg.list_manifests()
    data = []
    for key, manifest in manifests.items():
        is_disabled = reg.is_disabled(key)
        data.append({
            "key": key,
            "version": manifest.version,
            "tier": manifest.tier.value if hasattr(manifest.tier, "value") else str(manifest.tier),
            "auth": manifest.auth.value if hasattr(manifest.auth, "value") else str(manifest.auth),
            "surfaces": [s.model_dump() for s in manifest.surfaces],
            "rate_limits": manifest.rate_limits.model_dump(),
            "capabilities": manifest.capabilities,
            "error_map": manifest.error_map,
            "instance_param": manifest.instance_param,
            "disabled": is_disabled,
            "health": "disabled" if is_disabled else "healthy",
        })
    return {"connectors": data, "count": len(data)}


@router.get("/{connector_key}/manifest", status_code=200)
async def get_connector_manifest(
    connector_key: str = Path(...),
    reg: ConnectorRegistry = Depends(get_registry),
) -> Dict[str, Any]:
    """Retrieves manifest and status for a specific connector."""
    manifest = reg.get_manifest(connector_key)
    is_disabled = reg.is_disabled(connector_key)
    return {
        "manifest": manifest.model_dump(),
        "disabled": is_disabled,
        "health": "disabled" if is_disabled else "healthy",
    }


@router.post("/{connector_key}/kill-switch", status_code=200)
async def toggle_connector_kill_switch(
    connector_key: str = Path(...),
    reg: ConnectorRegistry = Depends(get_registry),
) -> Dict[str, Any]:
    """Toggles kill-switch for a connector."""
    _ = reg.get_manifest(connector_key)  # Ensures connector exists
    if reg.is_disabled(connector_key):
        reg.enable_connector(connector_key)
        new_state = False
    else:
        reg.disable_connector(connector_key)
        new_state = True

    return {
        "connector_key": connector_key,
        "disabled": new_state,
        "health": "disabled" if new_state else "healthy",
        "message": f"Connector '{connector_key}' {'disabled' if new_state else 're-enabled'}.",
    }



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
