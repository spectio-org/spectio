// The demo's server (issue #160): `fetch` and `EventSource` answered in the browser, with the routes
// the Runs list, Run detail and its Graph tab read. Two Nextflow runs of the demo pipeline (one
// live, one finished for the diff) and one failed Snakemake run. Nothing leaves the page.
import type { GraphDocument } from "../runs/graph/types";
import { PARAMS, ROOT, STEPS } from "./pipeline";
import { type Sim, advance, countsOf, finished, graphOf, iso, newSim } from "./sim";

const API = "/api/v1";
export const LIVE = "run_01JCDE7M0RN5Q2P3R5S7T9V1W1";
export const DONE = "run_01JCDE7M0RN5Q2P3R5S7T9V1W2";
export const SMK = "run_01JCDE7M0RN5Q2P3R5S7T9V1W3";
/** Simulated seconds per real second. */
export const SPEED = 15;

const NO_RESOURCES = { cpus: null, memory_bytes: null, time_s: null, realtime_s: null, cpu_percent: null, peak_rss_bytes: null, source: null };

interface State {
  live: Sim;
  done: Sim;
  paused: boolean;
}
let state: State;

export function reset(): void {
  const now = Date.now();
  const done = newSim(now - 3 * 3600_000, { pace: 1.2, skip: [`${ROOT}:BAM_QC:RSEQC_INFEREXPERIMENT`] });
  advance(done, 20_000);
  // the live run resumes the previous one: the genome preparation is reused from its cache
  const live = newSim(now, { cached: STEPS.filter((s) => s.id.includes(":PREPARE_GENOME:")).map((s) => s.id) });
  advance(live, 30); // already started when the page opens
  state = { live, done, paused: false };
}

export const setPaused = (paused: boolean) => (state.paused = paused);
export const isPaused = () => state.paused;

const sims = (): Record<string, Sim> => ({ [LIVE]: state.live, [DONE]: state.done });

function runOf(id: string): Record<string, unknown> | null {
  if (id === SMK) return SMK_RUN;
  const sim = sims()[id];
  if (!sim) return null;
  const end = finished(sim) ? Math.max(...sim.tasks.map((t) => t.end ?? 0)) : null;
  const counts = countsOf(sim.tasks);
  return {
    id,
    name: id === LIVE ? "rnaseq-ko-vs-wt" : "rnaseq-ko-vs-wt-previous",
    state: end === null ? "running" : "succeeded",
    origin: "ui",
    created_at: iso(sim, -5),
    started_at: iso(sim, 0),
    ended_at: end === null ? null : iso(sim, end),
    workflow: { engine: "nextflow", engine_version: "26.10.4", location: "nf-core/rnaseq", name: "nf-core/rnaseq", version: "3.27.0" },
    profiles: ["docker"],
    failure: null,
    head: { session: `spectio-${id}`, node: "login1", alive: end === null, exit_code: end === null ? null : 0, checked: true },
    task_counts: counts,
    summary: {
      tasks: { done: (counts.succeeded ?? 0) + (counts.cached ?? 0), total: sim.tasks.length, failed: 0, cached: counts.cached ?? 0 },
      last_failure: null,
      stage_mode: "quarters",
    },
  };
}

const DETAIL = {
  stages_note: null,
  failures: [],
  failures_total: 0,
  command: null,
  parent_run_id: null,
  resumed_as: [],
  results_dir: "/scratch/demo/spectio-runs/rnaseq-ko-vs-wt/results",
};

function detailOf(id: string): Record<string, unknown> | null {
  const run = runOf(id);
  if (!run) return null;
  const running = run.state === "running";
  return {
    ...run,
    ...DETAIL,
    params: id === SMK ? { samples: "config/samples.tsv", ref: "data/genome.fa" } : PARAMS,
    actions: { resume: running ? { allowed: false, reason: "running" } : { allowed: false, reason: "demo" } },
  };
}

function tasksOf(id: string, process: string | null, wanted: string | null) {
  if (id === SMK) return smkTasks(process, wanted);
  const sim = sims()[id];
  if (!sim) return [];
  return sim.tasks
    .filter((t) => !process || t.step.id === process)
    .filter((t) => !wanted || wanted.split(",").includes(t.state))
    .map((t) => ({
      id: t.id,
      process: t.step.id,
      tag: t.sample,
      name: `${t.step.id.split(":").at(-1)}${t.sample ? ` (${t.sample})` : ""}`,
      state: t.state,
      stage_id: t.step.stage,
      attempt_n: t.attempt || null,
      resources: t.state === "succeeded" ? resources(t.id, t.step.seconds, Math.round(t.step.cpu * 12)) : NO_RESOURCES,
      efficiency: t.state === "succeeded" ? efficiencyOf(t.id, t.step.seconds) : undefined,
      slurm: null,
    }));
}

function outputsOf(id: string, process: string) {
  if (id === SMK) return smkOutputs(process);
  const sim = sims()[id];
  const step = STEPS.find((s) => s.id === process);
  if (!sim || !step) return [];
  return sim.tasks
    .filter((t) => t.step.id === process && t.state === "succeeded")
    .flatMap((t) =>
      step.outputs.map((o) => {
        const path = o.replace("{s}", t.sample ?? "");
        return { path, task_id: t.id, attempt_n: t.attempt, state: "present", temp: false, root: "results", size: sizeOf(path) };
      }),
    );
}

function graphFor(id: string): GraphDocument | null {
  if (id === SMK) return SMK_GRAPH;
  const sim = sims()[id];
  return sim ? graphOf(sim) : null;
}

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": status >= 400 ? "application/problem+json" : "application/json" },
  });
const missing = (what: string) => json(404, { type: "/problems/not-found", title: "Not found", detail: `${what} is not part of this demo` });

/** Answers one request of the app, by path; the demo has no writes. */
export function answer(url: URL, method = "GET"): Response {
  const path = decodeURIComponent(url.pathname.slice(API.length));
  const q = url.searchParams;
  if (method !== "GET") return json(403, { type: "/problems/forbidden", title: "Read-only demo", detail: "This demo does not launch, stop or change runs." });
  if (path === "/version") return json(200, { version: "0.0.2-demo", node: "login1", runs_root: "/scratch/demo/spectio-runs", account: "demo", executor: "local" });
  if (path === "/features") return json(200, { features: ["graph_view"] });
  if (path === "/catalog") return json(200, { items: [], file: { path: "~/.spectio/catalog.toml", state: "missing", detail: null } });
  if (path === "/me/notifications") return json(200, { items: [], unread: 0, read_up_to: null });
  if (path === "/workflows:source") {
    const block = sourceOf(q.get("name") ?? "");
    return block ? json(200, block) : missing("This step's code");
  }
  if (path === "/runs:summary") {
    const groups: Record<string, number> = {};
    for (const r of [LIVE, DONE, SMK].map(runOf)) groups[String(r!.state)] = (groups[String(r!.state)] ?? 0) + 1;
    return json(200, { groups: Object.entries(groups).map(([key, count]) => ({ key, count })) });
  }
  if (path === "/runs") {
    const states = q.get("state")?.split(",");
    const items = [LIVE, DONE, SMK].map(runOf).filter((r) => !states || states.includes(String(r!.state)));
    return json(200, { items, next: null });
  }
  const m = /^\/runs\/([^/]+)(\/.*)?$/.exec(path);
  if (!m) return missing(path);
  const [, id, rest = ""] = m;
  const detail = detailOf(id);
  if (!detail) return missing("This run");
  if (rest === "") return json(200, detail);
  if (rest === "/graph") return json(200, graphFor(id));
  if (rest === "/stages") return json(200, { items: [] });
  if (rest === "/tasks") return json(200, { items: tasksOf(id, q.get("process"), q.get("state")), next: null });
  if (rest === "/processes") {
    const doc = graphFor(id)!;
    return json(200, {
      items: doc.nodes.map((n) => ({ process: n.id, stage_id: n.stage_id, counts: n.counts ?? {}, retries: n.retries ?? 0, status: n.status, pipeline_order: n.pipeline_order })),
    });
  }
  const out = /^\/processes\/(.+)\/outputs$/.exec(rest);
  if (out) return json(200, { items: outputsOf(id, out[1]) });
  const head = /^\/processes\/(.+)\/outputs:head$/.exec(rest);
  if (head) {
    const p = q.get("path") ?? "";
    if (!outputsOf(id, head[1]).some((o) => o.path === p)) return missing("This file");
    const text = contentOf(p);
    return text === null ? json(422, { type: "/problems/not-text", title: "Not text", detail: "a binary file has no head to show" }) : json(200, { text: text.split("\n").slice(0, 40).join("\n"), more: true, gzip: /\.gz$/.test(p) });
  }
  const res = /^\/results\/(stat|text|raw)\/(.+)$/.exec(rest);
  if (res) {
    const [, how, p] = res;
    const name = p.split("/").pop()!;
    if (how === "stat") return json(200, { root: "/scratch/demo/results", path: p, name, type: "file", size: sizeOf(p), mtime: "2026-11-10T10:30:00Z" });
    const text = contentOf(p);
    if (text === null) return missing("This file's content");
    return new Response(text, { status: 200, headers: { "content-type": how === "raw" && p.endsWith(".svg") ? "image/svg+xml" : "text/plain; charset=utf-8" } });
  }
  return missing(path);
}

type Handler = (event: MessageEvent) => void;
const sources = new Set<DemoEventSource>();

/** The live stream: one frame per tick for the live run, as `spectio.run.delta`. */
export class DemoEventSource {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 2;
  readyState = DemoEventSource.CONNECTING;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  private handlers = new Map<string, Handler>();
  constructor(readonly url: string) {
    sources.add(this);
    setTimeout(() => {
      this.readyState = DemoEventSource.OPEN;
      this.onopen?.();
    }, 50);
  }
  addEventListener(type: string, handler: Handler) {
    this.handlers.set(type, handler);
  }
  close() {
    this.readyState = DemoEventSource.CLOSED;
    sources.delete(this);
  }
  emit(runId: string) {
    this.handlers.get("spectio.run.delta")?.(new MessageEvent("spectio.run.delta", { data: JSON.stringify({ run_id: runId }) }));
  }
}

/** Advances the live run by one real second and tells the open streams. */
export function tick(): void {
  if (state.paused || finished(state.live)) return;
  advance(state.live, SPEED);
  sources.forEach((s) => s.emit(LIVE));
}

/** Installs the demo server in place of the network. */
export function install(): void {
  reset();
  const real = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(input instanceof Request ? input.url : String(input), window.location.href);
    if (!url.pathname.startsWith(API)) return real(input, init);
    return answer(url, init?.method ?? (input instanceof Request ? input.method : "GET"));
  };
  (window as unknown as { EventSource: unknown }).EventSource = DemoEventSource;
  setInterval(tick, 1000);
}

// --- The Snakemake run: a finished rule graph, a checkpoint, temporary files, one failed job ---

const SMK_SAMPLES = ["A", "B", "C", "D"];
const REGIONS = ["chr1", "chr2"];
interface Rule {
  id: string;
  file: string;
  /** The jobs' wildcards, sorted by name as the server keys them. */
  jobs: string[];
  seconds: number;
  kind?: "checkpoint";
  temp?: boolean;
  outputs: (key: string) => string[];
  input: string;
  shell: string;
}
const perSample = SMK_SAMPLES.map((x) => `sample=${x}`);
const val = (key: string, name: string) => new RegExp(`(?:^|, )${name}=([^,]+)`).exec(key)?.[1] ?? "";
const RULES: Rule[] = [
  { id: "fastp", file: "rules/qc.smk", jobs: perSample, seconds: 120, outputs: (k) => [`trimmed/${val(k, "sample")}.R1.fq.gz`], input: 'expand("reads/{sample}.R{r}.fq.gz", r=[1, 2])', shell: "fastp -i {input[0]} -I {input[1]} -o {output} --json {log}" },
  { id: "fastqc", file: "rules/qc.smk", jobs: perSample, seconds: 60, outputs: (k) => [`qc/fastqc/${val(k, "sample")}_fastqc.html`], input: '"reads/{sample}.R1.fq.gz"', shell: "fastqc {input} -o qc/fastqc" },
  { id: "bwa_map", file: "rules/mapping.smk", jobs: perSample, seconds: 600, temp: true, outputs: (k) => [`mapped/${val(k, "sample")}.bam`], input: '"trimmed/{sample}.R1.fq.gz"', shell: "bwa mem -t {threads} {params.ref} {input} | samtools view -b - > {output}" },
  { id: "samtools_sort", file: "rules/mapping.smk", jobs: perSample, seconds: 180, outputs: (k) => [`sorted/${val(k, "sample")}.bam`], input: '"mapped/{sample}.bam"', shell: "samtools sort -o {output} {input}" },
  { id: "samtools_index", file: "rules/mapping.smk", jobs: perSample, seconds: 40, outputs: (k) => [`sorted/${val(k, "sample")}.bam.bai`], input: '"sorted/{sample}.bam"', shell: "samtools index {input}" },
  { id: "split_regions", file: "rules/calling.smk", jobs: [""], seconds: 30, kind: "checkpoint", outputs: () => ["regions/"], input: "config[\"ref\"] + \".fai\"", shell: "split_regions.py {input} {output}" },
  { id: "call_variants", file: "rules/calling.smk", jobs: perSample.flatMap((sm) => REGIONS.map((r) => `region=${r}, ${sm}`)), seconds: 420, outputs: (k) => [`calls/${val(k, "sample")}.${val(k, "region")}.vcf.gz`], input: 'bam="sorted/{sample}.bam", region="regions/{region}.bed"', shell: "bcftools mpileup -R {input.region} {input.bam} | bcftools call -mv -Oz -o {output}" },
  { id: "merge_vcfs", file: "rules/calling.smk", jobs: [""], seconds: 90, outputs: () => ["calls/all.vcf.gz"], input: "aggregate_calls", shell: "bcftools concat -Oz -o {output} {input}" },
  { id: "plot_quals", file: "rules/calling.smk", jobs: [""], seconds: 20, outputs: () => ["plots/quals.svg"], input: '"calls/all.vcf.gz"', shell: "plot-quals.py {input} {output}" },
  { id: "multiqc", file: "rules/qc.smk", jobs: [""], seconds: 50, outputs: () => ["qc/multiqc_report.html"], input: 'expand("qc/fastqc/{sample}_fastqc.html", sample=SAMPLES)', shell: "multiqc qc -o qc" },
];
const FAILED_JOB = "region=chr2, sample=C";
/** Rules after the failed job never ran. */
const BLOCKED = new Set(["merge_vcfs", "plot_quals"]);

interface SmkJob {
  id: string;
  rule: Rule;
  key: string;
  state: "succeeded" | "failed" | "not_scheduled";
}
let n = 0;
const SMK_JOBS: SmkJob[] = RULES.flatMap((r) =>
  r.jobs.map((key) => ({
    id: `tsk_s${String(++n).padStart(3, "0")}`,
    rule: r,
    key,
    state: BLOCKED.has(r.id) ? ("not_scheduled" as const) : r.id === "call_variants" && key === FAILED_JOB ? ("failed" as const) : ("succeeded" as const),
  })),
);

const SMK_STAGES: Record<string, string> = { qc: "rules/qc.smk", mapping: "rules/mapping.smk", calling: "rules/calling.smk" };

function smkNode(r: Rule, i: number) {
  const jobs = SMK_JOBS.filter((j) => j.rule === r);
  const counts: Record<string, number> = {};
  for (const j of jobs) counts[j.state] = (counts[j.state] ?? 0) + 1;
  const failed = counts.failed ?? 0;
  const status = BLOCKED.has(r.id) ? "not_needed" : failed ? "failed" : "done";
  return {
    id: r.id,
    name: r.id,
    kind: r.kind ?? ("rule" as const),
    stage_id: r.file.replace("rules/", "").replace(".smk", ""),
    subworkflow: null,
    source: { file: `workflow/${r.file}`, line: null },
    condition: null,
    params: r.id === "bwa_map" || r.id === "call_variants" ? ["ref"] : r.id === "fastp" ? ["samples"] : [],
    status: status as "done" | "failed" | "not_needed",
    counts: BLOCKED.has(r.id) ? {} : counts,
    retries: 0,
    pipeline_order: i,
    temp: r.temp ?? false,
    metrics: BLOCKED.has(r.id) ? {} : { duration_s: r.seconds * (r.jobs.length > 4 ? 2 : 1), cpu_mean: 0.4 + (r.seconds % 7) / 12, mem_max: 0.3 + (r.seconds % 5) / 8, failed },
  };
}

const SMK_GRAPH: GraphDocument = {
  version: 1,
  engine: "snakemake",
  producer: "smk-rulegraph",
  complete: true,
  groups: Object.entries(SMK_STAGES).map(([id, name]) => ({ id: `stage:${id}`, kind: "stage" as const, name, parent: null, condition: null })),
  nodes: [...RULES.map(smkNode), { ...smkNode({ ...RULES[8], id: "all", file: "Snakefile", jobs: [""] }, RULES.length), stage_id: null, counts: {}, metrics: {} }],
  edges: [
    ["fastp", "bwa_map"],
    ["fastp", "multiqc"],
    ["fastqc", "multiqc"],
    ["bwa_map", "samtools_sort"],
    ["samtools_sort", "samtools_index"],
    ["samtools_sort", "multiqc"],
    ["samtools_index", "call_variants"],
    ["split_regions", "call_variants"],
    ["call_variants", "merge_vcfs"],
    ["merge_vcfs", "plot_quals"],
    ["merge_vcfs", "all"],
    ["plot_quals", "all"],
    ["multiqc", "all"],
  ].map(([source, target]) => ({ source, target })),
};

function smkTasks(process: string | null, wanted: string | null) {
  return SMK_JOBS.filter((j) => !process || j.rule.id === process)
    .filter((j) => !wanted || wanted.split(",").includes(j.state))
    .map((j) => ({
      id: j.id,
      process: j.rule.id,
      tag: j.key || null,
      name: j.key ? `${j.rule.id} (${j.key})` : j.rule.id,
      state: j.state,
      stage_id: j.rule.file.replace("rules/", "").replace(".smk", ""),
      attempt_n: j.state === "not_scheduled" ? null : 1,
      resources: j.state === "not_scheduled" ? NO_RESOURCES : resources(j.id, j.rule.seconds, 4),
      efficiency: j.state === "succeeded" ? efficiencyOf(j.id, j.rule.seconds) : undefined,
      slurm: null,
    }));
}

function smkOutputs(process: string) {
  return SMK_JOBS.filter((j) => j.rule.id === process && j.state === "succeeded").flatMap((j) =>
    j.rule.outputs(j.key).map((path) => ({ path, task_id: j.id, attempt_n: 1, state: j.rule.temp ? "removed" : "present", temp: !!j.rule.temp, root: "launch", size: j.rule.temp ? null : sizeOf(path) })),
  );
}

/** Made-up resources for a demo job, stable for its id. */
function resources(id: string, seconds: number, cpus: number) {
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return { cpus, memory_bytes: 8 * 2 ** 30, time_s: null, realtime_s: Math.round(seconds * (0.8 + (h % 40) / 100)), cpu_percent: 60 + (h % 35), peak_rss_bytes: (2 + (h % 50) / 10) * 2 ** 30, source: "trace" as const };
}

/** `GET /workflows:source`: made-up code for a demo step, in the engine's syntax. */
function sourceOf(name: string) {
  const r = RULES.find((x) => x.id === name);
  if (r) {
    const code = [
      `${r.kind ?? "rule"} ${r.id}:`,
      `    input:`,
      `        ${r.input}`,
      `    output:`,
      `        ${r.temp ? `temp("${r.outputs("sample={sample}")[0].replace("{sample}", "{sample}")}")` : `"${r.outputs("sample={sample}, region={region}")[0]}"`}`,
      `    log:`,
      `        "logs/${r.id}/{sample}.log"`,
      `    threads: 4`,
      `    conda:`,
      `        "../envs/${r.id.split("_")[0]}.yaml"`,
      `    shell:`,
      `        "${r.shell}"`,
    ].join("\n");
    return { file: `workflow/${r.file}`, line: 3 + RULES.filter((x) => x.file === r.file).indexOf(r) * 14, code, truncated: false };
  }
  const step = STEPS.find((x) => x.id.split(":").at(-1) === name.split(":").at(-1));
  if (!step) return null;
  const proc = step.id.split(":").at(-1)!;
  const tool = proc.split("_")[0].toLowerCase();
  const code = [
    `process ${proc} {`,
    `    tag "$meta.id"`,
    `    label 'process_${step.cpu > 0.8 ? "high" : "medium"}'`,
    ``,
    `    conda "\${moduleDir}/environment.yml"`,
    `    container "community.wave.seqera.io/library/${tool}:latest"`,
    ``,
    `    input:`,
    step.perSample ? `    tuple val(meta), path(reads)` : `    path(inputs)`,
    ``,
    `    output:`,
    ...step.outputs.map((o) => `    path "${o.split("/").at(-1)!.replace("{s}", "${meta.id}")}", emit: ${o.split(".").at(-1)}`),
    `    path "versions.yml", emit: versions`,
    ``,
    ...(step.params.length ? [`    when:`, `    ${step.params.find((p) => p.startsWith("skip_")) ? `!params.${step.params.find((p) => p.startsWith("skip_"))}` : "task.ext.when == null || task.ext.when"}`, ``] : []),
    `    script:`,
    `    def args = task.ext.args ?: ''`,
    `    """`,
    `    ${tool} \\`,
    `        $args \\`,
    ...step.params.filter((p) => !p.startsWith("skip_")).map((p) => `        --${p.replace(/_/g, "-")} \${params.${p}} \\`),
    `        --threads $task.cpus`,
    `    """`,
    `}`,
  ].join("\n");
  return { file: step.file, line: 1, code, truncated: false };
}

const SMK_RUN = {
  id: SMK,
  name: "variant-calling-batch3",
  state: "failed",
  origin: "cli-observed",
  created_at: "2026-11-10T14:00:00Z",
  started_at: "2026-11-10T14:00:04Z",
  ended_at: "2026-11-10T14:23:10Z",
  workflow: { engine: "snakemake", engine_version: "9.27.1", location: "/g/demo-lab/pipelines/variant-calling", name: "variant-calling", version: null },
  profiles: [],
  failure: { kind: "task", detail: "Rule call_variants failed for sample C, region chr2 (exit 1)." },
  head: { session: null, node: "login1", alive: false, exit_code: 1, checked: true },
  task_counts: { succeeded: SMK_JOBS.filter((j) => j.state === "succeeded").length, failed: 1, not_scheduled: 2 },
  summary: { tasks: { done: SMK_JOBS.filter((j) => j.state === "succeeded").length, total: SMK_JOBS.length, failed: 1, cached: 0 }, last_failure: null, stage_mode: "quarters" },
};

/** A demo file's size, stable for its path: reads and alignments are large, reports small. */
function sizeOf(path: string): number {
  let h = 0;
  for (const c of path) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  const base = /\.(bam|cram)$/.test(path) ? 2.1e9 : /\.(fq|fastq)\.gz$/.test(path) ? 8.4e8 : /\.vcf\.gz$/.test(path) ? 3.2e6 : /\.(svg|html)$/.test(path) ? 1.8e5 : 4.2e4;
  return Math.round(base * (0.6 + (h % 80) / 100));
}

/** Made-up content for the first lines and the preview, by kind; null for binary files. */
function contentOf(path: string): string | null {
  const sample = /([A-Z]+\d+|S\d+)/.exec(path.split("/").pop() ?? "")?.[1] ?? "S1";
  if (/\.(fq|fastq)(\.gz)?$/.test(path))
    return Array.from({ length: 12 }, (_, i) => `@${sample}.${i + 1} 1:N:0:ACGTAC\nGATTACAGATTACACCGTAGGCTAACGGTTACAGGATTACCA\n+\nIIIIIIIIIHHHHHGGGGGFFFFEEEEDDDCCCBBBAAA@@\n`).join("").trimEnd();
  if (/\.vcf(\.gz)?$/.test(path))
    return ["##fileformat=VCFv4.2", "##source=bcftools", `#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t${sample}`, ...Array.from({ length: 20 }, (_, i) => `chr1\t${10234 + i * 917}\t.\tA\tG\t${(40 + i * 3.1).toFixed(1)}\tPASS\tDP=${30 + i}\tGT\t0/1`)].join("\n");
  if (/\.(bed)$/.test(path)) return Array.from({ length: 20 }, (_, i) => `chr${1 + (i % 3)}\t${i * 10000}\t${i * 10000 + 5000}\tgene_${i}`).join("\n");
  if (/\.(tsv|tab|sf)$/.test(path) || /quant/.test(path)) return ["Name\tLength\tTPM\tNumReads", ...Array.from({ length: 20 }, (_, i) => `ENST0000${4000 + i}\t${1200 + i * 37}\t${(i * 1.7).toFixed(2)}\t${i * 113}`)].join("\n");
  if (/\.json$/.test(path)) return JSON.stringify({ sample, reads: 1204331, passed: 1180022, gc: 0.48 }, null, 2);
  if (/\.svg$/.test(path))
    return `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="160" viewBox="0 0 320 160"><rect width="320" height="160" fill="#f8f9fa"/>${Array.from({ length: 16 }, (_, i) => `<rect x="${12 + i * 19}" y="${150 - (20 + ((i * 37) % 110))}" width="14" height="${20 + ((i * 37) % 110)}" fill="#4c6ef5"/>`).join("")}</svg>`;
  if (/\.(fa|fasta|txt|log)$/.test(path)) return `>chr1\n${"ACGT".repeat(30)}\n${"GGCA".repeat(30)}`;
  return null;
}

/** Made-up efficiency for a demo job, stable for its id (peak memory over the 8 GiB asked). */
function efficiencyOf(id: string, seconds: number) {
  let h = 0;
  for (const c of id) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  const peak = (2 + (h % 50) / 10) * 2 ** 30;
  return { cpu: (60 + (h % 35)) / 100 / 1.2, mem: peak / (8 * 2 ** 30), elapsed_s: seconds, peak_rss_bytes: peak, state: "available", source: "trace", reason: null };
}
