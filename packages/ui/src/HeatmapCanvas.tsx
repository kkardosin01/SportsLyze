"use client";

import { useEffect, useRef } from "react";

// Proporção do campo: 100m (comprimento) x 64m (largura) — ver
// packages/cv-pipeline/src/sportslyze_cv/homography. A matriz do heatmap
// vem no formato [linhas=largura][colunas=comprimento].
const CANVAS_WIDTH = 700;
const CANVAS_HEIGHT = Math.round((CANVAS_WIDTH * 64) / 100);

const GRADIENT_STOPS: Array<[number, number, number]> = [
  [37, 99, 235], // azul (baixa densidade)
  [16, 185, 129], // verde
  [250, 204, 21], // amarelo
  [239, 68, 68], // vermelho (alta densidade)
];

function colorForIntensity(t: number): string {
  const clamped = Math.min(1, Math.max(0, t));
  const scaled = clamped * (GRADIENT_STOPS.length - 1);
  const index = Math.min(GRADIENT_STOPS.length - 2, Math.floor(scaled));
  const localT = scaled - index;
  const [r1, g1, b1] = GRADIENT_STOPS[index]!;
  const [r2, g2, b2] = GRADIENT_STOPS[index + 1]!;
  const r = Math.round(r1 + (r2 - r1) * localT);
  const g = Math.round(g1 + (g2 - g1) * localT);
  const b = Math.round(b1 + (b2 - b1) * localT);
  return `rgb(${r}, ${g}, ${b})`;
}

/** Renderiza a matriz de densidade (heatmap) sobre um campo estilizado,
 * usando Canvas 2D puro — sem dependências externas. */
export function HeatmapCanvas({ heatmap }: { heatmap: number[][] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rows = heatmap.length;
    const cols = rows > 0 ? (heatmap[0]?.length ?? 0) : 0;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Fundo do campo
    ctx.fillStyle = "#1f7a3f";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (rows > 0 && cols > 0) {
      let max = 0;
      for (const row of heatmap) {
        for (const value of row) {
          if (value > max) max = value;
        }
      }

      const cellWidth = canvas.width / cols;
      const cellHeight = canvas.height / rows;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const value = heatmap[r]?.[c];
          if (!value || max === 0) continue;
          const intensity = value / max;
          ctx.fillStyle = colorForIntensity(intensity);
          ctx.globalAlpha = 0.2 + 0.7 * intensity;
          ctx.fillRect(
            c * cellWidth,
            r * cellHeight,
            cellWidth + 1,
            cellHeight + 1,
          );
        }
      }
      ctx.globalAlpha = 1;
    }

    // Marcações do campo
    ctx.strokeStyle = "rgba(255, 255, 255, 0.7)";
    ctx.lineWidth = 2;
    ctx.strokeRect(2, 2, canvas.width - 4, canvas.height - 4);

    ctx.beginPath();
    ctx.moveTo(canvas.width / 2, 0);
    ctx.lineTo(canvas.width / 2, canvas.height);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(canvas.width / 2, canvas.height / 2, canvas.height * 0.14, 0, Math.PI * 2);
    ctx.stroke();

    const areaWidth = canvas.width * 0.16;
    const areaHeight = canvas.height * 0.55;
    ctx.strokeRect(2, (canvas.height - areaHeight) / 2, areaWidth, areaHeight);
    ctx.strokeRect(
      canvas.width - areaWidth - 2,
      (canvas.height - areaHeight) / 2,
      areaWidth,
      areaHeight,
    );
  }, [heatmap]);

  return (
    <canvas
      ref={canvasRef}
      width={CANVAS_WIDTH}
      height={CANVAS_HEIGHT}
      className="w-full max-w-[700px] rounded-lg shadow-inner"
    />
  );
}
