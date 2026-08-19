export type AnalysisJobStatus = "queued" | "processing" | "done" | "failed";

export interface AnalysisJob {
  id: string;
  video_id: string;
  status: AnalysisJobStatus;
  current_stage: string | null;
  progress_pct: number;
  error_message: string | null;
  estimated_duration_seconds: number | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface DetectedPlayer {
  id: string;
  video_id: string;
  track_id: number;
  label: string;
  ocr_jersey_number: number | null;
  ocr_confidence: number | null;
  thumbnail_path: string | null;
  athlete_id: string | null;
  linked_at: string | null;
}

export interface PlayerMatchStats {
  id: string;
  video_id: string;
  match_id: string | null;
  detected_player_id: string;
  athlete_id: string | null;
  touches: number;
  passes_completed: number;
  passes_attempted: number;
  dribbles_successful: number;
  dribbles_attempted: number;
  fouls_committed: number;
  fouls_suffered: number;
  shots: number;
  distance_km: number | null;
  avg_speed_kmh: number | null;
  max_speed_kmh: number | null;
  heatmap: number[][] | null;
}

export type EventType =
  | "passe"
  | "drible"
  | "desarme"
  | "falta"
  | "finalizacao"
  | "triangulacao"
  | "jogada_ensaiada";

export interface MatchEvent {
  id: string;
  video_id: string;
  match_id: string | null;
  event_type: EventType;
  start_time_ms: number;
  end_time_ms: number;
  primary_player_id: string | null;
  secondary_player_id: string | null;
  confidence: number | null;
}

export interface Clip {
  id: string;
  event_id: string;
  storage_path: string;
  thumbnail_path: string | null;
  duration_seconds: number | null;
}
