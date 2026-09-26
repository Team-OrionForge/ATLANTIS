"""Main FastAPI application module for Project Atlantis."""

from contextlib import asynccontextmanager
import json
import logging
import os
import time
from typing import AsyncGenerator
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.batch_routes import router as batch_router
from api.exceptions import AtlantisBaseException
from api.routes import router as sonar_router
from api.schemas import HealthResponse
from pipeline.detector import get_detector

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("atlantis.api.main")

START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """App lifespan event handler to warm model singleton at startup."""
    logger.info("Initializing Project Atlantis API service...")
    try:
        detector = get_detector()
        if detector.is_degraded_mode:
            logger.warning("Project Atlantis running in DEGRADED heuristic-only mode.")
        else:
            logger.info("YOLOv8-Seg model loaded and warmed successfully.")
    except Exception as exc:
        logger.error(f"Failed to initialize detector model during startup: {exc}")
    yield
    logger.info("Shutting down Project Atlantis API service.")


app = FastAPI(
    title="Project Atlantis — Marine Target & Debris Detection API",
    description="Autonomous Multi-Class Marine Target & Debris Detection from Dual-Channel Side-Scan Sonar Imagery",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
cors_origins_raw = os.getenv("CORS_ORIGINS", '["http://localhost:5173", "http://127.0.0.1:5173"]')
try:
    origins = json.loads(cors_origins_raw)
except Exception:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AtlantisBaseException)
async def atlantis_exception_handler(request: Request, exc: AtlantisBaseException) -> JSONResponse:
    """Global exception handler for custom Atlantis errors."""
    logger.error(f"Atlantis exception on {request.url.path}: [{exc.code}] {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code, "detail": str(exc)},
    )


@app.get("/api/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Liveness and readiness check endpoint."""
    detector = get_detector()
    uptime = time.time() - START_TIME
    return HealthResponse(
        status="ok",
        model_loaded=(not detector.is_degraded_mode),
        degraded_mode=detector.is_degraded_mode,
        version="1.0.0",
        uptime_seconds=round(uptime, 2),
    )


app.include_router(sonar_router)
app.include_router(batch_router)
