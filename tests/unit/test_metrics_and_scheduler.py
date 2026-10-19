from datetime import datetime, timedelta, timezone
import pytest

from connectors.devto.client import DevtoConnector
from connectors.ghost.client import GhostConnector
from connectors.hashnode.client import HashnodeConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload
from engine.certification_harness import AlertRecord, CertificationHarness, CertificationStore
from engine.recertification_scheduler import RecertificationScheduler


@pytest.mark.asyncio
async def test_fetch_metrics_on_three_connectors_unavailable_is_null_never_zero():
    """Rule: fetch_metrics on 3 connectors (devto, ghost, hashnode); unavailable metrics must be null/None, never 0."""
    devto_conn = DevtoConnector(registry.get_manifest("devto"))
    ghost_conn = GhostConnector(registry.get_manifest("ghost"))
    hashnode_conn = HashnodeConnector(registry.get_manifest("hashnode"))

    conn_payload = ConnectionPayload(api_key="metric_key")

    # 1. Devto metrics
    devto_metrics = await devto_conn.fetch_metrics("article_123", conn_payload)
    assert devto_metrics.views is not None and devto_metrics.views > 0
    # Unavailable fields must be None / null, NEVER 0!
    assert devto_metrics.shares is None, "Unavailable metric 'shares' must be None (null in JSON), never 0"
    assert devto_metrics.saves is None, "Unavailable metric 'saves' must be None (null in JSON), never 0"
    assert devto_metrics.watch_time_s is None
    assert devto_metrics.shares != 0
    assert devto_metrics.saves != 0

    # 2. Ghost metrics
    ghost_metrics = await ghost_conn.fetch_metrics("ghost_post_456", conn_payload)
    assert ghost_metrics.views is not None and ghost_metrics.views > 0
    assert ghost_metrics.likes is None, "Unavailable metric 'likes' must be None (null), never 0"
    assert ghost_metrics.comments is None, "Unavailable metric 'comments' must be None (null), never 0"
    assert ghost_metrics.shares is None
    assert ghost_metrics.likes != 0

    # 3. Hashnode metrics
    hashnode_metrics = await hashnode_conn.fetch_metrics("hn_post_789", conn_payload)
    assert hashnode_metrics.views is not None and hashnode_metrics.views > 0
    assert hashnode_metrics.likes is not None and hashnode_metrics.likes > 0
    assert hashnode_metrics.shares is None, "Unavailable metric 'shares' must be None (null), never 0"
    assert hashnode_metrics.saves is None
    assert hashnode_metrics.shares != 0


@pytest.mark.asyncio
async def test_thirty_day_recertification_scheduler_demotes_and_alerts():
    """Rule: 30-day recertification scheduler triggers recertification; failing probe demotes to L0 and generates an alert."""
    store = CertificationStore()
    harness = CertificationHarness(store=store)
    scheduler = RecertificationScheduler(harness=harness)

    now = datetime.now(timezone.utc)
    # Destination certified 35 days ago (lapsed beyond 30 days)
    old_cert_date = (now - timedelta(days=35)).isoformat()

    destinations = [
        {
            "id": "dest_lapsed_35d",
            "name": "Lapsed Destination",
            "platform_key": "discourse",
            "level": "L2",
            "last_certified_at": old_cert_date,
            "parameters": {"base_url": "http://test/discourse", "category_id": 1},
            "connection": {"base_url": "http://test/discourse", "api_key": "valid_key"},
        },
        {
            "id": "dest_fresh_5d",
            "name": "Fresh Destination",
            "platform_key": "discourse",
            "level": "L2",
            "last_certified_at": (now - timedelta(days=5)).isoformat(),
            "parameters": {"base_url": "http://test/discourse"},
        },
    ]

    report = await scheduler.scan_and_recertify(destinations, now=now, is_mock=True)

    # Assert only the 35-day old destination was inspected
    assert report["inspected"] == 1
    # Fresh 5-day destination was untouched
    assert destinations[1]["level"] == "L2"
    # Lapsed destination was recertified
    assert report["passed"] + report["failed"] == 1

    # Verify that a failing destination gets demoted to L0 and alert raised
    failing_destination = [
        {
            "id": "dest_failing_recert",
            "name": "Failing Destination",
            "platform_key": "discourse",
            "level": "L2",
            "last_certified_at": old_cert_date,
            "parameters": {"base_url": "http://invalid-dead-host.internal"},
            "connection": {"auth_type": "none"},
        }
    ]
    fail_report = await scheduler.scan_and_recertify(failing_destination, now=now, is_mock=True)
    assert fail_report["failed"] == 1
    assert failing_destination[0]["level"] == "L0"
    assert failing_destination[0]["parameters"]["excluded_from_publishing"] is True
    assert failing_destination[0]["parameters"]["excluded_from_recommendations"] is True

    # Assert alert was recorded
    alerts = store.list_alerts("dest_failing_recert")
    assert len(alerts) >= 1
    assert alerts[0].severity == "CRITICAL"
