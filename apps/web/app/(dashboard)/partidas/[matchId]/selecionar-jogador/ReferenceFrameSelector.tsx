"use client";

import type { ReferenceFrame, SelectionHint } from "@sportslyze/shared-types";
import { useEffect, useRef, useState } from "react";

interface Props {
  referenceFrame: ReferenceFrame;
  hints: SelectionHint[];
  onCreateHint: (bbox: { x1: number; y1: number; x2: number; y2: number }) => void;
}

/** Mostra o frame de referência extraído do vídeo e permite ao coach
 * desenhar uma bbox (clique e arraste) marcando um jogador. As coordenadas
 * do desenho (em pixels da tela) são convertidas para o espaço de pixels
 * original do frame antes de serem enviadas — é isso que o worker usa como
 * prior espacial no tracking. */
export function ReferenceFrameSelector({ referenceFrame, hints, onCreateHint }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawCurrent, setDrawCurrent] = useState<{ x: number; y: number } | null>(null);

  function draw() {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const scaleX = canvas.width / referenceFrame.frame_width;
    const scaleY = canvas.height / referenceFrame.frame_height;

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
  }, [referenceFrame]);

  function positionFromEvent(e: React.MouseEvent<HTMLCanvasElement>) {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function handleMouseDown(e: React.MouseEvent<HTMLCanvasElement>) {
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
    if (!drawStart || !drawCurrent || !canvas) {
      setDrawStart(null);
      setDrawCurrent(null);
      return;
    }

    const scaleX = referenceFrame.frame_width / canvas.width;
    const scaleY = referenceFrame.frame_height / canvas.height;
    const x1 = Math.min(drawStart.x, drawCurrent.x) * scaleX;
    const y1 = Math.min(drawStart.y, drawCurrent.y) * scaleY;
    const x2 = Math.max(drawStart.x, drawCurrent.x) * scaleX;
    const y2 = Math.max(drawStart.y, drawCurrent.y) * scaleY;

    setDrawStart(null);
    setDrawCurrent(null);

    // Ignora arrastos minúsculos (cliques acidentais).
    if (x2 - x1 < 5 || y2 - y1 < 5) return;

    onCreateHint({ x1, y1, x2, y2 });
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-3xl">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={referenceFrame.image_url}
        alt="Frame de referência do vídeo"
        className="w-full select-none rounded-lg"
        draggable={false}
        onLoad={syncCanvasSize}
      />
      <canvas
        ref={canvasRef}
        className="absolute left-0 top-0 h-full w-full cursor-crosshair"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      />
    </div>
  );
}
