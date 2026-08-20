"use client";

import type { Athlete, Team } from "@sportslyze/shared-types";
import { Button } from "@sportslyze/ui";
import Link from "next/link";
import { useEffect, useState } from "react";
import { createApiClient } from "@/lib/api-client";

export default function ClubePage() {
  const [clubId, setClubId] = useState<string | null>(null);
  const [teams, setTeams] = useState<Team[]>([]);
  const [athletes, setAthletes] = useState<Athlete[]>([]);
  const [teamName, setTeamName] = useState("");

  useEffect(() => {
    const api = createApiClient();
    api.listMyClubs().then((memberships: any) => {
      const first = memberships?.[0]?.clubs;
      if (first) setClubId(first.id);
    });
  }, []);

  useEffect(() => {
    if (!clubId) return;
    createApiClient().listAthletes(clubId).then(setAthletes);
  }, [clubId]);

  async function handleCreateTeam(event: React.FormEvent) {
    event.preventDefault();
    if (!clubId) return;
    const api = createApiClient();
    const team = await api.createTeam(clubId, { name: teamName });
    setTeams((prev) => [...prev, team]);
    setTeamName("");
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-bold">Meu clube</h1>
        <p className="text-sm text-gray-600">Gerencie elencos, membros da comissão e atletas.</p>
      </div>

      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 font-semibold">Elencos (categorias)</h2>
        <ul className="mb-4 space-y-2">
          {teams.map((team) => (
            <li key={team.id} className="rounded-lg border border-gray-200 px-4 py-2 text-sm">
              {team.name} {team.season ? `— ${team.season}` : ""}
            </li>
          ))}
          {teams.length === 0 ? <p className="text-sm text-gray-400">Nenhum elenco cadastrado ainda.</p> : null}
        </ul>
        <form onSubmit={handleCreateTeam} className="flex gap-2">
          <input
            placeholder="Ex: Sub-15"
            value={teamName}
            onChange={(e) => setTeamName(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
          <Button type="submit" disabled={!clubId}>
            Adicionar elenco
          </Button>
        </form>
      </section>

      <section className="rounded-xl bg-white p-6 shadow-sm">
        <h2 className="mb-4 font-semibold">Atletas</h2>
        <ul className="space-y-2">
          {athletes.map((athlete) => (
            <li key={athlete.id}>
              <Link
                href={`/clube/atletas/${athlete.id}/estatisticas`}
                className="block rounded-lg border border-gray-200 px-4 py-2 text-sm hover:bg-brand-50"
              >
                {athlete.full_name}
              </Link>
            </li>
          ))}
          {athletes.length === 0 ? (
            <p className="text-sm text-gray-400">Nenhum atleta cadastrado ainda.</p>
          ) : null}
        </ul>
      </section>
    </div>
  );
}
