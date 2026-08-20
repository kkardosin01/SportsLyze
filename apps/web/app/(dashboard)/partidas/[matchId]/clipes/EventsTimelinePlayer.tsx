"use client";

import type { MatchEventWithClips } from "@sportslyze/shared-types";
import { useRef, useState } from "react";

const EVENT_LABELS: Record<string, string> = {
  passe: "Passe",
  drible: "Drible",
  desarme: "Desarme",
  falta: "Falta",
  finalizacao: "Finalização",
  triangulacao: "Triangulação",
  jogada_ensaiada: "Jogada ensaiada",
};

interface Props {
  playbackUrl: string;
  events: MatchEventWithClips[];
}

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds)) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** Player do vídeo original com marcadores na barra de progresso para cada
 * evento detectado automaticamente (heurística de posse de bola, ver
 * `sportslyze_cv.events.EventDetector`) — clicar num marcador pula o vídeo
 * para o instante do evento. Abaixo, a lista dos mesmos eventos com o clipe
 * já cortado, quando disponível (o corte é acessório ao evento: pode faltar
 * se o ffmpeg falhar para aquele evento específico, sem impedir os demais). */
export function EventsTimelinePlayer({ playbackUrl, events }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  function seekTo(ms: number) {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = ms / 1000;
    video.play();
  }

  function togglePlay() {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) video.play();
    else video.pause();
  }

  function handleSeek(e: React.ChangeEvent<HTMLInputElement>) {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = Number(e.target.value);
    setCurrentTime(video.currentTime);
  }

  return (
    <div className="space-y-2">
      <video
        ref={videoRef}
        src={playbackUrl}
        className="w-full max-w-3xl rounded-lg bg-black"
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
        onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      />

      <div className="flex max-w-3xl items-center gap-3">
        <button
          type="button"
          onClick={togglePlay}
          className="rounded-lg bg-brand-700 px-3 py-1.5 text-sm text-white"
        >
          {isPlaying ? "Pausar" : "Reproduzir"}
        </button>

        <div className="relative flex-1">
          <input
            type="range"
            min={0}
            max={duration || 0}
            step={0.1}
            value={currentTime}
            onChange={handleSeek}
            className="w-full"
          />
          {duration > 0 ? (
            <div className="pointer-events-none absolute inset-x-0 top-1/2 h-0">
              {events.map((event) => (
                <button
                  key={event.id}
                  type="button"
                  title={`${EVENT_LABELS[event.event_type] ?? event.event_type} em ${formatTime(
                    event.start_time_ms / 1000,
                  )}`}
                  onClick={() => seekTo(event.start_time_ms)}
                  className="pointer-events-auto absolute top-1/2 h-2.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-sm bg-brand-700"
                  style={{ left: `${(event.start_time_ms / 1000 / duration) * 100}%` }}
                />
              ))}
            </div>
          ) : null}
        </div>

        <span className="w-24 text-right text-xs text-gray-500">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>

      <ul className="space-y-2">
        {events.map((event) => (
          <li key={event.id} className="rounded-lg bg-white p-3 shadow-sm">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => seekTo(event.start_time_ms)}
                className="text-sm font-medium text-brand-700 hover:underline"
              >
                {EVENT_LABELS[event.event_type] ?? event.event_type} — {formatTime(event.start_time_ms / 1000)}
              </button>
              {event.confidence != null ? (
                <span className="text-xs text-gray-400">confiança {(event.confidence * 100).toFixed(0)}%</span>
              ) : null}
            </div>

            {event.clips.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-3">
                {event.clips.map((clip) =>
                  clip.playback_url ? (
                    <video key={clip.id} src={clip.playback_url} controls className="w-64 rounded-lg bg-black" />
                  ) : null,
                )}
              </div>
            ) : (
              <p className="mt-1 text-xs text-gray-400">Clipe ainda não disponível para este evento.</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
