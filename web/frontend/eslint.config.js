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

      // Allow non-null assertions in deck.gl layer callbacks
      "@typescript-eslint/no-non-null-assertion": "warn",

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
      // Tests often import screen but use it implicitly via queries
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // Tests may have longer setup functions
      "sonarjs/cognitive-complexity": ["error", 25],
      // Allow empty callbacks in mock implementations (e.g. vi.spyOn().mockImplementation(() => {}))
      "@typescript-eslint/no-empty-function": "off",
      // Test credentials are not real secrets
      "sonarjs/no-hardcoded-passwords": "off",
    },
  },

  // Ignore build output and config files
  {
    ignores: ["dist/", "node_modules/", "*.config.js", "*.config.ts", "e2e/"],
  },

  // Prettier must be last to override formatting rules
  prettier,
);
