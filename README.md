# SportsLyze

Plataforma de análise de desempenho por vídeo para futebol de base — o "SofaScore das categorias de base". Comissões técnicas e atletas enviam o vídeo da partida; um pipeline de visão computacional open-source processa o vídeo e entrega clipes por evento, relatório por jogador, heatmap, distância percorrida e relatório em PDF.

> **Status:** Fase 1 (Fundação) em desenvolvimento. Ver seção [Roadmap](#roadmap).

## Arquitetura

Monorepo (Turborepo + pnpm workspaces) com apps TypeScript (web/mobile) e apps Python (api/worker):

```
apps/
  web/          Next.js 14 (App Router) — plataforma web
  mobile/       Expo (React Native) — app mobile
  api/          FastAPI — API REST /api/v1
  worker/       Celery — processamento assíncrono de vídeo
packages/
  cv-pipeline/  Pipeline de visão computacional (YOLOv8, ByteTrack, homografia, OCR)
  shared-types/ Tipos TS compartilhados entre web e mobile
  api-client/   Client TS tipado sobre a API
  ui/           Componentes React compartilhados
  config/       tsconfig/tailwind base compartilhados
infra/
  supabase/     Migrations e seed do Postgres (Supabase CLI)
  docker/       Dockerfiles de api/worker
```

**Fluxo de processamento:** upload do vídeo (resumável, via TUS/Supabase Storage) → API valida e enfileira job no Redis → worker Celery roda `ffmpeg` + YOLOv8 + ByteTrack + homografia + OCR → resultados salvos no Postgres → notificação in-app/e-mail → cliente consulta resultados. **O processamento nunca roda na request HTTP.**

## Pré-requisitos

- Node.js ≥ 20 e [pnpm](https://pnpm.io) ≥ 9
- Python ≥ 3.11 e [uv](https://github.com/astral-sh/uv)
- Docker e Docker Compose
- [Supabase CLI](https://supabase.com/docs/guides/cli)
- `ffmpeg` instalado localmente (se for rodar api/worker fora do Docker)

## Setup local

### 1. Clonar e instalar dependências JS/TS

```bash
pnpm install
```

### 2. Subir o Supabase local

```bash
supabase start
```

Isso sobe Postgres, Auth, Storage e Studio localmente. Anote a `service_role key`, `anon key` e a URL exibidas no output — vão para o `.env`.

Aplique as migrations e o seed de desenvolvimento:

```bash
supabase db reset
```

(`db reset` aplica todas as migrations em `infra/supabase/migrations` e roda `infra/supabase/seed.sql`.)

Crie os buckets de Storage (`videos`, `clips`, `reports`) pelo Studio local (`http://localhost:54323`) ou via CLI, marcando-os como privados — o acesso é sempre mediado pela API/RLS.

### 3. Variáveis de ambiente

```bash
cp .env.example .env
```

Preencha com os valores do `supabase start` (URL, service role key, JWT secret — disponível em `supabase status`) e demais variáveis. Veja todas as chaves documentadas em `.env.example`.

### 4. Subir Redis, API e worker

```bash
docker compose up redis api worker worker-beat
```

A API sobe em `http://localhost:8000` (docs em `/api/v1/docs`).

Alternativa sem Docker (desenvolvimento com reload mais rápido):

```bash
# API (não precisa do cv-pipeline, só o worker processa vídeo)
cd apps/api && uv pip install -e ".[dev]"
uv run uvicorn src.main:app --reload

# Worker (outro terminal)
cd apps/worker && uv pip install -e ".[dev]" -e ../../packages/cv-pipeline
uv run celery -A src.celery_app worker --loglevel=info
```

> **macOS (Apple Silicon) fora do Docker:** o WeasyPrint (geração de PDF) depende de libs nativas (Pango/Cairo/GObject) instaláveis via `brew install pango`. Se o worker falhar com `cannot load library 'libgobject-2.0-0'`, rode com `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (Homebrew não fica no dylib search path padrão nessa arquitetura). Isso não afeta os containers Docker (Linux), que já resolvem essas libs no path padrão.

### 5. Subir o web

```bash
pnpm dev:web
```

Acesse `http://localhost:3000`.

### 6. Subir o mobile (opcional nesta fase)

```bash
pnpm dev:mobile
```

## Variáveis de ambiente

Ver `.env.example` na raiz — cobre Supabase (URL, chaves, buckets), Redis, limites de upload, retenção de vídeo, SMTP e as variáveis `NEXT_PUBLIC_*`/`EXPO_PUBLIC_*` do web/mobile.

Destaques:
- `VIDEO_RETENTION_DAYS_DEFAULT` (padrão: 15): dias até o vídeo original ser apagado do Storage após a análise concluir. **A análise (clipes, stats, relatórios) continua disponível após a exclusão** — apenas o arquivo-fonte e o player do vídeo completo deixam de existir.
- `MAX_UPLOAD_SIZE_BYTES` (padrão: 8GB).

## Testes

```bash
# TypeScript
pnpm test

# Python (a partir de apps/api ou apps/worker)
uv run pytest
```

## Roadmap

- **Fase 1 — Fundação:** auth com RLS, cadastro de clube/elenco/atletas, upload resumável, pipeline de tracking (YOLOv8 + ByteTrack), tela de revisão/associação de jogadores, heatmap e distância via homografia, notificações, relatório PDF.
- **Fase 2 — Eventos e clipes:** heurísticas de passe/drible/falta/finalização/triangulação, corte automático de clipes, estatísticas agregadas multi-partida, scouting de adversário.
- **Fase 3 — Refinamentos:** export em áudio/slides, melhoria de re-identificação de jogadores, paridade mobile, suporte a basquete e planos pagos.

## Limitações conhecidas (v1)

- Detecção de eventos é heurística sobre tracking — precisão aproximada, melhora por fases.
- OCR de número de camisa é *best effort*; a identidade confiável do jogador vem sempre da associação manual feita na tela de revisão.
- Homografia automática do campo pode falhar em câmeras muito móveis/mal enquadradas — nesse caso a calibração manual (4 cantos do campo) é necessária.
