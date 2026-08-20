export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string | null;
  related_entity_type: string | null;
  related_entity_id: string | null;
  read_at: string | null;
  created_at: string;
}

export type ReportScope = "match" | "player";
export type ReportFormat = "pdf" | "audio" | "slides";

export interface Report {
  id: string;
  scope: ReportScope;
  match_id: string | null;
  athlete_id: string | null;
  format: ReportFormat;
  version: number;
  generated_at: string;
  download_url: string;
}
