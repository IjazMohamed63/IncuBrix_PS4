from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- Manifest Enums & Schemas ---

class ConnectorTier(str, Enum):
    NATIVE = "native"
    PROTOCOL = "protocol"
    BRIDGE = "bridge"
    FEED = "feed"
    ASSISTED = "assisted"


class ConnectorAuthType(str, Enum):
    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    BOT_TOKEN = "bot_token"
    NONE = "none"


class SurfaceSpec(BaseModel):
    title_max_chars: Optional[int] = None
    body_max_chars: Optional[int] = None
    links_allowed: bool = True


class Surface(BaseModel):
    key: str
    content_types: List[str]
    spec: SurfaceSpec


class RateLimitPerConnection(BaseModel):
    requests: int
    per_seconds: int


class RateLimits(BaseModel):
    per_connection: RateLimitPerConnection


class ConnectorManifest(BaseModel):
    key: str
    version: str
    tier: ConnectorTier
    auth: ConnectorAuthType
    surfaces: List[Surface]
    rate_limits: RateLimits
    capabilities: List[str]
    error_map: Dict[str, str] = Field(default_factory=dict)
    instance_param: Optional[str] = None


# --- Method Payloads ---

class MediaItem(BaseModel):
    url: str
    media_type: str  # image/png, video/mp4, etc.
    size_bytes: Optional[int] = None
    alt_text: Optional[str] = None


class Rendition(BaseModel):
    title: str
    body: str
    canonical_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    media: List[MediaItem] = Field(default_factory=list)
    ai_disclosure: Optional[str] = None
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class DestinationPayload(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    platform_key: Optional[str] = None
    surface: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ConnectionPayload(BaseModel):
    auth_type: str = "none"
    api_key: Optional[str] = None
    token: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    base_url: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


# --- Method Request / Response Contracts ---

class ValidateRequest(BaseModel):
    rendition: Rendition
    destination: DestinationPayload
    connection: ConnectionPayload


class ValidateResponse(BaseModel):
    ok: bool
    violations: List[str] = Field(default_factory=list)


class PublishRequest(BaseModel):
    rendition: Rendition
    destination: DestinationPayload
    connection: ConnectionPayload
    idempotency_key: str


class PublishResponse(BaseModel):
    platform_post_id: str
    live_url: str
    status: str


class GetStatusRequest(BaseModel):
    platform_post_id: str
    connection: ConnectionPayload


class GetStatusResponse(BaseModel):
    status: str
    live_url: str


class DeleteRequest(BaseModel):
    platform_post_id: str
    connection: ConnectionPayload


class DeleteResponse(BaseModel):
    deleted: bool


class FetchMetricsRequest(BaseModel):
    platform_post_id: str
    connection: ConnectionPayload
    since: Optional[str] = None


class FetchMetricsResponse(BaseModel):
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    watch_time_s: Optional[int] = None
    clicks: Optional[int] = None


class RefreshAuthRequest(BaseModel):
    connection: ConnectionPayload


class RefreshAuthResponse(BaseModel):
    expires_at: str


class BuildAssistPackRequest(BaseModel):
    rendition: Rendition
    destination: DestinationPayload


class ChecklistItem(BaseModel):
    id: str
    label: str
    required: bool = True


class BuildAssistPackResponse(BaseModel):
    files: List[str] = Field(default_factory=list)
    caption: str
    deep_link: str
    checklist: List[ChecklistItem] = Field(default_factory=list)
