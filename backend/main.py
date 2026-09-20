"""
main.py
=======
CrackXNet FastAPI Application Entry Point.

Startup sequence:
  1. Load CrackXNet model (once — never per request)
  2. Connect to MongoDB
  3. Mount static file directories (uploads, results)
  4. Register all routers

Run command:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Production:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
    (single worker to share the model in memory; multi-worker needs model server)
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.database import connect_db, disconnect_db
from backend.services.inference_service import startup_load_model, shutdown_model
from backend.routes.health import router as health_router
from backend.routes.inspection import router as inspection_router
from backend.routes.history import router as history_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.settings import router as settings_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("crackxnet")


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Startup:
        - Load CrackXNet model (single-load, shared across all requests)
        - Connect to MongoDB

    Shutdown:
        - Release model
        - Disconnect MongoDB
    """
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("  CrackXNet — PCB Defect Inspection System")
    logger.info("=" * 60)

    # 1. Load model
    logger.info("Loading CrackXNet model...")
    await startup_load_model()

    # 2. Connect database
    logger.info("Connecting to MongoDB...")
    await connect_db(settings.mongodb_uri, settings.database_name)

    logger.info("CrackXNet backend is ready.")
    logger.info("API: http://%s:%d", settings.host, settings.port)

    yield  # Application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down CrackXNet backend...")
    await shutdown_model()
    await disconnect_db()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------
settings = get_settings()

app = FastAPI(
    title="CrackXNet — PCB Defect Inspection API",
    description=(
        "Intelligent Real-Time PCB Surface Defect Inspection and "
        "Quality Decision Support System powered by CrackXNet."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow React dev server and production frontend
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite default dev port
        "http://localhost:3000",   # Alternative CRA / dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static file mounts (uploaded images + generated result images)
# ---------------------------------------------------------------------------
settings.ensure_dirs()

app.mount(
    "/static/uploads",
    StaticFiles(directory=settings.upload_dir),
    name="uploads",
)
app.mount(
    "/static/results",
    StaticFiles(directory=settings.results_dir),
    name="results",
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health_router)
app.include_router(inspection_router)
app.include_router(history_router)
app.include_router(dashboard_router)
app.include_router(settings_router)


# ---------------------------------------------------------------------------
# Root redirect to docs
# ---------------------------------------------------------------------------
from fastapi.responses import RedirectResponse  # noqa: E402


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")
