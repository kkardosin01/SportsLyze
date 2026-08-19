import Link from "next/link";

const TABS = [
  { href: "revisao-jogadores", label: "Revisão de jogadores" },
  { href: "heatmap", label: "Heatmap" },
  { href: "clipes", label: "Clipes" },
  { href: "relatorio", label: "Relatório" },
];

export default function PartidaPage({ params }: { params: { matchId: string } }) {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Partida</h1>

      {/* Player de vídeo com timeline de eventos clicável é adicionado quando
          o pipeline de eventos (Fase 2) estiver disponível. Na Fase 1, o
          acesso aos resultados é feito pelas abas abaixo. */}

      <nav className="flex gap-2 border-b border-gray-200">
        {TABS.map((tab) => (
          <Link
            key={tab.href}
            href={`/partidas/${params.matchId}/${tab.href}`}
            className="px-4 py-2 text-sm text-gray-600 hover:text-brand-700"
          >
            {tab.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
