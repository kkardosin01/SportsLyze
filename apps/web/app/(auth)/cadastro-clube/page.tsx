"use client";

import { Button } from "@sportslyze/ui";
import { useState } from "react";
import { createApiClient } from "@/lib/api-client";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

export default function CadastroClubePage() {
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [adminName, setAdminName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep] = useState<"form" | "verifique-email">("form");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const supabase = createSupabaseBrowserClient();
      const { error: signUpError } = await supabase.auth.signUp({
        email: adminEmail,
        password,
      });
      if (signUpError) throw new Error(signUpError.message);

      const api = createApiClient();
      await api.createClub({
        name,
        official_email_domain: domain,
        admin_full_name: adminName,
        admin_email: adminEmail,
      });

      setStep("verifique-email");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível concluir o cadastro.");
    } finally {
      setLoading(false);
    }
  }

  if (step === "verifique-email") {
    return (
      <div className="rounded-xl bg-white p-8 text-center shadow-sm">
        <h2 className="mb-2 text-lg font-semibold">Confirme seu e-mail</h2>
        <p className="text-sm text-gray-600">
          Enviamos um link de confirmação para {adminEmail}. Confirme para ativar o clube.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-xl bg-white p-8 shadow-sm">
      <h2 className="text-lg font-semibold">Cadastrar clube</h2>

      <Field label="Nome do clube" value={name} onChange={setName} />
      <Field
        label="Domínio de e-mail oficial (ex: clubeexemplo.com.br)"
        value={domain}
        onChange={setDomain}
      />
      <Field label="Seu nome (coordenador)" value={adminName} onChange={setAdminName} />
      <Field label="Seu e-mail (do domínio do clube)" type="email" value={adminEmail} onChange={setAdminEmail} />
      <Field label="Senha" type="password" value={password} onChange={setPassword} />

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <Button type="submit" disabled={loading} className="w-full">
        {loading ? "Cadastrando..." : "Cadastrar clube"}
      </Button>
    </form>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm text-gray-600">{label}</label>
      <input
        type={type}
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
      />
    </div>
  );
}
