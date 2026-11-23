import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env.CASETRACE_BASE_URL || 'http://127.0.0.1:15173',
    channel: process.env.CASETRACE_CHROME_CHANNEL || undefined,
    trace: 'retain-on-failure',
    video: process.env.CASETRACE_RECORD_DEMO ? 'on' : 'retain-on-failure',
    viewport: { width: 1440, height: 1000 },
  },
  webServer: process.env.CASETRACE_EXTERNAL_SERVER ? undefined : [
    { command: 'python ../scripts/serve_test_api.py', url: 'http://127.0.0.1:8000/health', timeout: 90_000 },
    { command: 'npm run dev -- --port 15173', url: 'http://127.0.0.1:15173', timeout: 60_000 },
  ],
})
