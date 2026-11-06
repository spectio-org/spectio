import { chromium, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { resolveTarget } from './base-url';

// Sign in once as a user does (P1 Task 12): a fresh link from `spectio login --print-link --json`,
// opened in a browser, whose bootstrap page exchanges the ticket for the session cookie. The specs
// reuse that cookie as storageState (playwright.config.ts). The server is serve-local.sh's: it
// writes the path of its spectio.toml to .local/<port>.config. Nothing to do for the stand-in.

const REPO = join(__dirname, '..', '..');
const LOCAL = join(__dirname, '.local');

/** The port of `url`, or the default of its scheme when it names none (CR-P3T12-05). */
export function portOf(url: string): string {
  const { port, protocol } = new URL(url);
  return port || (protocol === 'https:' ? '443' : '80');
}

/** Where the signed-in state of the server at `url` is kept; it holds the session cookie. */
export function statePath(url: string): string {
  return join(LOCAL, `${portOf(url)}.state.json`);
}

/** `error` as a new Error with the ticket masked and no cause: a goto error names the link (CR-P3T12-03). */
export function withoutTicket(error: unknown, ticket: string): Error {
  const message = error instanceof Error ? error.message : String(error);
  return new Error(`opening the token link failed: ${message.replaceAll(ticket, '<ticket>')}`);
}

export default async function globalSetup(): Promise<void> {
  const target = resolveTarget(process.env);
  if (target.serveStatic) return;
  const pointer = join(LOCAL, `${portOf(target.url)}.config`);
  let config: string;
  try {
    config = readFileSync(pointer, 'utf8').trim();
  } catch {
    throw new Error(`${pointer} is missing: start the server with bash tests/e2e/serve-local.sh --port N`);
  }
  const out = execFileSync('uv', ['run', '--locked', '--project', REPO, 'spectio', 'login', '--print-link', '--json'], {
    env: { ...process.env, SPECTIO_CONFIG: config },
    encoding: 'utf8',
  });
  const line = /^spectio-ticket-v1 (\{.*\})$/m.exec(out);
  if (!line) throw new Error('spectio login --print-link --json printed no ticket');
  const { ticket } = JSON.parse(line[1]) as { ticket: string };

  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    const exchange = page.waitForResponse('**/api/v1/auth/magic-links:exchange');
    try {
      await page.goto(new URL(`/auth/link#${ticket}`, target.url).href);
    } catch (error) {
      throw withoutTicket(error, ticket);
    }
    expect((await exchange).status()).toBe(204);
    await page.waitForURL(new URL('/', target.url).href);
    await page.context().storageState({ path: statePath(target.url) });
  } finally {
    await browser.close();
  }
}
