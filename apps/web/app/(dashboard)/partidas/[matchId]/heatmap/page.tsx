"use client";

/** Renderiza o heatmap (matriz de densidade) calculado a partir da
 * homografia do campo. A matriz vem de `player_match_stats.heatmap`
 * (consultado via Supabase client direto — RLS já garante o isolamento
 * por clube/atleta). */
export default function HeatmapPage() {
  return (
    <div className="space-y-4">
      <h2 className="font-semibold">Heatmap por jogador</h2>
      <p className="text-sm text-gray-500">
        Selecione um jogador na revisão de tracks para visualizar o heatmap de posicionamento em
        campo, calculado a partir da homografia (coordenadas de pixel convertidas em metros).
      </p>
    </div>
  );
}
