-- O CLI do Supabase concede por padrão apenas TRUNCATE/REFERENCES/TRIGGER/MAINTAIN
-- para os roles anon/authenticated/service_role nas tabelas criadas pelas migrations
-- de usuário — SELECT/INSERT/UPDATE/DELETE precisam ser concedidos explicitamente
-- (as policies de RLS só entram em vigor depois que o grant de tabela permite a
-- operação; sem o grant, toda query falha com "permission denied" antes mesmo de
-- avaliar as policies). O service_role também precisa do grant porque ele só
-- ignora RLS — não ignora privilégios de tabela.
grant usage on schema public to authenticated, service_role;

grant select, insert, update, delete on all tables in schema public to service_role;
grant select, insert, update, delete on all tables in schema public to authenticated;

alter default privileges in schema public
  grant select, insert, update, delete on tables to service_role;
alter default privileges in schema public
  grant select, insert, update, delete on tables to authenticated;
