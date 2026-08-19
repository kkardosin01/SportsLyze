import { SportsLyzeClient } from "@sportslyze/api-client";
import { createSupabaseBrowserClient } from "./supabase/client";

/** Instância do client de API para uso em componentes client-side. Injeta
 * automaticamente o access token da sessão Supabase em cada request. */
export function createApiClient() {
  const supabase = createSupabaseBrowserClient();

  return new SportsLyzeClient({
    baseUrl: process.env.NEXT_PUBLIC_API_URL!,
    getAccessToken: async () => {
      const { data } = await supabase.auth.getSession();
      return data.session?.access_token ?? null;
    },
  });
}
