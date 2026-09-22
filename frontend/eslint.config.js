import js from "@eslint/js";
import importPlugin from "eslint-plugin-import";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

const FEATURES = [
  "auth",
  "home",
  "users",
  "departments",
  "directories",
  "assets",
  "stock",
  "movements",
];

// Фича импортирует другую фичу только через её публичный index.ts.
const featureZones = FEATURES.flatMap((target) =>
  FEATURES.filter((from) => from !== target).map((from) => ({
    target: `./src/features/${target}`,
    from: `./src/features/${from}`,
    except: ["./index.ts"],
    message: "Другая фича импортируется только через её index.ts",
  })),
);

export default tseslint.config(
  { ignores: ["dist", "coverage", "src/api/schema.d.ts"] },
  {
    files: ["src/**/*.{ts,tsx}", "vite.config.ts"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: { globals: globals.browser },
    plugins: { "react-hooks": reactHooks, import: importPlugin },
    settings: { "import/resolver": { typescript: { project: "./tsconfig.json" } } },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      "import/no-restricted-paths": [
        "error",
        {
          zones: [
            {
              target: ["./src/api", "./src/theme", "./src/shared"],
              from: ["./src/features", "./src/layout", "./src/app"],
              message: "api, theme и shared не зависят от features, layout и app",
            },
            {
              target: "./src/layout",
              from: "./src/features",
              except: ["./auth/index.ts"],
              message: "layout использует из фич только features/auth через index.ts",
            },
            {
              target: "./src/features",
              from: ["./src/layout", "./src/app"],
              message: "Фичи не зависят от layout и app",
            },
            ...featureZones,
          ],
        },
      ],
    },
  },
);
