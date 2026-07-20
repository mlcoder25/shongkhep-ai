"""
Redis-backed cache for Shongkhep AI.

Responsibilities:
  - Summary result caching (hash of text + language → summary)
  - Rate limit counter backing (via limits[redis])
  - Generic key/value helpers used by other modules
"""
import hashlib
import json
import logging
from typing import Optional, Any

import redis as redis_lib
from app.config import settings

logger = logging.getLogger(__name__)

# ─── Connection pool ──────────────────────────────────────────────────────────
_pool: Optional[redis_lib.ConnectionPool] = None
_client: Optional[redis_lib.Redis] = None


def get_redis() -> Optional[redis_lib.Redis]:
    """Return the shared Redis client, or None if unavailable."""
    return _client


def connect() -> bool:
    """
    Initialise the Redis connection pool.
    Called once at app startup. Returns True on success.
    """
    global _pool, _client
    try:
        _pool = redis_lib.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )
        _client = redis_lib.Redis(connection_pool=_pool)
        _client.ping()
        logger.info("Redis connected: %s", settings.REDIS_URL)
        return True
    except Exception as exc:
        logger.warning("Redis unavailable — caching disabled: %s", exc)
        _client = None
        return False


def disconnect():
    """Close Redis connection pool on shutdown."""
    global _client, _pool
    if _pool:
        _pool.disconnect()
    _client = None
    _pool = None


# ─── Summary cache ────────────────────────────────────────────────────────────

def _summary_key(text: str, language: str, max_length: Optional[int]) -> str:
    """Deterministic cache key for a summarization request."""
    raw = f"{text}|{language}|{max_length or 'default'}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"summary:{digest}"


def get_cached_summary(text: str, language: str, max_length: Optional[int]) -> Optional[dict]:
    """
    Return a cached summary result dict, or None on miss / Redis unavailable.
    """
    if _client is None:
        return None
    try:
        key = _summary_key(text, language, max_length)
        value = _client.get(key)
        if value:
            logger.debug("Cache HIT for key %s", key[:20])
            return json.loads(value)
        return None
    except Exception as exc:
        logger.warning("Cache get error: %s", exc)
        return None


def set_cached_summary(
    text: str,
    language: str,
    max_length: Optional[int],
    result: dict,
    ttl: int = None,
) -> bool:
    """
    Store a summary result in Redis. Returns True if stored.
    """
    if _client is None:
        return False
    try:
        key = _summary_key(text, language, max_length)
        _client.setex(key, ttl or settings.CACHE_TTL_SECONDS, json.dumps(result))
        logger.debug("Cache SET key %s TTL=%ss", key[:20], ttl or settings.CACHE_TTL_SECONDS)
        return True
    except Exception as exc:
        logger.warning("Cache set error: %s", exc)
        return False


# ─── Generic helpers ──────────────────────────────────────────────────────────

def set_value(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    if _client is None:
        return False
    try:
        serialised = json.dumps(value) if not isinstance(value, str) else value
        if ttl:
            _client.setex(key, ttl, serialised)
        else:
            _client.set(key, serialised)
        return True
    except Exception:
        return False


def get_value(key: str) -> Optional[str]:
    if _client is None:
        return None
    try:
        return _client.get(key)
    except Exception:
        return None


def delete_key(key: str) -> bool:
    if _client is None:
        return False
    try:
        _client.delete(key)
        return True
    except Exception:
        return False


def health_check() -> dict:
    """Return Redis health info for the /health endpoint."""
    if _client is None:
        return {"status": "unavailable", "url": settings.REDIS_URL}
    try:
        info = _client.info("server")
        return {
            "status": "ok",
            "version": info.get("redis_version"),
            "used_memory_human": info.get("used_memory_human"),
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
