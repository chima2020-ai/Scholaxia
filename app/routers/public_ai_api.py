"""
Scholaxia Public AI API
------------------------
External developers call this endpoint using their API key.
Authenticated via x-api-key header or Bearer token.
Rate limited per tier. Usage logged per request.
"""

import time
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from app.core.database import get_db
from app.core.api_key_auth import (
    get_api_key_from_request,
    validate_api_key,
    check_rate_limit,
    log_api_usage,
    TIER_LIMITS,
)
from app.ai.prompt_builder import build_prompt, SUPPORTED_LANGUAGES
from app.ai.model_backend import run_inference
from app.ai.safety_filter import is_educational, sanitize_output

router = APIRouter(prefix="/v1", tags=["Public AI API"])

SUPPORTED_LANGUAGES_LIST = SUPPORTED_LANGUAGES


# ── Request / Response schemas ──────────────────────────────────────────────

class AIRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    subject: str = Field(..., min_length=1, max_length=100)
    education_level: str = Field(
        default="SS1",
        description="JSS1 | JSS2 | JSS3 | SS1 | SS2 | SS3 | JAMB | WAEC | NECO",
    )
    language: str = Field(default="english")
    stream: bool = Field(default=False, description="Streaming not yet supported — reserved for future use")


class AIResponse(BaseModel):
    answer: str
    subject: str
    education_level: str
    language: str
    tokens_used: int
    model: str = "scholaxia-edu-v1"


class UsageInfo(BaseModel):
    requests_today: int
    daily_limit: int
    remaining: int
    tier: str


# ── Dependency: resolve + validate API key ───────────────────────────────────

async def get_validated_api_key(request: Request, db: AsyncSession = Depends(get_db)):
    raw_key = await get_api_key_from_request(request)
    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Pass via 'x-api-key' header or 'Authorization: Bearer <key>'.",
        )
    api_key = await validate_api_key(raw_key, db)
    await check_rate_limit(api_key)
    return api_key


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/ai/ask", response_model=AIResponse)
async def public_ask(
    payload: AIRequest,
    request: Request,
    api_key=Depends(get_validated_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Ask the Scholaxia AI a question.

    - Authenticated via API key
    - Rate limited by tier
    - Education-only content enforced
    - Adapts explanation depth to education_level
    - Supports English, Igbo, Yoruba, Hausa, French, Arabic
    """
    if payload.language.lower() not in SUPPORTED_LANGUAGES_LIST:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language. Supported: {SUPPORTED_LANGUAGES_LIST}",
        )

    # Safety check
    safe, reason = is_educational(payload.question)
    if not safe:
        await log_api_usage(
            db=db, api_key=api_key, endpoint="/v1/ai/ask",
            tokens_used=0, response_ms=0, status_code=400,
            ip_address=request.client.host,
        )
        raise HTTPException(status_code=400, detail=reason)

    # Build prompt and run inference
    prompt = build_prompt(
        question=payload.question,
        subject=payload.subject,
        education_level=payload.education_level,
        language=payload.language,
        student_name="Student",
    )

    start_ms = int(time.time() * 1000)
    raw_answer = await run_inference(prompt)
    elapsed_ms = int(time.time() * 1000) - start_ms

    answer = sanitize_output(raw_answer)
    tokens_used = len(prompt.split()) + len(answer.split())  # approximate

    # Log usage
    await log_api_usage(
        db=db, api_key=api_key, endpoint="/v1/ai/ask",
        tokens_used=tokens_used, response_ms=elapsed_ms,
        status_code=200, ip_address=request.client.host,
    )

    return AIResponse(
        answer=answer,
        subject=payload.subject,
        education_level=payload.education_level,
        language=payload.language,
        tokens_used=tokens_used,
    )


@router.get("/ai/usage", response_model=UsageInfo)
async def get_usage(
    request: Request,
    api_key=Depends(get_validated_api_key),
):
    """Check your current usage and remaining quota for today."""
    from app.core.redis import get_redis
    from datetime import date

    redis = await get_redis()
    today = date.today().isoformat()
    daily_key = f"ratelimit:daily:{api_key.id}:{today}"
    count = await redis.get(daily_key)
    count = int(count) if count else 0
    limit = TIER_LIMITS[api_key.tier]

    return UsageInfo(
        requests_today=count,
        daily_limit=limit,
        remaining=max(0, limit - count),
        tier=api_key.tier,
    )


@router.get("/ai/models")
async def list_models():
    """List available Scholaxia AI models."""
    return {
        "models": [
            {
                "id": "sia-edu-v1",
                "name": "Sia",
                "description": "Sia — Scholaxia Intelligent Assistant. Friendly, adaptive AI tutor for JAMB, WAEC, NECO, Cambridge.",
                "supported_levels": ["Primary", "JSS1", "JSS2", "JSS3", "SS1", "SS2", "SS3", "JAMB", "WAEC", "NECO", "Cambridge"],
            "supported_languages": f"{len(SUPPORTED_LANGUAGES)}+ languages including English, Igbo, Yoruba, Hausa, French, Arabic, Spanish, Chinese, Hindi, Swahili and more",
                "max_tokens": 1024,
            }
        ]
    }
