from typing import Any

from src.repositories.base import SupabaseRepository


class ClubRepository(SupabaseRepository):
    table_name = "clubs"


class ClubMemberRepository(SupabaseRepository):
    table_name = "club_members"

    def find_membership(self, club_id: str, user_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table(self.table_name)
            .select("*")
            .eq("club_id", club_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        return result.data

    def list_by_user(self, user_id: str) -> list[dict[str, Any]]:
        result = self._client.table(self.table_name).select("*, clubs(*)").eq("user_id", user_id).execute()
        return result.data or []


class TeamRepository(SupabaseRepository):
    table_name = "teams"


class AthleteRepository(SupabaseRepository):
    table_name = "athletes"
