"use client";

import type { AggregatedStats } from "@sportslyze/shared-types";
import { HeatmapCanvas } from "@sportslyze/ui";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { createApiClient } from "@/lib/api-client";

/** Estatísticas agregadas do atleta em todas as partidas do próprio time
 * já analisadas — soma distância, médias de velocidade e heatmap somado
 * célula a célula (ver `StatsService.get_aggregated_stats` na API).
 * Vídeos de scouting de adversário não entram nessa agregação, pois não
 * representam a performance do atleta. */
export default function AtletaEstatisticasPage() {
  const { athleteId } = useParams<{ athleteId: string }>();
  const [stats, setStats] = useState<AggregatedStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!athleteId) return;
    setLoading(true);
    setError(null);
    createApiClient()
      .getAggregatedStats(athleteId)
      .then(setStats)
      .catch((err: Error) => setError(err.message ?? "Não foi possível carregar as estatísticas."))
      .finally(() => setLoading(false));
  }, [athleteId]);

  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Estatísticas agregadas</h2>

      {loading ? <p className="text-sm text-gray-400">Carregando...</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {stats && !loading ? (
        stats.matches_analyzed === 0 ? (
          <p className="text-sm text-gray-500">
            Nenhuma partida do próprio time com análise concluída para este atleta ainda.
          </p>
        ) : (
          <div className="space-y-6">
            <div className="space-y-6 rounded-xl bg-white p-6 shadow-sm">
              {stats.heatmap.length > 0 ? (
                <HeatmapCanvas heatmap={stats.heatmap} />
              ) : (
                <p className="text-sm text-gray-500">
                  Heatmap agregado ainda não disponível (nenhuma partida com homografia calculada).
                </p>
              )}

              <div className="grid grid-cols-4 gap-4 text-center">
                <Stat label="Partidas analisadas" value={String(stats.matches_analyzed)} />
                <Stat label="Distância total" value={`${stats.total_distance_km.toFixed(2)} km`} />
                <Stat label="Velocidade média" value={`${stats.avg_speed_kmh.toFixed(1)} km/h`} />
                <Stat label="Velocidade máxima" value={`${stats.max_speed_kmh.toFixed(1)} km/h`} />
              </div>
            </div>

            <div className="rounded-xl bg-white p-6 shadow-sm">
              <h3 className="mb-4 font-semibold">Por partida</h3>
              <ul className="space-y-2">
                {stats.matches.map((match) => (
                  <li
                    key={match.video_id}
                    className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-2 text-sm"
                  >
                    <span>
                      {match.opponent_name ? `vs. ${match.opponent_name}` : "Partida"}
                      {match.match_date ? ` — ${match.match_date}` : ""}
                    </span>
                    <span className="text-gray-500">
                      {match.distance_km.toFixed(2)} km · {match.avg_speed_kmh.toFixed(1)} km/h méd.
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-lg font-semibold">{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}
