import os
from pathlib import Path
from typing import Dict, Optional, Type
import yaml
from pydantic import ValidationError

from connectors.base import BaseConnector
from connectors.schemas import ConnectorManifest
from core.errors import ConnectorDisabledError, ErrorCode, IncuBrixError
from core.logging import get_logger

logger = get_logger("connector_registry")


class ConnectorRegistry:
    """Central registry for discovering, validating, and serving connectors."""

    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._manifests: Dict[str, ConnectorManifest] = {}
        self._disabled: set[str] = set()

    def load_manifest_from_path(self, file_path: Path) -> ConnectorManifest:
        """Loads and strictly validates a manifest YAML file against the Pydantic schema."""
        if not file_path.exists():
            raise IncuBrixError(
                code=ErrorCode.INVALID_MANIFEST,
                message=f"Manifest file not found: {file_path}",
                status_code=500,
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = yaml.safe_load(f)
        except Exception as e:
            raise IncuBrixError(
                code=ErrorCode.INVALID_MANIFEST,
                message=f"Failed to parse YAML manifest at {file_path}: {str(e)}",
                details={"file": str(file_path), "error": str(e)},
                status_code=500,
            )

        try:
            manifest = ConnectorManifest.model_validate(raw_data)
            return manifest
        except ValidationError as e:
            violations = [f"{' -> '.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in e.errors()]
            raise IncuBrixError(
                code=ErrorCode.INVALID_MANIFEST,
                message=f"Manifest validation failed for {file_path}: {len(violations)} errors detected.",
                details={"file": str(file_path), "violations": violations},
                status_code=500,
            )

    def register(self, connector: BaseConnector) -> None:
        """Registers an initialized connector instance."""
        key = connector.key
        self._connectors[key] = connector
        self._manifests[key] = connector.manifest
        logger.info(f"Registered connector '{key}' (version: {connector.manifest.version}, tier: {connector.manifest.tier})")

    def get_connector(self, connector_key: str) -> BaseConnector:
        """Retrieves a registered connector, enforcing the kill-switch."""
        if connector_key in self._disabled:
            raise ConnectorDisabledError(connector_key)

        connector = self._connectors.get(connector_key)
        if not connector:
            raise IncuBrixError(
                code=ErrorCode.NOT_FOUND,
                message=f"Connector '{connector_key}' is not registered.",
                details={"available_connectors": list(self._connectors.keys())},
                status_code=404,
            )
        return connector

    def get_manifest(self, connector_key: str) -> ConnectorManifest:
        """Retrieves the manifest for a connector."""
        if connector_key not in self._manifests:
            raise IncuBrixError(
                code=ErrorCode.NOT_FOUND,
                message=f"Connector '{connector_key}' not found in registry.",
                status_code=404,
            )
        return self._manifests[connector_key]

    def list_manifests(self) -> Dict[str, ConnectorManifest]:
        """Lists all registered connector manifests."""
        return self._manifests

    def disable_connector(self, connector_key: str) -> None:
        """Activates kill switch for specified connector."""
        self._disabled.add(connector_key)
        logger.warning(f"Connector '{connector_key}' disabled via kill switch.")

    def enable_connector(self, connector_key: str) -> None:
        """Deactivates kill switch for specified connector."""
        self._disabled.discard(connector_key)
        logger.info(f"Connector '{connector_key}' re-enabled.")

    def is_disabled(self, connector_key: str) -> bool:
        """Checks if connector is disabled."""
        return connector_key in self._disabled


# Global singleton instance
registry = ConnectorRegistry()
