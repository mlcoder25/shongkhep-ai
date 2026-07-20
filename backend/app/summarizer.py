"""
Summarizer module for Shongkhep AI — Qwen3 via Ollama.
"""
import re
import time
import logging
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

_model_loaded    = False
_model_name      = "qwen3:8b"
_ollama_base_url = "http://host.docker.internal:11434"
_use_ollama      = True
_tokenizer       = None
_model           = None


def load_model(model_name: str = "qwen3:8b") -> bool:
    global _model_loaded, _model_name, _use_ollama, _tokenizer, _model
    _model_name = model_name

    if _try_ollama(model_name):
        _use_ollama   = True
        _model_loaded = True
        logger.info("Using Ollama model: %s (MPS Apple Silicon)", model_name)
        return True

    logger.warning("Ollama unavailable — falling back to google/mt5-base")
    return _load_transformers_fallback()


def _try_ollama(model_name: str) -> bool:
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(f"{_ollama_base_url}/api/tags")
            if resp.status_code != 200:
                return False
            models = [m["name"] for m in resp.json().get("models", [])]
            base = model_name.split(":")[0]
            if not any(base in m for m in models):
                logger.warning("Ollama running but model '%s' not found. Run: ollama pull %s", model_name, model_name)
                return False
            logger.info("Ollama found model: %s", model_name)
            return True
    except Exception as exc:
        logger.debug("Ollama check failed: %s", exc)
        return False


def _load_transformers_fallback() -> bool:
    global _model_loaded, _use_ollama, _tokenizer, _model
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        fallback = "google/mt5-base"
        logger.info("Loading fallback model: %s", fallback)
        _tokenizer    = AutoTokenizer.from_pretrained(fallback)
        _model        = AutoModelForSeq2SeqLM.from_pretrained(fallback)
        _model.eval()
        _use_ollama   = False
        _model_loaded = True
        logger.info("Fallback %s loaded.", fallback)
        return True
    except Exception as exc:
        logger.error("Failed to load fallback: %s", exc)
        _model_loaded = False
        return False


def is_model_loaded() -> bool:
    return _model_loaded


def get_model_info() -> dict:
    if _use_ollama:
        return {"backend": "ollama", "model": _model_name, "url": _ollama_base_url, "device": "MPS (Apple Silicon)"}
    return {"backend": "transformers", "model": "google/mt5-base", "device": "cpu"}


def detect_language(text: str) -> str:
    bangla = len(re.findall(r'[\u0980-\u09FF]', text))
    alpha  = len(re.findall(r'[a-zA-Z\u0980-\u09FF]', text))
    if alpha and bangla / alpha > 0.3:
        return "bn"
    return "en"


def _build_ollama_messages(text: str, language: str) -> list:
    """
    /no_think MUST be at the END of the user message for Qwen3.
    It disables the chain-of-thought thinking block.
    Do NOT put it in the system prompt.
    """
    if language == "bn":
        user_content = (
            "নিচের বাংলা নিবন্ধটি পড়ো এবং ৩-৫টি স্পষ্ট বাক্যে সংক্ষেপ লেখো। "
            "শুধু সংক্ষেপ লেখো, অন্য কিছু নয়।\n\n"
            f"নিবন্ধ:\n{text}\n\n/no_think"
        )
    else:
        user_content = (
            "Read the following article and write a clear, concise summary in 3-5 sentences. "
            "Write ONLY the summary text, nothing else.\n\n"
            f"Article:\n{text}\n\n/no_think"
        )
    return [
        {
            "role": "system",
            "content": (
                "You are a professional news summarizer. "
                "Always reply with ONLY the summary text. "
                "No labels, no preamble, no extra commentary."
            ),
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]


def _clean_qwen_output(text: str) -> str:
    # Strip thinking blocks (even if /no_think didn't fully suppress them)
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Remove special tokens
    text = re.sub(r'<\|[^|]*\|>', '', text)
    text = re.sub(r'<extra_id_\d+>', '', text)
    # Remove common preamble labels
    text = re.sub(r'^(Here is |Here\'s |The summary:?|Summary:?)\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^সংক্ষেপ:?\s*', '', text, flags=re.IGNORECASE)
    # Clean whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def summarize(
    text: str,
    language: str = "auto",
    max_length: Optional[int] = None,
    min_length: int = 40,
) -> Tuple[str, str, int]:
    if not _model_loaded:
        raise RuntimeError("Summarization model is not loaded.")

    detected_lang = detect_language(text) if language == "auto" else language

    if _use_ollama:
        return _summarize_ollama(text, detected_lang, max_length)
    else:
        return _summarize_mt5(text, detected_lang, max_length, min_length)


def _summarize_ollama(text: str, language: str, max_length: Optional[int]) -> Tuple[str, str, int]:
    from app.config import settings

    messages = _build_ollama_messages(text, language)

    # num_predict must be large enough to cover thinking + summary
    # With /no_think in user message, thinking is suppressed but we still give headroom
    num_predict = max(512, max_length or settings.MAX_SUMMARY_LENGTH)

    payload = {
        "model":    _model_name,
        "messages": messages,
        "stream":   False,
        "options":  {
            "temperature": 0.3,
            "top_p":       0.9,
            "num_predict": num_predict,
        },
    }

    t0 = time.monotonic()
    try:
        with httpx.Client(timeout=180) as client:
            resp = client.post(f"{_ollama_base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        raise RuntimeError("Ollama timed out (180s). Please retry.")
    except Exception as exc:
        raise RuntimeError(f"Ollama request failed: {exc}")

    elapsed = time.monotonic() - t0
    raw     = data.get("message", {}).get("content", "")

    logger.debug("Qwen3 raw output (%d chars): %r", len(raw), raw[:500])

    summary = _clean_qwen_output(raw)

    if not summary:
        logger.warning("Empty after cleaning. Raw was: %r", raw[:500])
        # Last resort: if raw has content but cleaning removed everything,
        # return the raw text stripped of just the most harmful patterns
        fallback = raw.replace('<think>', '').replace('</think>', '').strip()
        if fallback:
            summary = fallback
        else:
            raise RuntimeError("Model returned empty summary. Please try again.")

    token_count = data.get("eval_count", len(summary.split()))
    logger.info("Qwen3 summarized %d chars → %d tokens in %.1fs", len(text), token_count, elapsed)

    try:
        from app.metrics import INFERENCE_LATENCY, INFERENCE_COUNTER
        INFERENCE_LATENCY.observe(elapsed)
        INFERENCE_COUNTER.labels(language=language).inc()
    except Exception:
        pass

    return summary, language, token_count


def _summarize_mt5(text: str, language: str, max_length: Optional[int], min_length: int) -> Tuple[str, str, int]:
    import torch
    from app.config import settings

    resolved_max = max_length or settings.MAX_SUMMARY_LENGTH
    resolved_min = min(min_length, resolved_max - 10)

    inputs = _tokenizer(
        f"summarize: {text}",
        return_tensors="pt", max_length=512, truncation=True, padding=False,
    )
    device = next(_model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    t0 = time.monotonic()
    with torch.no_grad():
        output_ids = _model.generate(
            inputs["input_ids"],
            attention_mask=inputs.get("attention_mask"),
            max_length=resolved_max, min_length=resolved_min,
            num_beams=4, early_stopping=True, no_repeat_ngram_size=3, length_penalty=1.0,
        )
    elapsed = time.monotonic() - t0

    summary = _tokenizer.decode(output_ids[0], skip_special_tokens=True)
    summary = re.sub(r'<extra_id_\d+>', '', summary).strip()
    summary = re.sub(r'[।,\s]{3,}', '। ', summary).strip()
    summary = re.sub(r'\s+', ' ', summary).strip()
    token_count = int(output_ids.shape[-1])

    logger.info("mt5-base summarized %d chars in %.1fs", len(text), elapsed)

    try:
        from app.metrics import INFERENCE_LATENCY, INFERENCE_COUNTER
        INFERENCE_LATENCY.observe(elapsed)
        INFERENCE_COUNTER.labels(language=language).inc()
    except Exception:
        pass

    return summary, language, token_count


__all__ = ["load_model", "is_model_loaded", "get_model_info", "summarize", "detect_language"]