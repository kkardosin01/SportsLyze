"use client";

import { useState } from "react";
import { UploadVideoForm } from "@/components/UploadVideoForm";
import { createApiClient } from "@/lib/api-client";

export default function AtletaPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-bold">Área do atleta</h1>
        <p className="text-sm text-gray-600">
          Envie o vídeo da sua partida para receber sua análise individual, ou o vídeo de um
          adversário para receber scouting.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h2 className="mb-2 font-semibold">Minha performance</h2>
          <UploadForBucket videoType="propria_equipe" />
        </div>
        <div className="rounded-xl bg-white p-6 shadow-sm">
          <h2 className="mb-2 font-semibold">Scouting de adversário</h2>
          <UploadForBucket videoType="adversario" />
        </div>
      </div>
    </div>
  );
}

function UploadForBucket({ videoType }: { videoType: "propria_equipe" | "adversario" }) {
  const [matchId, setMatchId] = useState<string | null>(null);

  if (!matchId) {
    return (
      <button
        className="text-sm text-brand-700 underline"
        onClick={async () => {
          const match = await createApiClient().createMatch({});
          setMatchId(match.id);
        }}
      >
        Selecionar vídeo
      </button>
    );
  }

  return <UploadVideoForm matchId={matchId} videoType={videoType} onCompleted={() => setMatchId(null)} />;
}
