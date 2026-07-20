"""
URL-based summarization endpoint.

  POST /api/v1/summarize/url

Accepts a URL, scrapes the article, then summarizes it.
Authentication: Bearer token or X-API-Key header (same as /summarize).
"""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, field_validator

from app.database import get_db
from app.models import User, UsageLog
from app.schemas import SummarizeResponse
from app.dependencies import enforce_monthly_limit
from app import summarizer, cache
from app.auth import decode_access_token
from app.scraper import scrape_article, ScraperError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security

router = APIRouter(tags=["URL Summarization"])
bearer_scheme = HTTPBearer(auto_error=False)


# ─── Request / Response schemas ───────────────────────────────────────────────

class URLSummarizeRequest(BaseModel):
    url: str
    language: Optional[str] = "auto"   # override auto-detection if needed
    max_length: Optional[int] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in {"en", "bn", "auto"}:
            raise ValueError("Language must be one of: en, bn, auto")
        return v


class URLSummarizeResponse(BaseModel):
    summary: str
    title: str
    url: str
    source_domain: str
    original_length: int
    summary_length: int
    language_detected: str
    tokens_used: int
    requests_remaining: int
    model: str
    cached: bool = False


# ─── Auth helper (shared pattern) ────────────────────────────────────────────

def _resolve_user(db, credentials, x_api_key) -> User:
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and payload.get("sub"):
            user = db.query(User).filter(
                User.id == payload["sub"], User.is_active == True
            ).first()
            if user:
                return user
    if x_api_key:
        user = db.query(User).filter(
            User.api_key == x_api_key, User.is_active == True
        ).first()
        if user:
            return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: provide Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ─── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/api/v1/summarize/url", response_model=URLSummarizeResponse)
def summarize_from_url(
    payload: URLSummarizeRequest,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    Paste any article URL — we fetch it, extract the text, and summarize it.

    Supports:
    - Bangla news: prothomalo.com, kalerkantho.com, bdnews24.com, samakal.com, jugantor.com
    - English news: thedailystar.net, bbc.com, reuters.com, and most others
    """
    user = _resolve_user(db, credentials, x_api_key)
    user = enforce_monthly_limit(user)

    # ── Step 1: Scrape article ────────────────────────────────────────────────
    try:
        article = scrape_article(payload.url)
    except ScraperError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected scraping error: {exc}",
        )

    # Resolve language: user override > scraper hint > auto
    effective_lang = payload.language if payload.language != "auto" else article.language_hint

    # ── Step 2: Cache check ───────────────────────────────────────────────────
    cached = cache.get_cached_summary(article.text, effective_lang, payload.max_length)
    if cached:
        try:
            from app.metrics import CACHE_HITS
            CACHE_HITS.inc()
        except ImportError:
            pass
        user.usage_count += 1
        db.add(UsageLog(
            user_id=user.id,
            article_language=cached["language_detected"],
            characters_used=article.char_count,
            summary_tokens=cached["tokens_used"],
            from_cache=True,
            endpoint="/api/v1/summarize/url",
        ))
        db.commit()
        db.refresh(user)
        return URLSummarizeResponse(
            **cached,
            title=article.title,
            url=payload.url,
            source_domain=article.source_domain,
            requests_remaining=user.remaining_requests,
            cached=True,
        )

    # ── Step 3: Model inference ───────────────────────────────────────────────
    if not summarizer.is_model_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model loading — please retry in a moment.",
        )

    try:
        summary, detected_lang, token_count = summarizer.summarize(
            text=article.text,
            language=effective_lang,
            max_length=payload.max_length,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}")

    result = {
        "summary": summary,
        "language_detected": detected_lang,
        "tokens_used": token_count,
        "original_length": article.char_count,
        "summary_length": len(summary),
        "model": "google/mt5-small",
        "cached": False,
    }
    cache.set_cached_summary(article.text, effective_lang, payload.max_length, result)

    # ── Step 4: Track usage ───────────────────────────────────────────────────
    user.usage_count += 1
    db.add(UsageLog(
        user_id=user.id,
        article_language=detected_lang,
        characters_used=article.char_count,
        summary_tokens=token_count,
        from_cache=False,
        endpoint="/api/v1/summarize/url",
    ))
    db.commit()
    db.refresh(user)

    return URLSummarizeResponse(
        **result,
        title=article.title,
        url=payload.url,
        source_domain=article.source_domain,
        requests_remaining=user.remaining_requests,
    )
