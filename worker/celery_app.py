from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "deribit_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "fetch-crypto-prices-every-minute": {
            "task": "worker.tasks.fetch_and_store_prices",
            "schedule": settings.price_fetch_interval_seconds,
        },
    },
)