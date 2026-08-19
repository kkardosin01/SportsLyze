from fastapi import APIRouter, Depends

from src.api.deps import get_notification_service
from src.core.security import CurrentUser, get_current_user
from src.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notificações"])


@router.get("")
def list_notifications(
    unread_only: bool = False,
    user: CurrentUser = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    return service.list_for_user(user.id, unread_only)


@router.post("/{notification_id}/read")
def mark_as_read(notification_id: str, service: NotificationService = Depends(get_notification_service)):
    return service.mark_read(notification_id)
