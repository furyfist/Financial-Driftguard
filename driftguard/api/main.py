from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from .auth import APIKeyMiddleware

from ..store.database import create_db
from ..scheduler.jobs import start_scheduler, stop_scheduler, restore_baselines_from_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    restore_baselines_from_db()
    try:
        import os
        from finsight.tracing import init_tracing
        init_tracing(project_name=os.getenv("PHOENIX_PROJECT_NAME", "finsight-ai"))
    except ImportError:
        pass  # finsight not installed — running as plain DriftGuard
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="DriftGuard API",
    description="Financial ML model drift monitoring with regime awareness",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyMiddleware)

from .routes import models, drift, alerts, demo
app.include_router(models.router)
app.include_router(drift.router)
app.include_router(alerts.router)
app.include_router(demo.router)

try:
    from .routes import agent as _agent_routes
    app.include_router(_agent_routes.router)
except ImportError:
    logging.getLogger(__name__).warning(
        "finsight not installed — /agent routes disabled"
    )

try:
    from .routes import experiments as _experiment_routes
    app.include_router(_experiment_routes.router)
except ImportError:
    logging.getLogger(__name__).warning(
        "finsight not installed — /experiments routes disabled"
    )

try:
    from .routes import trust as _trust_routes
    app.include_router(_trust_routes.router)
except ImportError:
    logging.getLogger(__name__).warning(
        "finsight not installed — /trust routes disabled"
    )


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}