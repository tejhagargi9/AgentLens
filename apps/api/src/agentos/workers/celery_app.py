from celery import Celery

from agentos.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "agentos",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["agentos.workers.tasks"],
)
celery_app.conf.task_track_started = True
