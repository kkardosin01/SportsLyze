from typing import Any

from supabase import Client


class SupabaseRepository:
    """Repositório base fino sobre o client Supabase (service role).

    Mantém o acesso a dados isolado da camada de serviço/regras de negócio,
    facilitando troca de storage/driver no futuro sem tocar nos services.
    """

    table_name: str

    def __init__(self, client: Client):
        self._client = client

    def get_by_id(self, record_id: str) -> dict[str, Any] | None:
        result = self._client.table(self.table_name).select("*").eq("id", record_id).maybe_single().execute()
        return result.data if result else None

    def list(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query = self._client.table(self.table_name).select("*")
        for key, value in (filters or {}).items():
            query = query.eq(key, value)
        result = query.execute()
        return result.data or []

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._client.table(self.table_name).insert(payload).execute()
        return result.data[0]

    def update(self, record_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = self._client.table(self.table_name).update(payload).eq("id", record_id).execute()
        return result.data[0]

    def delete(self, record_id: str) -> None:
        self._client.table(self.table_name).delete().eq("id", record_id).execute()
