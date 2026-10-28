import { test, expect } from '@playwright/test';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { resolveTarget, STATIC_URL } from './base-url';

function scenarioFile(state: object): string {
  const path = join(mkdtempSync(join(tmpdir(), 'spx-e2e-')), 'scenario.json');
  writeFileSync(path, JSON.stringify(state));
  return path;
}

test('no variable: the static stand-in page', () => {
  expect(resolveTarget({})).toEqual({ url: STATIC_URL, serveStatic: true });
});

test('SPECTIO_E2E_BASE_URL wins over SPECTIO_SCENARIO', () => {
  const env = { SPECTIO_E2E_BASE_URL: 'https://spectio.pages.dev/', SPECTIO_SCENARIO: '/nonexistent.json' };
  expect(resolveTarget(env)).toEqual({ url: 'https://spectio.pages.dev/', serveStatic: false });
});

test('SPECTIO_E2E_BASE_URL must be http or https', () => {
  expect(() => resolveTarget({ SPECTIO_E2E_BASE_URL: 'file:///etc/passwd' })).toThrow(/http or https/);
  expect(() => resolveTarget({ SPECTIO_E2E_BASE_URL: 'not a url' })).toThrow();
});

test('SPECTIO_SCENARIO: urls.spectio of the scenario JSON', () => {
  const path = scenarioFile({ id: 3, urls: { spectio: 'http://127.0.0.1:20300' } });
  expect(resolveTarget({ SPECTIO_SCENARIO: path })).toEqual({ url: 'http://127.0.0.1:20300', serveStatic: false });
});

test('SPECTIO_SCENARIO without urls.spectio says why', () => {
  const path = scenarioFile({ id: 3, urls: {} });  // what dev/scenario.py writes until Spectio runs in a scenario
  expect(() => resolveTarget({ SPECTIO_SCENARIO: path })).toThrow(/no urls\.spectio/);
});
