"""Task leve: extrai um único frame do vídeo para o coach marcar
visualmente um jogador (bbox) antes/durante a análise completa (ver
`tasks.process_video`, que consome `player_selection_hints` como prior
espacial). Roda em worker assíncrono pelo mesmo motivo do processamento
completo: baixar/decodificar vídeo não pode acontecer na request HTTP."""

import logging
import tempfile
from pathlib import Path

import cv2
from celery import shared_task
from sportslyze_cv.ffmpeg_utils import extract_single_frame, get_video_metadata

from src.core.config import get_settings
from src.db.session import get_supabase_admin

logger = logging.getLogger(__name__)

# Instante padrão do frame de referência: alguns segundos após o início,
# para reduzir a chance de pegar frames pretos/transição de abertura do
# vídeo, mas ainda perto o bastante do começo para o seek do ffmpeg ser
# rápido mesmo em mp4 sem faststart.
DEFAULT_TIMESTAMP_MS = 3000


@shared_task(name="tasks.extract_reference_frame", bind=True, max_retries=2)
def extract_reference_frame(
    self, video_id: str, created_by: str, timestamp_ms: int | None = None
) -> None:
    db = get_supabase_admin()
    settings = get_settings()

    try:
        video = db.table("videos").select("*").eq("id", video_id).single().execute().data
        if video is None:
            raise ValueError(f"Vídeo {video_id} não encontrado.")

        with tempfile.TemporaryDirectory(prefix="sportslyze_refframe_") as tmp_dir:
            local_video_path = _download_video(db, settings, video["storage_path"], tmp_dir)

            metadata = get_video_metadata(local_video_path)
            ts_ms = timestamp_ms if timestamp_ms is not None else min(
                DEFAULT_TIMESTAMP_MS, int(metadata.duration_seconds * 1000 * 0.5)
            )

            frame_path = Path(tmp_dir) / "reference_frame.jpg"
            extract_single_frame(local_video_path, frame_path, timestamp_ms=ts_ms)

            frame = cv2.imread(str(frame_path))
            if frame is None:
                raise ValueError("Não foi possível extrair o frame de referência deste vídeo.")
            height, width = frame.shape[:2]

            bucket = settings.supabase_storage_bucket_reference_frames
            storage_path = f"{video_id}/frame.jpg"
            db.storage.from_(bucket).upload(
                storage_path,
                frame_path.read_bytes(),
                {"content-type": "image/jpeg", "upsert": "true"},
            )

        db.table("video_reference_frames").upsert(
            {
                "video_id": video_id,
                "storage_path": storage_path,
                "timestamp_ms": ts_ms,
                "frame_width": width,
                "frame_height": height,
                "created_by": created_by,
            },
            on_conflict="video_id",
        ).execute()

    except Exception as exc:  # noqa: BLE001 — falha transitória de rede/storage se beneficia de retry
        logger.exception("Falha ao extrair frame de referência do vídeo %s", video_id)
        if self.request.retries < 2:
            raise self.retry(exc=exc, countdown=15 * (self.request.retries + 1))


def _download_video(db, settings, storage_path: str, tmp_dir: str) -> Path:
    bucket = settings.supabase_storage_bucket_videos
    data = db.storage.from_(bucket).download(storage_path)
    local_path = Path(tmp_dir) / "source.mp4"
    local_path.write_bytes(data)
    return local_path
