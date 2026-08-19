export type VideoOwnerType = "club" | "athlete";
export type VideoType = "propria_equipe" | "adversario";

export interface Match {
  id: string;
  club_id: string | null;
  team_id: string | null;
  athlete_id: string | null;
  opponent_name: string | null;
  match_date: string | null;
  competition: string | null;
  location: string | null;
  created_at: string;
}

export interface Video {
  id: string;
  owner_type: VideoOwnerType;
  owner_id: string;
  match_id: string | null;
  video_type: VideoType;
  original_filename: string;
  duration_seconds: number | null;
  size_bytes: number | null;
  retention_days: number;
  original_deleted_at: string | null;
  created_at: string;
}
