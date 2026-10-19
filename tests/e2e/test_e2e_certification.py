import pytest
from httpx import AsyncClient, ASGITransport

from connectors.discourse.client import DiscourseConnector
from connectors.registry import registry
from connectors.schemas import ConnectionPayload, DestinationPayload
from engine.certification_harness import (
    CertificationHarness,
    CertificationStore,
    certification_harness,
)
from mock_platforms.main import app as mock_platforms_app, posts_store, scenarios


@pytest.fixture
def mock_client():
    transport = ASGITransport(app=mock_platforms_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def clean_state():
    posts_store.clear()
    scenarios.clear()
    yield
    posts_store.clear()
    scenarios.clear()


@pytest.mark.asyncio
async def test_e2e_certification_eight_steps_lifecycle_mock_labelling(mock_client):
    """E2E Test: Full 8-step certification lifecycle in mock mode, verifying mock labelling and watchdog cleanup."""
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest, http_client=mock_client)

    destination = DestinationPayload(
        id="dest_cert_e2e_01",
        name="Discourse Production Forum",
        platform_key="discourse",
        parameters={"base_url": "http://test/discourse", "category_id": 1},
    )
    connection = ConnectionPayload(
        base_url="http://test/discourse",
        api_key="discourse_cert_key_8888",
        extra={"username": "incubrix_probe"},
    )

    # Execute Certification in MOCK mode
    cert_record = await certification_harness.run_certification(
        destination=destination,
        connection=connection,
        connector_override=connector,
        is_mock=True,
    )

    # 1. Assert all 8 steps were executed
    step_names = [s.step_name for s in cert_record.step_results]
    expected_steps = [
        "prerequisites",
        "validate",
        "publish",
        "confirm_live",
        "get_status",
        "delete",
        "store_evidence",
        "set_level",
    ]
    for step in expected_steps:
        assert step in step_names, f"Expected step '{step}' in certification results"

    # 2. Verify all step statuses passed
    for step in cert_record.step_results:
        assert step.status == "passed", f"Step {step.step_name} failed: {step.error}"
        assert step.timestamp_start <= step.timestamp_end

    # 3. Rule: Mock runs are labelled mock and CANNOT grant real-certified level
    assert cert_record.is_mock is True
    assert cert_record.status == "passed"
    assert cert_record.assigned_level == "L1-mock"
    assert cert_record.real_certified is False

    # 4. Verify Evidence S3 / storage URL
    assert cert_record.evidence_s3_url is not None
    assert "files" in cert_record.evidence_s3_url or "http" in cert_record.evidence_s3_url

    # 5. Verify Deletion Watchdog
    watchdogs = certification_harness.store.list_watchdogs()
    assert len(watchdogs) >= 1
    recent_wd = [w for w in watchdogs if w.destination_id == destination.id][0]
    assert recent_wd.is_deleted is True
    assert recent_wd.deleted_at is not None


@pytest.mark.asyncio
async def test_e2e_certification_contract_breakage_demotes_to_l0_and_alerts(mock_client):
    """E2E Test: A renamed API field fails certification, demotes to L0, excludes destination, and preserves prior evidence."""
    manifest = registry.get_manifest("discourse")
    connector = DiscourseConnector(manifest, http_client=mock_client)

    destination = DestinationPayload(
        id="dest_cert_breaking_02",
        name="Contract Breaking Destination",
        platform_key="discourse",
        parameters={"base_url": "http://test/discourse", "category_id": 1, "level": "L2"},
    )
    connection = ConnectionPayload(
        base_url="http://test/discourse",
        api_key="discourse_cert_key_8888",
        extra={"username": "incubrix_probe"},
    )

    # Step A: Perform initial successful mock run to create prior evidence
    first_run = await certification_harness.run_certification(
        destination=destination,
        connection=connection,
        connector_override=connector,
        is_mock=True,
    )
    assert first_run.status == "passed"
    first_evidence_url = first_run.evidence_s3_url
    assert first_evidence_url is not None

    # Step B: Trigger scripted scenario 'rename_id_field' simulating upstream API breaking change
    scenarios["discourse"] = {"rename_id_field": True}

    # Step C: Re-run certification against now broken destination
    second_run = await certification_harness.run_certification(
        destination=destination,
        connection=connection,
        connector_override=connector,
        is_mock=True,
    )

    # 1. Assert certification failed
    assert second_run.status == "failed"
    assert second_run.assigned_level == "L0"
    assert second_run.real_certified is False

    # 2. Destination parameters demoted to L0 and excluded from publishing/recommendations
    assert destination.parameters["level"] == "L0"
    assert destination.parameters["excluded_from_publishing"] is True
    assert destination.parameters["excluded_from_recommendations"] is True

    # 3. Alert record generated
    alerts = certification_harness.store.list_alerts(destination.id)
    assert len(alerts) >= 1
    latest_alert = alerts[-1]
    assert latest_alert.alert_type == "CONTRACT_BREAKAGE"
    assert latest_alert.severity == "CRITICAL"

    # 4. Prior evidence preserved
    assert first_evidence_url in second_run.prior_evidence_preserved
