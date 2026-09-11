"""
MATRIXCMS: Comprehensive Outreach Portal for Expedition Reports,
Scientific Datasets, Publications, Media, and Institutional Activities.

FastAPI Application Entry Point.
"""
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base
from app.services.storage import get_storage_root
from app.services.scheduler import start_scheduler, shutdown_scheduler

# Routers
from app.routers import (
    auth,
    expeditions,
    reports,
    datasets,
    publications,
    media,
    activities,
    search,
    generated_content,
    web,
)

logger = logging.getLogger("matrixcms")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager:
    1. Ensures all storage upload directories exist.
    2. Ensures database tables are initialized.
    3. Starts the background APScheduler for periodic outreach content generation.
    4. Shuts down background jobs cleanly on exit.
    """
    logger.info("Initializing MATRIXCMS Portal...")

    # Ensure storage root and subdirectories exist
    storage_root = get_storage_root()
    for subdir in ["reports", "datasets", "media"]:
        (storage_root / subdir).mkdir(parents=True, exist_ok=True)
    logger.info("Storage directories verified at: %s", storage_root)

    # Ensure database tables exist (SQLite development or PostgreSQL fallback)
    Base.metadata.create_all(bind=engine)
    logger.info("Database schemas verified.")

    # Start periodic content generation background scheduler
    scheduler = start_scheduler()
    logger.info("Periodic scheduler active.")

    yield

    # Shutdown scheduler cleanly
    shutdown_scheduler()
    logger.info("MATRIXCMS Portal shutdown complete.")


app = FastAPI(
    title="MATRIXCMS: Expedition & Research Outreach Portal",
    description=(
        "Comprehensive Open Science & Outreach Portal for Expedition Reports, "
        "Scientific Datasets, Peer-Reviewed Publications, Media Archives, "
        "and Automated LLM Outreach Content Generation. "
        "Affiliated with Chandigarh, Department of CSE."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware configured for development & production flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount /static directory to app/static
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
(static_dir / "css").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include all API routers
app.include_router(auth.router)
app.include_router(expeditions.router)
app.include_router(reports.router)
app.include_router(datasets.router)
app.include_router(publications.router)
app.include_router(media.router)
app.include_router(activities.router)
app.include_router(search.router)
app.include_router(generated_content.router)

# Include server-rendered HTML web router
app.include_router(web.router)
