// The page's own geotiff client (api §5.3.1, dev-env §15.3 req. 19, FU-P3-102d1). geotiff.js is
// given this client through `fromCustomClient`, never a URL: it reads only the one raw URL it is
// pinned to (built from the `stat` route's path, with `as=tiff`), sends only closed Ranges of at most
// 8 MiB + 1, and counts every request and byte against the view's budget before it is sent.
import { fromCustomClient, type BaseClient, type GeoTIFF } from "geotiff";
import { KIB, MIB } from "../preview";

export const RANGE_MAX = 8 * MIB + 1; // the server's cap per answer (step 8); geotiff asks one byte more
export const BUDGET = { requests: 2000, bytes: 256 * MIB }; // per opened view
export const IN_FLIGHT = 3;
const PROBLEM_MAX = 64 * KIB; // a problem body read for its detail
const BLOCK = 64 * KIB; // geotiff's BlockedSource default
const CACHE_BLOCKS = (64 * MIB) / BLOCK; // a block cache of at most 64 MiB

/** A request the client never sends: not one closed range of at most 8 MiB + 1 inside the file. */
export class Refused extends Error {}

/** The view's budget is spent: the view keeps what it drew and stops reading (ui-spec §4.4.1). */
export class Stopped extends Error {
  constructor(readonly limit: "requests" | "bytes") {
    super(`stopped reading: ${limit}`);
  }
}

/** The server answered something else than 206, with its problem's text when it gave one. */
export class Answered extends Error {
  constructor(
    readonly status: number,
    readonly detail: string | null,
  ) {
    super(`answered ${status}`);
  }
}

const CLOSED = /^bytes=(\d{1,15})-(\d{1,15})$/;

export class PinnedClient {
  requests = 0;
  bytes = 0;
  /** The last error a request threw, aborts aside: geotiff's BlockedSource hides it behind its own. */
  failure: Error | null = null;
  /** Told when the first request starts and when the last one ends (the viewer's "Reading tiles…"). */
  onBusy?: (busy: boolean) => void;
  private active = 0;
  private waiting: (() => void)[] = [];

  constructor(
    readonly url: string,
    readonly size: number,
    private readonly budget = BUDGET,
  ) {}

  /** One closed range inside the file; one longer than RANGE_MAX (geotiff merges consecutive
   * blocks) is sent as several closed ranges of at most 8 MiB, each charged, answered as one. */
  async request({ headers, signal }: { headers?: HeadersInit; signal?: AbortSignal } = {}) {
    try {
      const range = new Headers(headers).get("range") ?? "";
      const m = CLOSED.exec(range);
      const [first, last] = m ? [Number(m[1]), Number(m[2])] : [0, -1];
      if (!m || last < first || first >= this.size) throw new Refused(`not sent: ${range}`);
      const end = Math.min(last, this.size - 1);
      const step = end - first + 1 > RANGE_MAX ? RANGE_MAX - 1 : RANGE_MAX;
      const pieces: Promise<ArrayBuffer>[] = [];
      for (let at = first; at <= end; at += step) pieces.push(this.piece(at, Math.min(at + step - 1, last), signal));
      const parts = await Promise.all(pieces);
      const data = parts.length === 1 ? parts[0] : join(parts);
      const contentRange = `bytes ${first}-${end}/${this.size}`;
      return { ok: true, status: 206, getHeader: (name: string) => (name.toLowerCase() === "content-range" ? contentRange : null), getData: async () => data };
    } catch (err) {
      if ((err as Error).name !== "AbortError") this.failure = err as Error;
      throw err;
    }
  }

  private async piece(first: number, last: number, signal?: AbortSignal): Promise<ArrayBuffer> {
    const length = Math.min(last, this.size - 1) - first + 1;
    for (let attempt = 0; ; attempt++) {
      if (attempt) await new Promise((done) => setTimeout(done, 1000)); // a 503 is asked again once, after 1 s
      this.charge(length);
      // the slot is held across the fetch and the body read: the server has 3 imaging slots
      while (this.active >= IN_FLIGHT) await new Promise<void>((go) => this.waiting.push(go));
      if (this.active++ === 0) this.onBusy?.(true);
      try {
        const answer = await fetch(this.url, { headers: { Range: `bytes=${first}-${last}` }, signal, credentials: "same-origin" });
        if (answer.status === 503 && attempt === 0) {
          await answer.body?.cancel();
          continue;
        }
        if (answer.status !== 206) throw new Answered(answer.status, await problem(answer));
        const declared = answer.headers.get("content-length");
        const data = declared === null || Number(declared) === length ? await readAtMost(answer, length) : (await answer.body?.cancel(), null);
        if (data?.byteLength !== length) throw new Answered(206, "not the range asked");
        return data.buffer as ArrayBuffer;
      } finally {
        this.active--;
        this.waiting.shift()?.();
        if (this.active === 0 && !this.waiting.length) this.onBusy?.(false);
      }
    }
  }

  private charge(length: number) {
    if (this.requests + 1 > this.budget.requests) throw new Stopped("requests");
    if (this.bytes + length > this.budget.bytes) throw new Stopped("bytes");
    this.requests++;
    this.bytes += length;
  }
}

function join(parts: ArrayBuffer[]): ArrayBuffer {
  const all = new Uint8Array(parts.reduce((n, p) => n + p.byteLength, 0));
  let at = 0;
  for (const p of parts) {
    all.set(new Uint8Array(p), at);
    at += p.byteLength;
  }
  return all.buffer;
}

/** Runs a geotiff read on `client`, rethrowing the client's own error (Stopped, Refused,
 * Answered) instead of the AggregateError BlockedSource turns it into; any other error (the
 * page's own included) is rethrown as it is. */
export async function reading<T>(client: PinnedClient, read: () => Promise<T>): Promise<T> {
  try {
    return await read();
  } catch (err) {
    throw (err as Error)?.name === "AggregateError" ? (client.failure ?? err) : err;
  }
}

/** The body, read up to `max` bytes; null (and the rest cancelled) when it is longer. */
export async function readAtMost(answer: Response, max: number): Promise<Uint8Array | null> {
  const reader = answer.body?.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  for (;;) {
    const next = await reader?.read();
    if (!next || next.done) break;
    total += next.value.byteLength;
    if (total > max) {
      await reader?.cancel();
      return null;
    }
    chunks.push(next.value);
  }
  const all = new Uint8Array(total);
  chunks.reduce((at, c) => (all.set(c, at), at + c.byteLength), 0);
  return all;
}

/** The detail of a problem body of at most 64 KiB; any other body is cancelled unread. */
export async function problem(answer: Response): Promise<string | null> {
  if (!answer.headers.get("content-type")?.startsWith("application/problem+json")) {
    await answer.body?.cancel();
    return null;
  }
  try {
    const text = await readAtMost(answer, PROBLEM_MAX);
    const body = (text && JSON.parse(new TextDecoder().decode(text))) as { detail?: unknown } | null;
    return typeof body?.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}

/** Opens the TIFF at `url` (the raw route with `as=tiff`) of `size` bytes, from the `stat` route. */
export async function openTiff(url: string, size: number, signal?: AbortSignal, budget = BUDGET): Promise<{ tiff: GeoTIFF; client: PinnedClient }> {
  const client = new PinnedClient(url, size, budget);
  const tiff = await reading(client, () => fromCustomClient(client as unknown as BaseClient, { blockSize: BLOCK, cacheSize: CACHE_BLOCKS }, signal));
  return { tiff, client };
}
