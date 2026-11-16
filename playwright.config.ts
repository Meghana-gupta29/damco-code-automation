import { defineConfig, devices } from "@playwright/test"

const resultsFile = process.env.QA_UI_RESULTS || "runs/_last/results_ui_raw.json"

export default defineConfig({
  testDir: "./generated/ui",
  testMatch: /.*\.spec\.ts/,
  timeout: 30_000,
  expect: { timeout: 7_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["json", { outputFile: resultsFile }]],
  use: {
    baseURL: process.env.QA_UI_URL || "http://localhost:8000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  outputDir: "runs/_last/ui-artifacts",
})
