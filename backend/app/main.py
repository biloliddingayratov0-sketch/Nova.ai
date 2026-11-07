import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import (
    FRONTEND_URL,
    GENERATED_DIR,
    MEDIA_DIR,
    RATE_LIMIT_PER_MINUTE,
)
from app.database.connection import Base, engine
from app.database.migration import run_migrations
import app.models  # Ensures all models are registered

# Import Routers
from app.routes.auth import router as auth_router
from app.routes.images import router as images_router
from app.routes.history import router as history_router
from app.routes.chat import router as chat_router
from app.routes.code import router as code_router
from app.routes.videos import router as videos_router
from app.routes.voice import router as voice_router
from app.routes.music import router as music_router
from app.routes.audio_studio import router as audio_studio_router
from app.routes.dashboard import router as dashboard_router
from app.routes.creations import router as creations_router
from app.routes.subscriptions import router as subscriptions_router
from app.routes.payments import router as payments_router
from app.routes.admin import router as admin_router
from app.routes.notifications import router as notifications_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nova_ai")

# Run schema migrations and seed plans
try:
    run_migrations()
    logger.info("Database migrations and seeding completed successfully.")
except Exception as e:
    logger.error(f"Migration error: {e}", exc_info=True)

limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NOVA AI Master Platform starting up...")
    yield
    logger.info("NOVA AI Platform shutting down...")

app = FastAPI(
    title="NOVA AI — Ultimate Master AI Platform",
    description="Enterprise-grade AI SaaS API: Multi-modal Creative Studio, Assistant, Video, Voice & Code",
    version="3.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
CORS_ORIGINS = [
    FRONTEND_URL,
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "*",  # Permissive for local development and test previews
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Static media mounts
app.mount(
    "/generated",
    StaticFiles(directory=str(GENERATED_DIR)),
    name="generated",
)
app.mount(
    "/media",
    StaticFiles(directory=str(MEDIA_DIR)),
    name="media",
)

# Register All Routes
app.include_router(auth_router)
app.include_router(images_router)
app.include_router(history_router)
app.include_router(chat_router)
app.include_router(code_router)
app.include_router(videos_router)
app.include_router(voice_router)
app.include_router(music_router)
app.include_router(audio_studio_router)
app.include_router(dashboard_router)
app.include_router(creations_router)
app.include_router(subscriptions_router)
app.include_router(payments_router)
app.include_router(admin_router)
app.include_router(notifications_router)


@app.get("/")
def home():
    return {
        "name": "NOVA AI Master Platform",
        "version": "3.0.0",
        "status": "online",
        "docs": "/docs",
        "services": [
            "chat", "code", "images", "videos", "voice",
            "music", "audio_studio", "subscriptions", "payments", "admin"
        ],
    }


@app.get("/health")
def health():
    return {"status": "healthy", "platform": "NOVA AI", "version": "3.0.0"}
