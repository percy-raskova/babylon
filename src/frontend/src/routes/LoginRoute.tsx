/**
 * Login route — posts credentials via the session slice's `login` action
 * (which itself hits `/accounts/login/`, form-encoded, mirroring the
 * legacy `LoginPage`). Real endpoint, no fixtures.
 *
 * SKIN: Design Bible §9b "THE INSTALLER" — this is a menu, the map is
 * absent, so it gets the FULL Guix-installer dialog treatment: flat dead
 * field, one centered plate, hard zero-blur offset shadow, a crimson
 * title tab breaking the top border, and a keyboard-hint footer.
 *
 * Colors reference the `--ksbc-*` role tokens from `index.css` (Lane
 * SKIN-CHROME) — single source of truth for the palette; this file
 * holds no literal hex.
 */

import { useState } from "react";
import { useNavigate } from "react-router";
import { useStore } from "@/store";

const FIELD = "var(--ksbc-field)";
const CRIMSON = "var(--ksbc-accent-crimson)";
const GOLD = "var(--ksbc-accent-gold)";
const INK = "var(--ksbc-ink)";
const MUTED = "var(--ksbc-muted-1)";
const MUTED_LIGHT = "var(--ksbc-muted-2)";
const SHADOW = "var(--ksbc-key-shadow)";

export function LoginRoute(): React.JSX.Element {
  const login = useStore((s) => s.session.login);
  const error = useStore((s) => s.session.error);
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setSubmitting(true);
    const ok = await login(username, password);
    setSubmitting(false);
    if (ok) {
      navigate("/lobby");
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center p-6 font-mono"
      style={{ background: FIELD }}
    >
      <div
        className="relative w-full max-w-[400px] border-2 p-8"
        style={{
          background: FIELD,
          borderColor: CRIMSON,
          boxShadow: `8px 8px 0 0 ${SHADOW}`,
        }}
      >
        {/* Title tab — breaks the top border line (fieldset/legend idiom) */}
        <span
          className="absolute -top-[11px] left-6 px-2 text-[11px] font-bold uppercase tracking-[0.3em]"
          style={{ background: FIELD, color: CRIMSON }}
        >
          ┤ Login ├
        </span>

        <div className="mb-1 text-center text-2xl font-bold tracking-[6px]" style={{ color: INK }}>
          BABYLON
        </div>
        <p
          className="mb-8 text-center text-[10px] uppercase tracking-[3px]"
          style={{ color: MUTED_LIGHT }}
        >
          The Fall of America
        </p>

        <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-3">
          {/* Inner well — double-line border in crimson around the field group */}
          <div className="flex flex-col gap-3 p-3" style={{ border: `3px double ${CRIMSON}` }}>
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              className="px-3 py-2.5 text-sm outline-none"
              style={{ background: FIELD, color: INK, border: `1px solid ${MUTED}` }}
              onFocus={(e) => (e.currentTarget.style.borderColor = CRIMSON)}
              onBlur={(e) => (e.currentTarget.style.borderColor = MUTED)}
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              className="px-3 py-2.5 text-sm outline-none"
              style={{ background: FIELD, color: INK, border: `1px solid ${MUTED}` }}
              onFocus={(e) => (e.currentTarget.style.borderColor = CRIMSON)}
              onBlur={(e) => (e.currentTarget.style.borderColor = MUTED)}
            />
          </div>
          {error && (
            <p role="alert" className="m-0 text-[12px]" style={{ color: CRIMSON }}>
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="mt-2 border-2 px-3 py-2.5 text-[12px] font-bold uppercase tracking-[3px] transition-transform active:translate-x-[2px] active:translate-y-[2px] disabled:opacity-50"
            style={{
              background: CRIMSON,
              color: INK,
              borderColor: SHADOW,
              boxShadow: `3px 3px 0 0 ${SHADOW}`,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = GOLD;
              e.currentTarget.style.color = SHADOW;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = CRIMSON;
              e.currentTarget.style.color = INK;
            }}
          >
            {submitting ? "Authenticating…" : "Enter"}
          </button>
        </form>

        <p
          className="mt-6 text-center text-[9px] uppercase tracking-[0.2em]"
          style={{ color: MUTED_LIGHT }}
        >
          Tab — switch fields · Enter — submit
        </p>
      </div>
    </div>
  );
}
