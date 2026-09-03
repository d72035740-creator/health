import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.bioimpedance import router as bioimpedance_router
from app.api.routes.health import router as health_router
from app.api.routes.simulation import router as simulation_router
from app.api.routes.system import router as system_router
from app.api.routes.virtual_sensors import router as virtual_sensors_router
from app.api.routes.measurement import router as measurement_router
from app.api.routes.baseline import router as baseline_router
from app.api.routes.scenarios import router as scenarios_router
from app.api.routes.views import router as views_router
from app.api.websocket.simulation import router as simulation_websocket_router
from app.api.websocket.system import router as system_websocket_router
from app.api.websocket.runtime import router as runtime_websocket_router
from app.core.config import get_settings
from app.core.logging import configure_logging


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Aequor API starting", extra={"environment": settings.environment})
    yield
    logger.info("Aequor API stopped")


app = FastAPI(
    title="Aequor Health API",
    version="0.4.0",
    description=(
        "Phase 3 virtual wearable sensor and bilateral bioimpedance digital twin API. Synthetic raw acquisitions "
        "are not clinically validated; no clinical inference is implemented."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_unexpected_errors(request: Request, call_next):  # type: ignore[no-untyped-def]
    try:
        return await call_next(request)
    except Exception:
        logger.exception(
            "Unexpected request failure",
            extra={"method": request.method, "path": request.url.path},
        )
        raise


app.include_router(health_router)
app.include_router(bioimpedance_router)
app.include_router(virtual_sensors_router)
app.include_router(measurement_router)
app.include_router(baseline_router)
app.include_router(scenarios_router)
app.include_router(views_router)
app.include_router(simulation_router)
app.include_router(system_router)
app.include_router(system_websocket_router)
app.include_router(runtime_websocket_router)
app.include_router(simulation_websocket_router)
