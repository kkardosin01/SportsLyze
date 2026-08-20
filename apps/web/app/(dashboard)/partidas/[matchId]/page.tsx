"use client";

import type { Video } from "@sportslyze/shared-types";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { createApiClient } from "@/lib/api-client";

const TABS_PROPRIA_EQUIPE = [
  { href: "selecionar-jogador", label: "Selecionar jogador" },
  { href: "revisao-jogadores", label: "Revisão de jogadores" },
  { href: "heatmap", label: "Heatmap" },
  { href: "clipes", label: "Clipes" },
  { href: "relatorio", label: "Relatório" },
];

// Vídeo de scouting do adversário: os jogadores detectados não pertencem ao
// elenco do clube, então as abas de vinculação manual (que sempre apontam
// para `athletes` do próprio clube) não fazem sentido aqui — mostramos uma
// aba de "Jogadores (scouting)" somente leitura no lugar delas. Heatmap,
// clipes e relatório continuam válidos, pois não dependem do vínculo.
const TABS_ADVERSARIO = [
  { href: "scouting", label: "Jogadores (scouting)" },
  { href: "heatmap", label: "Heatmap" },
  { href: "clipes", label: "Clipes" },
  { href: "relatorio", label: "Relatório" },
];

export default function PartidaPage({ params }: { params: { matchId: string } }) {
  const videoId = useSearchParams().get("videoId");
  const [video, setVideo] = useState<Video | null>(null);

  useEffect(() => {
    if (!videoId) return;
    createApiClient().getVideo(videoId).then(setVideo);
  }, [videoId]);

  const tabs = video?.video_type === "adversario" ? TABS_ADVERSARIO : TABS_PROPRIA_EQUIPE;
  const query = videoId ? `?videoId=${videoId}` : "";

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Partida</h1>

      {/* Player de vídeo com timeline de eventos clicável é adicionado quando
          o pipeline de eventos (Fase 2) estiver disponível. Na Fase 1, o
          acesso aos resultados é feito pelas abas abaixo. */}

      <nav className="flex gap-2 border-b border-gray-200">
        {tabs.map((tab) => (
          <Link
            key={tab.href}
            href={`/partidas/${params.matchId}/${tab.href}${query}`}
            className="px-4 py-2 text-sm text-gray-600 hover:text-brand-700"
          >
            {tab.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
