// Our own decoder worker (FU-P3-102d2): bundled by Vite into /assets/ (worker-src 'self', no
// blob:), it answers each message of pool.ts with the decoded tile or the reason it was refused.
import { answer } from "./decode";

self.onmessage = async ({ data }: MessageEvent) => {
  const { message, transfer } = await answer(data);
  self.postMessage(message, { transfer });
};
