"use client";

import type { DetectedPlayer } from "@sportslyze/shared-types";
import { Button } from "@sportslyze/ui";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { createApiClient } from "@/lib/api-client";

/** Tela de revisão manual: associa cada track anônimo ("Jogador A", "Jogador
 * B"...) a um atleta cadastrado. O número de camisa por OCR aparece só como
 * sugestão — nunca é a fonte de verdade da identidade do jogador. */
export default function RevisaoJogadoresPage() {
  const videoId = useSearchParams().get("videoId");
  const [players, setPlayers] = useState<DetectedPlayer[]>([]);

  useEffect(() => {
    if (!videoId) return;
    createApiClient().listDetectedPlayers(videoId).then(setPlayers);
  }, [videoId]);

  async function handleLink(detectedPlayerId: string, athleteId: string) {
    if (!videoId) return;
    const updated = await createApiClient().linkPlayerToAthlete(videoId, detectedPlayerId, athleteId);
    setPlayers((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  }

  if (!videoId) {
    return <p className="text-sm text-gray-500">Vídeo não informado.</p>;
  }

  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Revisão de jogadores</h2>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {players.map((player) => (
          <div key={player.id} className="rounded-xl bg-white p-4 shadow-sm">
            <p className="font-medium">{player.label}</p>
            {player.ocr_jersey_number ? (
              <p className="text-xs text-gray-500">Sugestão OCR: nº {player.ocr_jersey_number}</p>
            ) : null}
            {player.athlete_id ? (
              <p className="mt-2 text-sm text-brand-700">Vinculado</p>
            ) : (
              <Button
                variant="secondary"
                className="mt-2 w-full"
                onClick={() => {
                  const athleteId = window.prompt("ID do atleta para vincular:");
                  if (athleteId) handleLink(player.id, athleteId);
                }}
              >
                Associar atleta
              </Button>
            )}
          </div>
        ))}
        {players.length === 0 ? (
          <p className="text-sm text-gray-400">Nenhum jogador detectado ainda — a análise pode estar em andamento.</p>
        ) : null}
      </div>
    </div>
  );
}
