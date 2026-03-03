/// <reference types="vitest/config" />
import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(
  viteConfig,
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
        exclude: [
          "src/test/**",
          "src/**/*.test.{ts,tsx}",
          "src/vite-env.d.ts",
          "src/main.tsx",
        ],
        thresholds: {
          lines: 80,
          branches: 75,
          functions: 80,
        },
      },
    },
  }),
);
