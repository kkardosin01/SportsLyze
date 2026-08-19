"""OCR de número de camisa (PaddleOCR) — sempre best-effort, nunca fonte
única de identidade do jogador.

Na base, é comum não haver número fixo/legível na camisa. O resultado
daqui é salvo em `detected_players.ocr_jersey_number` apenas como
sugestão; a associação confiável vem da revisão manual feita pela
comissão/atleta na UI (ver `detected_players.athlete_id`).
"""

import re
from dataclasses import dataclass

import numpy as np


@dataclass
class JerseyNumberGuess:
    number: int | None
    confidence: float


class JerseyNumberOCR:
    def __init__(self, min_confidence: float = 0.6):
        from paddleocr import PaddleOCR  # import tardio

        self._ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        self._min_confidence = min_confidence

    def read(self, player_crop: np.ndarray) -> JerseyNumberGuess:
        """Recebe o crop (bbox) do jogador e tenta ler o número nas costas
        da camisa. Retorna None quando não há dígitos legíveis com
        confiança suficiente."""
        result = self._ocr.ocr(player_crop, cls=True)
        if not result or not result[0]:
            return JerseyNumberGuess(number=None, confidence=0.0)

        best_number: int | None = None
        best_confidence = 0.0
        for _, (text, confidence) in result[0]:
            digits = re.sub(r"\D", "", text)
            if digits and confidence > best_confidence:
                best_number = int(digits[:2])  # números de camisa têm no máx. 2 dígitos
                best_confidence = confidence

        if best_confidence < self._min_confidence:
            return JerseyNumberGuess(number=None, confidence=best_confidence)

        return JerseyNumberGuess(number=best_number, confidence=best_confidence)
