/**
 * Login route — posts credentials via the session slice's `login` action
 * (which itself hits `/accounts/login/`, form-encoded, mirroring the
 * legacy `LoginPage`). Real endpoint, no fixtures.
 */

import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router";
import { useStore } from "@/store";

export function LoginRoute(): React.JSX.Element {
  const login = useStore((s) => s.session.login);
  const error = useStore((s) => s.session.error);
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent): Promise<void> {
    e.preventDefault();
    setSubmitting(true);
    const ok = await login(username, password);
    setSubmitting(false);
    if (ok) {
      navigate("/lobby");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-void">
      <div className="w-full max-w-[380px] rounded-lg border border-rebar bg-concrete p-10 text-center">
        <div className="mb-1 text-2xl font-bold tracking-[6px] text-spire">BABYLON</div>
        <p className="mb-8 text-[10px] uppercase tracking-[3px] text-ash">The Fall of America</p>

        <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
            className="rounded-md border border-wet-steel bg-void px-3 py-2.5 text-sm text-bone outline-none focus:border-spire"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            className="rounded-md border border-wet-steel bg-void px-3 py-2.5 text-sm text-bone outline-none focus:border-spire"
          />
          {error && (
            <p role="alert" className="m-0 text-[12px] text-laser">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="mt-2 rounded-md bg-spire px-3 py-2.5 text-[12px] font-bold uppercase tracking-[3px] text-void hover:brightness-110 disabled:opacity-50"
          >
            {submitting ? "Authenticating…" : "Enter"}
          </button>
        </form>
      </div>
    </div>
  );
}
