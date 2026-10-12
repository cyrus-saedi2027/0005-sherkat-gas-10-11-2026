import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    css: {
      // global.css is processed so tokens.test.ts can read it with ?raw
      // (unprocessed CSS imports resolve to an empty string in Vitest).
      include: [/styles\/global\.css/],
      modules: { classNameStrategy: "non-scoped" },
    },
  },
});
