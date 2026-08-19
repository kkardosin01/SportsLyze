import { SportsLyzeClient } from "@sportslyze/api-client";
import { supabase } from "./supabase";

export const apiClient = new SportsLyzeClient({
  baseUrl: process.env.EXPO_PUBLIC_API_URL!,
  getAccessToken: async () => {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  },
});
