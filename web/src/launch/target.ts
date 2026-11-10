import type { Inspected, JSONSchema, TargetInspected } from "../api";

// Launch's single target mode (ui-spec §4.15; api §5.9): a module becomes a form like a pipeline's,
// one field per declared input, so the rest of the form (Before Launch, the params preview) is
// the same code.

/** A registry module, as the server checks it (`spectio_sdk.targets.REGISTRY_NAME`). */
export const REGISTRY_NAME = /^[a-z0-9][a-z0-9_-]{0,63}\/[a-z0-9][a-z0-9_.-]{0,127}$/;

type ModuleAnswer = Extract<TargetInspected, { kind: "module" }>;

/** A module's input type as a schema type: a map is JSON, a number stays one, the rest is text. */
function inputSchema(type: string, description: string): JSONSchema {
  const t = type.toLowerCase();
  const schema = t === "map" ? "object" : ["integer", "number", "boolean"].includes(t) ? t : "string";
  return { type: schema, ...(description ? { description } : {}) };
}

/** The module as the form's `Inspected`: every input required, no profiles, no schema file. */
export function moduleInspected(module: ModuleAnswer, location: string, pipeline: Inspected | null): Inspected {
  return {
    location,
    revision: null,
    engine: "nextflow",
    engine_files: ["main.nf"],
    name: module.name,
    version: module.version,
    engine_version: pipeline?.engine_version ?? null,
    engine_versions: pipeline?.engine_versions ?? {},
    schema: module.inputs.length
      ? {
          type: "object",
          required: module.inputs.map((i) => i.name),
          properties: Object.fromEntries(module.inputs.map((i) => [i.name, inputSchema(i.type, i.description)])),
        }
      : null,
    schema_source: "none",
    profiles: pipeline?.profiles ?? [],
    params_file: null,
  };
}

/** "make_reads 12, qc_stats 12, qc_report 1 (25 jobs)" */
export function planText(plan: { jobs: Record<string, number>; total: number }): string {
  const jobs = Object.entries(plan.jobs).map(([rule, n]) => `${rule} ${n}`);
  return `${jobs.join(", ")} (${plan.total} ${plan.total === 1 ? "job" : "jobs"})`;
}
