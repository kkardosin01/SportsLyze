"""Task principal: processa um vídeo enviado (download -> pipeline de CV ->
persistência dos resultados -> notificação). Roda inteiramente em worker
assíncrono — nunca na request HTTP da API."""

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task
from sportslyze_cv.pipeline import VideoProcessingPipeline

from src.core.config import get_settings
from src.db.session import get_supabase_admin

logger = logging.getLogger(__name__)

# Máximo de tentativas automáticas antes de marcar o job como `failed`
# definitivamente (falhas transitórias de rede/storage se beneficiam de retry;
# vídeo corrompido ou codec inválido não se beneficia e falha rápido).
MAX_RETRIES = 2


@shared_task(name="tasks.process_video", bind=True, max_retries=MAX_RETRIES)
def process_video(self, video_id: str, job_id: str) -> None:
    db = get_supabase_admin()
    settings = get_settings()

    try:
        _update_job(db, job_id, status="processing", current_stage="iniciando", progress_pct=0, started_at=_now())

        video = db.table("videos").select("*").eq("id", video_id).single().execute().data
        if video is None:
            raise ValueError(f"Vídeo {video_id} não encontrado.")

        with tempfile.TemporaryDirectory(prefix="sportslyze_video_") as tmp_dir:
            local_path = _download_video(db, settings, video["storage_path"], tmp_dir)

            pipeline = VideoProcessingPipeline(
                detect_model_path=settings.yolo_model_path, enable_ocr=settings.enable_ocr
            )

            def on_progress(stage: str, pct: int) -> None:
                _update_job(db, job_id, current_stage=stage, progress_pct=pct)

            result = pipeline.run(local_path, on_progress=on_progress)

        _persist_results(db, video_id, result)

        _update_job(
            db, job_id, status="done", current_stage="concluido", progress_pct=100, finished_at=_now()
        )

        from src.tasks.notifications import notify_analysis_done

        notify_analysis_done.delay(video_id)

    except Exception as exc:  # noqa: BLE001 — job precisa registrar qualquer falha, não só as esperadas
        logger.exception("Falha ao processar vídeo %s", video_id)
        if self.request.retries < MAX_RETRIES:
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

        _update_job(
            db,
            job_id,
            status="failed",
            error_message=_user_friendly_error(exc),
            finished_at=_now(),
        )
        from src.tasks.notifications import notify_analysis_failed

        notify_analysis_failed.delay(video_id, _user_friendly_error(exc))


def _download_video(db, settings, storage_path: str, tmp_dir: str) -> Path:
    bucket = settings.supabase_storage_bucket_videos
    data = db.storage.from_(bucket).download(storage_path)
    local_path = Path(tmp_dir) / "source.mp4"
    local_path.write_bytes(data)
    return local_path


def _persist_results(db, video_id: str, result) -> None:
    for player in result.players:
        db.table("detected_players").upsert(
            {
                "video_id": video_id,
                "track_id": player.track_id,
                "label": player.label,
                "ocr_jersey_number": player.ocr_jersey_number,
                "ocr_confidence": player.ocr_confidence,
                "thumbnail_path": player.thumbnail_path,
            },
            on_conflict="video_id,track_id",
        ).execute()

        detected = (
            db.table("detected_players")
            .select("id")
            .eq("video_id", video_id)
            .eq("track_id", player.track_id)
            .single()
            .execute()
            .data
        )

        db.table("player_match_stats").insert(
            {
                "video_id": video_id,
                "detected_player_id": detected["id"],
                "distance_km": player.distance_km,
                "avg_speed_kmh": player.avg_speed_kmh,
                "max_speed_kmh": player.max_speed_kmh,
                "heatmap": player.heatmap,
            }
        ).execute()

    if result.field_calibrated and result.homography_matrix:
        db.table("field_homography").insert(
            {
                "video_id": video_id,
                "segment_start_ms": 0,
                "segment_end_ms": int(result.duration_seconds * 1000),
                "homography_matrix": result.homography_matrix,
            }
        ).execute()


def _update_job(db, job_id: str, **fields) -> None:
    db.table("analysis_jobs").update(fields).eq("id", job_id).execute()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_friendly_error(exc: Exception) -> str:
    return (
        "Não foi possível concluir a análise deste vídeo. Verifique se o arquivo "
        "não está corrompido e tente novamente. Se o problema persistir, "
        "entre em contato com o suporte."
    )
