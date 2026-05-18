import uuid
import secrets
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, BigInteger, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
import enum


class ApiKeyTier(str, enum.Enum):
    free = "free"           # 100 requests/day
    starter = "starter"     # 5,000 requests/day
    growth = "growth"       # 50,000 requests/day
    enterprise = "enterprise"  # unlimited (custom billing)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    # The actual key — stored hashed, prefix shown to user
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)  # e.g. "sxa_live_ab12"

    name: Mapped[str] = mapped_column(String(100), nullable=False)       # developer-given label
    tier: Mapped[ApiKeyTier] = mapped_column(Enum(ApiKeyTier), default=ApiKeyTier.free)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_origins: Mapped[str] = mapped_column(Text, nullable=True)    # comma-separated domains
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    usage_logs: Mapped[list["ApiUsageLog"]] = relationship("ApiUsageLog", back_populates="api_key")


class ApiUsageLog(Base):
    __tablename__ = "api_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), index=True)
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    response_ms: Mapped[int] = mapped_column(Integer, default=0)   # latency
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    api_key: Mapped["ApiKey"] = relationship("ApiKey", back_populates="usage_logs")


# Daily usage counter (fast lookup — also mirrored in Redis)
class ApiDailyUsage(Base):
    __tablename__ = "api_daily_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), index=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False)          # YYYY-MM-DD
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[BigInteger] = mapped_column(BigInteger, default=0)
