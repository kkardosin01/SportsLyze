"use client";

import type { DetectedPlayer } from "@sportslyze/shared-types";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { createApiClient } from "@/lib/api-client";

/** Visão somente leitura dos jogadores detectados em um vídeo de scouting do
 * adversário. Diferente de `revisao-jogadores`, não há vinculação a
 * `athletes` do clube — os jogadores aqui são do time rival, então só a
 * sugestão de número de camisa (OCR) é exibida. */
export default function ScoutingPage() {
  const videoId = useSearchParams().get("videoId");
  const [players, setPlayers] = useState<DetectedPlayer[]>([]);

  useEffect(() => {
    if (!videoId) return;
    createApiClient().listDetectedPlayers(videoId).then(setPlayers);
  }, [videoId]);

  if (!videoId) {
    return <p className="text-sm text-gray-500">Vídeo não informado.</p>;
  }

  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Jogadores detectados (scouting)</h2>
      <p className="text-sm text-gray-500">
        Jogadores do time adversário detectados automaticamente neste vídeo de scouting. Números de
        camisa são sugestões de OCR — confira contra a súmula da partida.
      </p>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {players.map((player) => (
          <div key={player.id} className="rounded-xl bg-white p-4 shadow-sm">
            <p className="font-medium">{player.label}</p>
            {player.ocr_jersey_number ? (
              <p className="text-xs text-gray-500">Sugestão OCR: nº {player.ocr_jersey_number}</p>
            ) : (
              <p className="text-xs text-gray-400">Número não identificado</p>
            )}
          </div>
        ))}
        {players.length === 0 ? (
          <p className="text-sm text-gray-400">
            Nenhum jogador detectado ainda — a análise pode estar em andamento.
          </p>
        ) : null}
      </div>
    </div>
  );
}
