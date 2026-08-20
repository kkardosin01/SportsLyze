"use client";

import type { SelectionHint } from "@sportslyze/shared-types";
import { Button } from "@sportslyze/ui";
import { useEffect, useRef, useState } from "react";

interface Props {
  playbackUrl: string;
  hints: SelectionHint[];
  onCreateHint: (bbox: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    timestampMs: number;
    frameWidth: number;
    frameHeight: number;
  }) => void;
}

function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds)) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** Reprodução do vídeo original com pausa/scrub, permitindo ao coach marcar
 * visualmente um jogador (clique e arraste) em qualquer instante do vídeo —
 * não apenas no frame de referência estático. Usa controles próprios (em vez
 * dos controles nativos do <video>) porque o overlay de canvas usado para
 * desenhar a bbox precisa cobrir toda a área do vídeo, o que bloquearia
 * cliques nos controles nativos. O vídeo é pausado automaticamente ao
 * começar o desenho para evitar marcar em movimento. As marcações existentes
 * são exibidas sobre o quadro atual apenas como referência (foram desenhadas
 * em instantes possivelmente diferentes). */
export function VideoFrameSelector({ playbackUrl, hints, onCreateHint }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawCurrent, setDrawCurrent] = useState<{ x: number; y: number } | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  function draw() {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx || !video || !video.videoWidth || !video.videoHeight) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const scaleX = canvas.width / video.videoWidth;
    const scaleY = canvas.height / video.videoHeight;

    ctx.strokeStyle = "#2563eb";
    ctx.lineWidth = 2;
    ctx.font = "12px sans-serif";
    ctx.fillStyle = "#2563eb";
    for (const hint of hints) {
      const x = hint.bbox_x1 * scaleX;
      const y = hint.bbox_y1 * scaleY;
      const w = (hint.bbox_x2 - hint.bbox_x1) * scaleX;
      const h = (hint.bbox_y2 - hint.bbox_y1) * scaleY;
      ctx.strokeRect(x, y, w, h);
      ctx.fillText(hint.athlete_id.slice(0, 8), x + 2, y - 4 < 0 ? y + 12 : y - 4);
    }

    if (drawStart && drawCurrent) {
      ctx.strokeStyle = "#ef4444";
      ctx.strokeRect(
        Math.min(drawStart.x, drawCurrent.x),
        Math.min(drawStart.y, drawCurrent.y),
        Math.abs(drawCurrent.x - drawStart.x),
        Math.abs(drawCurrent.y - drawStart.y),
      );
    }
  }

  useEffect(() => {
    draw();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hints, drawStart, drawCurrent]);

  function syncCanvasSize() {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    draw();
  }

  useEffect(() => {
    syncCanvasSize();
    window.addEventListener("resize", syncCanvasSize);
    return () => window.removeEventListener("resize", syncCanvasSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playbackUrl]);

  function positionFromEvent(e: React.MouseEvent<HTMLCanvasElement>) {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function handleMouseDown(e: React.MouseEvent<HTMLCanvasElement>) {
    videoRef.current?.pause();
    const pos = positionFromEvent(e);
    setDrawStart(pos);
    setDrawCurrent(pos);
  }

  function handleMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!drawStart) return;
    setDrawCurrent(positionFromEvent(e));
  }

  function handleMouseUp() {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!drawStart || !drawCurrent || !canvas || !video || !video.videoWidth || !video.videoHeight) {
      setDrawStart(null);
      setDrawCurrent(null);
      return;
    }

    const scaleX = video.videoWidth / canvas.width;
    const scaleY = video.videoHeight / canvas.height;
    const x1 = Math.min(drawStart.x, drawCurrent.x) * scaleX;
    const y1 = Math.min(drawStart.y, drawCurrent.y) * scaleY;
    const x2 = Math.max(drawStart.x, drawCurrent.x) * scaleX;
    const y2 = Math.max(drawStart.y, drawCurrent.y) * scaleY;

    setDrawStart(null);
    setDrawCurrent(null);

    // Ignora arrastos minúsculos (cliques acidentais).
    if (x2 - x1 < 5 || y2 - y1 < 5) return;

    onCreateHint({
      x1,
      y1,
      x2,
      y2,
      timestampMs: Math.round(video.currentTime * 1000),
      frameWidth: video.videoWidth,
      frameHeight: video.videoHeight,
    });
  }

  function togglePlay() {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      video.play();
    } else {
      video.pause();
    }
  }

  function handleSeek(e: React.ChangeEvent<HTMLInputElement>) {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = Number(e.target.value);
    setCurrentTime(video.currentTime);
  }

  return (
    <div className="space-y-2">
      <div ref={containerRef} className="relative w-full max-w-3xl">
        <video
          ref={videoRef}
          src={playbackUrl}
          className="w-full select-none rounded-lg bg-black"
          onLoadedMetadata={(e) => {
            setDuration(e.currentTarget.duration);
            syncCanvasSize();
          }}
          onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
        />
        <canvas
          ref={canvasRef}
          className="absolute left-0 top-0 h-full w-full cursor-crosshair"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        />
      </div>

      <div className="flex max-w-3xl items-center gap-3">
        <Button variant="secondary" onClick={togglePlay}>
          {isPlaying ? "Pausar" : "Reproduzir"}
        </Button>
        <input
          type="range"
          min={0}
          max={duration || 0}
          step={0.1}
          value={currentTime}
          onChange={handleSeek}
          className="flex-1"
        />
        <span className="w-24 text-right text-xs text-gray-500">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>
      </div>
    </div>
  );
}
