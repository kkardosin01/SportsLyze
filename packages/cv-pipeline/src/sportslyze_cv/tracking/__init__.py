"""Tracking multi-jogador entre frames usando ByteTrack (via `supervision`).

Recebe as detecções por frame (packages.detection) e mantém um `track_id`
estável por jogador ao longo do vídeo, mesmo com oclusões curtas.
"""

from dataclasses import dataclass

import numpy as np

from sportslyze_cv.detection import Detection


@dataclass
class TrackedObject:
    track_id: int
    detection_class: str
    bbox_xyxy: tuple[float, float, float, float]
    confidence: float
    frame_index: int


class MultiObjectTracker:
    def __init__(self, frame_rate: int = 2):
        import supervision as sv  # import tardio

        self._tracker = sv.ByteTrack(frame_rate=frame_rate)
        self._sv = sv

    def update(self, frame_index: int, detections: list[Detection]) -> list[TrackedObject]:
        if not detections:
            return []

        xyxy = np.array([d.bbox_xyxy for d in detections])
        confidence = np.array([d.confidence for d in detections])
        class_ids = np.array([0 if d.detection_class == "player" else 1 for d in detections])

        sv_detections = self._sv.Detections(xyxy=xyxy, confidence=confidence, class_id=class_ids)
        tracked = self._tracker.update_with_detections(sv_detections)

        results: list[TrackedObject] = []
        for i in range(len(tracked)):
            results.append(
                TrackedObject(
                    track_id=int(tracked.tracker_id[i]),
                    detection_class="player" if tracked.class_id[i] == 0 else "ball",
                    bbox_xyxy=tuple(tracked.xyxy[i].tolist()),
                    confidence=float(tracked.confidence[i]),
                    frame_index=frame_index,
                )
            )
        return results
