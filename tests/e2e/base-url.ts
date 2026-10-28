import { readFileSync } from 'node:fs';

// Port of the static stand-in page. Scenario ports start at 20100 (dev/scenario.py, id 1), so it never collides.
export const STATIC_PORT = 8710;
export const STATIC_URL = `http://127.0.0.1:${STATIC_PORT}`;

export type Target = { url: string; serveStatic: boolean };

/** Where the tests run: SPECTIO_E2E_BASE_URL, else urls.spectio of SPECTIO_SCENARIO, else the static stand-in. */
export function resolveTarget(env: NodeJS.ProcessEnv): Target {
  if (env.SPECTIO_E2E_BASE_URL) {
    const { protocol, username, password, search } = new URL(env.SPECTIO_E2E_BASE_URL);
    if (protocol !== 'http:' && protocol !== 'https:') throw new Error('SPECTIO_E2E_BASE_URL must be http or https');
    // Traces and reports keep the URL: a credential in it would end up in a CI artifact (SEC-T6-01).
    if (username || password || search) throw new Error('SPECTIO_E2E_BASE_URL must carry no user, password or query');
    return { url: env.SPECTIO_E2E_BASE_URL, serveStatic: false };
  }
  if (env.SPECTIO_SCENARIO) {
    // The JSON that `dev/scenario.py up` prints and saves as .scenarios/<id>/scenario.json.
    const url = JSON.parse(readFileSync(env.SPECTIO_SCENARIO, 'utf8')).urls?.spectio;
    if (!url) throw new Error(`${env.SPECTIO_SCENARIO} has no urls.spectio: this scenario does not run Spectio yet`);
    return resolveTarget({ SPECTIO_E2E_BASE_URL: url });
  }
  return { url: STATIC_URL, serveStatic: true };
}
