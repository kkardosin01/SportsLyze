from src.repositories.base import SupabaseRepository


class ReportRepository(SupabaseRepository):
    table_name = "reports"

    def list_for_match(self, match_id: str) -> list[dict]:
        result = (
            self._client.table(self.table_name)
            .select("*")
            .eq("match_id", match_id)
            .order("generated_at", desc=True)
            .execute()
        )
        return result.data or []
