from pydantic import BaseModel, EmailStr, field_validator, ConfigDict, HttpUrl
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from app.models import PlanType


# ─── Auth ─────────────────────────────────────────────────────────────────────

class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ─── User ─────────────────────────────────────────────────────────────────────

class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    plan: PlanType
    usage_count: int
    monthly_limit: int
    remaining_requests: int
    usage_percentage: float
    api_key: str
    created_at: datetime


class UserPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    plan: PlanType
    usage_count: int
    monthly_limit: int
    remaining_requests: int
    usage_percentage: float
    created_at: datetime


# ─── Summarizer (sync) ────────────────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    text: str
    language: Optional[str] = "auto"
    max_length: Optional[int] = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 50:
            raise ValueError("Text must be at least 50 characters")
        if len(v) > 10000:
            raise ValueError("Text must not exceed 10,000 characters")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in {"en", "bn", "auto"}:
            raise ValueError("Language must be one of: en, bn, auto")
        return v


class SummarizeResponse(BaseModel):
    summary: str
    original_length: int
    summary_length: int
    language_detected: str
    tokens_used: int
    requests_remaining: int
    model: str
    cached: bool = False


# ─── Async job ────────────────────────────────────────────────────────────────

class AsyncJobResponse(BaseModel):
    job_id: str
    status: str           # "PENDING" | "STARTED" | "SUCCESS" | "FAILURE"
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[SummarizeResponse] = None
    error: Optional[str] = None
    requests_remaining: Optional[int] = None


# ─── Usage ────────────────────────────────────────────────────────────────────

class UsageLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    article_language: str
    characters_used: int
    summary_tokens: int
    from_cache: bool
    job_id: Optional[str]
    created_at: datetime


class UsageStatsResponse(BaseModel):
    total_requests: int
    total_characters_processed: int
    plan: PlanType
    monthly_limit: int
    usage_count: int
    remaining_requests: int
    usage_percentage: float
    recent_logs: List[UsageLogEntry]


# ─── Plans ────────────────────────────────────────────────────────────────────

class UpgradePlanRequest(BaseModel):
    plan: PlanType


class UpgradePlanResponse(BaseModel):
    message: str
    new_plan: PlanType
    new_monthly_limit: int


# ─── API Key ──────────────────────────────────────────────────────────────────

class RegenerateKeyResponse(BaseModel):
    api_key: str
    message: str


# ─── Webhooks ─────────────────────────────────────────────────────────────────

class WebhookCreateRequest(BaseModel):
    url: str
    secret: Optional[str] = None
    events: Optional[List[str]] = ["summarize.complete"]

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    events: str
    is_active: bool
    created_at: datetime


# ─── Admin ────────────────────────────────────────────────────────────────────

class AdminUserListEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    plan: PlanType
    usage_count: int
    monthly_limit: int
    is_active: bool
    created_at: datetime


class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    users_by_plan: dict
    total_requests_all_time: int
    model_info: dict
    redis_health: dict


# ─── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool
    model_info: dict
    redis: dict
    app_name: str
