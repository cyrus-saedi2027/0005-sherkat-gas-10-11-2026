import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";

export default tseslint.config(
  { ignores: ["**/dist/**", "**/node_modules/**", "backend/**", "**/*.d.ts", "**/coverage/**", "e2e/.artifacts/**", "packages/core/src/api/schema.ts"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    },
  },
  {
    // packages that must stay platform-neutral (React Native–portable)
    files: ["packages/core/src/**", "packages/motion/src/**", "packages/data/src/**"],
    ignores: ["**/*.test.ts", "**/platform.web.ts"],
    rules: {
      "no-restricted-imports": ["error", { paths: ["react-dom"], patterns: ["react-dom/*"] }],
      "no-restricted-globals": ["error", "window", "document", "localStorage", "sessionStorage", "navigator"],
    },
  },
);
