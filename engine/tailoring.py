import re
from typing import Optional
from connectors.schemas import DestinationPayload, Rendition

DEFAULT_AI_DISCLOSURE = "AI Disclosure: Content researched and drafted with AI assistance."


class ContentTailoringEngine:
    """Adapts content renditions to destination community rules, AI disclosure mandates, and format limits."""

    def tailor(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
    ) -> Rendition:
        tailored = rendition.model_copy(deep=True)

        # 1. Enforce Mandatory AI Disclosure (HC14)
        disclosure_required = destination.parameters.get("disclosure_required", False)
        if disclosure_required and not tailored.ai_disclosure:
            tailored.ai_disclosure = DEFAULT_AI_DISCLOSURE
            # Append to body if not already present in body
            if DEFAULT_AI_DISCLOSURE not in tailored.body:
                tailored.body = f"{tailored.body}\n\n[{DEFAULT_AI_DISCLOSURE}]"

        # 2. Canonical URL Tagging for Articles
        if not tailored.canonical_url and destination.parameters.get("require_canonical_url"):
            tailored.canonical_url = destination.url

        # 3. Word-Boundary Truncation for Titles
        title_limit = destination.parameters.get("title_max_chars")
        if title_limit and len(tailored.title) > title_limit:
            tailored.title = self._truncate_at_word_boundary(tailored.title, title_limit)

        # 4. Word-Boundary Truncation for Bodies
        body_limit = destination.parameters.get("body_max_chars")
        if body_limit and len(tailored.body) > body_limit:
            tailored.body = self._truncate_at_word_boundary(tailored.body, body_limit)

        return tailored

    def _truncate_at_word_boundary(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars - 3]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        return f"{truncated}..."


tailoring_engine = ContentTailoringEngine()
