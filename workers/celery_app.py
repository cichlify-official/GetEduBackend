from celery import Celery
from config.settings import settings

celery_app = Celery(
    "language_ai_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["workers.ai_tasks"] 
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_routes={
        "workers.ai_tasks.grade_essay": {"queue": "ai_tasks"},
        "workers.ai_tasks.analyze_speaking": {"queue": "ai_tasks"},
    },

    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50,
)
