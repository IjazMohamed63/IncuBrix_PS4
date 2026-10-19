from abc import ABC, abstractmethod
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from core.logging import get_logger

logger = get_logger("rule_capture")


class ProposedRules(BaseModel):
    frequency_cap: int = 24
    self_promo_allowed: bool = True
    link_policy: str = "allowed"  # allowed, none, whitelist
    disclosure_required: bool = False
    automation_allowed: bool = True
    title_max_chars: Optional[int] = None
    body_max_chars: Optional[int] = None
    rationale: Dict[str, str] = Field(default_factory=dict)
    confidence_score: float = 0.95


class RuleProposalRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"prop_{uuid.uuid4().hex[:10]}")
    destination_id: str
    status: str = "pending_confirmation"  # pending_confirmation, activated, rejected
    rules_source_url: Optional[str] = None
    proposed_rules: ProposedRules
    proposed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None


class RuleCaptureAdapter(ABC):
    """Abstract interface for AI rule extraction adapters."""

    @abstractmethod
    async def extract_rules(self, rules_text: str, rules_url: Optional[str] = None) -> ProposedRules:
        raise NotImplementedError


class MockRuleCaptureAdapter(RuleCaptureAdapter):
    """Default deterministic rule extraction adapter analyzing community guidelines."""

    async def extract_rules(self, rules_text: str, rules_url: Optional[str] = None) -> ProposedRules:
        text = rules_text.lower()
        rationale: Dict[str, str] = {}

        # 1. Frequency Cap
        frequency_cap = 24
        if "once a week" in text or "weekly" in text or "7 days" in text:
            frequency_cap = 168
            rationale["frequency_cap"] = "Detected rule limiting posts to once per week (168h)."
        elif "twice a day" in text:
            frequency_cap = 12
            rationale["frequency_cap"] = "Detected rule permitting posts every 12 hours."
        elif "daily" in text or "once per day" in text or "24 hours" in text:
            frequency_cap = 24
            rationale["frequency_cap"] = "Detected standard once-per-day posting rule (24h)."

        # 2. Self Promotion
        self_promo = True
        if any(term in text for term in ("no self-promotion", "no self promotion", "no commercial ads", "no ads", "no sales pitches")):
            self_promo = False
            rationale["self_promo_allowed"] = "Prohibits self-promotion or advertising."

        # 3. Link Policy
        link_policy = "allowed"
        if "no external links" in text or "no links" in text:
            link_policy = "none"
            rationale["link_policy"] = "Strictly prohibits external hyperlinks (link_policy: none)."
        elif "whitelist" in text or "approved domains only" in text or "trusted links only" in text:
            link_policy = "whitelist"
            rationale["link_policy"] = "Restricts links to approved domain whitelist."

        # 4. AI Disclosure
        disclosure_required = False
        if any(term in text for term in ("disclose ai", "ai disclosure required", "must tag ai", "transparent ai")):
            disclosure_required = True
            rationale["disclosure_required"] = "Mandates explicit AI-generated content disclosure tag."

        # 5. Automation / Bots
        automation_allowed = True
        if any(term in text for term in ("no bots", "no automated posting", "manual posting only", "human only")):
            automation_allowed = False
            rationale["automation_allowed"] = "Community forbids automated bot posting; requires human publication."

        # 6. Formatting limits
        title_limit = None
        match_title = re.search(r'title\s+(?:limit|max|under)\s+(\d+)', text)
        if match_title:
            title_limit = int(match_title.group(1))
            rationale["title_max_chars"] = f"Detected title length ceiling of {title_limit} characters."

        body_limit = None
        match_body = re.search(r'body\s+(?:limit|max|under)\s+(\d+)', text)
        if match_body:
            body_limit = int(match_body.group(1))
            rationale["body_max_chars"] = f"Detected body length ceiling of {body_limit} characters."

        return ProposedRules(
            frequency_cap=frequency_cap,
            self_promo_allowed=self_promo,
            link_policy=link_policy,
            disclosure_required=disclosure_required,
            automation_allowed=automation_allowed,
            title_max_chars=title_limit,
            body_max_chars=body_limit,
            rationale=rationale,
            confidence_score=0.96,
        )


class RuleCaptureManager:
    """Manages AI rule proposal and human confirmation lifecycle."""

    def __init__(self, adapter: Optional[RuleCaptureAdapter] = None):
        self.adapter = adapter or MockRuleCaptureAdapter()
        self._proposals: Dict[str, RuleProposalRecord] = {}

    async def propose_rules(
        self,
        destination_id: str,
        rules_text: str,
        rules_url: Optional[str] = None,
    ) -> RuleProposalRecord:
        """Extracts proposed rules via AI adapter and stores as pending human confirmation."""
        proposed = await self.adapter.extract_rules(rules_text, rules_url)
        record = RuleProposalRecord(
            destination_id=destination_id,
            rules_source_url=rules_url,
            proposed_rules=proposed,
        )
        self._proposals[record.id] = record
        logger.info(f"Rule proposal '{record.id}' generated for destination '{destination_id}' (status: pending_confirmation)")
        return record

    def confirm_rules(
        self,
        proposal_id: str,
        destination_parameters: Dict[str, Any],
        confirmed_by: str = "human_operator",
    ) -> RuleProposalRecord:
        """Human confirmation step: activates proposed rules into destination parameters."""
        record = self._proposals.get(proposal_id)
        if not record:
            raise KeyError(f"Rule proposal '{proposal_id}' not found.")

        # Activate rules on destination
        rules = record.proposed_rules
        destination_parameters["frequency_cap"] = rules.frequency_cap
        destination_parameters["self_promo_allowed"] = rules.self_promo_allowed
        destination_parameters["link_policy"] = rules.link_policy
        destination_parameters["disclosure_required"] = rules.disclosure_required
        destination_parameters["automation_allowed"] = rules.automation_allowed
        if rules.title_max_chars:
            destination_parameters["title_max_chars"] = rules.title_max_chars
        if rules.body_max_chars:
            destination_parameters["body_max_chars"] = rules.body_max_chars

        record.status = "activated"
        record.confirmed_at = datetime.now(timezone.utc)
        record.confirmed_by = confirmed_by
        logger.info(f"Rule proposal '{proposal_id}' confirmed and activated by {confirmed_by}!")
        return record

    def get_proposal(self, proposal_id: str) -> Optional[RuleProposalRecord]:
        return self._proposals.get(proposal_id)


rule_capture_manager = RuleCaptureManager()
