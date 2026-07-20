import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey,
    Enum as SAEnum, Boolean, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class PlanType(str, enum.Enum):
    FREE     = "free"
    STUDENT  = "student"
    BASIC    = "basic"
    PRO      = "pro"
    BUSINESS = "business"

PLAN_LIMITS = {
    PlanType.FREE:     50,
    PlanType.STUDENT:  300,
    PlanType.BASIC:    1000,
    PlanType.PRO:      5000,
    PlanType.BUSINESS: 20000,
}

def generate_api_key() -> str:
    return f"sk-{uuid.uuid4().hex}{uuid.uuid4().hex}"


class User(Base):
    __tablename__ = "users"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email          = Column(String(255), unique=True, nullable=False, index=True)
    password_hash  = Column(String(255), nullable=False)
    api_key        = Column(String(128), unique=True, nullable=False, default=generate_api_key, index=True)
    plan           = Column(SAEnum(PlanType), nullable=False, default=PlanType.FREE)
    usage_count    = Column(Integer, nullable=False, default=0)
    monthly_limit  = Column(Integer, nullable=False, default=PLAN_LIMITS[PlanType.FREE])
    is_active      = Column(Boolean, nullable=False, default=True)
    is_admin       = Column(Boolean, nullable=False, default=False)
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at     = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_reset_at  = Column(DateTime, nullable=False, default=datetime.utcnow)

    usage_logs = relationship("UsageLog", back_populates="user", cascade="all, delete-orphan")
    webhooks   = relationship("Webhook",  back_populates="user", cascade="all, delete-orphan")

    @property
    def remaining_requests(self) -> int:
        return max(0, self.monthly_limit - self.usage_count)

    @property
    def usage_percentage(self) -> float:
        if self.monthly_limit == 0:
            return 100.0
        return round((self.usage_count / self.monthly_limit) * 100, 2)

    def __repr__(self):
        return f"<User {self.email} plan={self.plan}>"


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    article_language = Column(String(10), nullable=False, default="auto")
    characters_used  = Column(Integer, nullable=False, default=0)
    summary_tokens   = Column(Integer, nullable=False, default=0)
    endpoint         = Column(String(64), nullable=False, default="/api/v1/summarize")
    job_id           = Column(String(64), nullable=True)
    from_cache       = Column(Boolean, nullable=False, default=False)
    created_at       = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="usage_logs")


class WebhookEvent(str, enum.Enum):
    SUMMARIZE_COMPLETE = "summarize.complete"
    LIMIT_REACHED      = "limit.reached"
    LIMIT_WARNING      = "limit.warning"


class Webhook(Base):
    __tablename__ = "webhooks"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    url        = Column(String(512), nullable=False)
    secret     = Column(String(128), nullable=True)
    events     = Column(String(256), nullable=False, default="summarize.complete")
    is_active  = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="webhooks")

    @property
    def event_list(self) -> list:
        return [e.strip() for e in self.events.split(",") if e.strip()]
