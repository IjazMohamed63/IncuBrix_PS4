import re
from typing import List, Optional, Tuple
from connectors.base import BaseConnector
from connectors.schemas import ConnectionPayload, DestinationPayload, Rendition, ValidateResponse
from core.logging import get_logger

logger = get_logger("tailoring_engine")

DEFAULT_AI_DISCLOSURE = "AI Disclosure: Content researched and drafted with AI assistance."


class ContentTailoringEngine:
    """Adapts content renditions to destination community rules, AI disclosure mandates,
    surface types, and format limits with post-tailoring contract re-validation.
    """

    def tailor(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
    ) -> Rendition:
        tailored = rendition.model_copy(deep=True)
        surface = (destination.surface or "default").lower()

        # 1. Enforce Mandatory AI Disclosure (HC14)
        disclosure_required = destination.parameters.get("disclosure_required", False)
        if disclosure_required:
            tailored.ai_disclosure = DEFAULT_AI_DISCLOSURE
            if DEFAULT_AI_DISCLOSURE not in tailored.body:
                tailored.body = f"{tailored.body}\n\n[{DEFAULT_AI_DISCLOSURE}]"

        # 2. Canonical URL Tagging for Articles
        if surface in ("article", "blog", "publication") or destination.parameters.get("require_canonical_url"):
            if not tailored.canonical_url and destination.url:
                tailored.canonical_url = destination.url

        # 3. Discussion-First Tailoring for Forums
        if surface in ("forum", "discussion", "community"):
            tailored.body = self._adapt_discussion_first(tailored.body, tailored.title)

        # 4. Hashtag Style Adaptation
        hashtag_style = destination.parameters.get("hashtag_style", "default").lower()
        max_hashtags = destination.parameters.get("max_hashtags")
        tailored.tags = self._adapt_hashtags(tailored.tags, hashtag_style, max_hashtags)

        # 5. Non-English Handling: Preserve Multilingual Unicode text as-is without stripping
        # Ensure UTF-8 normalization (NFKC) while preserving Arabic, Hindi, CJK, etc.
        import unicodedata
        tailored.title = unicodedata.normalize("NFKC", tailored.title)
        tailored.body = unicodedata.normalize("NFKC", tailored.body)

        # 6. Word-Boundary Truncation for Titles
        title_limit = destination.parameters.get("title_max_chars")
        if title_limit and len(tailored.title) > title_limit:
            tailored.title = self._truncate_at_word_boundary(tailored.title, title_limit)

        # 7. Word-Boundary Truncation for Bodies
        body_limit = destination.parameters.get("body_max_chars")
        if body_limit and len(tailored.body) > body_limit:
            tailored.body = self._truncate_at_word_boundary(tailored.body, body_limit)

        return tailored

    async def tailor_and_validate(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
        connector: BaseConnector,
    ) -> Tuple[Rendition, ValidateResponse]:
        """Tailors rendition and executes re-validation against connector specification."""
        tailored = self.tailor(rendition, destination)
        val_res = await connector.validate(tailored, destination, connection)
        logger.info(f"Tailored rendition validated against '{destination.platform_key}': ok={val_res.ok}")
        return tailored, val_res

    def _adapt_discussion_first(self, body: str, title: str) -> str:
        """Adapts content for community forums by framing it as a discussion prompt."""
        discussion_prompt = "\n\n---\n**Discussion:** How are you approaching this in your architecture? Would love to hear your thoughts and experiences below!"
        if "discussion:" not in body.lower() and "what are your thoughts" not in body.lower():
            return f"{body.strip()}{discussion_prompt}"
        return body

    def _adapt_hashtags(self, tags: List[str], style: str, max_tags: Optional[int]) -> List[str]:
        """Adapts hashtag styling and limits."""
        if not tags:
            return []

        adapted = list(tags)
        if style == "none":
            return []
        if style == "camelcase":
            adapted = ["".join(word.capitalize() for word in re.split(r'[-_\s]+', t)) for t in adapted]
        elif style == "lowercase":
            adapted = [t.lower().replace(" ", "") for t in adapted]

        if max_tags is not None and len(adapted) > max_tags:
            adapted = adapted[:max_tags]

        return adapted

    def _truncate_at_word_boundary(self, text: str, max_chars: int) -> str:
        """Truncates string at nearest word boundary without slicing mid-word."""
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars - 3]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        return f"{truncated}..."


tailoring_engine = ContentTailoringEngine()
