"use client";

import type { MatchEventWithClips } from "@sportslyze/shared-types";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { createApiClient } from "@/lib/api-client";
import { EventsTimelinePlayer } from "./EventsTimelinePlayer";

/** Lista os eventos detectados automaticamente (heurísticas sobre o
 * tracking, ver `sportslyze_cv.events.EventDetector`) sobre um player do
 * vídeo original, com marcadores clicáveis na timeline e os clipes já
 * cortados para cada evento, quando disponíveis. Fase 2 detecta passe,
 * drible, triangulação, finalização e falta — "desarme" e "jogada
 * ensaiada" ficam para um próximo incremento (exigem classificação de
 * time, ainda não implementada). */
export default function ClipesPage() {
  const videoId = useSearchParams().get("videoId");
  const [playbackUrl, setPlaybackUrl] = useState<string | null>(null);
  const [events, setEvents] = useState<MatchEventWithClips[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!videoId) return;
    setLoading(true);
    setError(null);
    Promise.all([createApiClient().getPlaybackUrl(videoId), createApiClient().listEvents(videoId)])
      .then(([playback, eventList]) => {
        setPlaybackUrl(playback.url);
        setEvents(eventList);
      })
      .catch((err: Error) => setError(err.message ?? "Não foi possível carregar os eventos."))
      .finally(() => setLoading(false));
  }, [videoId]);

  if (!videoId) {
    return <p className="text-sm text-gray-500">Vídeo não informado.</p>;
  }

  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Clipes por evento</h2>
      <p className="text-sm text-gray-500">
        Eventos detectados automaticamente a partir do rastreamento de jogadores e da bola: passe,
        drible, triangulação, finalização e falta. Os tipos desarme e jogada ensaiada ficam para um
        próximo incremento — exigem identificar o time de cada jogador, o que ainda não é feito
        automaticamente.
      </p>

      {loading ? <p className="text-sm text-gray-400">Carregando...</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {playbackUrl && !loading ? (
        events.length > 0 ? (
          <EventsTimelinePlayer playbackUrl={playbackUrl} events={events} />
        ) : (
          <div className="space-y-4">
            <video src={playbackUrl} controls className="w-full max-w-3xl rounded-lg bg-black" />
            <p className="text-sm text-gray-500">
              Nenhum evento detectado ainda — a análise pode estar em andamento ou não encontrou
              transições de posse de bola suficientemente confiáveis neste vídeo.
            </p>
          </div>
        )
      ) : null}
    </div>
  );
}
