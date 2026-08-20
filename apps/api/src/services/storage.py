import uuid

from supabase import Client

from src.core.config import get_settings


class StorageService:
    def __init__(self, client: Client):
        self._client = client
        self._settings = get_settings()

    def build_video_path(self, owner_type: str, owner_id: str, original_filename: str) -> str:
        extension = original_filename.rsplit(".", 1)[-1].lower()
        return f"{owner_type}/{owner_id}/{uuid.uuid4()}.{extension}"

    def create_resumable_upload_url(self, storage_path: str) -> str:
        """Cria uma URL de upload assinada no bucket de vídeos.

        Para uploads grandes (~4-8GB) o client (web/mobile) deve usar o
        protocolo TUS do Supabase Storage, que suporta upload resumável em
        chunks. Esta URL serve como ponto de entrada para a sessão TUS.
        """
        bucket = self._settings.supabase_storage_bucket_videos
        result = self._client.storage.from_(bucket).create_signed_upload_url(storage_path)
        return result["signed_url"]

    def delete_video_file(self, storage_path: str) -> None:
        bucket = self._settings.supabase_storage_bucket_videos
        self._client.storage.from_(bucket).remove([storage_path])

    def create_signed_reference_frame_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """URL assinada de curta duração para o frontend exibir o frame de
        referência — o bucket é privado (frames de vídeo de atletas menores
        de idade), então nunca expomos um link permanente."""
        bucket = self._settings.supabase_storage_bucket_reference_frames
        result = self._client.storage.from_(bucket).create_signed_url(storage_path, expires_in)
        return result.get("signedURL") or result.get("signed_url")

    def create_signed_video_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """URL assinada de curta duração para o frontend reproduzir o vídeo
        original — o bucket é privado pelo mesmo motivo do frame de
        referência. O Supabase Storage é compatível com Range Requests, então
        essa URL funciona diretamente em um elemento <video> com seek."""
        bucket = self._settings.supabase_storage_bucket_videos
        result = self._client.storage.from_(bucket).create_signed_url(storage_path, expires_in)
        return result.get("signedURL") or result.get("signed_url")
