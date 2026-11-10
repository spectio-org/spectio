// zod's eval probe (CR-P3FU102G-03; dev-env §15.3 req. 19, zero CSP violations): zod 4.6.7 runs
// `new Function("")` the first time a schema of Viv's loaders is built (v4/core/util.js:218-226,
// schemas.js:1195-1196); the CSP reports it even though zod catches the throw. The page sets zod's
// jitless config before Viv loads, so the probe never runs and its cached answer is "no eval".
import "./decode"; // as in the page: our decoders are registered before Viv's chunk loads
import { util } from "zod/v4/core";
import { expect, test } from "vitest";

test("Viv's schemas are built after zod's jitless config: the eval probe never ran", async () => {
  await import("./viv");
  expect(util.allowsEval.value).toBe(false); // jsdom allows eval: without jitless the probe would say true
});
