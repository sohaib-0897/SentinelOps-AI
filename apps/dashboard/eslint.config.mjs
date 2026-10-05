import { defineConfig, globalIgnores } from "eslint/config";
import js from "@eslint/js";
import ts from "typescript-eslint";
import hooks from "eslint-plugin-react-hooks";
import a11y from "eslint-plugin-jsx-a11y";

export default defineConfig([
  globalIgnores([".next/**", "next-env.d.ts", "coverage/**"]),
  js.configs.recommended, ...ts.configs.recommended,
  {files: ["src/**/*.{ts,tsx}"], plugins: {"react-hooks": hooks, "jsx-a11y": a11y}, rules: {...hooks.configs.recommended.rules, ...a11y.flatConfigs.recommended.rules}},
]);
