import importlib
import inspect
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.middleware.correlation import CorrelationIdMiddleware
from api.middleware.error_handler import register_error_handlers
from api.middleware.security import DemoSecurityMiddleware
from api.routers.certification import router as certification_router
from api.routers.connectors import router as connector_router
from api.routers.destinations import router as destinations_router
from api.routers.files import router as files_router
from api.routers.health import router as health_router
from api.routers.jobs import router as jobs_router
from api.routers.publish import router as publish_router
from api.routers.rules import router as rules_router
from api.routers.security import router as security_router
from connectors.base import BaseConnector
from connectors.registry import registry
from core.config import get_settings
from core.logging import get_logger, setup_logging

settings = get_settings()
logger = get_logger("main")


def load_all_connectors():
    """Discovers and registers connectors from the connectors/ directory."""
    connectors_dir = Path(__file__).resolve().parent.parent / "connectors"

    for entry in sorted(connectors_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("__") or entry.name.startswith("."):
            continue

        manifest_path = entry / "manifest.yaml"
        client_path = entry / "client.py"

        if manifest_path.exists() and client_path.exists():
            try:
                manifest = registry.load_manifest_from_path(manifest_path)
                module_name = f"connectors.{entry.name}.client"
                module = importlib.import_module(module_name)

                connector_cls = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        inspect.isclass(attr)
                        and issubclass(attr, BaseConnector)
                        and attr is not BaseConnector
                    ):
                        connector_cls = attr
                        break

                if connector_cls:
                    registry.register(connector_cls(manifest))
                else:
                    logger.warning(f"No BaseConnector subclass found in {module_name}")
            except Exception as e:
                logger.error(f"Failed to load connector from {entry.name}: {str(e)}")
                raise

    logger.info(f"Loaded {len(registry.list_manifests())} connector(s) at startup: {list(registry.list_manifests().keys())}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager executing startup and shutdown tasks."""
    setup_logging(settings.log_level)
    logger.info(f"Starting {settings.app_name} (env: {settings.app_env}, sim: {settings.simulation_mode})")

    # Load and validate all connector manifests at startup
    load_all_connectors()

    yield

    logger.info(f"Shutting down {settings.app_name}...")


app = FastAPI(
    title="IncuBrix Long-Tail Distribution Network",
    version="1.0.0",
    description="Containerized distribution connector engine for Engineering Assessment 4.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Register Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-Id", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(DemoSecurityMiddleware)

# Register Global Exception Handlers
register_error_handlers(app)

# Mount Routes
app.include_router(health_router)
app.include_router(connector_router)
app.include_router(destinations_router)
app.include_router(publish_router)
app.include_router(jobs_router)
app.include_router(files_router)
app.include_router(certification_router)
app.include_router(rules_router)
app.include_router(security_router)

# Initial load of connectors
load_all_connectors()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=settings.app_host, port=settings.app_port, reload=settings.debug)
