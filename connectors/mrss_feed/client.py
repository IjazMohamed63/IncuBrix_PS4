from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, Optional
import xml.etree.ElementTree as ET

from connectors.base import BaseConnector
from connectors.schemas import (
    ConnectionPayload,
    ConnectorManifest,
    DeleteResponse,
    DestinationPayload,
    GetStatusResponse,
    PublishResponse,
    Rendition,
    ValidateResponse,
)
from core.errors import DestinationSpecViolationError, ErrorCode, IncuBrixError

# In-memory store for generated feed items
_mrss_feed_items: Dict[str, Dict[str, Any]] = {}


class MRSSFeedConnector(BaseConnector):
    """Media RSS 2.0 XML feed generator and syndication connector."""

    def __init__(self, manifest: ConnectorManifest, http_client: Optional[Any] = None):
        super().__init__(manifest)

    async def validate(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
    ) -> ValidateResponse:
        violations = []
        spec = self.manifest.surfaces[0].spec

        if not rendition.title:
            violations.append("title: MRSS feed item requires a title.")

        if not rendition.body:
            violations.append("body: MRSS feed item requires description / body text.")

        if rendition.media:
            for item in rendition.media:
                if item.media_type not in spec.allowed_media_types:
                    violations.append(f"media: Unsupported media type '{item.media_type}' for MRSS syndication.")

        return ValidateResponse(ok=len(violations) == 0, violations=violations)

    async def publish(
        self,
        rendition: Rendition,
        destination: DestinationPayload,
        connection: ConnectionPayload,
        idempotency_key: str,
    ) -> PublishResponse:
        guid = f"urn:uuid:{hashlib.sha256(idempotency_key.encode('utf-8')).hexdigest()[:16]}"
        pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

        # Build XML element
        item_el = ET.Element("item")
        title_el = ET.SubElement(item_el, "title")
        title_el.text = rendition.title

        desc_el = ET.SubElement(item_el, "description")
        desc_el.text = rendition.body

        guid_el = ET.SubElement(item_el, "guid", isPermaLink="false")
        guid_el.text = guid

        pub_date_el = ET.SubElement(item_el, "pubDate")
        pub_date_el.text = pub_date

        if rendition.canonical_url:
            link_el = ET.SubElement(item_el, "link")
            link_el.text = rendition.canonical_url

        if rendition.media:
            for m in rendition.media:
                media_el = ET.SubElement(
                    item_el,
                    "enclosure",
                    url=m.url,
                    type=m.media_type,
                    length="1048576",
                )

        xml_string = ET.tostring(item_el, encoding="utf-8").decode("utf-8")

        _mrss_feed_items[guid] = {
            "guid": guid,
            "title": rendition.title,
            "xml": xml_string,
            "pub_date": pub_date,
        }

        live_url = f"{destination.url or 'https://syndication.incubrix.com/feeds/rss.xml'}#{guid}"

        return PublishResponse(
            platform_post_id=guid,
            live_url=live_url,
            status="published",
        )

    async def get_status(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> GetStatusResponse:
        item = _mrss_feed_items.get(platform_post_id)
        if not item:
            return GetStatusResponse(status="not_found")
        return GetStatusResponse(status="active", live_url=f"https://syndication.incubrix.com/feeds/rss.xml#{platform_post_id}")

    async def delete(
        self,
        platform_post_id: str,
        connection: ConnectionPayload,
    ) -> DeleteResponse:
        _mrss_feed_items.pop(platform_post_id, None)
        return DeleteResponse(deleted=True, details={"guid": platform_post_id})
