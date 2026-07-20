"""
PDF text extractor for Shongkhep AI — with OCR support.

Extraction strategy (in order):
  1. PyMuPDF direct text extraction  — fast, works for text-based PDFs
  2. PyMuPDF block extraction         — better for multi-column layouts
  3. pytesseract OCR                  — fallback for scanned/image PDFs
     - Supports: English + Bangla (ben) via Tesseract language packs

Limits:
  - Max 20MB file size
  - Max 50 pages (OCR: max 20 pages — slower)
  - Extracts up to 10,000 chars
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB  = 20
MAX_PAGES         = 50
MAX_PAGES_OCR     = 20      # OCR is slow — limit pages
MAX_CHARS         = 10000
MIN_CHARS         = 30


class PDFExtractError(Exception):
    pass


@dataclass
class PDFResult:
    text: str
    title: str
    page_count: int
    pages_read: int
    char_count: int
    is_scanned: bool
    used_ocr: bool
    language_hint: str


def _detect_language(text: str) -> str:
    bangla = len(re.findall(r'[\u0980-\u09FF]', text))
    alpha  = len(re.findall(r'[a-zA-Z\u0980-\u09FF]', text))
    if alpha and bangla / alpha > 0.3:
        return "bn"
    return "en"


def _clean(text: str) -> str:
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\r',   '\n', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def _is_tesseract_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _get_tesseract_lang(language_hint: str) -> str:
    """Return tesseract language string. Bangla = ben, English = eng."""
    if language_hint == "bn":
        return "ben+eng"
    return "eng+ben"   # try both, eng primary


def _ocr_page(page, lang: str = "eng+ben") -> str:
    """
    Run Tesseract OCR on a single PyMuPDF page.
    Renders the page to a high-res image then runs OCR.
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        # Render at 300 DPI for good OCR accuracy
        mat  = page.get_pixmap(matrix=__import__('fitz').Matrix(300 / 72, 300 / 72))
        img  = Image.frombytes("RGB", [mat.width, mat.height], mat.samples)
        text = pytesseract.image_to_string(img, lang=lang, config="--oem 3 --psm 6")
        return text
    except Exception as exc:
        logger.warning("OCR failed on page: %s", exc)
        return ""


def extract_text_from_bytes(
    file_bytes: bytes,
    filename: str = "document.pdf",
    force_ocr: bool = False,
) -> PDFResult:
    """
    Extract text from PDF bytes.

    Args:
        file_bytes: raw PDF content
        filename:   original filename (used for title fallback)
        force_ocr:  skip direct extraction, go straight to OCR

    Raises:
        PDFExtractError: if file is invalid, too large, encrypted, or no text found.
    """
    # ── Size check ────────────────────────────────────────────────────────────
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise PDFExtractError(
            f"File too large ({size_mb:.1f} MB). Maximum is {MAX_FILE_SIZE_MB} MB."
        )

    # ── Import PyMuPDF ────────────────────────────────────────────────────────
    try:
        import fitz
    except ImportError:
        raise PDFExtractError("PDF library not installed. Contact support.")

    # ── Open ──────────────────────────────────────────────────────────────────
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFExtractError(f"Could not open PDF: {exc}")

    if doc.is_encrypted:
        raise PDFExtractError("Password-protected PDFs are not supported.")

    total_pages   = doc.page_count
    pages_to_read = min(total_pages, MAX_PAGES)

    # ── Title ─────────────────────────────────────────────────────────────────
    meta  = doc.metadata or {}
    title = (meta.get("title") or "").strip()
    if not title:
        title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()

    # ── Strategy 1 & 2: Direct text extraction ────────────────────────────────
    all_parts   = []
    total_chars = 0
    is_scanned  = True
    used_ocr    = False

    if not force_ocr:
        for page_num in range(pages_to_read):
            if total_chars >= MAX_CHARS:
                break
            try:
                page      = doc[page_num]
                page_text = page.get_text("text")

                # Fallback to block extraction for complex layouts
                if len(page_text.strip()) < 20:
                    blocks    = page.get_text("blocks")
                    page_text = "\n".join(
                        b[4] for b in blocks
                        if isinstance(b[4], str) and len(b[4].strip()) > 5
                    )

                page_text = _clean(page_text)
                if len(page_text.strip()) > 10:
                    is_scanned = False
                    remaining  = MAX_CHARS - total_chars
                    all_parts.append(page_text[:remaining])
                    total_chars += len(page_text[:remaining])

            except Exception as exc:
                logger.warning("Page %d read error: %s", page_num + 1, exc)

    full_text = _clean("\n\n".join(all_parts))

    # ── Strategy 3: OCR fallback ──────────────────────────────────────────────
    if (is_scanned or force_ocr or len(full_text) < MIN_CHARS):
        if _is_tesseract_available():
            logger.info(
                "PDF '%s' — low text yield (%d chars), attempting OCR on %d pages",
                filename, len(full_text), min(total_pages, MAX_PAGES_OCR),
            )

            # Detect language hint from whatever text we have
            lang_hint = _detect_language(full_text) if full_text else "en"
            tess_lang = _get_tesseract_lang(lang_hint)

            ocr_parts   = []
            ocr_chars   = 0
            pages_for_ocr = min(total_pages, MAX_PAGES_OCR)

            for page_num in range(pages_for_ocr):
                if ocr_chars >= MAX_CHARS:
                    break
                try:
                    page      = doc[page_num]
                    ocr_text  = _ocr_page(page, lang=tess_lang)
                    ocr_text  = _clean(ocr_text)
                    if len(ocr_text.strip()) > 10:
                        remaining = MAX_CHARS - ocr_chars
                        ocr_parts.append(ocr_text[:remaining])
                        ocr_chars += len(ocr_text[:remaining])
                except Exception as exc:
                    logger.warning("OCR page %d failed: %s", page_num + 1, exc)

            if ocr_parts:
                full_text  = _clean("\n\n".join(ocr_parts))
                is_scanned = True
                used_ocr   = True
                total_chars = len(full_text)
                logger.info("OCR extracted %d chars from '%s'", total_chars, filename)
        else:
            logger.warning(
                "Tesseract not available — cannot OCR '%s'. "
                "Install tesseract-ocr in the Docker image.", filename
            )

    doc.close()

    # ── Final validation ──────────────────────────────────────────────────────
    if not full_text or len(full_text) < MIN_CHARS:
        raise PDFExtractError(
            f"Could not extract readable text from this PDF "
            f"(only {len(full_text)} characters found). "
            "The file may be a scanned image without a text layer, "
            "or the text may be embedded as graphics."
        )

    lang = _detect_language(full_text)

    logger.info(
        "PDF '%s' done — %d/%d pages, %d chars, lang=%s, ocr=%s",
        filename, min(pages_to_read, total_pages), total_pages,
        len(full_text), lang, used_ocr,
    )

    return PDFResult(
        text=full_text,
        title=title,
        page_count=total_pages,
        pages_read=pages_to_read,
        char_count=len(full_text),
        is_scanned=is_scanned,
        used_ocr=used_ocr,
        language_hint=lang,
    )
