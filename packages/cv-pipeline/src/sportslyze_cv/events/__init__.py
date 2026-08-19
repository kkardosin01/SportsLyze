"""Detecção de eventos (passe, drible, desarme, falta, finalização,
triangulação, jogada ensaiada) a partir de heurísticas sobre o tracking.

Implementação prevista para a Fase 2 do roadmap. As tabelas `events` e
`clips` já existem no schema desde a Fase 1 para não exigir migration
adicional quando este módulo for implementado. Ver PRD: precisão de
eventos via heurística é aproximada por natureza e evolui em fases.
"""

from dataclasses import dataclass
from typing import Literal

EventType = Literal[
    "passe", "drible", "desarme", "falta", "finalizacao", "triangulacao", "jogada_ensaiada"
]


@dataclass
class DetectedEvent:
    event_type: EventType
    start_time_ms: int
    end_time_ms: int
    primary_track_id: int
    secondary_track_id: int | None
    confidence: float
    metadata: dict


class EventDetector:
    """Placeholder da Fase 2. A entrada esperada é a série temporal de
    posições de jogadores/bola (já convertidas para coordenadas de campo
    via homografia) produzida pelo pipeline de tracking da Fase 1."""

    def detect(self, tracked_positions, ball_positions) -> list[DetectedEvent]:
        raise NotImplementedError(
            "Detecção de eventos será implementada na Fase 2 (heurísticas de posse, "
            "passes, triangulações e dribles sobre as posições já rastreadas)."
        )
