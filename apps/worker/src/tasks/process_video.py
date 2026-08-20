"""Task principal: processa um vídeo enviado (download -> pipeline de CV ->
persistência dos resultados -> notificação). Roda inteiramente em worker
assíncrono — nunca na request HTTP da API."""

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task
from sportslyze_cv.events import DetectedEvent
from sportslyze_cv.ffmpeg_utils import (
    cut_clip,
    extract_single_frame,
    get_video_metadata,
)
from sportslyze_cv.pipeline import SelectionHint, VideoProcessingPipeline

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

        # Vídeo de scouting de adversário: os jogadores detectados são do
        # time rival, então marcações manuais do coach (que sempre apontam
        # para `athletes` do próprio clube) não fazem sentido aqui — vincular
        # seria semanticamente errado. Eventos, estatísticas e heatmap
        # continuam sendo calculados normalmente, só o vínculo com o elenco
        # próprio é pulado.
        hint_rows = [] if video["video_type"] == "adversario" else _load_selection_hints(db, video_id)
        selection_hints = [
            SelectionHint(
                athlete_id=row["athlete_id"],
                timestamp_ms=row["timestamp_ms"],
                bbox_xyxy=(row["bbox_x1"], row["bbox_y1"], row["bbox_x2"], row["bbox_y2"]),
            )
            for row in hint_rows
        ]

        with tempfile.TemporaryDirectory(prefix="sportslyze_video_") as tmp_dir:
            local_path = _download_video(db, settings, video["storage_path"], tmp_dir)

            pipeline = VideoProcessingPipeline(
                detect_model_path=settings.yolo_model_path, enable_ocr=settings.enable_ocr
            )

            def on_progress(stage: str, pct: int) -> None:
                _update_job(db, job_id, current_stage=stage, progress_pct=pct)

            result = pipeline.run(local_path, on_progress=on_progress, selection_hints=selection_hints)

            # Persistência fica dentro do `with` porque o corte de clipes
            # (ver `_persist_events`) precisa do arquivo de vídeo baixado,
            # que é apagado assim que o diretório temporário é liberado.
            _persist_results(db, settings, video_id, result, hint_rows, local_path, tmp_dir)

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


def _load_selection_hints(db, video_id: str) -> list[dict]:
    return db.table("player_selection_hints").select("*").eq("video_id", video_id).execute().data or []


def _persist_results(
    db, settings, video_id: str, result, hint_rows: list[dict], local_video_path: Path, tmp_dir: str
) -> None:
    # track_id -> (athlete_id, created_by) para os hints que o pipeline
    # conseguiu casar espacialmente com um track detectado (ver
    # `PipelineResult.resolved_hints` / `_resolve_hints` no cv-pipeline).
    created_by_athlete = {row["athlete_id"]: row["created_by"] for row in hint_rows}
    track_to_hint = {
        track_id: (athlete_id, created_by_athlete[athlete_id])
        for athlete_id, track_id in result.resolved_hints.items()
        if athlete_id in created_by_athlete
    }

    # track_id -> detected_players.id, para vincular os eventos (que se
    # referem a jogadores por track_id) aos registros já persistidos.
    track_to_detected_player_id: dict[int, str] = {}

    for player in result.players:
        payload = {
            "video_id": video_id,
            "track_id": player.track_id,
            "label": player.label,
            "ocr_jersey_number": player.ocr_jersey_number,
            "ocr_confidence": player.ocr_confidence,
            "thumbnail_path": player.thumbnail_path,
        }

        hint_match = track_to_hint.get(player.track_id)
        if hint_match is not None:
            athlete_id, created_by = hint_match
            payload.update(
                {"athlete_id": athlete_id, "linked_by_user_id": created_by, "linked_at": _now()}
            )

        db.table("detected_players").upsert(payload, on_conflict="video_id,track_id").execute()

        detected = (
            db.table("detected_players")
            .select("id")
            .eq("video_id", video_id)
            .eq("track_id", player.track_id)
            .single()
            .execute()
            .data
        )
        track_to_detected_player_id[player.track_id] = detected["id"]

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

    _persist_events(
        db, settings, video_id, result.events, track_to_detected_player_id, local_video_path, tmp_dir
    )


def _persist_events(
    db,
    settings,
    video_id: str,
    events: list[DetectedEvent],
    track_to_detected_player_id: dict[int, str],
    local_video_path: Path,
    tmp_dir: str,
) -> None:
    bucket = settings.supabase_storage_bucket_clips

    for event in events:
        event_row = (
            db.table("events")
            .insert(
                {
                    "video_id": video_id,
                    "event_type": event.event_type,
                    "start_time_ms": event.start_time_ms,
                    "end_time_ms": event.end_time_ms,
                    "primary_player_id": track_to_detected_player_id.get(event.primary_track_id),
                    "secondary_player_id": (
                        track_to_detected_player_id.get(event.secondary_track_id)
                        if event.secondary_track_id is not None
                        else None
                    ),
                    "confidence": event.confidence,
                }
            )
            .execute()
            .data[0]
        )

        try:
            _cut_and_upload_clip(db, bucket, video_id, event_row, event, local_video_path, tmp_dir)
        except Exception:  # noqa: BLE001 — corte de clipe é acessório ao evento já persistido;
            # falha ao gerar um clipe não deve derrubar o job nem impedir os demais eventos.
            logger.exception(
                "Falha ao gerar clipe para o evento %s do vídeo %s", event_row["id"], video_id
            )


def _cut_and_upload_clip(
    db, bucket: str, video_id: str, event_row: dict, event: DetectedEvent, local_video_path: Path, tmp_dir: str
) -> None:
    clip_path = Path(tmp_dir) / f"clip_{event_row['id']}.mp4"
    cut_clip(local_video_path, clip_path, event.start_time_ms, event.end_time_ms)

    thumb_path = Path(tmp_dir) / f"clip_{event_row['id']}.jpg"
    extract_single_frame(local_video_path, thumb_path, timestamp_ms=event.start_time_ms)

    clip_storage_path = f"{video_id}/{event_row['id']}.mp4"
    thumb_storage_path = f"{video_id}/{event_row['id']}.jpg"

    db.storage.from_(bucket).upload(
        clip_storage_path, clip_path.read_bytes(), {"content-type": "video/mp4", "upsert": "true"}
    )
    db.storage.from_(bucket).upload(
        thumb_storage_path, thumb_path.read_bytes(), {"content-type": "image/jpeg", "upsert": "true"}
    )

    db.table("clips").insert(
        {
            "event_id": event_row["id"],
            "storage_path": clip_storage_path,
            "thumbnail_path": thumb_storage_path,
            "duration_seconds": round(get_video_metadata(clip_path).duration_seconds),
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
