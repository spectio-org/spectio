// Our own decoder worker (FU-P3-102d2): bundled by Vite into /assets/ (worker-src 'self', no
// blob:), it answers each message of pool.ts with the decoded tile or Zarr chunk, or the reason it
// was refused.
import { reply } from "./codecs";

self.onmessage = async ({ data }: MessageEvent) => {
  const { message, transfer } = await reply(data);
  self.postMessage(message, { transfer });
};
