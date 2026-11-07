import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# AI API Keys
API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
REPLICATE_API_KEY: str = os.getenv("REPLICATE_API_KEY", "").strip()

# AI Models (Real models, with valid OpenAI defaults)
IMAGE_MODEL: str = os.getenv("AI_IMAGE_MODEL", "dall-e-3").strip()
IMAGE_EDIT_MODEL: str = os.getenv("AI_IMAGE_EDIT_MODEL", "dall-e-2").strip()
CHAT_MODEL: str = os.getenv("AI_CHAT_MODEL", "gpt-4o-mini").strip()
CODE_MODEL: str = os.getenv("AI_CODE_MODEL", "gpt-4o-mini").strip()
VIDEO_MODEL: str = os.getenv("AI_VIDEO_MODEL", "nova-video-v1").strip()
AUDIO_MODEL: str = os.getenv("AI_AUDIO_MODEL", "tts-1").strip()

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./nova_ai.db").strip()

# Security & JWT
JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_nova_ai_jwt_key_2026_production").strip()
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256").strip()
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

# Frontend & CORS
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500").strip()
RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
MAX_HISTORY_PER_PAGE: int = int(os.getenv("MAX_HISTORY_PER_PAGE", "50"))

# Payment Credentials (Uzbekistan)
CLICK_SERVICE_ID: str = os.getenv("CLICK_SERVICE_ID", "test_click_service_id").strip()
CLICK_MERCHANT_ID: str = os.getenv("CLICK_MERCHANT_ID", "test_click_merchant_id").strip()
CLICK_SECRET_KEY: str = os.getenv("CLICK_SECRET_KEY", "test_click_secret_key").strip()

PAYME_MERCHANT_ID: str = os.getenv("PAYME_MERCHANT_ID", "test_payme_merchant_id").strip()
PAYME_SECRET_KEY: str = os.getenv("PAYME_SECRET_KEY", "test_payme_secret_key").strip()

UZUM_MERCHANT_ID: str = os.getenv("UZUM_MERCHANT_ID", "test_uzum_merchant_id").strip()
UZUM_SECRET_KEY: str = os.getenv("UZUM_SECRET_KEY", "test_uzum_secret_key").strip()

# Directories
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_DIR = MEDIA_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_DIR = MEDIA_DIR / "videos"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

CODE_DIR = MEDIA_DIR / "code"
CODE_DIR.mkdir(parents=True, exist_ok=True)

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Configure it in backend/.env")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is missing. Configure it in backend/.env")
