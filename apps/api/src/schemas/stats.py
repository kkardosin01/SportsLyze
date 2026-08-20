from datetime import date

from pydantic import BaseModel


class MatchStatsSummary(BaseModel):
    video_id: str
    match_id: str | None
    match_date: date | None
    opponent_name: str | None
    distance_km: float
    avg_speed_kmh: float
    max_speed_kmh: float


class AggregatedStatsOut(BaseModel):
    matches_analyzed: int
    total_distance_km: float
    avg_speed_kmh: float
    max_speed_kmh: float
    heatmap: list[list[int]]
    matches: list[MatchStatsSummary]
