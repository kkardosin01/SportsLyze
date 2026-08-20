"""Orquestrador do pipeline de visão computacional — Fase 1.

Etapas: extração de frames -> detecção + tracking -> homografia do campo
-> sugestão de número de camisa (OCR) -> cálculo de heatmap/distância.
Cada etapa reporta progresso via `on_progress`, que o worker usa para
atualizar `analysis_jobs.current_stage` / `progress_pct` no banco.
"""

import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import cv2

from sportslyze_cv.detection import PlayerBallDetector
from sportslyze_cv.ffmpeg_utils import extract_frames, get_video_metadata
from sportslyze_cv.homography import detect_field_corners, estimate_homography
from sportslyze_cv.ocr import JerseyNumberOCR
from sportslyze_cv.stats import compute_player_movement_stats
from sportslyze_cv.tracking import MultiObjectTracker, TrackedObject

SAMPLE_FPS = 2.0
ProgressCallback = Callable[[str, int], None]


@dataclass
class PlayerResult:
    track_id: int
    label: str
    ocr_jersey_number: int | None
    ocr_confidence: float | None
    thumbnail_path: str | None
    distance_km: float
    avg_speed_kmh: float
    max_speed_kmh: float
    heatmap: list[list[int]]


@dataclass
class SelectionHint:
    """Marcação manual do coach: 'este bbox, neste instante, é este atleta'.
    Usada como prior espacial para pré-vincular um track — nunca como
    substituto de número de camisa."""

    athlete_id: str
    timestamp_ms: int
    bbox_xyxy: tuple[float, float, float, float]


# IoU mínimo para aceitar a resolução de um hint contra um track detectado.
# Abaixo disso a marcação do coach não bate com nenhuma detecção próxima o
# suficiente (frame de referência divergente da detecção, jogador fora de
# quadro no instante indicado etc.) — melhor não vincular do que vincular
# errado; o coach ainda pode corrigir manualmente na revisão pós-análise.
MIN_HINT_IOU = 0.3


@dataclass
class PipelineResult:
    duration_seconds: float
    players: list[PlayerResult] = field(default_factory=list)
    homography_matrix: list[list[float]] | None = None
    field_calibrated: bool = False
    # athlete_id -> track_id, para os hints que encontraram correspondência
    resolved_hints: dict[str, int] = field(default_factory=dict)


def _iou(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_area = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
    if inter_area == 0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union_area = area_a + area_b - inter_area
    return inter_area / union_area if union_area > 0 else 0.0


class VideoProcessingPipeline:
    def __init__(self, detect_model_path: str = "yolov8n.pt", enable_ocr: bool = True):
        self._detector = PlayerBallDetector(model_path=detect_model_path)
        self._ocr = JerseyNumberOCR() if enable_ocr else None

    def run(
        self,
        video_path: str | Path,
        on_progress: ProgressCallback | None = None,
        manual_field_corners: list[tuple[float, float]] | None = None,
        selection_hints: list[SelectionHint] | None = None,
    ) -> PipelineResult:
        video_path = Path(video_path)
        report = lambda stage, pct: on_progress and on_progress(stage, pct)  # noqa: E731

        report("extraindo_frames", 5)
        metadata = get_video_metadata(video_path)

        with tempfile.TemporaryDirectory(prefix="sportslyze_frames_") as tmp_dir:
            frame_paths = extract_frames(video_path, tmp_dir, sample_fps=SAMPLE_FPS)
            report("extraindo_frames", 20)

            report("rastreando_jogadores", 25)
            tracked_positions, first_frame, sample_crops = self._track_all_frames(
                frame_paths, on_progress=lambda pct: report("rastreando_jogadores", 25 + int(pct * 0.45))
            )

            report("calibrando_campo", 72)
            homography = self._calibrate_field(first_frame, manual_field_corners)

            report("calculando_estatisticas", 80)
            movement_stats = (
                compute_player_movement_stats(tracked_positions, homography, SAMPLE_FPS)
                if homography
                else {}
            )

            report("sugerindo_numeros", 90)
            players = self._build_player_results(movement_stats, sample_crops)

            resolved_hints = self._resolve_hints(selection_hints, tracked_positions) if selection_hints else {}

        report("concluido", 100)
        return PipelineResult(
            duration_seconds=metadata.duration_seconds,
            players=players,
            homography_matrix=homography.to_jsonable() if homography else None,
            field_calibrated=homography is not None,
            resolved_hints=resolved_hints,
        )

    def _resolve_hints(
        self, hints: list[SelectionHint], tracked_positions: list[TrackedObject]
    ) -> dict[str, int]:
        """Para cada hint (marcação manual do coach), acha o track detectado
        mais próximo espacialmente no frame amostrado mais perto do
        timestamp indicado, usando IoU — prior espacial, não identidade por
        número de camisa."""
        resolved: dict[str, int] = {}
        for hint in hints:
            frame_index = round(hint.timestamp_ms / 1000 * SAMPLE_FPS)
            candidates = [
                obj
                for obj in tracked_positions
                if obj.detection_class == "player" and obj.frame_index == frame_index
            ]
            if not candidates:
                # Sem detecção exatamente nesse frame amostrado — tenta o mais próximo disponível.
                candidates = [obj for obj in tracked_positions if obj.detection_class == "player"]
                if not candidates:
                    continue
                closest_index = min(
                    (obj.frame_index for obj in candidates), key=lambda idx: abs(idx - frame_index)
                )
                candidates = [obj for obj in candidates if obj.frame_index == closest_index]

            best = max(candidates, key=lambda obj: _iou(hint.bbox_xyxy, obj.bbox_xyxy))
            if _iou(hint.bbox_xyxy, best.bbox_xyxy) >= MIN_HINT_IOU:
                resolved[hint.athlete_id] = best.track_id
        return resolved

    def _track_all_frames(
        self, frame_paths: list[Path], on_progress: Callable[[int], None] | None = None
    ) -> tuple[list[TrackedObject], "cv2.Mat | None", dict[int, Path]]:
        tracker = MultiObjectTracker(frame_rate=int(SAMPLE_FPS))
        all_tracked: list[TrackedObject] = []
        sample_crops: dict[int, Path] = {}
        first_frame = None

        total = len(frame_paths) or 1
        for index, frame_path in enumerate(frame_paths):
            frame = cv2.imread(str(frame_path))
            if frame is None:
                continue
            if first_frame is None:
                first_frame = frame

            detections = self._detector.detect(frame)
            tracked = tracker.update(index, detections)
            all_tracked.extend(tracked)

            self._maybe_save_thumbnail(frame, tracked, sample_crops)

            if on_progress:
                on_progress(int((index + 1) / total * 100))

        return all_tracked, first_frame, sample_crops

    def _maybe_save_thumbnail(
        self, frame, tracked: list[TrackedObject], sample_crops: dict[int, Path]
    ) -> None:
        for obj in tracked:
            if obj.detection_class != "player" or obj.track_id in sample_crops:
                continue
            x1, y1, x2, y2 = (int(v) for v in obj.bbox_xyxy)
            crop = frame[max(0, y1) : y2, max(0, x1) : x2]
            if crop.size == 0:
                continue
            thumb_path = Path(tempfile.gettempdir()) / f"sportslyze_track_{obj.track_id}.jpg"
            cv2.imwrite(str(thumb_path), crop)
            sample_crops[obj.track_id] = thumb_path

    def _calibrate_field(self, first_frame, manual_field_corners):
        if manual_field_corners:
            return estimate_homography(manual_field_corners)
        if first_frame is None:
            return None
        auto_corners = detect_field_corners(first_frame)
        if auto_corners is None:
            # Detecção automática falhou — API deve solicitar calibração manual na UI.
            return None
        return estimate_homography(auto_corners)

    def _build_player_results(
        self, movement_stats: dict, sample_crops: dict[int, Path]
    ) -> list[PlayerResult]:
        results: list[PlayerResult] = []
        track_ids = set(movement_stats.keys()) | set(sample_crops.keys())

        for i, track_id in enumerate(sorted(track_ids)):
            stats = movement_stats.get(track_id)
            ocr_number, ocr_confidence = None, None
            thumbnail_path = sample_crops.get(track_id)

            if self._ocr and thumbnail_path:
                crop = cv2.imread(str(thumbnail_path))
                if crop is not None:
                    guess = self._ocr.read(crop)
                    ocr_number, ocr_confidence = guess.number, guess.confidence

            results.append(
                PlayerResult(
                    track_id=track_id,
                    label=f"Jogador {chr(65 + i % 26)}{'' if i < 26 else i // 26}",
                    ocr_jersey_number=ocr_number,
                    ocr_confidence=ocr_confidence,
                    thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
                    distance_km=stats.distance_km if stats else 0.0,
                    avg_speed_kmh=stats.avg_speed_kmh if stats else 0.0,
                    max_speed_kmh=stats.max_speed_kmh if stats else 0.0,
                    heatmap=stats.heatmap if stats else [],
                )
            )
        return results
