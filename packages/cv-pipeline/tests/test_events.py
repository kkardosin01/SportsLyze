"""Testes das heurísticas de `sportslyze_cv.events.EventDetector`.

Cada teste constrói um `tracked_positions` sintético mínimo (bboxes de
jogador/bola por frame) suficiente para disparar (ou não) a heurística sob
teste, isolando-a das demais sempre que possível."""

import numpy as np
import pytest
from sportslyze_cv.events import DetectedEvent, EventDetector
from sportslyze_cv.homography import Homography
from sportslyze_cv.tracking import TrackedObject

SAMPLE_FPS = 2.0


def _obj(track_id: int, cls: str, bbox: tuple[float, float, float, float], frame: int, confidence: float = 0.9) -> TrackedObject:
    return TrackedObject(track_id=track_id, detection_class=cls, bbox_xyxy=bbox, confidence=confidence, frame_index=frame)


def test_passe_still_detected_after_refactor():
    """Regressão: a heurística original de passe não deve mudar de
    comportamento com a adição das novas heurísticas."""
    tracked = [
        _obj(1, "player", (100, 100, 140, 180), frame=0),
        _obj(1, "ball", (115, 130, 125, 140), frame=0),
        _obj(2, "player", (300, 100, 340, 180), frame=2),
        _obj(2, "ball", (315, 130, 325, 140), frame=2),
    ]

    events = EventDetector().detect(tracked, SAMPLE_FPS)
    passes = [e for e in events if e.event_type == "passe"]

    assert len(passes) == 1
    assert passes[0].primary_track_id == 1
    assert passes[0].secondary_track_id == 2
    assert passes[0].confidence >= 0.15


def test_drible_detected_for_sustained_possession_with_displacement():
    tracked = []
    for frame, x in enumerate([100, 200, 300, 400, 500]):
        bbox = (x, 100, x + 40, 180)
        tracked.append(_obj(5, "player", bbox, frame=frame))
        ball_bbox = (x + 15, 130, x + 25, 140)
        tracked.append(_obj(5, "ball", ball_bbox, frame=frame))

    events = EventDetector().detect(tracked, SAMPLE_FPS)
    dribles = [e for e in events if e.event_type == "drible"]

    assert len(dribles) == 1
    assert dribles[0].primary_track_id == 5
    assert dribles[0].secondary_track_id is None


def test_drible_not_detected_when_player_stays_still():
    tracked = []
    for frame in range(5):
        bbox = (100, 100, 140, 180)
        tracked.append(_obj(5, "player", bbox, frame=frame))
        tracked.append(_obj(5, "ball", (115, 130, 125, 140), frame=frame))

    events = EventDetector().detect(tracked, SAMPLE_FPS)
    dribles = [e for e in events if e.event_type == "drible"]

    assert dribles == []


def test_drible_not_detected_for_short_possession():
    tracked = []
    for frame, x in enumerate([100, 300]):
        bbox = (x, 100, x + 40, 180)
        tracked.append(_obj(5, "player", bbox, frame=frame))
        tracked.append(_obj(5, "ball", (x + 15, 130, x + 25, 140), frame=frame))

    events = EventDetector().detect(tracked, SAMPLE_FPS)
    dribles = [e for e in events if e.event_type == "drible"]

    assert dribles == []


def test_triangulacao_detected_for_three_player_pass_chain():
    passes = [
        DetectedEvent("passe", 0, 500, primary_track_id=1, secondary_track_id=2, confidence=0.9, metadata={}),
        DetectedEvent("passe", 600, 1000, primary_track_id=2, secondary_track_id=3, confidence=0.8, metadata={}),
        DetectedEvent("passe", 1100, 1500, primary_track_id=3, secondary_track_id=1, confidence=0.85, metadata={}),
    ]

    events = EventDetector()._detect_triangulacao(passes)

    assert len(events) == 1
    event = events[0]
    assert event.event_type == "triangulacao"
    assert event.start_time_ms == 0
    assert event.end_time_ms == 1500
    assert event.primary_track_id == 1
    assert event.secondary_track_id == 1
    assert event.confidence == pytest.approx((0.9 + 0.8 + 0.85) / 3, abs=0.01)


def test_triangulacao_not_detected_for_two_distinct_players_only():
    # A e B trocam passes repetidamente, mas nenhum terceiro jogador entra na jogada.
    passes = [
        DetectedEvent("passe", 0, 500, primary_track_id=1, secondary_track_id=2, confidence=0.9, metadata={}),
        DetectedEvent("passe", 600, 1000, primary_track_id=2, secondary_track_id=1, confidence=0.8, metadata={}),
        DetectedEvent("passe", 1100, 1500, primary_track_id=1, secondary_track_id=2, confidence=0.85, metadata={}),
    ]

    events = EventDetector()._detect_triangulacao(passes)

    assert events == []


def test_triangulacao_not_detected_when_chain_breaks_gap():
    passes = [
        DetectedEvent("passe", 0, 500, primary_track_id=1, secondary_track_id=2, confidence=0.9, metadata={}),
        # gap grande demais entre o fim do passe anterior e o início deste
        DetectedEvent("passe", 20000, 20500, primary_track_id=2, secondary_track_id=3, confidence=0.8, metadata={}),
        DetectedEvent("passe", 20600, 21000, primary_track_id=3, secondary_track_id=1, confidence=0.85, metadata={}),
    ]

    events = EventDetector()._detect_triangulacao(passes)

    assert events == []


def test_falta_detected_for_contested_transition_with_bbox_overlap():
    passes = [
        DetectedEvent("passe", 0, 1000, primary_track_id=1, secondary_track_id=2, confidence=0.2, metadata={}),
    ]
    # bboxes de 1 e 2 se sobrepõem fortemente nos frames 0, 1 e 2 (contato sustentado)
    player_positions = {
        1: {
            0: (100, 100, 140, 180),
            1: (102, 101, 142, 181),
            2: (104, 102, 144, 182),
        },
        2: {
            0: (105, 100, 145, 180),
            1: (107, 101, 147, 181),
            2: (109, 102, 149, 182),
        },
    }

    events = EventDetector()._detect_falta(passes, player_positions, SAMPLE_FPS)

    assert len(events) == 1
    event = events[0]
    assert event.event_type == "falta"
    assert event.primary_track_id == 1
    assert event.secondary_track_id == 2
    assert event.confidence <= 0.35


def test_falta_not_detected_for_clean_pass():
    passes = [
        DetectedEvent("passe", 0, 1000, primary_track_id=1, secondary_track_id=2, confidence=0.9, metadata={}),
    ]
    player_positions = {
        1: {0: (100, 100, 140, 180)},
        2: {2: (300, 100, 340, 180)},
    }

    events = EventDetector()._detect_falta(passes, player_positions, SAMPLE_FPS)

    assert events == []


def test_falta_not_detected_without_sustained_contact():
    passes = [
        DetectedEvent("passe", 0, 1000, primary_track_id=1, secondary_track_id=2, confidence=0.2, metadata={}),
    ]
    # jogadores distantes — sem sobreposição de bbox
    player_positions = {
        1: {0: (100, 100, 140, 180), 1: (100, 100, 140, 180), 2: (100, 100, 140, 180)},
        2: {0: (400, 100, 440, 180), 1: (400, 100, 440, 180), 2: (400, 100, 440, 180)},
    }

    events = EventDetector()._detect_falta(passes, player_positions, SAMPLE_FPS)

    assert events == []


def test_finalizacao_detected_for_ball_escaping_toward_goal_zone():
    homography = Homography(matrix=np.eye(3))

    tracked = [
        # jogador 9 com a bola no meio-campo, frames 0 e 1
        _obj(9, "player", (30, -8, 70, 72), frame=0),
        _obj(9, "ball", (45, 27, 55, 37), frame=0),
        _obj(9, "player", (30, -8, 70, 72), frame=1),
        _obj(9, "ball", (45, 27, 55, 37), frame=1),
        # bola solta, sem ninguém por perto, indo em direção ao gol (x cresce)
        _obj(9, "ball", (80, 27, 90, 37), frame=3),
        # jogador 2 só recupera a posse bem mais tarde — confirma que a bola "escapou"
        _obj(2, "player", (-10, -8, 30, 72), frame=10),
        _obj(2, "ball", (5, 27, 15, 37), frame=10),
    ]

    events = EventDetector().detect(tracked, SAMPLE_FPS, homography)
    shots = [e for e in events if e.event_type == "finalizacao"]

    assert len(shots) == 1
    assert shots[0].primary_track_id == 9
    assert shots[0].secondary_track_id is None
    assert shots[0].confidence > 0


def test_finalizacao_not_detected_without_homography():
    tracked = [
        _obj(9, "player", (30, -8, 70, 72), frame=0),
        _obj(9, "ball", (45, 27, 55, 37), frame=0),
        _obj(9, "player", (30, -8, 70, 72), frame=1),
        _obj(9, "ball", (45, 27, 55, 37), frame=1),
        _obj(9, "ball", (80, 27, 90, 37), frame=3),
        _obj(2, "player", (-10, -8, 30, 72), frame=10),
        _obj(2, "ball", (5, 27, 15, 37), frame=10),
    ]

    events = EventDetector().detect(tracked, SAMPLE_FPS, homography=None)
    shots = [e for e in events if e.event_type == "finalizacao"]

    assert shots == []
