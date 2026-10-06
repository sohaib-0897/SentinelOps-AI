import { defineConfig, globalIgnores } from "eslint/config";
import js from "@eslint/js";
import ts from "typescript-eslint";
import hooks from "eslint-plugin-react-hooks";
import a11y from "eslint-plugin-jsx-a11y";

export default defineConfig([
  globalIgnores([".next/**", ".local/**", "next-env.d.ts", "coverage/**"]),
  js.configs.recommended, ...ts.configs.recommended,
  {files: ["src/**/*.{ts,tsx}"], plugins: {"react-hooks": hooks, "jsx-a11y": a11y}, rules: {...hooks.configs.recommended.rules, ...a11y.flatConfigs.recommended.rules}},
  // Named scroll regions need a tab stop so keyboard users can scroll long source records.
  {files: ["src/components/incident-detail.tsx"], rules: {"jsx-a11y/no-noninteractive-tabindex": ["error", {roles: ["region"]}]}},
]);
