from fastapi import HTTPException, status

from src.repositories.clubs import AthleteRepository, ClubMemberRepository
from src.repositories.videos import (
    DetectedPlayerRepository,
    MatchRepository,
    PlayerMatchStatsRepository,
    VideoRepository,
)

_EMPTY_STATS = {
    "matches_analyzed": 0,
    "total_distance_km": 0.0,
    "avg_speed_kmh": 0.0,
    "max_speed_kmh": 0.0,
    "heatmap": [],
    "matches": [],
}


def _sum_heatmaps(heatmaps: list[list[list[int]]]) -> list[list[int]]:
    """Soma célula a célula os heatmaps (mesma grade fixa — ver
    `HEATMAP_GRID_WIDTH`/`HEATMAP_GRID_LENGTH` em `sportslyze_cv.stats`).
    Vídeos sem homografia calibrada têm heatmap vazio e são ignorados aqui,
    igual ao que já acontece na visualização por partida."""
    total: list[list[int]] = []
    for heatmap in heatmaps:
        if not heatmap:
            continue
        if not total:
            total = [row[:] for row in heatmap]
            continue
        for r, row in enumerate(heatmap):
            for c, value in enumerate(row):
                total[r][c] += value
    return total


class StatsService:
    """Agrega `player_match_stats` de um atleta através de múltiplas
    partidas (todas as em que ele foi identificado via `detected_players`),
    reaproveitando o mesmo padrão de junção usado em
    `tasks.generate_match_report` no worker."""

    def __init__(
        self,
        athlete_repo: AthleteRepository,
        member_repo: ClubMemberRepository,
        detected_player_repo: DetectedPlayerRepository,
        stats_repo: PlayerMatchStatsRepository,
        video_repo: VideoRepository,
        match_repo: MatchRepository,
    ):
        self._athletes = athlete_repo
        self._members = member_repo
        self._detected_players = detected_player_repo
        self._stats = stats_repo
        self._videos = video_repo
        self._matches = match_repo

    def _ensure_athlete_access(self, athlete_id: str, user_id: str) -> dict:
        athlete = self._athletes.get_by_id(athlete_id)
        if athlete is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Atleta não encontrado.")

        if athlete.get("user_id") == user_id:
            return athlete
        if athlete.get("club_id") and self._members.find_membership(athlete["club_id"], user_id) is not None:
            return athlete

        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem acesso a este atleta.")

    def get_aggregated_stats(self, athlete_id: str, user_id: str) -> dict:
        self._ensure_athlete_access(athlete_id, user_id)

        detected_players = self._detected_players.list_for_athlete(athlete_id)
        if not detected_players:
            return dict(_EMPTY_STATS)

        detected_player_ids = [dp["id"] for dp in detected_players]
        video_ids = list({dp["video_id"] for dp in detected_players})

        stats_rows = self._stats.list_for_detected_players(detected_player_ids)
        videos_by_id = {v["id"]: v for v in self._videos.list_by_ids(video_ids)}

        # Só a performance do próprio atleta em vídeos do próprio time entra
        # na agregação — vídeos de scouting de adversário não representam a
        # performance do atleta.
        own_rows = [
            row
            for row in stats_rows
            if (videos_by_id.get(row["video_id"]) or {}).get("video_type") == "propria_equipe"
        ]
        if not own_rows:
            return dict(_EMPTY_STATS)

        match_ids = {
            videos_by_id[row["video_id"]]["match_id"]
            for row in own_rows
            if videos_by_id[row["video_id"]].get("match_id")
        }
        matches_by_id = {m["id"]: m for m in self._matches.list_by_ids(list(match_ids))}

        total_distance = sum(row["distance_km"] or 0.0 for row in own_rows)
        avg_speed = sum(row["avg_speed_kmh"] or 0.0 for row in own_rows) / len(own_rows)
        max_speed = max((row["max_speed_kmh"] or 0.0 for row in own_rows), default=0.0)
        heatmap = _sum_heatmaps([row["heatmap"] for row in own_rows if row.get("heatmap")])

        matches = [
            {
                "video_id": row["video_id"],
                "match_id": videos_by_id[row["video_id"]].get("match_id"),
                "match_date": (matches_by_id.get(videos_by_id[row["video_id"]].get("match_id")) or {}).get(
                    "match_date"
                ),
                "opponent_name": (
                    matches_by_id.get(videos_by_id[row["video_id"]].get("match_id")) or {}
                ).get("opponent_name"),
                "distance_km": row["distance_km"] or 0.0,
                "avg_speed_kmh": row["avg_speed_kmh"] or 0.0,
                "max_speed_kmh": row["max_speed_kmh"] or 0.0,
            }
            for row in own_rows
        ]

        return {
            "matches_analyzed": len(own_rows),
            "total_distance_km": total_distance,
            "avg_speed_kmh": avg_speed,
            "max_speed_kmh": max_speed,
            "heatmap": heatmap,
            "matches": matches,
        }
