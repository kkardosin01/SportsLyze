"""Testes de `sportslyze_cv.pipeline._merge_players_by_jersey` — fusão de
tracks do ByteTrack que o OCR leu com o mesmo número de camisa (ver
docstring da função), simulando um jogador que a re-identificação por
movimento perdeu e reencontrou como um `track_id` novo."""

from sportslyze_cv.pipeline import PlayerResult, _merge_players_by_jersey


def _player(
    track_id: int,
    jersey: int | None,
    confidence: float | None = 0.8,
    distance_km: float = 1.0,
    avg_speed_kmh: float = 6.0,
    max_speed_kmh: float = 20.0,
    heatmap: list[list[int]] | None = None,
) -> PlayerResult:
    return PlayerResult(
        track_id=track_id,
        label=f"Jogador {track_id}",
        ocr_jersey_number=jersey,
        ocr_confidence=confidence,
        thumbnail_path=f"/tmp/track_{track_id}.jpg",
        distance_km=distance_km,
        avg_speed_kmh=avg_speed_kmh,
        max_speed_kmh=max_speed_kmh,
        heatmap=heatmap if heatmap is not None else [[0, 0], [0, 0]],
        member_track_ids=[track_id],
    )


def test_two_tracks_with_same_confident_jersey_are_merged():
    players = [
        _player(1, jersey=10, distance_km=1.0, avg_speed_kmh=6.0, max_speed_kmh=18.0),
        _player(2, jersey=10, distance_km=2.0, avg_speed_kmh=8.0, max_speed_kmh=22.0),
    ]

    merged = _merge_players_by_jersey(players)

    assert len(merged) == 1
    result = merged[0]
    assert result.track_id == 1  # menor track_id vira o representante
    assert sorted(result.member_track_ids) == [1, 2]
    assert result.distance_km == 3.0
    assert result.max_speed_kmh == 22.0
    # velocidade média ponderada pela distância de cada trecho: (1*6 + 2*8) / 3
    assert result.avg_speed_kmh == round((1.0 * 6.0 + 2.0 * 8.0) / 3.0, 2)


def test_tracks_with_different_jersey_numbers_are_not_merged():
    players = [_player(1, jersey=10), _player(2, jersey=7)]

    merged = _merge_players_by_jersey(players)

    assert len(merged) == 2
    assert {p.track_id for p in merged} == {1, 2}


def test_tracks_without_confident_jersey_are_never_merged():
    players = [_player(1, jersey=None), _player(2, jersey=None)]

    merged = _merge_players_by_jersey(players)

    assert len(merged) == 2
    assert all(p.member_track_ids == [p.track_id] for p in merged)


def test_three_tracks_with_same_jersey_merge_into_one():
    players = [
        _player(3, jersey=9, distance_km=1.0),
        _player(1, jersey=9, distance_km=1.0),
        _player(2, jersey=9, distance_km=1.0),
    ]

    merged = _merge_players_by_jersey(players)

    assert len(merged) == 1
    result = merged[0]
    assert result.track_id == 1
    assert sorted(result.member_track_ids) == [1, 2, 3]
    assert result.distance_km == 3.0


def test_merge_sums_heatmaps_elementwise():
    players = [
        _player(1, jersey=5, heatmap=[[1, 0], [0, 2]]),
        _player(2, jersey=5, heatmap=[[0, 3], [1, 0]]),
    ]

    merged = _merge_players_by_jersey(players)

    assert merged[0].heatmap == [[1, 3], [1, 2]]


def test_merge_keeps_thumbnail_and_confidence_from_highest_confidence_read():
    players = [
        _player(1, jersey=5, confidence=0.6),
        _player(2, jersey=5, confidence=0.95),
    ]

    merged = _merge_players_by_jersey(players)

    assert merged[0].ocr_confidence == 0.95
    assert merged[0].thumbnail_path == "/tmp/track_2.jpg"
