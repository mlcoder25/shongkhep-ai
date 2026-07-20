"""
Celery application instance for Shongkhep AI.

Import this module to get the ``celery_app`` object.
The actual task definitions live in ``app/tasks.py``.

Start a worker with:
    celery -A app.worker worker --loglevel=info --concurrency=2
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "shongkhep",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timeouts
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,

    # Result expiry — keep job results for 24 hours
    result_expires=86400,

    # Retry
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Routing
    task_default_queue="summarize",
    task_routes={
        "app.tasks.summarize_async": {"queue": "summarize"},
        "app.tasks.deliver_webhook": {"queue": "webhooks"},
    },

    # Worker
    worker_prefetch_multiplier=1,   # one task at a time per worker (model is heavy)
    worker_max_tasks_per_child=50,  # recycle workers to prevent memory leaks
)
