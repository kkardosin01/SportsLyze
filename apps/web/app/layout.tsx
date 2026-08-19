import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SportsLyze",
  description: "Análise de desempenho por vídeo para futebol de base",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
