from datetime import datetime, timedelta, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from connectors.registry import registry
from connectors.schemas import DestinationPayload, Rendition
from core.logging import get_logger

logger = get_logger("rules_engine")

URL_REGEX = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
PROMO_KEYWORDS = ["buy now", "discount", "coupon", "limited offer", "sale", "pricing", "sign up now", "affiliate"]


class RuleAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    RESCHEDULE = "reschedule"


class RuleDecision(BaseModel):
    action: RuleAction
    rule: Optional[str] = None
    reason: str
    retry_at: Optional[datetime] = None
    required_human_action: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class RuleAuditRecord(BaseModel):
    id: str
    destination_id: str
    decision: RuleAction
    rule_violated: Optional[str] = None
    reason: str
    next_allowed_at: Optional[datetime] = None
    human_action_required: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RulesAuditStore:
    """In-memory and durable audit repository for posting rule evaluations and publication history."""

    def __init__(self):
        self._audits: List[RuleAuditRecord] = []
        self._publication_history: Dict[str, List[datetime]] = {}  # destination_id -> [timestamps]

    def record_decision(self, record: RuleAuditRecord) -> None:
        self._audits.append(record)

    def record_publication(self, destination_id: str, timestamp: Optional[datetime] = None) -> None:
        ts = timestamp or datetime.now(timezone.utc)
        if destination_id not in self._publication_history:
            self._publication_history[destination_id] = []
        self._publication_history[destination_id].append(ts)

    def get_last_publication_time(self, destination_id: str) -> Optional[datetime]:
        history = self._publication_history.get(destination_id, [])
        return history[-1] if history else None

    def list_audits(self, destination_id: Optional[str] = None) -> List[RuleAuditRecord]:
        if destination_id:
            return [a for a in self._audits if a.destination_id == destination_id]
        return list(self._audits)

    def clear(self) -> None:
        self._audits.clear()
        self._publication_history.clear()


audit_store = RulesAuditStore()


class PostingRulesEngine:
    """Pre-flight posting rules engine executing deterministic compliance evaluation before connector invocation."""

    def __init__(self, store: Optional[RulesAuditStore] = None):
        self.store = store or audit_store

    def evaluate(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        now: Optional[datetime] = None,
    ) -> RuleDecision:
        current_time = now or datetime.now(timezone.utc)
        dest_id = destination.id or "default_dest"
        warnings: List[str] = []

        # 1. Automation Permission Check
        automation_allowed = destination.parameters.get("automation_allowed", True)
        if destination.parameters.get("connector_key") == "assisted" or not automation_allowed:
            if destination.parameters.get("automation_allowed") is False:
                decision = RuleDecision(
                    action=RuleAction.BLOCK,
                    rule="automation_permission",
                    reason="Destination strictly forbids automated bot posting; manual human posting required.",
                    required_human_action="Use assisted posting workflow to download content and publish manually.",
                )
                self._record_audit(dest_id, decision)
                return decision

        # 2. Connector / Certification Eligibility Check
        connector_key = destination.platform_key or destination.parameters.get("connector_key")
        if connector_key and registry.is_disabled(connector_key):
            decision = RuleDecision(
                action=RuleAction.BLOCK,
                rule="connector_eligibility",
                reason=f"Connector '{connector_key}' is disabled via kill-switch.",
                required_human_action="Re-enable connector in registry once platform service is restored.",
            )
            self._record_audit(dest_id, decision)
            return decision

        level = destination.parameters.get("level", "L1")
        if level == "L0":
            decision = RuleDecision(
                action=RuleAction.BLOCK,
                rule="certification_eligibility",
                reason="Destination is at certification level L0 (demoted/uncertified). Publishing is blocked.",
                required_human_action="Run automated recertification before scheduling publications.",
            )
            self._record_audit(dest_id, decision)
            return decision

        # 3. Frequency Cap Check
        frequency_cap_hours = destination.parameters.get("frequency_cap", 24)
        last_pub_time = self.store.get_last_publication_time(dest_id)
        if last_pub_time and frequency_cap_hours > 0:
            window = timedelta(hours=frequency_cap_hours)
            elapsed = current_time - last_pub_time
            if elapsed < window:
                next_allowed = last_pub_time + window
                decision = RuleDecision(
                    action=RuleAction.RESCHEDULE,
                    rule="frequency_cap",
                    reason=f"Destination frequency cap of {frequency_cap_hours}h active. Elapsed: {elapsed.total_seconds()/3600:.1f}h.",
                    retry_at=next_allowed,
                    required_human_action=f"Reschedule post for {next_allowed.isoformat()}.",
                )
                self._record_audit(dest_id, decision)
                return decision

        # 4. Self-Promotion Policy Check
        self_promo_allowed = destination.parameters.get("self_promo_allowed", True)
        is_promo = rendition.custom_fields.get("is_promotional", False)
        # Check text heuristics
        combined_text = f"{rendition.title} {rendition.body}".lower()
        if any(kw in combined_text for kw in PROMO_KEYWORDS):
            is_promo = True

        if not self_promo_allowed and is_promo:
            decision = RuleDecision(
                action=RuleAction.BLOCK,
                rule="self_promo",
                reason="Destination strictly forbids promotional content or links.",
                required_human_action="Remove promotional claims, sales pitches, or commercial links.",
            )
            self._record_audit(dest_id, decision)
            return decision

        # 5. Link Policy Check
        link_policy = destination.parameters.get("link_policy", "allowed").lower()
        extracted_links = URL_REGEX.findall(f"{rendition.title} {rendition.body}")
        if rendition.canonical_url:
            extracted_links.append(rendition.canonical_url)

        if link_policy == "none" and extracted_links:
            decision = RuleDecision(
                action=RuleAction.BLOCK,
                rule="link_policy",
                reason="Destination strictly forbids external links (link_policy: none).",
                required_human_action="Remove all external URLs from post title and body.",
            )
            self._record_audit(dest_id, decision)
            return decision

        if link_policy == "whitelist" and extracted_links:
            allowed_domains = destination.parameters.get("allowed_domains", [])
            for link in extracted_links:
                domain_match = any(d in link for d in allowed_domains)
                if not domain_match:
                    decision = RuleDecision(
                        action=RuleAction.BLOCK,
                        rule="link_policy",
                        reason=f"Link '{link}' violates destination domain whitelist: {allowed_domains}.",
                        required_human_action="Replace link with an approved whitelisted domain.",
                    )
                    self._record_audit(dest_id, decision)
                    return decision

        # 6. AI-Disclosure Requirement Check
        disclosure_required = destination.parameters.get("disclosure_required", False)
        if disclosure_required and not rendition.ai_disclosure:
            decision = RuleDecision(
                action=RuleAction.BLOCK,
                rule="ai_disclosure",
                reason="Destination requires mandatory AI-content disclosure statement.",
                required_human_action="Include a transparent AI disclosure tag in the rendition.",
                warnings=["AI disclosure tag is mandatory for this destination"],
            )
            self._record_audit(dest_id, decision)
            return decision

        # 7. Content Type & Media Compatibility Check
        allowed_media_types = destination.parameters.get("allowed_media_types")
        if allowed_media_types and rendition.media:
            for item in rendition.media:
                if item.media_type not in allowed_media_types:
                    decision = RuleDecision(
                        action=RuleAction.BLOCK,
                        rule="content_type",
                        reason=f"Media type '{item.media_type}' is unsupported by destination (allowed: {allowed_media_types}).",
                        required_human_action=f"Convert media attachment to one of: {allowed_media_types}.",
                    )
                    self._record_audit(dest_id, decision)
                    return decision

        # 8. Format Limits Check (Surface level checks)
        title_max = destination.parameters.get("title_max_chars")
        if title_max and len(rendition.title) > title_max:
            decision = RuleDecision(
                action=RuleAction.BLOCK,
                rule="format_limits",
                reason=f"Title exceeds destination maximum length of {title_max} characters (got {len(rendition.title)}).",
                required_human_action="Shorten title to fit destination character limit.",
            )
            self._record_audit(dest_id, decision)
            return decision

        body_max = destination.parameters.get("body_max_chars")
        if body_max and len(rendition.body) > body_max:
            decision = RuleDecision(
                action=RuleAction.BLOCK,
                rule="format_limits",
                reason=f"Body exceeds destination maximum length of {body_max} characters (got {len(rendition.body)}).",
                required_human_action="Shorten body content to fit destination character limit.",
            )
            self._record_audit(dest_id, decision)
            return decision

        # All rules passed!
        decision = RuleDecision(
            action=RuleAction.ALLOW,
            rule=None,
            reason="All pre-flight posting rules and community policies verified successfully.",
            warnings=warnings,
        )
        self._record_audit(dest_id, decision)
        return decision

    def _record_audit(self, destination_id: str, decision: RuleDecision) -> None:
        import uuid
        audit_rec = RuleAuditRecord(
            id=str(uuid.uuid4()),
            destination_id=destination_id,
            decision=decision.action,
            rule_violated=decision.rule,
            reason=decision.reason,
            next_allowed_at=decision.retry_at,
            human_action_required=decision.required_human_action,
        )
        self.store.record_decision(audit_rec)
        logger.info(
            f"Rule Engine decision for dest '{destination_id}': {decision.action.value.upper()}"
            f" (rule: {decision.rule or 'none'}, reason: {decision.reason})"
        )
