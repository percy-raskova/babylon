/// <reference types="vitest/config" />
import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(
  // vite.config.ts exports the function form since it reads .env via
  // loadEnv (spec-113 Phase V) — resolve it for the test-runner context.
  viteConfig({ mode: "test", command: "serve" }),
  defineConfig({
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      include: ["src/**/*.test.{ts,tsx}"],
      globals: true,
      css: false,
      coverage: {
        provider: "v8",
        include: ["src/**/*.{ts,tsx}"],
        exclude: ["src/test/**", "src/**/*.test.{ts,tsx}", "src/vite-env.d.ts", "src/main.tsx"],
      },
    },
  }),
);
