import Link from "next/link";

const NAV_ITEMS = [
  { href: "/clube", label: "Clube" },
  { href: "/partidas", label: "Partidas" },
  { href: "/atleta", label: "Área do atleta" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 border-r border-gray-200 bg-white p-6">
        <p className="mb-8 text-lg font-bold text-brand-700">SportsLyze</p>
        <nav className="space-y-2">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-brand-50 hover:text-brand-700"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
