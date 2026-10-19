from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.routers.destinations import _catalogue_store
from connectors.schemas import DestinationPayload, Rendition
from core.errors import ErrorCode, IncuBrixError
from engine.rules_engine import PostingRulesEngine, RuleDecision, audit_store
from engine.tailoring import tailoring_engine

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])
rules_engine = PostingRulesEngine()


class RuleEvaluateRequest(BaseModel):
    destination_id: str
    rendition: Rendition


class TailorPreviewRequest(BaseModel):
    destination_id: str
    rendition: Rendition


@router.get("/audits", status_code=status.HTTP_200_OK)
async def list_rule_audits(destination_id: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """Lists pre-flight rule decisions and audit records."""
    audits = audit_store.list_audits(destination_id)
    return [
        {
            "id": a.id,
            "destination_id": a.destination_id,
            "decision": a.decision.value if hasattr(a.decision, "value") else str(a.decision),
            "rule_violated": a.rule_violated,
            "reason": a.reason,
            "next_allowed_at": a.next_allowed_at.isoformat() if a.next_allowed_at else None,
            "human_action_required": a.human_action_required,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        }
        for a in audits
    ]


@router.post("/evaluate", status_code=status.HTTP_200_OK)
async def evaluate_rules(req: RuleEvaluateRequest) -> Dict[str, Any]:
    """Pre-flight posting rules evaluation without executing publication."""
    dest_data = _catalogue_store.get(req.destination_id)
    if not dest_data:
        raise IncuBrixError(
            code=ErrorCode.NOT_FOUND,
            message=f"Destination '{req.destination_id}' not found in catalogue.",
            status_code=404,
        )

    destination = DestinationPayload(
        id=dest_data["id"],
        name=dest_data["name"],
        url=dest_data["url"],
        platform_key=dest_data["platform_key"],
        surface=dest_data.get("surface", "default"),
        parameters=dest_data.get("parameters", {}),
    )

    decision = rules_engine.evaluate(rendition=req.rendition, destination=destination)

    return {
        "action": decision.action.value,
        "rule": decision.rule,
        "reason": decision.reason,
        "retry_at": decision.retry_at.isoformat() if decision.retry_at else None,
        "required_human_action": decision.required_human_action,
        "warnings": decision.warnings,
    }


@router.post("/tailor", status_code=status.HTTP_200_OK)
async def tailor_rendition_preview(req: TailorPreviewRequest) -> Dict[str, Any]:
    """Generates tailored rendition adapted to destination rules, AI disclosure, and surface limits."""
    dest_data = _catalogue_store.get(req.destination_id)
    if not dest_data:
        raise IncuBrixError(
            code=ErrorCode.NOT_FOUND,
            message=f"Destination '{req.destination_id}' not found in catalogue.",
            status_code=404,
        )

    destination = DestinationPayload(
        id=dest_data["id"],
        name=dest_data["name"],
        url=dest_data["url"],
        platform_key=dest_data["platform_key"],
        surface=dest_data.get("surface", "default"),
        parameters=dest_data.get("parameters", {}),
    )

    tailored = tailoring_engine.tailor(rendition=req.rendition, destination=destination)

    # Calculate modifications
    modifications = []
    if tailored.ai_disclosure and not req.rendition.ai_disclosure:
        modifications.append("Appended mandatory AI disclosure tag")
    if tailored.canonical_url and not req.rendition.canonical_url:
        modifications.append(f"Set canonical URL to destination ({destination.url})")
    if len(tailored.title) < len(req.rendition.title):
        modifications.append(f"Truncated title to {len(tailored.title)} chars at word boundary")
    if len(tailored.body) != len(req.rendition.body):
        if len(tailored.body) < len(req.rendition.body):
            modifications.append(f"Truncated body to {len(tailored.body)} chars at word boundary")
        else:
            modifications.append("Adapted body with community discussion prompt")
    if tailored.tags != req.rendition.tags:
        modifications.append("Adapted hashtags to destination case/limit specifications")

    return {
        "destination_id": req.destination_id,
        "tailored_rendition": tailored.model_dump(),
        "modifications": modifications,
    }


@router.get("/policies", status_code=status.HTTP_200_OK)
async def list_policies() -> List[Dict[str, Any]]:
    """Returns the comprehensive active pre-flight rule policies."""
    return [
        {
            "id": "frequency_cap",
            "name": "Frequency Cap",
            "description": "Enforces minimum cool-off interval between publications per destination.",
            "enforcement": "Reschedules with exact next allowed timestamp (HTTP 202).",
            "default": "24 hours",
        },
        {
            "id": "self_promo",
            "name": "Self-Promotion Policy",
            "description": "Prohibits commercial sales pitches, discount codes, or promotional keywords.",
            "enforcement": "Blocks post before connector invocation with required human rewrite.",
            "default": "Strict keyword and flag inspection",
        },
        {
            "id": "link_policy",
            "name": "Link Policy & Whitelisting",
            "description": "Restricts external URLs according to destination policy ('none', 'whitelist', 'allowed').",
            "enforcement": "Blocks post if unauthorized external domains are present.",
            "default": "Allowed with domain verification",
        },
        {
            "id": "ai_disclosure",
            "name": "Mandatory AI Disclosure",
            "description": "Requires explicit disclosure statement on AI-assisted or generated content.",
            "enforcement": "Blocks unlabelled posts or automatically injects compliance disclaimer.",
            "default": "Required where specified by platform policy",
        },
        {
            "id": "format_limits",
            "name": "Format Limits & Character Caps",
            "description": "Validates title and body length limits and media file size/type constraints.",
            "enforcement": "Truncates at word boundary or blocks with field-level violation report.",
            "default": "Per-surface character boundaries",
        },
        {
            "id": "automation_permission",
            "name": "Automation Permission",
            "description": "Ensures bot posting is permitted; directs non-automated destinations to Assisted posting workflow.",
            "enforcement": "Diverts to BuildAssistPack with downloadable asset bundle.",
            "default": "Assisted pack required for manual surfaces",
        },
        {
            "id": "connector_eligibility",
            "name": "Kill-Switch & Connector Eligibility",
            "description": "Verifies connector is not disabled by operator kill-switch or emergency maintenance.",
            "enforcement": "Blocks publication with 503 Service Unavailable alert.",
            "default": "Active monitoring",
        },
        {
            "id": "certification_eligibility",
            "name": "Certification Level Eligibility",
            "description": "Blocks destinations demoted to L0 until automated 8-step recertification passes.",
            "enforcement": "Prevents live dispatch to degraded or broken destination integrations.",
            "default": "L1+ required for active publishing",
        },
    ]
