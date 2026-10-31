// The public demo's entry (vite --mode demo only; main.tsx imports it behind the mode, so the
// normal build has neither this code nor the recording: scripts/check-dist.mjs checks it).
import raw from "../../demo/fixtures.json?raw";
import { install, shiftTimes } from "./stub";

export { DemoBanner } from "./DemoBanner";

export function startDemo() {
  install(shiftTimes(JSON.parse(raw), new Date()));
}
