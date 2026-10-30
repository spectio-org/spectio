// A small typed client of the routes the screens use (P1 Tasks 17 and 18; api §5).
// Hand-written: the OpenAPI snapshot has no response models yet (follow-up FU-P3-21).

export type Engine = "nextflow" | "snakemake";
export const ENGINES: Engine[] = ["nextflow", "snakemake"];
export const ENGINE_FILES: Record<Engine, string[]> = {
  nextflow: ["main.nf"],
  snakemake: ["Snakefile", "workflow/Snakefile"],
};

export type JSONSchema = Record<string, unknown>;

/** `GET /api/v1/workflows:inspect` */
export interface Inspected {
  location: string;
  revision: string | null;
  engine: Engine | null;
  engine_files: string[];
  name: string;
  version: string | null;
  engine_version: string | null;
  engine_versions: Partial<Record<Engine, string | null>>;
  schema: JSONSchema | null;
  schema_source: "nextflow_schema.json" | "config.schema.yaml" | "inferred" | "none";
  profiles: string[];
}

/** The body of `POST /api/v1/runs` (api §5 note of 2026-10-30). */
export interface LaunchBody {
  workflow: { location: string; revision: string | null; engine: Engine };
  name?: string;
  profiles: string[];
  params: Record<string, unknown>;
}

export interface Launched {
  id: string;
  name: string;
  state: string;
}

/** `GET /api/v1/version` */
export interface ServerVersion {
  version: string;
  node: string;
  runs_root: string;
  account: string;
  executor: string;
}

export interface FieldError {
  field: string;
  message: string;
}

/** An RFC 9457 problem; a 422 carries `errors` with a dotted `field` (inbox #86 rule 3). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly errors: FieldError[] = [],
  ) {
    super(message);
  }
}

const API = "/api/v1";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API + path, init);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail ?? body?.title ?? `HTTP ${response.status}`;
    throw new ApiError(response.status, detail, Array.isArray(body?.errors) ? body.errors : []);
  }
  return body as T;
}

export function getVersion(signal?: AbortSignal): Promise<ServerVersion> {
  return call("/version", { signal });
}

export function inspect(
  location: string,
  revision: string | null,
  signal?: AbortSignal,
): Promise<Inspected> {
  const query = new URLSearchParams({ location });
  if (revision) query.set("revision", revision);
  return call(`/workflows:inspect?${query}`, { signal });
}

export function launch(body: LaunchBody): Promise<Launched> {
  return call("/runs", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}
