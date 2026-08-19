export type ClubMemberRole = "coordenador" | "preparador" | "analista";

export interface Club {
  id: string;
  name: string;
  official_email_domain: string;
  verified_at: string | null;
  created_at: string;
}

export interface ClubMember {
  id: string;
  club_id: string;
  user_id: string;
  role: ClubMemberRole;
  created_at: string;
}

export interface Team {
  id: string;
  club_id: string;
  name: string;
  season: string | null;
  created_at: string;
}

export interface Athlete {
  id: string;
  club_id: string | null;
  team_id: string | null;
  user_id: string | null;
  full_name: string;
  birth_date: string | null;
  position: string | null;
  jersey_number: number | null;
  created_at: string;
}
