from fastapi import APIRouter, Depends

from src.api.deps import get_report_service
from src.core.security import CurrentUser, get_current_user
from src.schemas.report import ReportOut, ReportRequest
from src.services.report_service import ReportService

router = APIRouter(prefix="/matches/{match_id}", tags=["relatórios"])


@router.post("/report", status_code=202)
def request_match_report(
    match_id: str,
    payload: ReportRequest = ReportRequest(),
    user: CurrentUser = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    """Enfileira a geração do relatório da partida no formato solicitado
    (PDF, slides ou áudio). A geração roda no worker; o client consulta
    `GET /matches/{match_id}/reports` para saber quando fica disponível."""
    service.request_report(match_id, user.id, payload.format)
    return {"status": "queued"}


@router.get("/reports", response_model=list[ReportOut])
def list_match_reports(
    match_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
):
    return service.list_reports(match_id, user.id)
