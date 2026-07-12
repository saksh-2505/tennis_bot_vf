"""Developer Console API — FastAPI backend for the internal engineering console.

Read-only access to TimescaleDB. No business logic duplication.
WebSocket support for live updates.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from console_api.deps import get_settings
from console_api.ws import router as ws_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Console API starting")
    yield
    logger.info("Console API shutting down")


app = FastAPI(
    title="Sports Trading Platform — Developer Console API",
    version="4.0.0",
    description="Read-only internal engineering console API. No business logic.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])

from console_api.routers import (
    analytics,
    collectors,
    database,
    discovery,
    incidents,
    matches,
    matching,
    observability,
    overview,
    pipeline,
    quality,
    registry,
    repair,
    reports,
    search,
    timeline,
    validation,
    verification,
)

app.include_router(overview.router, prefix="/api", tags=["Overview"])
app.include_router(matches.router, prefix="/api", tags=["Matches"])
app.include_router(collectors.router, prefix="/api", tags=["Collectors"])
app.include_router(matching.router, prefix="/api", tags=["Market Matching"])
app.include_router(discovery.router, prefix="/api", tags=["Discovery"])
app.include_router(registry.router, prefix="/api", tags=["Registry"])
app.include_router(database.router, prefix="/api", tags=["Database"])
app.include_router(quality.router, prefix="/api", tags=["Quality"])
app.include_router(validation.router, prefix="/api", tags=["Validation"])
app.include_router(verification.router, prefix="/api", tags=["Verification"])
app.include_router(observability.router, prefix="/api", tags=["Observability"])
app.include_router(pipeline.router, prefix="/api", tags=["Pipeline"])
app.include_router(incidents.router, prefix="/api", tags=["Incidents"])
app.include_router(repair.router, prefix="/api", tags=["Repair"])
app.include_router(reports.router, prefix="/api", tags=["Reports"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(timeline.router, prefix="/api", tags=["Timeline"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "4.0.0"}
