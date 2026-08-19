from functools import lru_cache

from celery import Celery

from src.core.config import get_settings


@lru_cache
def get_celery_client() -> Celery:
    """Client Celery usado apenas como produtor de tasks pela API.

    A API não importa o código das tasks (isso vive em apps/worker) — apenas
    despacha pelo nome, mantendo API e worker desacoplados e deployáveis
    separadamente.
    """
    settings = get_settings()
    return Celery(broker=settings.redis_url, backend=settings.redis_url)
