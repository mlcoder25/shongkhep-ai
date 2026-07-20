"""
Prometheus metrics for Shongkhep AI.

Metrics exposed at /metrics (scraped by Prometheus):
  - shongkhep_inference_latency_seconds   Histogram
  - shongkhep_inference_total             Counter (by language)
  - shongkhep_cache_hits_total            Counter
  - shongkhep_cache_misses_total          Counter
  - shongkhep_api_requests_total          Counter (by endpoint, status)
  - shongkhep_active_users_total          Gauge
  - shongkhep_plan_users                  Gauge (by plan)
"""
from prometheus_client import Counter, Histogram, Gauge, Summary

# ─── Inference ────────────────────────────────────────────────────────────────
INFERENCE_LATENCY = Histogram(
    "shongkhep_inference_latency_seconds",
    "mT5 inference duration in seconds",
    buckets=[0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0],
)

INFERENCE_COUNTER = Counter(
    "shongkhep_inference_total",
    "Total summarization requests processed by the model",
    labelnames=["language"],
)

# ─── Cache ────────────────────────────────────────────────────────────────────
CACHE_HITS = Counter(
    "shongkhep_cache_hits_total",
    "Summary results served from Redis cache",
)

CACHE_MISSES = Counter(
    "shongkhep_cache_misses_total",
    "Summarization requests that required model inference (cache miss)",
)

# ─── API ──────────────────────────────────────────────────────────────────────
API_REQUESTS = Counter(
    "shongkhep_api_requests_total",
    "Total API requests by endpoint and HTTP status",
    labelnames=["endpoint", "method", "status_code"],
)

# ─── Business metrics ─────────────────────────────────────────────────────────
ACTIVE_USERS = Gauge(
    "shongkhep_active_users_total",
    "Total registered active users",
)

PLAN_USERS = Gauge(
    "shongkhep_plan_users",
    "Number of users per plan",
    labelnames=["plan"],
)

MONTHLY_USAGE_RATIO = Summary(
    "shongkhep_monthly_usage_ratio",
    "Distribution of usage_count / monthly_limit across all users",
)

# ─── Celery ───────────────────────────────────────────────────────────────────
CELERY_TASKS_SUBMITTED = Counter(
    "shongkhep_celery_tasks_submitted_total",
    "Async summarize tasks submitted to Celery queue",
)

CELERY_TASKS_FAILED = Counter(
    "shongkhep_celery_tasks_failed_total",
    "Async summarize tasks that ended in failure",
)
