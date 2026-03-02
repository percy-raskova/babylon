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
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>BABYLON</h1>
        <p style={styles.subtitle}>The Fall of America</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={styles.input}
            autoComplete="username"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={styles.input}
            autoComplete="current-password"
            required
          />
          {error && <p style={styles.error}>{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            style={styles.button}
          >
            {submitting ? "Logging in..." : "Log In"}
          </button>
        </form>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "100vh",
    background: "linear-gradient(135deg, #0a0a0f 0%, #1a0a1a 100%)",
  },
  card: {
    background: "#141420",
    border: "1px solid #2a2a3a",
    borderRadius: "12px",
    padding: "48px 40px",
    width: "100%",
    maxWidth: "400px",
    textAlign: "center" as const,
  },
  title: {
    fontSize: "32px",
    fontWeight: 700,
    color: "#c8a860",
    letterSpacing: "6px",
    marginBottom: "4px",
  },
  subtitle: {
    fontSize: "14px",
    color: "#666",
    letterSpacing: "2px",
    marginBottom: "32px",
    textTransform: "uppercase" as const,
  },
  form: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "16px",
  },
  input: {
    background: "#0e0e18",
    border: "1px solid #2a2a3a",
    borderRadius: "8px",
    padding: "12px 16px",
    color: "#e0e0e0",
    fontSize: "14px",
    outline: "none",
  },
  error: {
    color: "#e04040",
    fontSize: "13px",
    margin: 0,
  },
  button: {
    background: "#c8a860",
    color: "#0a0a0f",
    border: "none",
    borderRadius: "8px",
    padding: "12px",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
    letterSpacing: "1px",
    textTransform: "uppercase" as const,
    marginTop: "8px",
  },
};
