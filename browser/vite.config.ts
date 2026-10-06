import { defineConfig } from "vite-plus";
import { playwright } from "@vitest/browser-playwright";

export default defineConfig({
  server: { host: "127.0.0.1", hmr: process.env.RECONNECT_FROZEN_RUN === "1" ? false : undefined },
  test: {
    maxWorkers: 1,
    fileParallelism: false,
    reporters: ["verbose"],
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    browser: {
      enabled: true,
      provider: playwright(),
      headless: true,
      instances: [{ browser: "chromium", name: "chromium" }],
    },
  },
});
