"""Homografia do campo: converte coordenadas de pixel em coordenadas reais
do gramado (metros), base para heatmap e distância percorrida.

Limitação conhecida (v1): a detecção automática das linhas do campo
(`detect_field_corners`) é heurística (segmentação de cor de grama + Hough
lines) e funciona melhor em câmeras fixas e bem enquadradas. Quando falha,
a comissão técnica pode calibrar manualmente marcando os 4 cantos do campo
na UI — `estimate_homography` aceita esses pontos diretamente. Fase futura:
modelo de keypoints de campo treinado (ex: abordagem estilo SoccerNet).
"""

from dataclasses import dataclass

import cv2
import numpy as np

# Campo padrão FIFA para categorias de base: 100m x 64m (ajustável por partida)
FIELD_LENGTH_M = 100.0
FIELD_WIDTH_M = 64.0


@dataclass
class Homography:
    matrix: np.ndarray  # 3x3, pixel -> metros

    def to_jsonable(self) -> list[list[float]]:
        return self.matrix.tolist()

    @staticmethod
    def from_jsonable(data: list[list[float]]) -> "Homography":
        return Homography(matrix=np.array(data))


def estimate_homography(pixel_corners: list[tuple[float, float]]) -> Homography:
    """Recebe os 4 cantos do campo em pixels (ordem: sup-esq, sup-dir,
    inf-dir, inf-esq) e retorna a matriz de homografia para o retângulo
    real do campo em metros."""
    if len(pixel_corners) != 4:
        raise ValueError("São necessários exatamente 4 pontos (cantos do campo).")

    src = np.array(pixel_corners, dtype=np.float32)
    dst = np.array(
        [[0, 0], [FIELD_LENGTH_M, 0], [FIELD_LENGTH_M, FIELD_WIDTH_M], [0, FIELD_WIDTH_M]],
        dtype=np.float32,
    )
    matrix, _ = cv2.findHomography(src, dst)
    return Homography(matrix=matrix)


def detect_field_corners(frame: np.ndarray) -> list[tuple[float, float]] | None:
    """Tentativa best-effort de detectar os 4 cantos do campo via
    segmentação de cor de grama + maior contorno. Retorna None quando a
    confiança é baixa — nesse caso a API deve solicitar calibração manual."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < 0.2 * frame.shape[0] * frame.shape[1]:
        return None  # área de grama insuficiente para confiar na detecção

    epsilon = 0.02 * cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, epsilon, True)
    if len(approx) != 4:
        return None  # forma não convergiu para um quadrilátero confiável

    points = [tuple(point[0].tolist()) for point in approx]
    return _order_corners_clockwise(points)


def pixel_to_field(point_xy: tuple[float, float], homography: Homography) -> tuple[float, float]:
    point = np.array([[point_xy]], dtype=np.float32)
    transformed = cv2.perspectiveTransform(point, homography.matrix)
    x, y = transformed[0][0]
    return float(x), float(y)


def _order_corners_clockwise(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pts = np.array(points, dtype=np.float32)
    center = pts.mean(axis=0)
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    ordered = pts[np.argsort(angles)]
    return [tuple(p) for p in ordered]
