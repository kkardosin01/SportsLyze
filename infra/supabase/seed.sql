-- ============================================================================
-- SportsLyze — Seed de dados de exemplo (desenvolvimento local)
-- ============================================================================
-- Requer que os usuários abaixo já existam em auth.users (criados via
-- Supabase Auth no setup local, ver README). Os UUIDs são fixos para
-- facilitar testes manuais e fixtures de teste automatizado.

insert into plans (id, name, price_cents, currency, features, is_active) values
  ('00000000-0000-0000-0000-000000000001', 'Gratuito', 0, 'BRL', '{"video_limit_per_month": 4}', true),
  ('00000000-0000-0000-0000-000000000002', 'Clube Pro', 0, 'BRL', '{"video_limit_per_month": null}', false);

insert into clubs (id, name, official_email_domain, verified_at) values
  ('10000000-0000-0000-0000-000000000001', 'Clube Exemplo FC', 'clubeexemplo.com.br', now());

insert into teams (id, club_id, name, season) values
  ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'Sub-15', '2026'),
  ('20000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', 'Sub-17', '2026');

-- club_members: substitua pelos UUIDs reais de auth.users criados localmente
-- insert into club_members (club_id, user_id, role) values
--   ('10000000-0000-0000-0000-000000000001', '<uuid-do-usuario-coordenador>', 'coordenador');

insert into athletes (id, club_id, team_id, full_name, birth_date, position, jersey_number) values
  ('30000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'João Silva', '2011-03-14', 'Meio-campo', null),
  ('30000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'Pedro Souza', '2011-07-02', 'Atacante', null);

insert into matches (id, club_id, team_id, opponent_name, match_date, competition, location) values
  ('40000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001', 'Time Adversário FC', '2026-08-10', 'Campeonato Regional Sub-15', 'CT Clube Exemplo');
