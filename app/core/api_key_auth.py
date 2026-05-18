"""
API Key Authentication & Rate Limiting
---------------------------------------
Handles authentication for external developers using Scholaxia AI API.
Uses Redis for fast rate limit counters (no DB hit per request).
Falls back to DB for key validation with a Redis cache layer.
"""

import hashlib
import secrets
import time
from datetime import datetime, date
from typing import Optional

from fastapi import Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.redis import get_redis
from app.models.api_key import ApiKey, ApiKeyTier, ApiUsageLog

# Daily request limits per tier
TIER_LIMITS = {
    ApiKeyTier.free: 100,
    ApiKeyTier.starter: 5_000,
    ApiKeyTier.growth: 50_000,
    ApiKeyTier.enterprise: 999_999_999,  # effectively unlimited
}

RATE_LIMIT_WINDOW = 60   # seconds for per-minute burst limit
BURST_LIMITS = {
    ApiKeyTier.free: 5,
    ApiKeyTier.starter: 60,
    ApiKeyTier.growth: 300,
    ApiKeyTier.enterprise: 1000,
}


def generate_api_key() -> tuple[str, str, str]:
    """
    Returns (raw_key, key_hash, key_prefix).
    raw_key is shown to the developer ONCE and never stored.
    key_hash is stored in the DB.
    key_prefix is stored for display (e.g. sxa_live_ab12cd...)
    """
    raw = "sxa_live_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    key_prefix = raw[:16]
    return raw, key_hash, key_prefix


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def get_api_key_from_request(request: Request) -> Optional[str]:
    """Extract API key from Authorization header or x-api-key header."""
    # Support: "Authorization: Bearer sxa_live_..." or "x-api-key: sxa_live_..."
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        key = auth[7:].strip()
        if key.startswith("sxa_"):
            return key
    return request.headers.get("x-api-key", "").strip() or None


async def validate_api_key(raw_key: str, db: AsyncSession) -> ApiKey:
    """Validate key against DB (with Redis cache)."""
    key_hash = hash_key(raw_key)

    try:
        redis = await get_redis()
        if redis:
            cache_key = f"apikey:valid:{key_hash}"
            cached = await redis.get(cache_key)
            if cached == "invalid":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    except HTTPException:
        raise
    except Exception:
        pass  # Redis unavailable — skip cache

    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()

    if not api_key or not api_key.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or inactive API key")

    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    return api_key


async def check_rate_limit(api_key: ApiKey):
    """Rate limiting — gracefully skips if Redis unavailable."""
    try:
        redis = await get_redis()
        if not redis:
            return  # skip rate limiting if Redis down

        key_id = str(api_key.id)
        today = date.today().isoformat()

        daily_key = f"ratelimit:daily:{key_id}:{today}"
        daily_count = await redis.get(daily_key)
        daily_count = int(daily_count) if daily_count else 0
        daily_limit = TIER_LIMITS[api_key.tier]

        if daily_count >= daily_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily limit of {daily_limit} requests reached.",
            )

        burst_key = f"ratelimit:burst:{key_id}"
        burst_count = await redis.get(burst_key)
        burst_count = int(burst_count) if burst_count else 0
        burst_limit = BURST_LIMITS[api_key.tier]

        if burst_count >= burst_limit:
            ttl = await redis.ttl(burst_key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Retry after {ttl}s.",
            )

        pipe = redis.pipeline()
        pipe.incr(daily_key)
        pipe.expire(daily_key, 86400)
        pipe.incr(burst_key)
        pipe.expire(burst_key, RATE_LIMIT_WINDOW)
        await pipe.execute()
    except HTTPException:
        raise
    except Exception:
        pass  # Redis unavailable — allow request


async def log_api_usage(
    db: AsyncSession,
    api_key: ApiKey,
    endpoint: str,
    tokens_used: int,
    response_ms: int,
    status_code: int,
    ip_address: str,
):
    """Persist usage log and update last_used_at."""
    log = ApiUsageLog(
        api_key_id=api_key.id,
        endpoint=endpoint,
        tokens_used=tokens_used,
        response_ms=response_ms,
        status_code=status_code,
        ip_address=ip_address,
    )
    db.add(log)

    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key.id)
        .values(last_used_at=datetime.utcnow())
    )
