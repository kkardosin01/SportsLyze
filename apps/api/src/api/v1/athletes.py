from fastapi import APIRouter, Depends

from src.api.deps import get_stats_service
from src.core.security import CurrentUser, get_current_user
from src.schemas.stats import AggregatedStatsOut
from src.services.stats_service import StatsService

router = APIRouter(prefix="/athletes", tags=["atletas"])


@router.get("/{athlete_id}/stats/aggregated", response_model=AggregatedStatsOut)
def get_aggregated_stats(
    athlete_id: str,
    user: CurrentUser = Depends(get_current_user),
    service: StatsService = Depends(get_stats_service),
):
    """Estatísticas agregadas do atleta em todas as partidas do próprio
    time já analisadas (soma distância, médias de velocidade, heatmap
    somado e a lista por partida)."""
    return service.get_aggregated_stats(athlete_id, user.id)
