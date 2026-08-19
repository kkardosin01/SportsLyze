"""Utilitários de ffmpeg: metadados, extração de frames e corte de clipes.

Toda interação com ffmpeg passa por subprocess — não há dependência de
biblioteca Python de vídeo pesada aqui, só o binário `ffmpeg`/`ffprobe`
precisa estar disponível no PATH (já incluído nas imagens Docker de
api/worker).
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VideoMetadata:
    duration_seconds: float
    width: int
    height: int
    fps: float
    codec: str


def get_video_metadata(video_path: str | Path) -> VideoMetadata:
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,codec_name,r_frame_rate:format=duration",
            "-of", "json",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    stream = data["stream" if "stream" in data else "streams"][0] if "streams" in data else data["streams"][0]
    num, den = stream["r_frame_rate"].split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    return VideoMetadata(
        duration_seconds=float(data["format"]["duration"]),
        width=int(stream["width"]),
        height=int(stream["height"]),
        fps=fps,
        codec=stream["codec_name"],
    )


def extract_frames(
    video_path: str | Path, output_dir: str | Path, sample_fps: float = 2.0
) -> list[Path]:
    """Extrai frames em intervalos regulares (padrão: 2 fps) para reduzir o
    custo computacional da detecção — não processamos todos os frames do
    vídeo original."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(output_dir / "frame_%08d.jpg")

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", f"fps={sample_fps}",
            "-qscale:v", "2",
            pattern,
        ],
        capture_output=True,
        check=True,
    )
    return sorted(output_dir.glob("frame_*.jpg"))


def cut_clip(
    video_path: str | Path, output_path: str | Path, start_ms: int, end_ms: int, padding_ms: int = 1000
) -> Path:
    """Corta um clipe do vídeo original entre start_ms/end_ms, com uma
    margem de contexto (padding) antes e depois do evento detectado."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    start_s = max(0, (start_ms - padding_ms) / 1000)
    duration_s = (end_ms - start_ms + 2 * padding_ms) / 1000

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(start_s),
            "-i", str(video_path),
            "-t", str(duration_s),
            "-c", "copy",
            str(output_path),
        ],
        capture_output=True,
        check=True,
    )
    return output_path
