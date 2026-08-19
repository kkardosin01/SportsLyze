"""Detecção de jogadores e bola por frame usando YOLOv8 (ultralytics).

Fase 1 usa um modelo YOLOv8 pré-treinado em COCO (classes "person" e
"sports ball") como baseline honesto. Fine-tuning em dataset de futebol
de base é um item natural de fase futura para melhorar precisão de bola
pequena/ocluída.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

DetectionClass = Literal["player", "ball"]


@dataclass
class Detection:
    detection_class: DetectionClass
    bbox_xyxy: tuple[float, float, float, float]
    confidence: float


class PlayerBallDetector:
    _COCO_PERSON_CLASS_ID = 0
    _COCO_BALL_CLASS_ID = 32

    def __init__(self, model_path: str = "yolov8n.pt", confidence_threshold: float = 0.35):
        from ultralytics import YOLO  # import tardio: dependência pesada só carregada quando necessário

        self._model = YOLO(model_path)
        self._confidence_threshold = confidence_threshold

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self._model.predict(
            frame, conf=self._confidence_threshold, classes=[self._COCO_PERSON_CLASS_ID, self._COCO_BALL_CLASS_ID],
            verbose=False,
        )[0]

        detections: list[Detection] = []
        for box in results.boxes:
            class_id = int(box.cls[0])
            detection_class: DetectionClass = "player" if class_id == self._COCO_PERSON_CLASS_ID else "ball"
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(
                Detection(
                    detection_class=detection_class,
                    bbox_xyxy=(x1, y1, x2, y2),
                    confidence=float(box.conf[0]),
                )
            )
        return detections
