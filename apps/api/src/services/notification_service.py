from datetime import datetime, timezone

from src.repositories.videos import NotificationRepository


class NotificationService:
    def __init__(self, repo: NotificationRepository):
        self._repo = repo

    def list_for_user(self, user_id: str, unread_only: bool = False) -> list[dict]:
        return self._repo.list_for_user(user_id, unread_only)

    def mark_read(self, notification_id: str) -> dict:
        return self._repo.update(notification_id, {"read_at": datetime.now(timezone.utc).isoformat()})

    def notify(self, user_id: str, type_: str, title: str, message: str | None = None) -> dict:
        return self._repo.create(
            {"user_id": user_id, "type": type_, "title": title, "message": message}
        )
