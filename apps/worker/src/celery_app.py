from celery import Celery
from celery.schedules import crontab

from src.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sportslyze_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.tasks.process_video",
        "src.tasks.reference_frame",
        "src.tasks.generate_report",
        "src.tasks.notifications",
        "src.tasks.cleanup",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=6 * 60 * 60,  # 6h — vídeos de ~90-120min podem levar bastante para processar
    task_soft_time_limit=6 * 60 * 60 - 60,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Job diário de limpeza de vídeos originais expirados (retenção configurável por vídeo)
celery_app.conf.beat_schedule = {
    "cleanup-expired-videos": {
        "task": "tasks.cleanup_expired_videos",
        "schedule": crontab(hour=3, minute=0),
    },
}
