"use client";

import { ProgressBar } from "@sportslyze/ui";
import { useState } from "react";
import * as tus from "tus-js-client";
import { createApiClient } from "@/lib/api-client";

interface UploadVideoFormProps {
  matchId: string;
  videoType: "propria_equipe" | "adversario";
  onCompleted: (videoId: string) => void;
}

/** Upload resumável via protocolo TUS (suportado nativamente pelo Supabase
 * Storage), necessário porque os vídeos de partida (~90-120min) costumam
 * passar de 4-8GB — upload direto via multipart simples não é confiável
 * para arquivos desse tamanho em conexões de campo/CT. */
export function UploadVideoForm({ matchId, videoType, onCompleted }: UploadVideoFormProps) {
  const [progressPct, setProgressPct] = useState(0);
  const [status, setStatus] = useState<"idle" | "uploading" | "processando_metadados" | "erro">("idle");
  const [error, setError] = useState<string | null>(null);

  async function handleFileSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setStatus("uploading");
    setError(null);

    try {
      const api = createApiClient();
      const { video_id, upload_url } = await api.initiateVideoUpload({
        match_id: matchId,
        video_type: videoType,
        original_filename: file.name,
        size_bytes: file.size,
      });

      await new Promise<void>((resolve, reject) => {
        const upload = new tus.Upload(file, {
          uploadUrl: upload_url,
          chunkSize: 50 * 1024 * 1024, // 50MB por chunk
          retryDelays: [0, 3000, 10000, 30000],
          onError: reject,
          onProgress: (bytesUploaded, bytesTotal) => {
            setProgressPct(Math.round((bytesUploaded / bytesTotal) * 100));
          },
          onSuccess: () => resolve(),
        });
        upload.start();
      });

      setStatus("processando_metadados");
      const durationSeconds = await readVideoDuration(file);
      await api.completeVideoUpload({ video_id, duration_seconds: durationSeconds, codec: "h264" });

      onCompleted(video_id);
    } catch (err) {
      setStatus("erro");
      setError(err instanceof Error ? err.message : "Falha no upload do vídeo.");
    }
  }

  return (
    <div className="space-y-3">
      <input type="file" accept="video/mp4" onChange={handleFileSelected} disabled={status === "uploading"} />
      {status === "uploading" ? <ProgressBar progressPct={progressPct} label="Enviando vídeo..." /> : null}
      {status === "processando_metadados" ? (
        <p className="text-sm text-gray-600">Finalizando envio e enfileirando análise...</p>
      ) : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}

function readVideoDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(video.src);
      resolve(Math.round(video.duration));
    };
    video.onerror = () => reject(new Error("Não foi possível ler os metadados do vídeo."));
    video.src = URL.createObjectURL(file);
  });
}
