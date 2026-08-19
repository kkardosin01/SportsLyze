"use client";

import type { Match } from "@sportslyze/shared-types";
import { Button } from "@sportslyze/ui";
import Link from "next/link";
import { useState } from "react";
import { UploadVideoForm } from "@/components/UploadVideoForm";
import { createApiClient } from "@/lib/api-client";

export default function PartidasPage() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [creating, setCreating] = useState(false);
  const [opponentName, setOpponentName] = useState("");
  const [uploadingMatchId, setUploadingMatchId] = useState<string | null>(null);

  async function handleCreateMatch(event: React.FormEvent) {
    event.preventDefault();
    const api = createApiClient();
    const match = await api.createMatch({ opponent_name: opponentName });
    setMatches((prev) => [match, ...prev]);
    setOpponentName("");
    setCreating(false);
    setUploadingMatchId(match.id);
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Partidas</h1>
          <p className="text-sm text-gray-600">Envie o vídeo da partida para iniciar a análise.</p>
        </div>
        <Button onClick={() => setCreating(true)}>Nova partida</Button>
      </div>

      {creating ? (
        <form onSubmit={handleCreateMatch} className="flex gap-2 rounded-xl bg-white p-4 shadow-sm">
          <input
            placeholder="Adversário"
            value={opponentName}
            onChange={(e) => setOpponentName(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <Button type="submit">Criar</Button>
        </form>
      ) : null}

      {uploadingMatchId ? (
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h2 className="mb-4 font-semibold">Enviar vídeo da partida</h2>
          <UploadVideoForm
            matchId={uploadingMatchId}
            videoType="propria_equipe"
            onCompleted={() => setUploadingMatchId(null)}
          />
        </div>
      ) : null}

      <ul className="space-y-2">
        {matches.map((match) => (
          <li key={match.id}>
            <Link
              href={`/partidas/${match.id}`}
              className="block rounded-xl bg-white p-4 shadow-sm hover:bg-brand-50"
            >
              <p className="font-medium">{match.opponent_name ?? "Partida sem adversário definido"}</p>
              <p className="text-sm text-gray-500">{match.match_date ?? "Data não definida"}</p>
            </Link>
          </li>
        ))}
        {matches.length === 0 ? <p className="text-sm text-gray-400">Nenhuma partida cadastrada ainda.</p> : null}
      </ul>
    </div>
  );
}
