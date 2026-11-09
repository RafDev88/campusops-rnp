import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5174",
    headless: true,
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROME_PATH || undefined,
    },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: process.env.QA_PYTHON
        ? `"${process.env.QA_PYTHON}" ../scripts/qa_server.py`
        : "python ../scripts/qa_server.py",
      cwd: "../backend",
      url: "http://127.0.0.1:8001/api/health",
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: "npm run dev -- --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      env: { CAMPUSOPS_API_TARGET: "http://127.0.0.1:8001" },
    },
  ],
});
