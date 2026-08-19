from fastapi import APIRouter, Depends

from src.core.celery_client import get_celery_client
from src.core.security import CurrentUser, get_current_user

router = APIRouter(prefix="/matches/{match_id}/report", tags=["relatórios"])


@router.post("", status_code=202)
def request_match_report(match_id: str, user: CurrentUser = Depends(get_current_user)):
    """Enfileira a geração do relatório PDF da partida. A geração roda no
    worker (WeasyPrint); o client consulta `reports` (via Supabase) para
    saber quando o PDF fica disponível."""
    celery_client = get_celery_client()
    celery_client.send_task("tasks.generate_match_report", args=[match_id, user.id])
    return {"status": "queued"}
