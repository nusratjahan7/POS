import { defineConfig } from "vitest/config";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths()],
  test: {
    environment: "jsdom",
    // React Testing Library needs React's development build (it exports `act`);
    // without this an ambient NODE_ENV=production breaks component tests.
    env: { NODE_ENV: "development" },
    include: ["src/**/*.test.ts?(x)"],
  },
});
