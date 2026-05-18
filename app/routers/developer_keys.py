"""
Developer API Key Management
------------------------------
Developers create, list, rotate, and revoke their API keys here.
The raw key is returned ONCE on creation — never again.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.api_key_auth import generate_api_key, TIER_LIMITS
from app.models.api_key import ApiKey, ApiKeyTier, ApiUsageLog
from app.models.user import UserRole

router = APIRouter(prefix="/developer/keys", tags=["Developer Portal"])


def require_developer(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in (UserRole.developer, UserRole.admin):
        raise HTTPException(status_code=403, detail="Developer account required")
    return current_user


class CreateKeyRequest(BaseModel):
    name: str
    tier: ApiKeyTier = ApiKeyTier.free
    allowed_origins: Optional[str] = None   # comma-separated: "myapp.com,localhost"
    expires_at: Optional[datetime] = None


class KeyCreatedResponse(BaseModel):
    id: str
    name: str
    key: str          # raw key — shown ONCE
    key_prefix: str
    tier: str
    daily_limit: int
    message: str


class KeySummaryResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    tier: str
    daily_limit: int
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]


@router.post("/", response_model=KeyCreatedResponse, status_code=201)
async def create_api_key(
    payload: CreateKeyRequest,
    current_user: dict = Depends(require_developer),
    db: AsyncSession = Depends(get_db),
):
    # Limit free tier to 3 keys per developer
    count_result = await db.execute(
        select(func.count(ApiKey.id)).where(
            ApiKey.owner_id == current_user["sub"],
            ApiKey.is_active == True,  # noqa: E712
        )
    )
    active_count = count_result.scalar()
    if active_count >= 10:
        raise HTTPException(status_code=400, detail="Maximum of 10 active API keys allowed")

    raw_key, key_hash, key_prefix = generate_api_key()

    api_key = ApiKey(
        owner_id=current_user["sub"],
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=payload.name,
        tier=payload.tier,
        allowed_origins=payload.allowed_origins,
        expires_at=payload.expires_at,
    )
    db.add(api_key)
    await db.flush()

    return KeyCreatedResponse(
        id=str(api_key.id),
        name=api_key.name,
        key=raw_key,
        key_prefix=key_prefix,
        tier=api_key.tier,
        daily_limit=TIER_LIMITS[api_key.tier],
        message="Save this key securely. It will NOT be shown again.",
    )


@router.get("/", response_model=list[KeySummaryResponse])
async def list_my_keys(
    current_user: dict = Depends(require_developer),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.owner_id == current_user["sub"]).order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        KeySummaryResponse(
            id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            tier=k.tier,
            daily_limit=TIER_LIMITS[k.tier],
            is_active=k.is_active,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
            expires_at=k.expires_at,
        )
        for k in keys
    ]


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(require_developer),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.owner_id == current_user["sub"])
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="Key not found")
    api_key.is_active = False


@router.get("/{key_id}/usage")
async def get_key_usage(
    key_id: str,
    current_user: dict = Depends(require_developer),
    db: AsyncSession = Depends(get_db),
):
    """Returns last 30 days of usage stats for a key."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.owner_id == current_user["sub"])
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="Key not found")

    logs_result = await db.execute(
        select(ApiUsageLog)
        .where(ApiUsageLog.api_key_id == key_id)
        .order_by(ApiUsageLog.created_at.desc())
        .limit(500)
    )
    logs = logs_result.scalars().all()

    total_requests = len(logs)
    total_tokens = sum(l.tokens_used for l in logs)
    avg_latency = round(sum(l.response_ms for l in logs) / total_requests, 1) if total_requests else 0

    return {
        "key_id": key_id,
        "key_prefix": api_key.key_prefix,
        "tier": api_key.tier,
        "daily_limit": TIER_LIMITS[api_key.tier],
        "total_requests": total_requests,
        "total_tokens_used": total_tokens,
        "avg_latency_ms": avg_latency,
        "recent_logs": [
            {
                "endpoint": l.endpoint,
                "tokens": l.tokens_used,
                "status": l.status_code,
                "latency_ms": l.response_ms,
                "at": l.created_at,
            }
            for l in logs[:50]
        ],
    }
