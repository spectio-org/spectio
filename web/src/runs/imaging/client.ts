// The page's own geotiff client (api §5.3.1, dev-env §15.3 req. 19, FU-P3-102d1). geotiff.js is
// given this client through `fromCustomClient`, never a URL: it reads only the one raw URL it is
// pinned to (built from the `stat` route's path, with `as=tiff`), sends only one closed Range per
// request, and counts every request and byte against the view's budget before it is sent.
import { fromCustomClient, type BaseClient, type GeoTIFF } from "geotiff";
import { KIB, MIB } from "../preview";

export const RANGE_MAX = 8 * MIB + 1; // the server's cap per answer (step 8); geotiff asks one byte more
export const BUDGET = { requests: 2000, bytes: 256 * MIB }; // per opened view
export const IN_FLIGHT = 3;
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
  private active = 0;
  private waiting: (() => void)[] = [];

  constructor(
    readonly url: string,
    readonly size: number,
    private readonly budget = BUDGET,
  ) {}

  async request({ headers, signal }: { headers?: HeadersInit; signal?: AbortSignal } = {}) {
    const range = new Headers(headers).get("range") ?? "";
    const m = CLOSED.exec(range);
    const [first, last] = m ? [Number(m[1]), Number(m[2])] : [0, -1];
    if (!m || last < first || last - first + 1 > RANGE_MAX || first >= this.size) throw new Refused(`not sent: ${range}`);
    const length = Math.min(last, this.size - 1) - first + 1;
    for (let attempt = 0; ; attempt++) {
      this.charge(length);
      const answer = await this.fetch(range, signal);
      if (answer.status === 503 && attempt === 0) {
        await new Promise((done) => setTimeout(done, 1000)); // a 503 is asked again once, after 1 s
        continue;
      }
      if (answer.status !== 206) throw new Answered(answer.status, await problem(answer));
      const data = await answer.arrayBuffer();
      if (data.byteLength > length) throw new Answered(206, "longer than the range asked");
      return { ok: true, status: 206, getHeader: (name: string) => answer.headers.get(name), getData: async () => data };
    }
  }

  private charge(length: number) {
    if (this.requests + 1 > this.budget.requests) throw new Stopped("requests");
    if (this.bytes + length > this.budget.bytes) throw new Stopped("bytes");
    this.requests++;
    this.bytes += length;
  }

  private async fetch(range: string, signal?: AbortSignal) {
    while (this.active >= IN_FLIGHT) await new Promise<void>((go) => this.waiting.push(go));
    this.active++;
    try {
      return await fetch(this.url, { headers: { Range: range }, signal, credentials: "same-origin" });
    } finally {
      this.active--;
      this.waiting.shift()?.();
    }
  }
}

async function problem(answer: Response): Promise<string | null> {
  try {
    const body = (await answer.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : null;
  } catch {
    return null;
  }
}

/** Opens the TIFF at `url` (the raw route with `as=tiff`) of `size` bytes, from the `stat` route. */
export async function openTiff(url: string, size: number, signal?: AbortSignal): Promise<{ tiff: GeoTIFF; client: PinnedClient }> {
  const client = new PinnedClient(url, size);
  const tiff = await fromCustomClient(client as unknown as BaseClient, { blockSize: BLOCK, cacheSize: CACHE_BLOCKS }, signal);
  return { tiff, client };
}
