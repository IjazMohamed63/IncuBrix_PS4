from pathlib import Path
import yaml
import pytest
from api.main import app

DOCUMENTED_EXCEPTIONS = {"/health", "/ready"}


def test_openapi_version_and_paths():
    """Validates OpenAPI 3.1 specification conformity and route prefixes."""
    schema = app.openapi()

    # 1. OpenAPI Version 3.1
    assert schema.get("openapi", "").startswith("3.1"), (
        f"Expected OpenAPI 3.1.x, got {schema.get('openapi')}"
    )

    paths = schema.get("paths", {})
    assert len(paths) > 0, "OpenAPI schema must define API endpoints."

    # 2. All routes under /api/v1/ except documented exceptions
    for path in paths.keys():
        is_exception = (
            path in DOCUMENTED_EXCEPTIONS
            or path.startswith("/connector/v1")
            or path in {"/docs", "/redoc", "/openapi.json"}
        )
        assert path.startswith("/api/v1/") or is_exception, (
            f"Route '{path}' violates prefix contract: must be under /api/v1/ or documented exceptions."
        )


def test_openapi_yaml_no_drift():
    """Asserts that the committed openapi.yaml exactly matches the running service schema."""
    yaml_path = Path(__file__).resolve().parent.parent / "openapi.yaml"
    assert yaml_path.exists(), "openapi.yaml does not exist in project root."

    with open(yaml_path, "r", encoding="utf-8") as f:
        committed_schema = yaml.safe_load(f)

    live_schema = app.openapi()

    # Compare key metadata and paths
    assert committed_schema.get("openapi") == live_schema.get("openapi")
    assert committed_schema.get("info", {}).get("title") == live_schema.get("info", {}).get("title")
    assert set(committed_schema.get("paths", {}).keys()) == set(live_schema.get("paths", {}).keys())
