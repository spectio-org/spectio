// zod's jitless config, set before Viv's loaders build their schemas (viv.ts imports this first):
// zod 4.6.7 otherwise probes for eval with `new Function("")` (v4/core/util.js:218-226), which the
// CSP reports as a violation even though zod catches the throw (CR-P3FU102G-03, req. 19).
import { config } from "zod/v4/core";

config({ jitless: true });
