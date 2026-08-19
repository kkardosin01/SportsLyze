-- ============================================================================
-- SportsLyze — Schema inicial (Fase 1)
-- ============================================================================

create extension if not exists "pgcrypto";

-- ============================================================================
-- Perfis (estende auth.users)
-- ============================================================================
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null,
  avatar_url text,
  user_type text not null check (user_type in ('club_member', 'athlete')),
  created_at timestamptz not null default now()
);

-- ============================================================================
-- Clubes e hierarquia
-- ============================================================================
create table clubs (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  official_email_domain text not null,
  verified_at timestamptz,
  created_at timestamptz not null default now()
);

create table club_members (
  id uuid primary key default gen_random_uuid(),
  club_id uuid not null references clubs(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('coordenador', 'preparador', 'analista')),
  created_at timestamptz not null default now(),
  unique (club_id, user_id)
);

create table teams (
  id uuid primary key default gen_random_uuid(),
  club_id uuid not null references clubs(id) on delete cascade,
  name text not null,
  season text,
  created_at timestamptz not null default now()
);

create table athletes (
  id uuid primary key default gen_random_uuid(),
  club_id uuid references clubs(id) on delete cascade,
  team_id uuid references teams(id) on delete set null,
  user_id uuid references auth.users(id) on delete set null,
  full_name text not null,
  birth_date date,
  position text,
  jersey_number int,
  created_at timestamptz not null default now()
);

-- ============================================================================
-- Partidas e vídeos
-- ============================================================================
create table matches (
  id uuid primary key default gen_random_uuid(),
  club_id uuid references clubs(id) on delete cascade,
  team_id uuid references teams(id) on delete set null,
  athlete_id uuid references athletes(id) on delete cascade,
  created_by uuid references auth.users(id),
  opponent_name text,
  match_date date,
  competition text,
  location text,
  created_at timestamptz not null default now(),
  constraint match_has_owner check (club_id is not null or athlete_id is not null)
);

create table videos (
  id uuid primary key default gen_random_uuid(),
  owner_type text not null check (owner_type in ('club', 'athlete')),
  owner_id uuid not null,
  match_id uuid references matches(id) on delete cascade,
  video_type text not null check (video_type in ('propria_equipe', 'adversario')),
  storage_path text,
  original_filename text not null,
  duration_seconds int,
  size_bytes bigint,
  codec text,
  uploaded_by uuid not null references auth.users(id),
  retention_days int not null default 15,
  original_deleted_at timestamptz,
  created_at timestamptz not null default now()
);

-- ============================================================================
-- Processamento
-- ============================================================================
create table analysis_jobs (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id) on delete cascade,
  status text not null default 'queued' check (status in ('queued', 'processing', 'done', 'failed')),
  current_stage text,
  progress_pct int not null default 0 check (progress_pct between 0 and 100),
  error_message text,
  estimated_duration_seconds int,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now()
);

create table field_homography (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id) on delete cascade,
  segment_start_ms int not null,
  segment_end_ms int not null,
  homography_matrix jsonb not null,
  field_corners jsonb,
  created_at timestamptz not null default now()
);

-- ============================================================================
-- Jogadores rastreados (tracks anônimos + vínculo manual)
-- ============================================================================
create table detected_players (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id) on delete cascade,
  track_id int not null,
  label text not null,
  ocr_jersey_number int,
  ocr_confidence numeric,
  thumbnail_path text,
  athlete_id uuid references athletes(id) on delete set null,
  linked_by_user_id uuid references auth.users(id),
  linked_at timestamptz,
  created_at timestamptz not null default now(),
  unique (video_id, track_id)
);

-- ============================================================================
-- Eventos e clipes (Fase 2, tabelas já criadas na Fase 1)
-- ============================================================================
create table events (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id) on delete cascade,
  match_id uuid references matches(id) on delete cascade,
  event_type text not null check (event_type in
    ('passe', 'drible', 'desarme', 'falta', 'finalizacao', 'triangulacao', 'jogada_ensaiada')),
  start_time_ms int not null,
  end_time_ms int not null,
  primary_player_id uuid references detected_players(id) on delete set null,
  secondary_player_id uuid references detected_players(id) on delete set null,
  confidence numeric,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create table clips (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references events(id) on delete cascade,
  storage_path text not null,
  thumbnail_path text,
  duration_seconds int,
  created_at timestamptz not null default now()
);

-- ============================================================================
-- Estatísticas por jogador/partida
-- ============================================================================
create table player_match_stats (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id) on delete cascade,
  match_id uuid references matches(id) on delete cascade,
  detected_player_id uuid not null references detected_players(id) on delete cascade,
  athlete_id uuid references athletes(id) on delete set null,
  touches int not null default 0,
  passes_completed int not null default 0,
  passes_attempted int not null default 0,
  dribbles_successful int not null default 0,
  dribbles_attempted int not null default 0,
  fouls_committed int not null default 0,
  fouls_suffered int not null default 0,
  shots int not null default 0,
  distance_km numeric,
  avg_speed_kmh numeric,
  max_speed_kmh numeric,
  heatmap jsonb,
  created_at timestamptz not null default now()
);

-- ============================================================================
-- Relatórios
-- ============================================================================
create table reports (
  id uuid primary key default gen_random_uuid(),
  scope text not null check (scope in ('match', 'player')),
  match_id uuid references matches(id) on delete cascade,
  athlete_id uuid references athletes(id) on delete cascade,
  format text not null default 'pdf' check (format in ('pdf', 'audio', 'slides')),
  storage_path text not null,
  version int not null default 1,
  generated_at timestamptz not null default now(),
  created_by uuid references auth.users(id)
);

-- ============================================================================
-- Notificações
-- ============================================================================
create table notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  type text not null,
  title text not null,
  message text,
  related_entity_type text,
  related_entity_id uuid,
  read_at timestamptz,
  created_at timestamptz not null default now()
);

-- ============================================================================
-- Planos e assinaturas (modelado na Fase 1, sem cobrança ativa)
-- ============================================================================
create table plans (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  price_cents int not null default 0,
  currency text not null default 'BRL',
  features jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table subscriptions (
  id uuid primary key default gen_random_uuid(),
  subscriber_type text not null check (subscriber_type in ('club', 'athlete')),
  subscriber_id uuid not null,
  plan_id uuid not null references plans(id),
  status text not null default 'trialing' check (status in ('trialing', 'active', 'canceled', 'past_due')),
  current_period_end timestamptz,
  created_at timestamptz not null default now()
);

-- ============================================================================
-- Índices
-- ============================================================================
create index idx_club_members_user on club_members(user_id);
create index idx_teams_club on teams(club_id);
create index idx_athletes_club on athletes(club_id);
create index idx_athletes_user on athletes(user_id);
create index idx_matches_club on matches(club_id);
create index idx_matches_athlete on matches(athlete_id);
create index idx_videos_match on videos(match_id);
create index idx_videos_owner on videos(owner_type, owner_id);
create index idx_analysis_jobs_video on analysis_jobs(video_id);
create index idx_detected_players_video on detected_players(video_id);
create index idx_events_video on events(video_id);
create index idx_events_match on events(match_id);
create index idx_clips_event on clips(event_id);
create index idx_player_match_stats_video on player_match_stats(video_id);
create index idx_player_match_stats_athlete on player_match_stats(athlete_id);
create index idx_notifications_user on notifications(user_id, read_at);

-- ============================================================================
-- Funções auxiliares para RLS
-- ============================================================================
create or replace function is_club_member(target_club_id uuid)
returns boolean
language sql
security definer
stable
as $$
  select exists (
    select 1 from club_members
    where club_id = target_club_id and user_id = auth.uid()
  );
$$;

create or replace function owns_athlete(target_athlete_id uuid)
returns boolean
language sql
security definer
stable
as $$
  select exists (
    select 1 from athletes
    where id = target_athlete_id and user_id = auth.uid()
  );
$$;

create or replace function can_access_video(target_video_id uuid)
returns boolean
language sql
security definer
stable
as $$
  select exists (
    select 1 from videos v
    where v.id = target_video_id
      and (
        (v.owner_type = 'club' and is_club_member(v.owner_id))
        or (v.owner_type = 'athlete' and v.owner_id = auth.uid())
      )
  );
$$;

-- ============================================================================
-- Row Level Security
-- ============================================================================
alter table profiles enable row level security;
alter table clubs enable row level security;
alter table club_members enable row level security;
alter table teams enable row level security;
alter table athletes enable row level security;
alter table matches enable row level security;
alter table videos enable row level security;
alter table analysis_jobs enable row level security;
alter table field_homography enable row level security;
alter table detected_players enable row level security;
alter table events enable row level security;
alter table clips enable row level security;
alter table player_match_stats enable row level security;
alter table reports enable row level security;
alter table notifications enable row level security;
alter table subscriptions enable row level security;

-- profiles: cada usuário vê e edita o próprio perfil
create policy "profiles_self" on profiles
  for all using (id = auth.uid()) with check (id = auth.uid());

-- clubs: membros do clube podem ler; escrita restrita a coordenador (via service role/API)
create policy "clubs_select_member" on clubs
  for select using (is_club_member(id));

-- club_members: visível para membros do mesmo clube
create policy "club_members_select" on club_members
  for select using (is_club_member(club_id));

-- teams
create policy "teams_select" on teams
  for select using (is_club_member(club_id));

-- athletes: membros do clube OU o próprio atleta
create policy "athletes_select" on athletes
  for select using (
    (club_id is not null and is_club_member(club_id))
    or user_id = auth.uid()
  );

-- matches: dono (clube ou atleta)
create policy "matches_select" on matches
  for select using (
    (club_id is not null and is_club_member(club_id))
    or (athlete_id is not null and owns_athlete(athlete_id))
  );

-- videos: dono (clube ou atleta)
create policy "videos_select" on videos
  for select using (
    (owner_type = 'club' and is_club_member(owner_id))
    or (owner_type = 'athlete' and owner_id = auth.uid())
  );

-- tabelas dependentes de vídeo: reaproveitam can_access_video
create policy "analysis_jobs_select" on analysis_jobs
  for select using (can_access_video(video_id));

create policy "field_homography_select" on field_homography
  for select using (can_access_video(video_id));

create policy "detected_players_select" on detected_players
  for select using (can_access_video(video_id));

create policy "events_select" on events
  for select using (can_access_video(video_id));

create policy "clips_select" on clips
  for select using (
    exists (
      select 1 from events e
      where e.id = clips.event_id and can_access_video(e.video_id)
    )
  );

create policy "player_match_stats_select" on player_match_stats
  for select using (can_access_video(video_id));

-- reports: dono do match ou do athlete
create policy "reports_select" on reports
  for select using (
    (match_id is not null and exists (
      select 1 from matches m where m.id = reports.match_id
        and ((m.club_id is not null and is_club_member(m.club_id))
             or (m.athlete_id is not null and owns_athlete(m.athlete_id)))
    ))
    or (athlete_id is not null and owns_athlete(athlete_id))
  );

-- notifications: só o próprio usuário
create policy "notifications_select" on notifications
  for select using (user_id = auth.uid());

create policy "notifications_update_own" on notifications
  for update using (user_id = auth.uid());

-- subscriptions: membros do clube ou o próprio atleta
create policy "subscriptions_select" on subscriptions
  for select using (
    (subscriber_type = 'club' and is_club_member(subscriber_id))
    or (subscriber_type = 'athlete' and owns_athlete(subscriber_id))
  );

-- Nota: políticas de INSERT/UPDATE/DELETE para escrita de dados (upload de vídeo,
-- criação de clube/elenco/atleta, associação manual de jogador etc.) são aplicadas
-- via API (FastAPI usando service role), que valida regras de negócio antes de
-- gravar. Policies de escrita adicionais podem ser adicionadas por tabela conforme
-- os endpoints forem implementados.
