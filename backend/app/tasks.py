"""
Celery tasks for Shongkhep AI.

Tasks:
  summarize_async  — Run mT5 inference in a background worker process.
  deliver_webhook  — POST a summary result to a user-registered webhook URL.
"""
import logging
from typing import Optional

import httpx
from celery import Task
from celery.utils.log import get_task_logger

from app.worker import celery_app
from app.config import settings

logger = get_task_logger(__name__)


# ─── Model bootstrap for Celery workers ──────────────────────────────────────

class SummarizeTask(Task):
    """
    Custom Task class that loads the mT5 model once per worker process
    (not once per task call), saving significant startup overhead.
    """
    abstract = True
    _model_loaded: bool = False

    def __init__(self):
        super().__init__()
        self._model_loaded = False

    @property
    def model_ready(self) -> bool:
        if not self._model_loaded:
            from app import summarizer
            ok = summarizer.load_model(settings.MODEL_NAME)
            self._model_loaded = ok
        return self._model_loaded


# ─── Summarize task ───────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    base=SummarizeTask,
    name="app.tasks.summarize_async",
    max_retries=2,
    default_retry_delay=5,
    throws=(ValueError,),
)
def summarize_async(
    self,
    text: str,
    language: str = "auto",
    max_length: Optional[int] = None,
    user_id: Optional[str] = None,
) -> dict:
    """
    Run mT5 inference asynchronously.

    Returns:
        {
            "summary": str,
            "language_detected": str,
            "tokens_used": int,
            "original_length": int,
            "summary_length": int,
            "model": str,
        }
    """
    if not self.model_ready:
        raise self.retry(exc=RuntimeError("Model not ready"), countdown=10)

    try:
        from app import summarizer
        from app import cache

        # Check cache first
        cached = cache.get_cached_summary(text, language, max_length)
        if cached:
            logger.info("Cache hit for user=%s lang=%s", user_id, language)
            return cached

        summary, detected_lang, token_count = summarizer.summarize(
            text=text,
            language=language,
            max_length=max_length,
        )

        result = {
            "summary": summary,
            "language_detected": detected_lang,
            "tokens_used": token_count,
            "original_length": len(text),
            "summary_length": len(summary),
            "model": settings.MODEL_NAME,
            "cached": False,
        }

        cache.set_cached_summary(text, language, max_length, result)
        logger.info("Summarization complete user=%s lang=%s tokens=%d", user_id, detected_lang, token_count)
        return result

    except Exception as exc:
        logger.exception("summarize_async failed for user=%s: %s", user_id, exc)
        raise self.retry(exc=exc)


# ─── Webhook delivery task ────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="app.tasks.deliver_webhook",
    max_retries=settings.WEBHOOK_MAX_RETRIES,
    default_retry_delay=30,
)
def deliver_webhook(
    self,
    webhook_url: str,
    payload: dict,
    secret: Optional[str] = None,
) -> dict:
    """
    POST a JSON payload to a user-registered webhook endpoint.
    Signs the request with HMAC-SHA256 if a secret is provided.

    Returns status dict with http_status.
    """
    import hashlib, hmac, json, time

    headers = {
        "Content-Type": "application/json",
        "User-Agent": f"ShongkhepAI-Webhook/{settings.APP_VERSION}",
        "X-Shongkhep-Event": payload.get("event", "summarize.complete"),
        "X-Shongkhep-Timestamp": str(int(time.time())),
    }

    if secret:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        headers["X-Shongkhep-Signature"] = f"sha256={sig}"
    else:
        body = json.dumps(payload)

    try:
        with httpx.Client(timeout=settings.WEBHOOK_TIMEOUT_SECONDS) as client:
            resp = client.post(webhook_url, content=body, headers=headers)
            resp.raise_for_status()
            logger.info("Webhook delivered to %s → HTTP %d", webhook_url, resp.status_code)
            return {"delivered": True, "http_status": resp.status_code}

    except httpx.HTTPStatusError as exc:
        logger.warning("Webhook HTTP error %s → %d", webhook_url, exc.response.status_code)
        raise self.retry(exc=exc)

    except (httpx.TimeoutException, httpx.RequestError) as exc:
        logger.warning("Webhook request error %s: %s", webhook_url, exc)
        raise self.retry(exc=exc)
