from src.repositories.base import SupabaseRepository


class MatchRepository(SupabaseRepository):
    table_name = "matches"


class VideoRepository(SupabaseRepository):
    table_name = "videos"


class AnalysisJobRepository(SupabaseRepository):
    table_name = "analysis_jobs"

    def get_latest_for_video(self, video_id: str) -> dict | None:
        result = (
            self._client.table(self.table_name)
            .select("*")
            .eq("video_id", video_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None


class DetectedPlayerRepository(SupabaseRepository):
    table_name = "detected_players"

    def list_for_video(self, video_id: str) -> list[dict]:
        result = self._client.table(self.table_name).select("*").eq("video_id", video_id).execute()
        return result.data or []


class PlayerMatchStatsRepository(SupabaseRepository):
    table_name = "player_match_stats"

    def get_for_player(self, video_id: str, detected_player_id: str) -> dict | None:
        result = (
            self._client.table(self.table_name)
            .select("*")
            .eq("video_id", video_id)
            .eq("detected_player_id", detected_player_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None


class NotificationRepository(SupabaseRepository):
    table_name = "notifications"

    def list_for_user(self, user_id: str, unread_only: bool = False) -> list[dict]:
        query = self._client.table(self.table_name).select("*").eq("user_id", user_id)
        if unread_only:
            query = query.is_("read_at", "null")
        result = query.order("created_at", desc=True).execute()
        return result.data or []


class VideoReferenceFrameRepository(SupabaseRepository):
    table_name = "video_reference_frames"

    def get_for_video(self, video_id: str) -> dict | None:
        result = (
            self._client.table(self.table_name).select("*").eq("video_id", video_id).maybe_single().execute()
        )
        return result.data if result else None


class PlayerSelectionHintRepository(SupabaseRepository):
    table_name = "player_selection_hints"

    def list_for_video(self, video_id: str) -> list[dict]:
        result = self._client.table(self.table_name).select("*").eq("video_id", video_id).execute()
        return result.data or []

    def upsert(self, payload: dict) -> dict:
        result = self._client.table(self.table_name).upsert(payload, on_conflict="video_id,athlete_id").execute()
        return result.data[0]

    def delete_for_athlete(self, video_id: str, athlete_id: str) -> None:
        self._client.table(self.table_name).delete().eq("video_id", video_id).eq(
            "athlete_id", athlete_id
        ).execute()
