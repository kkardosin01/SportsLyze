"use client";

import type { Report, ReportFormat } from "@sportslyze/shared-types";
import { Button } from "@sportslyze/ui";
import { useEffect, useState } from "react";
import { createApiClient } from "@/lib/api-client";

const FORMAT_LABELS: Record<ReportFormat, string> = {
  pdf: "PDF",
  slides: "Slides",
  audio: "Áudio",
};

export default function RelatorioPage({ params }: { params: { matchId: string } }) {
  const [format, setFormat] = useState<ReportFormat>("pdf");
  const [requesting, setRequesting] = useState(false);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadReports() {
    setLoading(true);
    setError(null);
    try {
      const data = await createApiClient().listMatchReports(params.matchId);
      setReports(data);
    } catch (err) {
      setError((err as Error).message ?? "Não foi possível carregar os relatórios.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.matchId]);

  async function handleRequestReport() {
    setRequesting(true);
    setError(null);
    try {
      await createApiClient().requestMatchReport(params.matchId, format);
      await loadReports();
    } catch (err) {
      setError((err as Error).message ?? "Não foi possível solicitar o relatório.");
    } finally {
      setRequesting(false);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Relatório da partida</h2>
      <p className="text-sm text-gray-500">
        Gere o relatório da partida em PDF, slides ou áudio. A geração roda em segundo plano — quando
        concluída, o relatório aparece na lista abaixo para download.
      </p>

      <div className="flex items-center gap-2">
        <select
          value={format}
          onChange={(e) => setFormat(e.target.value as ReportFormat)}
          disabled={requesting}
          className="rounded border border-gray-300 px-2 py-1 text-sm"
        >
          {(Object.keys(FORMAT_LABELS) as ReportFormat[]).map((f) => (
            <option key={f} value={f}>
              {FORMAT_LABELS[f]}
            </option>
          ))}
        </select>
        <Button onClick={handleRequestReport} disabled={requesting}>
          {requesting ? "Solicitando..." : `Gerar relatório em ${FORMAT_LABELS[format]}`}
        </Button>
      </div>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="space-y-2">
        <h3 className="text-sm font-medium">Relatórios gerados</h3>
        {loading ? <p className="text-sm text-gray-400">Carregando...</p> : null}
        {!loading && reports.length === 0 ? (
          <p className="text-sm text-gray-500">Nenhum relatório gerado ainda.</p>
        ) : null}
        <ul className="space-y-1">
          {reports.map((report) => (
            <li key={report.id} className="flex items-center gap-2 text-sm">
              <span className="rounded bg-gray-100 px-2 py-0.5 text-xs font-medium">
                {FORMAT_LABELS[report.format]}
              </span>
              <span className="text-gray-500">{new Date(report.generated_at).toLocaleString("pt-BR")}</span>
              <a
                href={report.download_url}
                target="_blank"
                rel="noreferrer"
                className="text-blue-600 hover:underline"
              >
                Baixar
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
