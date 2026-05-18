from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Scholaxia"
    DEBUG: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Render sets DATABASE_URL automatically for PostgreSQL add-on
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    APPLE_CLIENT_ID: str = ""
    APPLE_TEAM_ID: str = ""
    APPLE_KEY_ID: str = ""
    APPLE_PRIVATE_KEY: str = ""

    # Cloudinary (Media Storage — replaces AWS S3)
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Stripe (Payments)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Firebase (Push Notifications)
    FIREBASE_CREDENTIALS_PATH: str = "firebase-credentials.json"

    # Brevo (OTP / Transactional Email)
    BREVO_API_KEY: str = ""
    BREVO_SENDER_EMAIL: str = "noreply@scholaxia.com"
    BREVO_SENDER_NAME: str = "Scholaxia"
    OTP_EXPIRE_MINUTES: int = 10

    # Custom AI Engine
    # "groq"   = Groq cloud API (free, fast, no local install needed) ← RECOMMENDED
    # "local"  = HuggingFace in-process (needs GPU + disk space)
    # "hosted" = your own inference server (Ollama, vLLM, TGI)
    AI_BACKEND: str = "groq"
    AI_LOCAL_MODEL_NAME: str = "mistralai/Mistral-7B-Instruct-v0.3"
    AI_LOCAL_DEVICE: str = "cpu"
    AI_HOSTED_BASE_URL: str = "http://localhost:11434"
    AI_HOSTED_MODEL_NAME: str = "scholaxia-edu"
    AI_HOSTED_API_KEY: str = ""
    AI_HOSTED_ENDPOINT_TYPE: str = "ollama"
    AI_MAX_TOKENS: int = 1024
    AI_TEMPERATURE: float = 0.4

    # Groq (free cloud AI — https://console.groq.com)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama3-70b-8192"   # fast + smart, free tier

    ADMIN_EMAIL: str = "admin@scholaxia.com"
    ADMIN_PASSWORD: str = "changeme"

    ALLOWED_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"


settings = Settings()

    # ElevenLabs (Text-to-Speech — Sia voice responses)
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"   # Rachel — warm and calm
    ELEVENLABS_MODEL_ID: str = "eleven_multilingual_v2"
