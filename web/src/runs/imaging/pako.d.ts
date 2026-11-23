// The part of pako 2.2.0 the capped Deflate decoder uses (decode.ts); pako ships no types.
declare module "pako" {
  export class Inflate {
    constructor(options?: { chunkSize?: number });
    push(data: Uint8Array, final: boolean): boolean;
    onData(chunk: Uint8Array): void;
    err: number;
    ended: boolean;
  }
  export function deflate(data: Uint8Array): Uint8Array;
}
