from typing import Any, Dict
from fastapi import APIRouter, Body, Header, HTTPException, status
from pydantic import BaseModel
from core.config import get_settings
from core.errors import ErrorCode, IncuBrixError

router = APIRouter(prefix="/api/v1/security", tags=["security"])
settings = get_settings()

# State store for revoked demo tokens
_revoked_tokens: set[str] = set()
_custom_simulation_mode: Dict[str, bool] = {"enabled": settings.simulation_mode}


class RevokeTokenRequest(BaseModel):
    token: str


class SimulationModeRequest(BaseModel):
    enabled: bool


def is_token_revoked(token: str) -> bool:
    return token in _revoked_tokens


def get_current_simulation_mode() -> bool:
    return _custom_simulation_mode.get("enabled", True)


@router.get("/token-status", status_code=status.HTTP_200_OK)
async def get_token_status(
    auth_header: str = Header(None, alias="X-IncuBrix-Token"),
) -> Dict[str, Any]:
    """Returns current revocable token status, rate limits, and simulation mode."""
    token = auth_header or settings.api_access_token
    revoked = is_token_revoked(token)
    sim_mode = get_current_simulation_mode()

    return {
        "token": token,
        "is_valid": not revoked,
        "status": "revoked" if revoked else "active",
        "simulation_mode": sim_mode,
        "rate_limits": {
            "limit_per_minute": 120,
            "remaining": 0 if revoked else 118,
            "reset_seconds": 60,
        },
        "webhook_signing_secret": f"{settings.webhook_signing_secret[:6]}...{settings.webhook_signing_secret[-4:]}",
    }


@router.post("/revoke-token", status_code=status.HTTP_200_OK)
async def revoke_token(req: RevokeTokenRequest) -> Dict[str, Any]:
    """Revokes a demo API access token immediately."""
    _revoked_tokens.add(req.token)
    return {
        "token": req.token,
        "status": "revoked",
        "message": f"Token '{req.token}' has been successfully revoked. API requests with this token will now return 401 Unauthorized.",
    }


@router.post("/restore-token", status_code=status.HTTP_200_OK)
async def restore_token(req: RevokeTokenRequest) -> Dict[str, Any]:
    """Restores a previously revoked demo API access token."""
    _revoked_tokens.discard(req.token)
    return {
        "token": req.token,
        "status": "active",
        "message": f"Token '{req.token}' has been restored.",
    }


@router.post("/simulation-mode", status_code=status.HTTP_200_OK)
async def set_simulation_mode(req: SimulationModeRequest) -> Dict[str, Any]:
    """Updates the global simulation mode banner and runtime flag."""
    _custom_simulation_mode["enabled"] = req.enabled
    return {
        "simulation_mode": req.enabled,
        "message": f"Simulation mode is now {'ENABLED' if req.enabled else 'DISABLED'}.",
    }
