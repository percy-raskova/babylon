import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// THE frontend since the spec-112 cutover — the cockpit owns the canonical
// dev port 5173 (the legacy web/frontend app was deleted at cutover).
export default defineConfig(({ mode }) => {
  // COCKPIT_BACKEND_URL overrides the Django proxy target (default :8000) —
  // for when a second checkout/worktree runs its own backend beside the
  // canonical one. Developers set it in `.env`/`.env.local` (template:
  // .env.example); an explicit shell variable always wins over the files.
  const fileEnv = loadEnv(mode, __dirname, "");
  const BACKEND =
    process.env.COCKPIT_BACKEND_URL ?? fileEnv.COCKPIT_BACKEND_URL ?? "http://localhost:8000";

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: BACKEND,
          changeOrigin: true,
        },
        "/accounts": {
          target: BACKEND,
          changeOrigin: true,
        },
        "/health": {
          target: BACKEND,
          changeOrigin: true,
        },
      },
    },
  };
});
