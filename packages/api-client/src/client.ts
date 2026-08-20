import type {
  AnalysisJob,
  Athlete,
  Club,
  DetectedPlayer,
  Match,
  MatchEventWithClips,
  Notification,
  PlaybackUrl,
  PlayerMatchStats,
  ReferenceFrame,
  SelectionHint,
  Team,
} from "@sportslyze/shared-types";

export interface SportsLyzeClientOptions {
  baseUrl: string;
  getAccessToken: () => Promise<string | null>;
}

export interface UploadInitiateResponse {
  video_id: string;
  upload_url: string;
  storage_path: string;
  max_upload_size_bytes: number;
}

/** Client TS fino sobre a API FastAPI (`/api/v1`), compartilhado entre web
 * e mobile. Tipos gerados a partir do OpenAPI substituem estes manuais
 * conforme os endpoints forem estabilizando (ver `codegen:api-client`). */
export class SportsLyzeClient {
  constructor(private readonly options: SportsLyzeClientOptions) {}

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const token = await this.options.getAccessToken();
    const response = await fetch(`${this.options.baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init?.headers,
      },
    });

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const error = new Error(body?.detail ?? `Erro ${response.status} ao chamar ${path}`) as Error & {
        status?: number;
      };
      error.status = response.status;
      throw error;
    }

    return response.status === 204 ? (undefined as T) : response.json();
  }

  // --- Clubes ---
  createClub(payload: { name: string; official_email_domain: string; admin_full_name: string; admin_email: string }) {
    return this.request<Club>("/clubs", { method: "POST", body: JSON.stringify(payload) });
  }

  listMyClubs() {
    return this.request<unknown[]>("/clubs/me");
  }

  createTeam(clubId: string, payload: { name: string; season?: string }) {
    return this.request<Team>(`/clubs/${clubId}/teams`, { method: "POST", body: JSON.stringify(payload) });
  }

  createAthlete(clubId: string, payload: Partial<Athlete> & { full_name: string }) {
    return this.request<Athlete>(`/clubs/${clubId}/athletes`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  // --- Partidas e upload de vídeo ---
  createMatch(payload: Partial<Match>, clubId?: string) {
    const query = clubId ? `?club_id=${clubId}` : "";
    return this.request<Match>(`/matches${query}`, { method: "POST", body: JSON.stringify(payload) });
  }

  initiateVideoUpload(
    payload: {
      match_id?: string;
      video_type: "propria_equipe" | "adversario";
      original_filename: string;
      size_bytes: number;
    },
    clubId?: string,
  ) {
    const query = clubId ? `?club_id=${clubId}` : "";
    return this.request<UploadInitiateResponse>(`/videos/upload/initiate${query}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  completeVideoUpload(payload: { video_id: string; duration_seconds: number; codec: string }) {
    return this.request(`/videos/upload/complete`, { method: "POST", body: JSON.stringify(payload) });
  }

  // --- Processamento ---
  getJobStatus(videoId: string) {
    return this.request<AnalysisJob>(`/videos/${videoId}/job`);
  }

  listDetectedPlayers(videoId: string) {
    return this.request<DetectedPlayer[]>(`/videos/${videoId}/players`);
  }

  linkPlayerToAthlete(videoId: string, detectedPlayerId: string, athleteId: string) {
    return this.request<DetectedPlayer>(`/videos/${videoId}/players/${detectedPlayerId}/link`, {
      method: "POST",
      body: JSON.stringify({ athlete_id: athleteId }),
    });
  }

  getPlayerStats(videoId: string, detectedPlayerId: string) {
    return this.request<PlayerMatchStats>(`/videos/${videoId}/players/${detectedPlayerId}/stats`);
  }

  // --- Seleção manual de jogador ---
  requestReferenceFrame(videoId: string) {
    return this.request<void>(`/videos/${videoId}/reference-frame`, { method: "POST" });
  }

  getReferenceFrame(videoId: string) {
    return this.request<ReferenceFrame>(`/videos/${videoId}/reference-frame`);
  }

  getPlaybackUrl(videoId: string) {
    return this.request<PlaybackUrl>(`/videos/${videoId}/playback-url`);
  }

  listSelectionHints(videoId: string) {
    return this.request<SelectionHint[]>(`/videos/${videoId}/selection-hints`);
  }

  createSelectionHint(
    videoId: string,
    payload: {
      athlete_id: string;
      timestamp_ms: number;
      bbox_x1: number;
      bbox_y1: number;
      bbox_x2: number;
      bbox_y2: number;
      frame_width: number;
      frame_height: number;
    },
  ) {
    return this.request<SelectionHint>(`/videos/${videoId}/selection-hints`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  deleteSelectionHint(videoId: string, athleteId: string) {
    return this.request<void>(`/videos/${videoId}/selection-hints/${athleteId}`, { method: "DELETE" });
  }

  // --- Eventos e clipes ---
  listEvents(videoId: string) {
    return this.request<MatchEventWithClips[]>(`/videos/${videoId}/events`);
  }

  // --- Relatórios ---
  requestMatchReport(matchId: string) {
    return this.request(`/matches/${matchId}/report`, { method: "POST" });
  }

  // --- Notificações ---
  listNotifications(unreadOnly = false) {
    return this.request<Notification[]>(`/notifications?unread_only=${unreadOnly}`);
  }

  markNotificationAsRead(notificationId: string) {
    return this.request(`/notifications/${notificationId}/read`, { method: "POST" });
  }
}
