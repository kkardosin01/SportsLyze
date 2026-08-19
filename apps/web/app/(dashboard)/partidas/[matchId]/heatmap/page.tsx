"use client";

import type { DetectedPlayer, PlayerMatchStats } from "@sportslyze/shared-types";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { createApiClient } from "@/lib/api-client";
import { HeatmapCanvas } from "./HeatmapCanvas";

/** Renderiza o heatmap (matriz de densidade) calculado a partir da
 * homografia do campo. A matriz vem de `player_match_stats.heatmap`,
 * exposta pela API em `/videos/{video_id}/players/{detected_player_id}/stats`. */
export default function HeatmapPage() {
  const videoId = useSearchParams().get("videoId");
  const [players, setPlayers] = useState<DetectedPlayer[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [stats, setStats] = useState<PlayerMatchStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!videoId) return;
    createApiClient()
      .listDetectedPlayers(videoId)
      .then((list) => {
        setPlayers(list);
        setSelectedId((current) => current ?? list[0]?.id ?? null);
      });
  }, [videoId]);

  useEffect(() => {
    if (!videoId || !selectedId) return;
    setLoading(true);
    setError(null);
    setNotFound(false);
    createApiClient()
      .getPlayerStats(videoId, selectedId)
      .then((data) => setStats(data))
      .catch((err: Error & { status?: number }) => {
        setStats(null);
        if (err.status === 404) {
          setNotFound(true);
        } else {
          setError(err.message ?? "Não foi possível carregar as estatísticas.");
        }
      })
      .finally(() => setLoading(false));
  }, [videoId, selectedId]);

  if (!videoId) {
    return <p className="text-sm text-gray-500">Vídeo não informado.</p>;
  }

  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Heatmap por jogador</h2>

      {players.length === 0 ? (
        <p className="text-sm text-gray-500">
          Nenhum jogador detectado ainda — a análise pode estar em andamento.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {players.map((player) => (
            <button
              key={player.id}
              onClick={() => setSelectedId(player.id)}
              className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
                selectedId === player.id
                  ? "bg-brand-700 text-white"
                  : "bg-white text-gray-600 shadow-sm hover:bg-brand-50"
              }`}
            >
              {player.label}
            </button>
          ))}
        </div>
      )}

      {loading ? <p className="text-sm text-gray-400">Carregando estatísticas...</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {notFound && !loading ? (
        <p className="text-sm text-gray-500">
          Estatísticas ainda não disponíveis para este jogador — pode ser que a análise não tenha
          conseguido calcular a homografia do campo neste vídeo.
        </p>
      ) : null}

      {stats && !loading ? (
        <div className="space-y-6 rounded-xl bg-white p-6 shadow-sm">
          {stats.heatmap && stats.heatmap.length > 0 ? (
            <HeatmapCanvas heatmap={stats.heatmap} />
          ) : (
            <p className="text-sm text-gray-500">
              Heatmap ainda não disponível para este jogador (homografia não calculada neste
              vídeo).
            </p>
          )}

          <div className="grid grid-cols-3 gap-4 text-center">
            <Stat
              label="Distância percorrida"
              value={stats.distance_km != null ? `${stats.distance_km.toFixed(2)} km` : "—"}
            />
            <Stat
              label="Velocidade média"
              value={stats.avg_speed_kmh != null ? `${stats.avg_speed_kmh.toFixed(1)} km/h` : "—"}
            />
            <Stat
              label="Velocidade máxima"
              value={stats.max_speed_kmh != null ? `${stats.max_speed_kmh.toFixed(1)} km/h` : "—"}
            />
          </div>
        </div>
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
