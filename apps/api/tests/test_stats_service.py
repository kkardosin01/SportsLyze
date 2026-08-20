"""Testes de `src.services.stats_service.StatsService` — controle de
acesso ao atleta e agregação de `player_match_stats` através de múltiplas
partidas, usando repositórios falsos (sem tocar o Supabase real)."""

import os

os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test")

import pytest
from fastapi import HTTPException

from src.services.stats_service import StatsService


class FakeAthleteRepo:
    def __init__(self, athlete: dict):
        self._athlete = athlete

    def get_by_id(self, athlete_id):
        return self._athlete if athlete_id == self._athlete["id"] else None


class FakeMemberRepo:
    def __init__(self, memberships):
        self._memberships = set(memberships)

    def find_membership(self, club_id, user_id):
        return {"club_id": club_id, "user_id": user_id} if (club_id, user_id) in self._memberships else None


class FakeDetectedPlayerRepo:
    def __init__(self, rows):
        self._rows = list(rows)

    def list_for_athlete(self, athlete_id):
        return [r for r in self._rows if r["athlete_id"] == athlete_id]


class FakeStatsRepo:
    def __init__(self, rows):
        self._rows = list(rows)

    def list_for_detected_players(self, detected_player_ids):
        return [r for r in self._rows if r["detected_player_id"] in detected_player_ids]


class FakeVideoRepo:
    def __init__(self, videos):
        self._videos = list(videos)

    def list_by_ids(self, video_ids):
        return [v for v in self._videos if v["id"] in video_ids]


class FakeMatchRepo:
    def __init__(self, matches):
        self._matches = list(matches)

    def list_by_ids(self, match_ids):
        return [m for m in self._matches if m["id"] in match_ids]


def _service(athlete, memberships=(), detected_players=(), stats=(), videos=(), matches=()):
    return StatsService(
        FakeAthleteRepo(athlete),
        FakeMemberRepo(memberships),
        FakeDetectedPlayerRepo(detected_players),
        FakeStatsRepo(stats),
        FakeVideoRepo(videos),
        FakeMatchRepo(matches),
    )


def test_access_denied_for_unrelated_user():
    athlete = {"id": "athlete-1", "club_id": "club-1", "user_id": None}
    service = _service(athlete)

    with pytest.raises(HTTPException) as exc_info:
        service.get_aggregated_stats("athlete-1", "user-x")

    assert exc_info.value.status_code == 403


def test_access_allowed_for_club_member():
    athlete = {"id": "athlete-1", "club_id": "club-1", "user_id": None}
    service = _service(athlete, memberships=[("club-1", "user-x")])

    result = service.get_aggregated_stats("athlete-1", "user-x")

    assert result["matches_analyzed"] == 0


def test_access_allowed_for_athlete_own_account():
    athlete = {"id": "athlete-1", "club_id": None, "user_id": "user-x"}
    service = _service(athlete)

    result = service.get_aggregated_stats("athlete-1", "user-x")

    assert result["matches_analyzed"] == 0


def test_athlete_not_found_raises_404():
    athlete = {"id": "athlete-1", "club_id": "club-1", "user_id": None}
    service = _service(athlete)

    with pytest.raises(HTTPException) as exc_info:
        service.get_aggregated_stats("athlete-does-not-exist", "user-x")

    assert exc_info.value.status_code == 404


def test_aggregates_across_matches_ignoring_scouting_video():
    athlete = {"id": "athlete-1", "club_id": "club-1", "user_id": None}
    detected_players = [
        {"id": "dp-1", "video_id": "video-1", "athlete_id": "athlete-1"},
        {"id": "dp-2", "video_id": "video-2", "athlete_id": "athlete-1"},
        {"id": "dp-3", "video_id": "video-3", "athlete_id": "athlete-1"},
    ]
    stats = [
        {
            "detected_player_id": "dp-1",
            "video_id": "video-1",
            "distance_km": 5.0,
            "avg_speed_kmh": 8.0,
            "max_speed_kmh": 20.0,
            "heatmap": [[1, 0], [0, 1]],
        },
        {
            "detected_player_id": "dp-2",
            "video_id": "video-2",
            "distance_km": 7.0,
            "avg_speed_kmh": 10.0,
            "max_speed_kmh": 24.0,
            "heatmap": [[2, 0], [0, 3]],
        },
        # Vídeo de scouting do adversário: não é performance do atleta, não deve entrar na agregação.
        {
            "detected_player_id": "dp-3",
            "video_id": "video-3",
            "distance_km": 999.0,
            "avg_speed_kmh": 999.0,
            "max_speed_kmh": 999.0,
            "heatmap": [[9, 9], [9, 9]],
        },
    ]
    videos = [
        {"id": "video-1", "video_type": "propria_equipe", "match_id": "match-1"},
        {"id": "video-2", "video_type": "propria_equipe", "match_id": "match-2"},
        {"id": "video-3", "video_type": "adversario", "match_id": "match-3"},
    ]
    matches = [
        {"id": "match-1", "match_date": "2026-01-10", "opponent_name": "Time A"},
        {"id": "match-2", "match_date": "2026-02-10", "opponent_name": "Time B"},
    ]

    service = _service(
        athlete,
        memberships=[("club-1", "user-x")],
        detected_players=detected_players,
        stats=stats,
        videos=videos,
        matches=matches,
    )

    result = service.get_aggregated_stats("athlete-1", "user-x")

    assert result["matches_analyzed"] == 2
    assert result["total_distance_km"] == pytest.approx(12.0)
    assert result["avg_speed_kmh"] == pytest.approx(9.0)
    assert result["max_speed_kmh"] == pytest.approx(24.0)
    assert result["heatmap"] == [[3, 0], [0, 4]]
    assert {m["video_id"] for m in result["matches"]} == {"video-1", "video-2"}


def test_empty_result_when_athlete_never_detected():
    athlete = {"id": "athlete-1", "club_id": "club-1", "user_id": None}
    service = _service(athlete, memberships=[("club-1", "user-x")])

    result = service.get_aggregated_stats("athlete-1", "user-x")

    assert result == {
        "matches_analyzed": 0,
        "total_distance_km": 0.0,
        "avg_speed_kmh": 0.0,
        "max_speed_kmh": 0.0,
        "heatmap": [],
        "matches": [],
    }
