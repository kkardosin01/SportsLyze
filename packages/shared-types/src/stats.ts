export interface MatchStatsSummary {
  video_id: string;
  match_id: string | null;
  match_date: string | null;
  opponent_name: string | null;
  distance_km: number;
  avg_speed_kmh: number;
  max_speed_kmh: number;
}

export interface AggregatedStats {
  matches_analyzed: number;
  total_distance_km: number;
  avg_speed_kmh: number;
  max_speed_kmh: number;
  heatmap: number[][];
  matches: MatchStatsSummary[];
}
