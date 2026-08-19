"use client";

import { Button } from "@sportslyze/ui";
import { useState } from "react";
import { createApiClient } from "@/lib/api-client";

export default function RelatorioPage({ params }: { params: { matchId: string } }) {
  const [status, setStatus] = useState<"idle" | "solicitado">("idle");

  async function handleRequestReport() {
    await createApiClient().requestMatchReport(params.matchId);
    setStatus("solicitado");
  }

  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Relatório da partida (PDF)</h2>
      <p className="text-sm text-gray-500">
        Geração de relatório em áudio e slides está prevista para fases futuras.
      </p>
      <Button onClick={handleRequestReport} disabled={status === "solicitado"}>
        {status === "solicitado" ? "Gerando relatório..." : "Gerar relatório PDF"}
      </Button>
    </div>
  );
}
