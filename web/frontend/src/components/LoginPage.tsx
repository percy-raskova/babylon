/**
 * Login page component.
 *
 * Posts credentials to Django's session auth endpoint.
 */

import { type FormEvent, useState } from "react";
import { postForm } from "@/api/client";
import type { AuthState } from "@/types/game";

interface LoginPageProps {
  onLogin: (user: AuthState) => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const res = await postForm<{ username: string }>(
      "/accounts/login/",
      { username, password },
    );

    setSubmitting(false);

    if (res.status === "ok") {
      onLogin({
        is_authenticated: true,
        username: res.data.username,
      });
    } else {
      setError(res.message ?? "Login failed");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-void to-blood-void">
      <div className="w-full max-w-[400px] rounded-xl border border-wet-concrete bg-dark-metal p-12 text-center">
        <h1 className="mb-1 text-[32px] font-bold tracking-[6px] text-gold">
          BABYLON
        </h1>
        <p className="mb-8 text-sm uppercase tracking-[2px] text-ash">
          The Fall of America
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="rounded-lg border border-wet-concrete bg-void px-4 py-3 text-sm text-bone outline-none focus:border-gold"
            autoComplete="username"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-lg border border-wet-concrete bg-void px-4 py-3 text-sm text-bone outline-none focus:border-gold"
            autoComplete="current-password"
            required
          />
          {error && <p className="m-0 text-[13px] text-crimson">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="mt-2 rounded-lg bg-gold px-3 py-3 text-sm font-semibold uppercase tracking-wider text-void hover:brightness-110 disabled:opacity-50"
          >
            {submitting ? "Logging in..." : "Log In"}
          </button>
        </form>
      </div>
    </div>
  );
}
