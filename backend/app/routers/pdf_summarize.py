"""
PDF summarization endpoint.
  POST /api/v1/summarize/pdf
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UsageLog
from app.dependencies import enforce_monthly_limit
from app import summarizer, cache
from app.auth import decode_access_token
from app.pdf_extractor import extract_text_from_bytes, PDFExtractError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["PDF Summarization"])
bearer_scheme = HTTPBearer(auto_error=False)


class PDFSummarizeResponse(BaseModel):
    summary: str
    title: str
    page_count: int
    pages_read: int
    original_length: int
    summary_length: int
    language_detected: str
    tokens_used: int
    requests_remaining: int
    model: str
    cached: bool = False
    used_ocr: bool = False


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


@router.post("/api/v1/summarize/pdf", response_model=PDFSummarizeResponse)
async def summarize_pdf(
    file: UploadFile = File(..., description="PDF file to summarize (max 20 MB)"),
    language: str = Form(default="auto", description="Language hint: auto | en | bn"),
    max_length: Optional[int] = Form(default=None),
    force_ocr: bool = Form(default=False, description="Force OCR even if text is found"),
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    Upload a PDF and get an AI summary.

    - Text-based PDFs: fast direct extraction
    - Scanned/image PDFs: automatic OCR via Tesseract (Bangla + English)
    - Up to 20 MB, 50 pages (OCR: 20 pages max)
    - Results cached in Redis for 1 hour
    """
    user = _resolve_user(db, credentials, x_api_key)
    user = enforce_monthly_limit(user)

    # File validation — just check extension
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Extract text (with OCR fallback)
    try:
        pdf_result = extract_text_from_bytes(file_bytes, filename, force_ocr=force_ocr)
    except PDFExtractError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected PDF extraction error: %s", exc)
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {exc}")

    effective_lang = language if language != "auto" else pdf_result.language_hint

    # Cache check
    cached = cache.get_cached_summary(pdf_result.text, effective_lang, max_length)
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
            characters_used=pdf_result.char_count,
            summary_tokens=cached["tokens_used"],
            from_cache=True,
            endpoint="/api/v1/summarize/pdf",
        ))
        db.commit()
        db.refresh(user)
        return PDFSummarizeResponse(
            **cached,
            title=pdf_result.title,
            page_count=pdf_result.page_count,
            pages_read=pdf_result.pages_read,
            requests_remaining=user.remaining_requests,
            cached=True,
            used_ocr=pdf_result.used_ocr,
        )

    if not summarizer.is_model_loaded():
        raise HTTPException(status_code=503, detail="Model loading — please retry shortly.")

    try:
        summary, detected_lang, token_count = summarizer.summarize(
            text=pdf_result.text,
            language=effective_lang,
            max_length=max_length,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}")

    result = {
        "summary":           summary,
        "language_detected": detected_lang,
        "tokens_used":       token_count,
        "original_length":   pdf_result.char_count,
        "summary_length":    len(summary),
        "model":             "qwen3:8b",
        "cached":            False,
    }
    cache.set_cached_summary(pdf_result.text, effective_lang, max_length, result)

    user.usage_count += 1
    db.add(UsageLog(
        user_id=user.id,
        article_language=detected_lang,
        characters_used=pdf_result.char_count,
        summary_tokens=token_count,
        from_cache=False,
        endpoint="/api/v1/summarize/pdf",
    ))
    db.commit()
    db.refresh(user)

    return PDFSummarizeResponse(
        **result,
        title=pdf_result.title,
        page_count=pdf_result.page_count,
        pages_read=pdf_result.pages_read,
        requests_remaining=user.remaining_requests,
        used_ocr=pdf_result.used_ocr,
    )
