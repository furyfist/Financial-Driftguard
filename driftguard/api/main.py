import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from .auth import APIKeyMiddleware

from ..store.database import create_db, migrate_model_versions
from ..scheduler.jobs import start_scheduler, stop_scheduler, restore_baselines_from_db

_log = logging.getLogger(__name__)


def _warn_missing_env() -> None:
    """Log warnings for missing or placeholder env vars at startup."""
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    core_keys = ["FRED_API_KEY"]
    if provider == "gemini":
        core_keys.append("GEMINI_API_KEY")
    else:
        core_keys.append("GROQ_API_KEY")

    for key in core_keys:
        val = os.getenv(key, "")
        if not val or val.startswith("your_"):
            _log.warning(
                "Startup warning: %s is not set — core LLM/macro features will be degraded", key
            )

    for key, feature in [
        ("SLACK_WEBHOOK_URL", "Slack notifications"),
        ("SMTP_HOST", "email notifications"),
    ]:
        val = os.getenv(key, "")
        if not val or val.startswith("your_"):
            _log.warning(
                "Startup warning: %s is not set — %s will be degraded", key, feature
            )

    phoenix_key = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "")
    if not phoenix_key or phoenix_key.startswith("your_"):
        _log.warning(
            "Startup warning: PHOENIX_COLLECTOR_ENDPOINT is not set — tracing will be degraded"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    migrate_model_versions()
    _warn_missing_env()
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

from .routes import models, drift, alerts, demo, versions
app.include_router(models.router)
app.include_router(versions.router)
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


@app.get("/health/scheduler")
def scheduler_health():
    from ..scheduler.jobs import scheduler
    if not scheduler.running:
        return {"status": "stopped", "jobs": []}
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return {"status": "running", "jobs": jobs}