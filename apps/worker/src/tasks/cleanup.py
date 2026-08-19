"""Job diário (Celery beat) que apaga o arquivo original de vídeos cuja
retenção expirou. A análise (clipes, eventos, stats, relatórios) continua
disponível normalmente — apenas o arquivo-fonte é removido do storage."""

import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task

from src.core.config import get_settings
from src.db.session import get_supabase_admin

logger = logging.getLogger(__name__)


@shared_task(name="tasks.cleanup_expired_videos")
def cleanup_expired_videos() -> int:
    db = get_supabase_admin()
    settings = get_settings()
    bucket = settings.supabase_storage_bucket_videos

    now = datetime.now(timezone.utc)
    # Busca vídeos ainda não limpos cujo job de análise já terminou (nunca
    # apagamos o original antes de a análise ter sido concluída com sucesso).
    candidates = (
        db.table("videos")
        .select("id, storage_path, retention_days, created_at, analysis_jobs(status)")
        .is_("original_deleted_at", "null")
        .not_.is_("storage_path", "null")
        .execute()
        .data
        or []
    )

    deleted_count = 0
    for video in candidates:
        jobs = video.get("analysis_jobs") or []
        if not any(job.get("status") == "done" for job in jobs):
            continue

        created_at = datetime.fromisoformat(video["created_at"])
        expires_at = created_at + timedelta(days=video["retention_days"])
        if now < expires_at:
            continue

        try:
            db.storage.from_(bucket).remove([video["storage_path"]])
            db.table("videos").update(
                {"storage_path": None, "original_deleted_at": now.isoformat()}
            ).eq("id", video["id"]).execute()
            deleted_count += 1
        except Exception:  # noqa: BLE001 — não interrompe a limpeza dos demais vídeos
            logger.exception("Falha ao apagar vídeo expirado %s", video["id"])

    logger.info("Limpeza de retenção: %d vídeo(s) removido(s).", deleted_count)
    return deleted_count
