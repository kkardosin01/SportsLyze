"""Estatísticas por jogador derivadas do tracking + homografia: heatmap e
distância percorrida (Fase 1). Estatísticas derivadas de eventos (toques,
passes, dribles, faltas...) são calculadas na Fase 2, junto com a
detecção de eventos.
"""

from dataclasses import dataclass

import numpy as np

from sportslyze_cv.homography import FIELD_LENGTH_M, FIELD_WIDTH_M, Homography, pixel_to_field
from sportslyze_cv.tracking import TrackedObject

HEATMAP_GRID_LENGTH = 50  # células ao longo do comprimento do campo
HEATMAP_GRID_WIDTH = 32  # células ao longo da largura do campo


@dataclass
class PlayerMovementStats:
    track_id: int
    distance_km: float
    avg_speed_kmh: float
    max_speed_kmh: float
    heatmap: list[list[int]]  # matriz [HEATMAP_GRID_WIDTH][HEATMAP_GRID_LENGTH]


def compute_player_movement_stats(
    tracked_positions: list[TrackedObject],
    homography: Homography,
    sample_fps: float,
) -> dict[int, PlayerMovementStats]:
    """Recebe todas as posições rastreadas (de todos os frames amostrados)
    de um vídeo já filtradas para `detection_class == "player"`, agrupa por
    track_id e calcula distância percorrida, velocidade e heatmap em
    coordenadas reais do campo (metros)."""
    positions_by_track: dict[int, list[tuple[int, float, float]]] = {}
    for obj in tracked_positions:
        if obj.detection_class != "player":
            continue
        center_x = (obj.bbox_xyxy[0] + obj.bbox_xyxy[2]) / 2
        # usa a base da bbox (pés do jogador) para melhor precisão de posição no campo
        foot_y = obj.bbox_xyxy[3]
        field_x, field_y = pixel_to_field((center_x, foot_y), homography)
        positions_by_track.setdefault(obj.track_id, []).append((obj.frame_index, field_x, field_y))

    results: dict[int, PlayerMovementStats] = {}
    seconds_per_frame = 1.0 / sample_fps

    for track_id, positions in positions_by_track.items():
        positions.sort(key=lambda p: p[0])
        heatmap = np.zeros((HEATMAP_GRID_WIDTH, HEATMAP_GRID_LENGTH), dtype=int)
        total_distance_m = 0.0
        speeds_kmh: list[float] = []

        for i, (_, x, y) in enumerate(positions):
            _accumulate_heatmap(heatmap, x, y)
            if i == 0:
                continue
            _, prev_x, prev_y = positions[i - 1]
            step_distance_m = float(np.hypot(x - prev_x, y - prev_y))
            total_distance_m += step_distance_m
            speed_kmh = (step_distance_m / seconds_per_frame) * 3.6
            # descarta outliers grosseiros (ex: erro de tracking/homografia)
            if speed_kmh < 40:
                speeds_kmh.append(speed_kmh)

        results[track_id] = PlayerMovementStats(
            track_id=track_id,
            distance_km=round(total_distance_m / 1000, 3),
            avg_speed_kmh=round(float(np.mean(speeds_kmh)), 2) if speeds_kmh else 0.0,
            max_speed_kmh=round(float(np.max(speeds_kmh)), 2) if speeds_kmh else 0.0,
            heatmap=heatmap.tolist(),
        )

    return results


def _accumulate_heatmap(heatmap: np.ndarray, field_x: float, field_y: float) -> None:
    col = int(np.clip(field_x / FIELD_LENGTH_M * HEATMAP_GRID_LENGTH, 0, HEATMAP_GRID_LENGTH - 1))
    row = int(np.clip(field_y / FIELD_WIDTH_M * HEATMAP_GRID_WIDTH, 0, HEATMAP_GRID_WIDTH - 1))
    heatmap[row, col] += 1
