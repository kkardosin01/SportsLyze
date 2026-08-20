"use client";

import type { ReferenceFrame, SelectionHint } from "@sportslyze/shared-types";
import { Button } from "@sportslyze/ui";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { createApiClient } from "@/lib/api-client";
import { ReferenceFrameSelector } from "./ReferenceFrameSelector";
import { VideoFrameSelector } from "./VideoFrameSelector";

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 60000;

/** Seleção manual de jogador: o coach marca visualmente um atleta já
 * cadastrado sobre um frame do vídeo, antes da análise completa. Isso vira
 * um prior espacial (não um substituto de número de camisa) que o worker
 * usa para pré-vincular automaticamente o track correspondente ao rodar o
 * tracking — ver `sportslyze_cv.pipeline._resolve_hints`. Quando nenhum
 * jogador é selecionado, a análise roda normalmente para o time todo. */
export default function SelecionarJogadorPage() {
  const videoId = useSearchParams().get("videoId");
  const [mode, setMode] = useState<"frame" | "video">("frame");
  const [frame, setFrame] = useState<ReferenceFrame | null>(null);
  const [hints, setHints] = useState<SelectionHint[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playbackUrl, setPlaybackUrl] = useState<string | null>(null);
  const [loadingPlayback, setLoadingPlayback] = useState(false);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const playbackRequested = useRef(false);

  const loadHints = useCallback(async () => {
    if (!videoId) return;
    setHints(await createApiClient().listSelectionHints(videoId));
  }, [videoId]);

  const loadFrame = useCallback(async () => {
    if (!videoId) return false;
    try {
      setFrame(await createApiClient().getReferenceFrame(videoId));
      return true;
    } catch (err: unknown) {
      if ((err as Error & { status?: number }).status !== 404) {
        setError((err as Error).message ?? "Não foi possível carregar o frame de referência.");
      }
      return false;
    }
  }, [videoId]);

  useEffect(() => {
    if (!videoId) return;
    loadFrame();
    loadHints();
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, [videoId, loadFrame, loadHints]);

  const loadPlaybackUrl = useCallback(async () => {
    if (!videoId) return;
    setLoadingPlayback(true);
    setError(null);
    try {
      const res = await createApiClient().getPlaybackUrl(videoId);
      setPlaybackUrl(res.url);
    } catch (err) {
      setError((err as Error).message ?? "Não foi possível carregar o vídeo.");
    } finally {
      setLoadingPlayback(false);
    }
  }, [videoId]);

  useEffect(() => {
    if (mode !== "video" || !videoId || playbackRequested.current) return;
    playbackRequested.current = true;
    loadPlaybackUrl();
  }, [mode, videoId, loadPlaybackUrl]);

  async function handleExtractFrame() {
    if (!videoId) return;
    setError(null);
    setExtracting(true);
    try {
      await createApiClient().requestReferenceFrame(videoId);

      const startedAt = Date.now();
      pollTimer.current = setInterval(async () => {
        const found = await loadFrame();
        if (found) {
          setExtracting(false);
          if (pollTimer.current) clearInterval(pollTimer.current);
          return;
        }
        if (Date.now() - startedAt > POLL_TIMEOUT_MS) {
          setExtracting(false);
          setError("Não foi possível extrair o frame de referência. Tente novamente.");
          if (pollTimer.current) clearInterval(pollTimer.current);
        }
      }, POLL_INTERVAL_MS);
    } catch (err) {
      setExtracting(false);
      setError((err as Error).message ?? "Não foi possível iniciar a extração do frame.");
    }
  }

  async function handleCreateHint(bbox: { x1: number; y1: number; x2: number; y2: number }) {
    if (!videoId || !frame) return;
    const athleteId = window.prompt("ID do atleta marcado neste jogador:");
    if (!athleteId) return;

    try {
      await createApiClient().createSelectionHint(videoId, {
        athlete_id: athleteId,
        timestamp_ms: frame.timestamp_ms,
        bbox_x1: bbox.x1,
        bbox_y1: bbox.y1,
        bbox_x2: bbox.x2,
        bbox_y2: bbox.y2,
        frame_width: frame.frame_width,
        frame_height: frame.frame_height,
      });
      await loadHints();
    } catch (err) {
      setError((err as Error).message ?? "Não foi possível salvar a marcação.");
    }
  }

  async function handleCreateHintFromVideo(bbox: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    timestampMs: number;
    frameWidth: number;
    frameHeight: number;
  }) {
    if (!videoId) return;
    const athleteId = window.prompt("ID do atleta marcado neste jogador:");
    if (!athleteId) return;

    try {
      await createApiClient().createSelectionHint(videoId, {
        athlete_id: athleteId,
        timestamp_ms: bbox.timestampMs,
        bbox_x1: bbox.x1,
        bbox_y1: bbox.y1,
        bbox_x2: bbox.x2,
        bbox_y2: bbox.y2,
        frame_width: bbox.frameWidth,
        frame_height: bbox.frameHeight,
      });
      await loadHints();
    } catch (err) {
      setError((err as Error).message ?? "Não foi possível salvar a marcação.");
    }
  }

  async function handleDeleteHint(athleteId: string) {
    if (!videoId) return;
    await createApiClient().deleteSelectionHint(videoId, athleteId);
    await loadHints();
  }

  if (!videoId) {
    return <p className="text-sm text-gray-500">Vídeo não informado.</p>;
  }

  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Selecionar jogador</h2>
      <p className="text-sm text-gray-500">
        Marque visualmente os jogadores que você quer priorizar na análise (opcional). Sem
        marcação, a análise considera o time todo normalmente — a identidade não depende do
        número de camisa, apenas da posição marcada aqui.
      </p>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="flex gap-2 border-b border-gray-200 text-sm">
        <button
          type="button"
          onClick={() => setMode("frame")}
          className={`px-3 py-2 ${mode === "frame" ? "border-b-2 border-brand-700 font-medium text-brand-700" : "text-gray-500"}`}
        >
          Frame estático
        </button>
        <button
          type="button"
          onClick={() => setMode("video")}
          className={`px-3 py-2 ${mode === "video" ? "border-b-2 border-brand-700 font-medium text-brand-700" : "text-gray-500"}`}
        >
          Durante a reprodução
        </button>
      </div>

      {mode === "frame" ? (
        !frame ? (
          <Button variant="secondary" onClick={handleExtractFrame} disabled={extracting}>
            {extracting ? "Extraindo frame do vídeo..." : "Selecionar jogador no vídeo"}
          </Button>
        ) : (
          <div className="space-y-4">
            <ReferenceFrameSelector referenceFrame={frame} hints={hints} onCreateHint={handleCreateHint} />
            <p className="text-xs text-gray-400">
              Clique e arraste sobre o jogador para marcá-lo. As marcações atuais aparecem em azul.
            </p>
          </div>
        )
      ) : loadingPlayback ? (
        <p className="text-sm text-gray-500">Carregando vídeo...</p>
      ) : playbackUrl ? (
        <div className="space-y-4">
          <VideoFrameSelector playbackUrl={playbackUrl} hints={hints} onCreateHint={handleCreateHintFromVideo} />
          <p className="text-xs text-gray-400">
            Pause o vídeo no instante desejado, depois clique e arraste sobre o jogador para
            marcá-lo. As marcações atuais aparecem em azul.
          </p>
        </div>
      ) : (
        <Button variant="secondary" onClick={loadPlaybackUrl}>
          Tentar novamente
        </Button>
      )}

      {hints.length > 0 ? (
        <div className="space-y-2">
          <p className="text-sm font-medium">Jogadores marcados</p>
          <ul className="space-y-1">
            {hints.map((hint) => (
              <li
                key={hint.id}
                className="flex items-center justify-between rounded-lg bg-white px-3 py-2 text-sm shadow-sm"
              >
                <span>Atleta {hint.athlete_id}</span>
                <Button variant="secondary" onClick={() => handleDeleteHint(hint.athlete_id)}>
                  Remover
                </Button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
