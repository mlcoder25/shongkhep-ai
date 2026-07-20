from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import User, UsageLog
from app.schemas import SummarizeRequest, SummarizeResponse, AsyncJobResponse, JobStatusResponse
from app.dependencies import enforce_monthly_limit
from app import summarizer, cache
from app.auth import decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security

router = APIRouter(prefix="/summarize", tags=["Summarization"])
bearer_scheme = HTTPBearer(auto_error=False)


def _resolve_user(db, credentials, x_api_key):
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and payload.get("sub"):
            user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
            if user:
                return user
    if x_api_key:
        user = db.query(User).filter(User.api_key == x_api_key, User.is_active == True).first()
        if user:
            return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: provide Bearer token or X-API-Key header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _write_usage_log(db, user, payload, result, job_id=None):
    user.usage_count += 1
    log = UsageLog(
        user_id=user.id,
        article_language=result["language_detected"],
        characters_used=len(payload.text),
        summary_tokens=result["tokens_used"],
        from_cache=result.get("cached", False),
        job_id=job_id,
    )
    db.add(log)
    db.commit()
    db.refresh(user)


def _maybe_fire_webhooks(user, result, db):
    active_hooks = [w for w in user.webhooks if w.is_active and "summarize.complete" in w.event_list]
    if not active_hooks:
        return
    try:
        from app.tasks import deliver_webhook
        payload = {"event": "summarize.complete", "data": result, "user_id": str(user.id)}
        for hook in active_hooks:
            deliver_webhook.delay(hook.url, payload, hook.secret)
    except Exception:
        pass


@router.post("", response_model=SummarizeResponse)
def summarize_sync(
    payload: SummarizeRequest,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Summarize synchronously. Checks Redis cache before running inference."""
    user = _resolve_user(db, credentials, x_api_key)
    user = enforce_monthly_limit(user)

    cached = cache.get_cached_summary(payload.text, payload.language, payload.max_length)
    if cached:
        try:
            from app.metrics import CACHE_HITS
            CACHE_HITS.inc()
        except ImportError:
            pass
        _write_usage_log(db, user, payload, {**cached, "cached": True})
        _maybe_fire_webhooks(user, cached, db)
        return SummarizeResponse(**cached, requests_remaining=user.remaining_requests, cached=True)

    try:
        from app.metrics import CACHE_MISSES
        CACHE_MISSES.inc()
    except ImportError:
        pass

    if not summarizer.is_model_loaded():
        raise HTTPException(status_code=503, detail="Model loading — please retry in a moment.")

    try:
        summary, detected_lang, token_count = summarizer.summarize(
            text=payload.text,
            language=payload.language,
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
        "original_length": len(payload.text),
        "summary_length": len(summary),
        "model": "google/mt5-small",
        "cached": False,
    }
    cache.set_cached_summary(payload.text, payload.language, payload.max_length, result)
    _write_usage_log(db, user, payload, result)
    _maybe_fire_webhooks(user, result, db)

    return SummarizeResponse(**result, requests_remaining=user.remaining_requests)


@router.post("/async", response_model=AsyncJobResponse, status_code=status.HTTP_202_ACCEPTED)
def summarize_submit_async(
    payload: SummarizeRequest,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Submit a summarization job to Celery. Returns job_id immediately."""
    user = _resolve_user(db, credentials, x_api_key)
    user = enforce_monthly_limit(user)

    try:
        from app.tasks import summarize_async
        from app.metrics import CELERY_TASKS_SUBMITTED
        task = summarize_async.delay(
            text=payload.text, language=payload.language,
            max_length=payload.max_length, user_id=str(user.id),
        )
        CELERY_TASKS_SUBMITTED.inc()
        user.usage_count += 1
        log = UsageLog(user_id=user.id, article_language=payload.language,
                       characters_used=len(payload.text), summary_tokens=0, job_id=task.id)
        db.add(log)
        db.commit()
        return AsyncJobResponse(job_id=task.id, status="PENDING", message="Job queued successfully.")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Poll for async job result."""
    user = _resolve_user(db, credentials, x_api_key)

    try:
        from celery.result import AsyncResult
        from app.worker import celery_app
        task_result = AsyncResult(job_id, app=celery_app)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Queue unavailable: {exc}")

    status_str = task_result.status
    if status_str == "SUCCESS":
        data = task_result.result
        log = db.query(UsageLog).filter(UsageLog.job_id == job_id).first()
        if log and log.summary_tokens == 0:
            log.summary_tokens = data.get("tokens_used", 0)
            log.from_cache = data.get("cached", False)
            log.article_language = data.get("language_detected", "auto")
            db.commit()
        return JobStatusResponse(
            job_id=job_id, status=status_str,
            result=SummarizeResponse(**data, requests_remaining=user.remaining_requests),
        )
    elif status_str == "FAILURE":
        return JobStatusResponse(job_id=job_id, status=status_str, error=str(task_result.result))
    return JobStatusResponse(job_id=job_id, status=status_str)
