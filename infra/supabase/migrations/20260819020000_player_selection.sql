-- Identificação manual de jogador durante a análise de vídeo.
--
-- Fluxo: o coach solicita a extração de um frame de referência do vídeo
-- (guardamos só o mais recente por vídeo — a seleção acontece uma vez,
-- antes/durante o processamento). Sobre esse frame, o coach desenha uma
-- bbox marcando um atleta já cadastrado (`player_selection_hints`). O
-- worker usa essa marcação como *prior espacial* ao rodar o tracking,
-- pré-vinculando o track cujo bbox no frame de referência tiver maior IoU
-- com o hint — nunca como substituto de número de camisa.

create table video_reference_frames (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null unique references videos(id) on delete cascade,
  storage_path text not null,
  timestamp_ms int not null,
  frame_width int not null,
  frame_height int not null,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

alter table video_reference_frames enable row level security;

create policy "video_reference_frames_select" on video_reference_frames
  for select using (can_access_video(video_id));

create policy "video_reference_frames_insert" on video_reference_frames
  for insert with check (can_access_video(video_id));

create policy "video_reference_frames_update" on video_reference_frames
  for update using (can_access_video(video_id));

create table player_selection_hints (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id) on delete cascade,
  athlete_id uuid not null references athletes(id) on delete cascade,
  timestamp_ms int not null,
  bbox_x1 numeric not null,
  bbox_y1 numeric not null,
  bbox_x2 numeric not null,
  bbox_y2 numeric not null,
  frame_width int not null,
  frame_height int not null,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  unique (video_id, athlete_id)
);

alter table player_selection_hints enable row level security;

create policy "player_selection_hints_select" on player_selection_hints
  for select using (can_access_video(video_id));

create policy "player_selection_hints_insert" on player_selection_hints
  for insert with check (can_access_video(video_id));

create policy "player_selection_hints_update" on player_selection_hints
  for update using (can_access_video(video_id));

create policy "player_selection_hints_delete" on player_selection_hints
  for delete using (can_access_video(video_id));
