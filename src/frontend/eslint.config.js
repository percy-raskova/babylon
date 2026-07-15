import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import sonarjs from "eslint-plugin-sonarjs";
import prettier from "eslint-config-prettier";

export default tseslint.config(
  // Base JS recommendations
  js.configs.recommended,

  // TypeScript strict + stylistic
  ...tseslint.configs.strict,
  ...tseslint.configs.stylistic,

  // SonarJS cognitive complexity
  sonarjs.configs.recommended,

  // React hooks rules
  {
    plugins: { "react-hooks": reactHooks },
    rules: reactHooks.configs.recommended.rules,
  },

  // Project-specific overrides
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      // Cyclomatic complexity: max 15 per function (matches Python ruff C90)
      complexity: ["error", { max: 15 }],

      // Cognitive complexity via sonarjs (max 15)
      "sonarjs/cognitive-complexity": ["error", 15],

      // No unused vars (TypeScript handles this, but enforce via lint too)
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],

      // Enforce explicit return types on exported functions
      "@typescript-eslint/explicit-module-boundary-types": "off",

      // Allow empty interfaces (for component props that may grow)
      "@typescript-eslint/no-empty-interface": "off",

      // Relax sonarjs rules that conflict with React patterns
      "sonarjs/no-duplicate-string": "off",
    },
  },

  // Test file overrides
  {
    files: ["src/**/*.test.{ts,tsx}", "src/test/**/*.{ts,tsx}"],
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "sonarjs/cognitive-complexity": ["error", 25],
      "@typescript-eslint/no-empty-function": "off",
      "sonarjs/no-hardcoded-passwords": "off",
      // `array[0]!`/`.find(...)!` on known-populated test fixtures is the
      // standard idiom across this suite's ported tests (spec-110 B2) —
      // web/frontend's own eslint config downgrades this rule to "warn"
      // globally for the same reason. Off (not "warn") here since test
      // files are the only place it appears; production code stays strict.
      "@typescript-eslint/no-non-null-assertion": "off",
      // Ported test assertions like `expect(x).toBe(0.42)` read back a
      // literal that was just assigned two lines above — not a genuine
      // float-drift risk, but sonarjs's static rule can't tell the
      // difference from real computed-float comparisons. Off for tests
      // only; production code (formulas, ramps) stays strict.
      "sonarjs/no-floating-point-equality": "off",
    },
  },

  // Provenance boundary (seam Sensor 3): the game-render tree must never
  // import test fixtures/relabels or the dev-only Observatory dashboard —
  // either would put a non-runtime value on screen. Routing (`App.tsx`, which
  // is not under any of these dirs) legitimately imports the Observatory
  // route, the `observatory/`/`mocks/` trees own those modules, and test
  // files legitimately consume fixtures — all excluded (App.tsx by scope,
  // tests by the `ignores` below).
  {
    files: [
      "src/components/**/*.{ts,tsx}",
      "src/lib/**/*.{ts,tsx}",
      "src/hooks/**/*.{ts,tsx}",
      "src/store/**/*.{ts,tsx}",
      "src/routes/**/*.{ts,tsx}",
    ],
    ignores: ["src/**/*.test.{ts,tsx}", "src/**/__tests__/**"],
    rules: {
      "@typescript-eslint/no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@/observatory", "@/observatory/*"],
              message:
                "Game-render code must not import the Observatory dev dashboard (seam Sensor 3: on-screen values must be runtime state, not dev tooling). Route it from App.tsx instead.",
            },
            {
              group: ["@/test/fixtures", "@/test/fixtures/*"],
              message:
                "Game-render code must not import test fixtures (seam Sensor 3: on-screen values must be real runtime data, never a fixture/relabel).",
            },
          ],
        },
      ],
    },
  },

  // Ignore build output and config files
  {
    ignores: ["dist/", "node_modules/", "*.config.js", "*.config.ts", "e2e/"],
  },

  // Prettier must be last to override formatting rules
  prettier,
);
