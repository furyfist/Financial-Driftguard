# driftguard/api/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..store.database import create_db
from ..scheduler.jobs import start_scheduler, stop_scheduler
from .routes import models, drift, alerts


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="DriftGuard API",
    description="Financial ML model drift monitoring with regime awareness",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models.router)
app.include_router(drift.router)
app.include_router(alerts.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}