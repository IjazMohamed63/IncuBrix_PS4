import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from pydantic import BaseModel

app = FastAPI(
    title="IncuBrix Mock Platforms Service",
    description="High-fidelity simulation server for Discourse, Dev.to, Lemmy, Ghost, and Signed Webhook partner.",
    version="1.0.0",
)

# In-memory stores for simulated state
posts_store: Dict[str, Dict[str, Any]] = {}
scenarios: Dict[str, Any] = {}

DEFAULT_WEBHOOK_SECRET = "test_webhook_secret_key_12345"


@app.get("/health")
async def health():
    return {"status": "pass", "service": "mock-platforms"}


# --- Simulation Scenario Controls ---

@app.post("/scenarios/{platform}")
async def set_scenario(platform: str, config: Dict[str, Any]):
    """Allows test suites to script platform behaviors (e.g. 429, 401, timeout, renamed field)."""
    scenarios[platform] = config
    return {"status": "configured", "platform": platform, "scenario": config}


@app.delete("/scenarios/{platform}")
async def clear_scenario(platform: str):
    scenarios.pop(platform, None)
    return {"status": "cleared", "platform": platform}


def check_scenario_errors(platform: str):
    """Checks and triggers scripted scenarios (401, 403, 422, 429, 503, timeout-before, unsupported-media)."""
    scenario = scenarios.get(platform, {})
    if scenario.get("timeout_before"):
        raise HTTPException(status_code=504, detail="Upstream gateway timeout before processing")

    if scenario.get("unsupported_media"):
        raise HTTPException(status_code=415, detail="Unsupported media format or MIME type")

    status = scenario.get("status_code")
    if status == 429:
        retry_after = scenario.get("retry_after", 30)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
    if status == 401:
        raise HTTPException(status_code=401, detail="Authentication token expired or invalid")
    if status == 403:
        raise HTTPException(status_code=403, detail="Forbidden / permission revoked")
    if status == 422:
        raise HTTPException(
            status_code=422,
            detail=scenario.get("error_message", "Content rejected by community moderation rules"),
        )
    if status and status >= 500:
        raise HTTPException(status_code=status, detail="Platform upstream service unavailable")


# --- Mock Discourse REST API ---

@app.post("/discourse/posts.json")
async def discourse_create_post(
    request: Request,
    api_key: Optional[str] = Header(None, alias="Api-Key"),
    api_username: Optional[str] = Header(None, alias="Api-Username"),
):
    check_scenario_errors("discourse")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing Api-Key header")

    data = await request.json()
    post_id = len(posts_store) + 1
    topic_id = data.get("topic_id", 100 + post_id)
    post_record = {
        "id": post_id,
        "name": api_username or "system",
        "username": api_username or "system",
        "raw": data.get("raw", ""),
        "topic_id": topic_id,
        "post_number": 1,
        "deleted": False,
    }

    scenario = scenarios.get("discourse", {})
    if scenario.get("rename_id_field"):
        post_record["discourse_post_identifier"] = post_record.pop("id")

    posts_store[f"discourse_{post_id}"] = post_record

    # Scenario: timeout after accept (record created on platform, but connection dropped/timed out)
    if scenario.get("timeout_after_accept"):
        raise HTTPException(status_code=504, detail="Gateway timeout after post accepted by platform")

    return post_record


@app.get("/discourse/posts/{post_id}.json")
async def discourse_get_post(post_id: int):
    check_scenario_errors("discourse")
    record = posts_store.get(f"discourse_{post_id}")
    if not record or record.get("deleted"):
        raise HTTPException(status_code=404, detail="Post not found")
    return record


@app.delete("/discourse/posts/{post_id}.json")
async def discourse_delete_post(post_id: int):
    scenario = scenarios.get("discourse", {})
    if scenario.get("delete_failure"):
        raise HTTPException(status_code=500, detail="Simulated platform delete failure")
    check_scenario_errors("discourse")
    record = posts_store.get(f"discourse_{post_id}")
    if not record:
        raise HTTPException(status_code=404, detail="Post not found")
    record["deleted"] = True
    return {"success": "OK"}



# --- Mock Lemmy HTTP API v3 ---

@app.post("/lemmy/api/v3/post")
async def lemmy_create_post(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    check_scenario_errors("lemmy")
    data = await request.json()
    token = data.get("auth") or (authorization.replace("Bearer ", "") if authorization else None)
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token for Lemmy")

    post_id = len(posts_store) + 200
    post_record = {
        "id": post_id,
        "name": data.get("name", ""),
        "body": data.get("body", ""),
        "community_id": data.get("community_id", 1),
        "creator_id": 1,
        "deleted": False,
        "removed": False,
        "ap_id": f"http://mock.lemmy/post/{post_id}",
    }
    posts_store[f"lemmy_{post_id}"] = post_record
    return {"post_view": {"post": post_record}}


@app.get("/lemmy/api/v3/post")
async def lemmy_get_post(id: int = Query(...)):
    check_scenario_errors("lemmy")
    record = posts_store.get(f"lemmy_{id}")
    if not record:
        raise HTTPException(status_code=404, detail="Post not found")
    return {"post_view": {"post": record}}


@app.post("/lemmy/api/v3/post/delete")
async def lemmy_delete_post(request: Request):
    check_scenario_errors("lemmy")
    data = await request.json()
    post_id = data.get("post_id")
    record = posts_store.get(f"lemmy_{post_id}")
    if not record:
        raise HTTPException(status_code=404, detail="Post not found")
    record["deleted"] = data.get("deleted", True)
    return {"post_view": {"post": record}}


# --- Mock Dev.to / Forem API ---

@app.post("/devto/api/articles")
async def devto_create_article(
    request: Request,
    api_key: Optional[str] = Header(None, alias="api-key"),
):
    check_scenario_errors("devto")
    if not api_key:
        raise HTTPException(status_code=401, detail="Unauthorized: missing api-key")

    data = await request.json()
    article = data.get("article", {})
    art_id = len(posts_store) + 1000

    record = {
        "id": art_id,
        "title": article.get("title", "Untitled"),
        "body_markdown": article.get("body_markdown", ""),
        "published": article.get("published", False),
        "url": f"http://mock.devto/articles/{art_id}",
        "tags": article.get("tags", []),
        "deleted": False,
    }
    posts_store[f"devto_{art_id}"] = record
    return record


@app.get("/devto/api/articles/{article_id}")
async def devto_get_article(article_id: int):
    check_scenario_errors("devto")
    record = posts_store.get(f"devto_{article_id}")
    if not record or record.get("deleted"):
        raise HTTPException(status_code=404, detail="Article not found")
    return record


@app.delete("/devto/api/articles/{article_id}")
async def devto_delete_article(article_id: int):
    check_scenario_errors("devto")
    record = posts_store.get(f"devto_{article_id}")
    if not record:
        raise HTTPException(status_code=404, detail="Article not found")
    record["deleted"] = True
    return Response(status_code=204)


# --- Mock Ghost Admin API ---

@app.post("/ghost/api/admin/posts/")
@app.post("/ghost/api/admin/posts")
async def ghost_create_post(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    check_scenario_errors("ghost")
    if not authorization or not authorization.startswith("Ghost "):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Ghost Admin JWT")

    data = await request.json()
    posts_list = data.get("posts", [])
    if not posts_list:
        raise HTTPException(status_code=422, detail="Missing post payload")

    p = posts_list[0]
    post_id = f"ghost_{len(posts_store) + 500}"
    record = {
        "id": post_id,
        "title": p.get("title", "Untitled"),
        "html": p.get("html", ""),
        "status": p.get("status", "published"),
        "url": f"http://mock.ghost/posts/{post_id}",
        "deleted": False,
    }
    posts_store[post_id] = record
    return {"posts": [record]}


@app.get("/ghost/api/admin/posts/{post_id}/")
@app.get("/ghost/api/admin/posts/{post_id}")
async def ghost_get_post(post_id: str):
    check_scenario_errors("ghost")
    record = posts_store.get(post_id)
    if not record or record.get("deleted"):
        raise HTTPException(status_code=404, detail="Post not found")
    return {"posts": [record]}


@app.delete("/ghost/api/admin/posts/{post_id}/")
@app.delete("/ghost/api/admin/posts/{post_id}")
async def ghost_delete_post(post_id: str):
    check_scenario_errors("ghost")
    record = posts_store.get(post_id)
    if not record:
        raise HTTPException(status_code=404, detail="Post not found")
    record["deleted"] = True
    return Response(status_code=204)


# --- Mock Partner Signed Webhook Receiver ---

@app.post("/partner/webhook")
async def partner_webhook(
    request: Request,
    signature_header: Optional[str] = Header(None, alias="X-IncuBrix-Signature"),
    timestamp_header: Optional[str] = Header(None, alias="X-IncuBrix-Timestamp"),
):
    check_scenario_errors("signed_webhook")
    raw_body = await request.body()
    body_str = raw_body.decode("utf-8")

    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing X-IncuBrix-Signature header")

    # Signature format: t=<timestamp>,v1=<signature>
    timestamp = timestamp_header
    v1_sig = None
    for part in signature_header.split(","):
        if part.startswith("t="):
            timestamp = part[2:]
        elif part.startswith("v1="):
            v1_sig = part[3:]

    if not timestamp or not v1_sig:
        raise HTTPException(status_code=401, detail="Malformed X-IncuBrix-Signature header")

    # Replay protection: check timestamp is within 300 seconds
    try:
        ts_val = float(timestamp)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format")

    now = time.time()
    if abs(now - ts_val) > 300:
        raise HTTPException(status_code=400, detail="Replay protection triggered: timestamp expired")

    # Compute expected HMAC-SHA256 signature
    scenario = scenarios.get("signed_webhook", {})
    secret = scenario.get("secret", DEFAULT_WEBHOOK_SECRET)
    payload_to_sign = f"{timestamp}.{body_str}"
    expected_sig = hmac.new(secret.encode("utf-8"), payload_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(v1_sig, expected_sig):
        raise HTTPException(status_code=401, detail="HMAC signature verification failed")

    delivery_id = f"wh_{int(ts_val)}_{len(posts_store) + 1}"
    record = {
        "delivery_id": delivery_id,
        "status": "delivered",
        "timestamp": timestamp,
        "bytes_received": len(raw_body),
        "signature_verified": True,
        "deleted": False,
    }
    posts_store[delivery_id] = record

    return {
        "delivery_id": delivery_id,
        "status": "delivered",
        "live_url": f"http://mock.partner/deliveries/{delivery_id}",
    }


@app.get("/partner/webhook/deliveries/{delivery_id}")
async def partner_get_delivery(delivery_id: str):
    check_scenario_errors("signed_webhook")
    record = posts_store.get(delivery_id)
    if not record or record.get("deleted"):
        raise HTTPException(status_code=404, detail="Webhook delivery not found")
    return {
        "delivery_id": delivery_id,
        "status": record["status"],
        "live_url": f"http://mock.partner/deliveries/{delivery_id}",
    }


@app.delete("/partner/webhook/deliveries/{delivery_id}")
async def partner_delete_delivery(delivery_id: str):
    check_scenario_errors("signed_webhook")
    record = posts_store.get(delivery_id)
    if not record:
        raise HTTPException(status_code=404, detail="Webhook delivery not found")
    record["deleted"] = True
    return {"deleted": True, "delivery_id": delivery_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mock_platforms.main:app", host="0.0.0.0", port=8080)
