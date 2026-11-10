import { defineConfig, devices } from '@playwright/test';
import { resolveTarget, STATIC_PORT, STATIC_URL } from './base-url';
import { statePath } from './global-setup';

// docs/specs/dev-environment-and-testing.md §6.1. Run: npm ci && npx playwright test (in tests/e2e).
const target = resolveTarget(process.env);

export default defineConfig({
  testDir: '.',
  forbidOnly: !!process.env.CI,
  reporter: [['list'], ['html', { open: 'never' }]],
  // A real server needs a session (P1 Task 12): global-setup.ts signs in once, every context reuses it.
  globalSetup: './global-setup.ts',
  // Traces record headers and cookies: keep them for the stand-in only (SEC-T6-01).
  use: {
    baseURL: target.url,
    trace: target.serveStatic ? 'retain-on-failure' : 'off',
    storageState: target.serveStatic ? undefined : statePath(target.url),
  },
  webServer: target.serveStatic
    ? { command: `python3 -m http.server ${STATIC_PORT} --bind 127.0.0.1 --directory static`, url: STATIC_URL }
    : undefined,
  projects: [
    { name: 'unit', testMatch: /\.unit\.ts$/ },
    { name: 'desktop', testMatch: /(\.e2e|skeleton\.spec|report\.spec|preview\.spec|environments\.spec|launch-environment\.spec|catalog\.spec|viewer\.spec)\.ts$/, use: { ...devices['Desktop Chrome'] } },
    // the viewer under the CSP on the other engines too (dev-env §15.3 req. 19 Tests); CI installs Chromium only
    { name: 'firefox', testMatch: /viewer\.spec\.ts$/, use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', testMatch: /viewer\.spec\.ts$/, use: { ...devices['Desktop Safari'] } },
    { name: 'phone', testMatch: /(\.e2e|skeleton\.spec|report\.spec|preview\.spec|environments\.spec|launch-environment\.spec|catalog\.spec)\.ts$/, use: { ...devices['Pixel 7'] } },
  ],
});
