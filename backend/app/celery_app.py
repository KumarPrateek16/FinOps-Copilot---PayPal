from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "finops_copilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes maximum for heavy agent operations
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Scheduled background tasks (Beat)
celery_app.conf.beat_schedule = {
    "sync-cashflow-sentinel-hourly": {
        "task": "app.workers.cashflow_tasks.sync_all_merchants_cashflow",
        "schedule": crontab(minute=0),  # Top of every hour
    },
}

