// The pool of our own decoder workers (FU-P3-102d2; dev-env §15.3 req. 19). geotiff's Pool starts
// a blob: worker (refused by worker-src 'self') and has no error path; this one speaks the same
// messages ({fileDirectory, buffer, id} in, {decoded, id} out) to decoder.worker.ts, bundled into
// /assets/, plus {error, id}, and `kind: "chunk"` for a Zarr chunk (FU-P3-102h). One decode per message and per worker; a decode past 10 s ends: the
// worker is terminated and replaced. geotiff reads it as its own (`readRasters({ pool })`).
import { NotDecoded } from "./decode";

export const DECODE_TIMEOUT = 10_000;
export const WORKERS = 2;

const ownWorker = () => new Worker(new URL("./decoder.worker.ts", import.meta.url), { type: "module" });

interface Job {
  fileDirectory: Record<string, unknown>; // a TIFF tile's, or a Zarr chunk's {compressor, bytes}
  kind: "tile" | "chunk";
  buffer: ArrayBuffer;
  resolve: (decoded: ArrayBuffer) => void;
  reject: (err: Error) => void;
}
interface Slot {
  worker: Worker;
  job?: Job;
  timer?: ReturnType<typeof setTimeout>;
}

export class DecoderPool {
  private readonly slots: Slot[];
  private queue: Job[] = [];
  private id = 0;

  constructor(
    size = WORKERS,
    private readonly create: () => Worker = ownWorker,
    private readonly timeout = DECODE_TIMEOUT,
  ) {
    this.slots = Array.from({ length: size }, () => ({ worker: create() }));
  }

  decode(fileDirectory: Record<string, unknown>, buffer: ArrayBuffer, kind: Job["kind"] = "tile"): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      this.queue.push({ fileDirectory, kind, buffer, resolve, reject });
      this.next();
    });
  }

  private next() {
    for (const slot of this.slots) {
      const job = !slot.job && this.queue.shift();
      if (job) this.run(slot, job);
    }
  }

  private run(slot: Slot, job: Job) {
    const id = this.id++;
    slot.job = job;
    slot.timer = setTimeout(() => this.end(slot, new NotDecoded("decoding took over 10 s"), true), this.timeout);
    slot.worker.onmessage = ({ data }: MessageEvent) => {
      if (data?.id === id) this.end(slot, typeof data.error === "string" ? new NotDecoded(data.error) : data.decoded);
    };
    slot.worker.onerror = () => this.end(slot, new NotDecoded("the decoder failed"), true);
    slot.worker.postMessage({ fileDirectory: job.fileDirectory, kind: job.kind, buffer: job.buffer, id }, [job.buffer]);
  }

  private end(slot: Slot, result: ArrayBuffer | Error, replace = false) {
    const job = slot.job;
    clearTimeout(slot.timer);
    slot.job = undefined;
    if (replace) {
      slot.worker.terminate();
      slot.worker = this.create();
    }
    if (result instanceof Error) job?.reject(result);
    else job?.resolve(result);
    this.next();
  }

  /** Ends every worker; decodes running or waiting are refused. */
  destroy() {
    for (const slot of this.slots) {
      clearTimeout(slot.timer);
      slot.job?.reject(new NotDecoded("the view was closed"));
      slot.job = undefined;
      slot.worker.terminate();
    }
    for (const job of this.queue.splice(0)) job.reject(new NotDecoded("the view was closed"));
  }
}
