from functools import lru_cache

from supabase import Client, create_client

from src.core.config import get_settings


@lru_cache
def get_supabase_admin() -> Client:
    """Client Supabase com service role key — usado pela API para ler/gravar
    dados após aplicar as regras de autorização nos services (RLS é a rede
    de segurança, não a única linha de defesa)."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
