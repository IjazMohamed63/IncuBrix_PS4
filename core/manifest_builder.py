from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class OutputManifest(BaseModel):
    """Structured output manifest included on every result.
    
    Guarantees that unknown or unprovided values default strictly to 'unknown'.
    """
    providers: Union[Dict[str, Any], List[Any], str] = "unknown"
    models: Union[Dict[str, Any], List[str], str] = "unknown"
    versions: Union[Dict[str, Any], str] = "unknown"
    settings: Union[Dict[str, Any], str] = Field(default_factory=lambda: "unknown")
    seed: Union[int, str] = "unknown"
    timings: Union[Dict[str, Any], str] = Field(
        default_factory=lambda: {
            "started_at": "unknown",
            "completed_at": "unknown",
            "duration_ms": "unknown",
        }
    )
    cost_estimate: Union[float, str] = "unknown"
    warnings: List[str] = Field(default_factory=list)
    licence_rights: str = "unknown"
    ai_generated: Union[bool, str] = "unknown"


def build_output_manifest(
    providers: Optional[Union[Dict[str, Any], List[Any], str]] = None,
    models: Optional[Union[Dict[str, Any], List[str], str]] = None,
    versions: Optional[Union[Dict[str, Any], str]] = None,
    settings: Optional[Dict[str, Any]] = None,
    seed: Optional[Union[int, str]] = None,
    timings: Optional[Dict[str, Any]] = None,
    cost_estimate: Optional[Union[float, str]] = None,
    warnings: Optional[List[str]] = None,
    licence_rights: Optional[str] = None,
    ai_generated: Optional[Union[bool, str]] = None,
) -> Dict[str, Any]:
    """Builds and serializes a compliant OutputManifest with 'unknown' defaults."""
    manifest = OutputManifest(
        providers=providers if providers is not None else "unknown",
        models=models if models is not None else "unknown",
        versions=versions if versions is not None else "unknown",
        settings=settings if settings is not None else "unknown",
        seed=seed if seed is not None else "unknown",
        timings=timings if timings is not None else {
            "started_at": "unknown",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": "unknown",
        },
        cost_estimate=cost_estimate if cost_estimate is not None else "unknown",
        warnings=warnings if warnings is not None else [],
        licence_rights=licence_rights if licence_rights is not None else "unknown",
        ai_generated=ai_generated if ai_generated is not None else "unknown",
    )
    return manifest.model_dump()
