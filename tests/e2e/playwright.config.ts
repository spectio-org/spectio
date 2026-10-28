import { defineConfig, devices } from '@playwright/test';
import { resolveTarget, STATIC_PORT, STATIC_URL } from './base-url';

// docs/specs/dev-environment-and-testing.md §6.1. Run: npm ci && npx playwright test (in tests/e2e).
const target = resolveTarget(process.env);

export default defineConfig({
  testDir: '.',
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: target.url, trace: 'retain-on-failure' },
  webServer: target.serveStatic
    ? { command: `python3 -m http.server ${STATIC_PORT} --bind 127.0.0.1 --directory static`, url: STATIC_URL }
    : undefined,
  projects: [
    { name: 'unit', testMatch: /\.unit\.ts$/ },
    { name: 'desktop', testMatch: /\.e2e\.ts$/, use: { ...devices['Desktop Chrome'] } },
    { name: 'phone', testMatch: /\.e2e\.ts$/, use: { ...devices['Pixel 7'] } },
  ],
});
