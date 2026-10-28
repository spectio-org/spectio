import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

test('@playwright/test is pinned to PLAYWRIGHT_VERSION of dev/versions.env', () => {
  const env = readFileSync(join(__dirname, '..', '..', 'dev', 'versions.env'), 'utf8');
  const pinned = /^PLAYWRIGHT_VERSION=(\S+)$/m.exec(env)?.[1];
  const pkg = JSON.parse(readFileSync(join(__dirname, 'package.json'), 'utf8'));
  expect(pkg.devDependencies['@playwright/test']).toBe(pinned);
});
