/**
 * Login page — Bunker Constructivism v2.
 *
 * Posts credentials to Django's session auth endpoint.
 * Full-viewport centered card with CRT overlay.
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

    const res = await postForm<{ username: string }>("/accounts/login/", { username, password });

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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-void">
      {/* Radial vignette */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background: "radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,.7) 100%)",
        }}
      />

      {/* CRT scanline overlay */}
      <div className="crt-overlay pointer-events-none absolute inset-0" />

      <div className="relative z-10 w-full max-w-[400px] rounded-xl border border-soot bg-dark-metal p-12 text-center shadow-[0_0_60px_rgba(0,0,0,.8),0_0_4px_rgba(200,168,96,.15)]">
        {/* Brand block */}
        <div className="mb-1 text-[36px] font-bold tracking-[8px] text-gold bloom-gold">
          BABYLON
        </div>
        <p className="mb-2 text-[11px] uppercase tracking-[3px] text-ash">The Fall of America</p>
        <div className="mx-auto mb-8 h-px w-24 bg-gradient-to-r from-transparent via-gold/40 to-transparent" />

        {/* Subtitle */}
        <p className="mb-6 text-[10px] leading-relaxed text-chassis">
          Geopolitical simulation engine modeling the collapse of American hegemony through MLM-TW
          theory. <span className="text-ash">Graph + Math = History</span>.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="rounded-lg border border-wet-concrete bg-void px-4 py-3 text-sm text-bone outline-none transition-colors placeholder:text-chassis focus:border-gold"
            autoComplete="username"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-lg border border-wet-concrete bg-void px-4 py-3 text-sm text-bone outline-none transition-colors placeholder:text-chassis focus:border-gold"
            autoComplete="current-password"
            required
          />
          {error && <p className="m-0 text-[12px] text-crimson">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="mt-2 rounded-lg bg-gold px-3 py-3 text-[12px] font-bold uppercase tracking-[3px] text-void transition-all hover:brightness-110 disabled:opacity-50"
          >
            {submitting ? "Authenticating..." : "Enter"}
          </button>
        </form>

        {/* Footer */}
        <div className="mt-8 flex items-center justify-center gap-2 text-[8px] uppercase tracking-widest text-chassis">
          <span>◐</span>
          <span>Constitution VII · Visual Vocabulary</span>
          <span>◐</span>
        </div>
      </div>
    </div>
  );
}
