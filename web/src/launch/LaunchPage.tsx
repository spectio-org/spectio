import {
  Anchor,
  Button,
  Checkbox,
  Group,
  NativeSelect,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { Fragment, type ReactNode, Suspense, lazy, useEffect, useId, useRef, useState } from "react";
import {
  ApiError,
  type CatalogList,
  ENGINE_FILES,
  type Engine,
  type EnvironmentItem,
  type EnvironmentList,
  type FieldError,
  type Inspected,
  type LaunchTemplate,
  type ParamsFile,
  type Run,
  type TargetIn,
  type TargetInspected,
  getLaunchTemplate,
  getRun,
  inspect,
  inspectTarget,
  launch,
  listCatalog,
  listEnvironments,
} from "../api";
import { label as envLabel } from "../environments/fields";
import { Icon, groupIcon } from "../icons";
import { runName } from "../runs/RunState";
import { engineName, executorLabel, plural, shortId } from "../runs/stateWord";
import { useServer } from "../server";
import { EngineMark, PipelineMark, markFor } from "../shell/EngineMark";
import { FoldSection } from "../shell/FoldSection";
import { PageHead } from "../shell/PageHead";
import "./launch.css";
import { usePhone } from "../shell/layout";
import { CatalogPicker, SaveToCatalog } from "./CatalogPicker";
import { EngineButtons } from "./EngineButtons";
import { EnvironmentRow } from "./EnvironmentRow";
import { entryFiles, guessEngine, hasEntry } from "./guessEngine";
import { ConfigFileRow, type Draft, NO_DRAFT, RESOURCE_LABELS, ResourcesRow, draftFrom, keptAs, readResources, summaryLine } from "./RunExtras";
import { TryPipelines } from "./TryPipelines";
import { REGISTRY_NAME, TRY_MODULES, moduleInspected } from "./target";
import {
  type EffectiveDefault,
  type Field,
  type Row,
  type Section,
  type Values,
  REQUIRED,
  buildParams,
  checkValue,
  effectiveDefault,
  isChanged,
  own,
  schemaFields,
  shownValue,
  sourceHint,
  toYaml,
  valuesFrom,
} from "./schemaFields";
import { GRAPH_VIEW, useFeatures } from "../runs/graph/features";

// the Workflow map, with React Flow and dagre: a lazy chunk (issue #160)
const LaunchMap = lazy(() => import("../runs/graph/LaunchMap").then((m) => ({ default: m.LaunchMap })));

// The 0.0.1 launch form (P1 Task 19; ui-spec §4.6 note 2026-10-29; boards LiteLaunch and
// LiteLaunchSnakemake, of which 0.0.1 shows less, UX-227). Native inputs and buttons only, a label
// on every field; a 422 lands on its field through Mantine's error, which sets aria-invalid and
// aria-describedby. Each schema group is a section that folds, open when it has an issue or a
// changed value (UX-PAR-30); the params preview and the request come from one `buildParams`
// (UX-PAR-32).

const SHORT_NAME = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9_][A-Za-z0-9._-]{0,99}$/;
const SOURCES: Record<Inspected["schema_source"], string> = {
  "nextflow_schema.json": "form from nextflow_schema.json",
  "config.schema.yaml": "form from config.schema.yaml",
  inferred: "form inferred from config/config.yaml (its types are not checked)",
  none: "no parameter schema: add parameters as name and value",
};

type Errors = Record<string, string>; // by form key: location, revision, engine, name, profile, environment, resources(.cpus|.mem|.time), config_file, params.<key>, form

/** One line of "Before Launch" (ui-spec §4.6 layout note, FU-P3-86h): its words, and the form key
 * (location, engine, environment, params.<key>) of the field its link moves focus to. */
interface Reason {
  text: string;
  to?: string;
}

/** The id of a parameter's input: keys are data, so encoded (no space in an id). */
const paramId = (key: string) => `param-${encodeURIComponent(key)}`;

/** The element a reason's link focuses, or whose first control it focuses. */
function targetId(to: string): string {
  if (to === "location") return "launch-location";
  if (to === "engine") return "engine-buttons";
  if (to === "environment") return "launch-where-body";
  if (to === "rule") return "launch-rule";
  if (to === "version") return "launch-version";
  if (to === "config_file") return "launch-config-file";
  if (to === "main_script") return "launch-main-script";
  if (to.startsWith("resources.")) return { "resources.cpus": "res-cpus", "resources.mem": "res-mem" }[to] ?? "res-time-h";
  return paramId(to.slice("params.".length));
}

/** Where a 422 error of `POST /runs` or of inspect is shown (fields are dotted, inbox #86): a
 * param error lands on the field of the longest key that names it or a value inside it
 * (`params.ref.release` on `ref.release`, UX-PAR-31). */
function formKey(field: string, keys: string[]): string {
  const bare = field.replace(/^workflow\./, "");
  if (bare === "target.version") return "version";
  if (bare === "target.name" || bare === "rule") return "rule";
  if (["location", "revision", "engine", "main_script", "name", "environment", "config_file"].includes(bare)) return bare;
  // api §5.7: default_resources.cpus, .mem_mib, .time_min, or the whole (a Snakemake profile)
  if (bare.startsWith("default_resources")) {
    return { "default_resources.cpus": "resources.cpus", "default_resources.mem_mib": "resources.mem", "default_resources.time_min": "resources.time" }[bare] ?? "resources";
  }
  if (bare.startsWith("profiles")) return "profile";
  if (!bare.startsWith("params.")) return "form";
  const rest = bare.slice("params.".length);
  const key = keys
    .filter((k) => rest === k || rest.startsWith(`${k}.`) || rest.startsWith(`${k}[`))
    .sort((a, b) => b.length - a.length)[0];
  return key ? `params.${key}` : "form";
}

function toErrors(errors: FieldError[], keys: string[]): Errors {
  const found: Errors = {};
  for (const { field, message } of errors) {
    const key = formKey(field, keys);
    const text = key === "form" ? `${field}: ${message}` : message;
    found[key] = found[key] ? `${found[key]}; ${text}` : text;
  }
  return found;
}

/** The line under the Profile select: where the engine finds the profiles, and how it gets one. */
const PROFILE_HINTS: Record<Engine, string> = {
  nextflow: "From the pipeline's nextflow.config · passed as -profile",
  snakemake: "From the pipeline's profiles/ directory · passed as --workflow-profile",
};

/** The two cards of "What to run" (ui-spec §4.15): a pipeline of three steps, and one step alone. */
const MODES = [
  { single: false, title: "Whole pipeline", sub: "Every step of a Nextflow or Snakemake pipeline", icon: "pipeline" as const },
  { single: true, title: "One step", sub: "A Nextflow module, or one Snakemake rule and what it needs", icon: "step" as const },
] as const;

/** One step's kind: a Nextflow module or a Snakemake rule, each with its engine and page head. */
type Kind = "module" | "rule";
const KINDS: Record<Kind, { label: string; engine: Engine; title: string; sub: string }> = {
  module: { label: "Nextflow module", engine: "nextflow", title: "Launch one module", sub: "Run a single Nextflow module, outside any pipeline." },
  rule: { label: "Snakemake rule", engine: "snakemake", title: "Launch one rule", sub: "Run one Snakemake rule and only the jobs it needs." },
};

/** A rule's dry run (§4.15): counting, its jobs by rule, or why it failed. */
type Plan = { state: "counting" } | { state: "ok"; jobs: Record<string, number>; total: number } | { state: "failed"; error: string };

/** Copy to a new launch (ui-spec §4.4 run tools note): the run the form was prefilled from. */
interface Prefill {
  template: LaunchTemplate;
  /** "wgs-cohort-12 (7T9V1W)" */
  run: string;
  name: string;
  /** Top-level keys of the run's params that no field of the form takes. */
  left: string[];
}

/** A `code_loading` field as the form names it. */
const loadingLabel = (field: string) =>
  field === "workflow.location"
    ? "Pipeline"
    : field === "config_file"
      ? "Extra config file"
      : field.startsWith("params.")
        ? field.slice(7)
        : `engine option ${field.replace(/^engine\./, "")}`;

/** `recent`: the server's recent runs, for "Try a test pipeline" (null while they load: nothing
 * shown). `initialLocation`: a pipeline to fill in and load at once (/launch?location=).
 * `copyFrom`: a run to prefill the form from (/launch?from=, Copy to a new launch); `onClear`
 * drops it. */
export function LaunchPage({
  onLaunched,
  recent = null,
  initialLocation,
  copyFrom,
  onClear,
}: {
  onLaunched: (id: string) => void;
  recent?: Run[] | null;
  initialLocation?: string;
  copyFrom?: string;
  onClear?: () => void;
}) {
  const server = useServer();
  const phone = usePhone();
  const [location, setLocation] = useState("");
  const [revision, setRevision] = useState("");
  const [loaded, setLoaded] = useState<Inspected | null>(null);
  const graphOn = useFeatures().includes(GRAPH_VIEW);
  const [loading, setLoading] = useState(false);
  const [engine, setEngine] = useState<Engine | null>(null);
  // The Nextflow entry script chosen (#351); until then main.nf when the pipeline has it
  const [mainScript, setMainScript] = useState<string | null>(null);
  // Profile as the user set it; until then, the chosen environment's default profile (§4.8.1)
  const [picked, setPicked] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [values, setValues] = useState<Values>({});
  const [rows, setRows] = useState<Row[]>([]);
  const [errors, setErrors] = useState<Errors>({});
  const [sending, setSending] = useState(false);
  // Launch pressed while a field is wrong: empty required fields then say so on the field too
  const [tried, setTried] = useState(false);
  // The 201 answer's warnings (api §5.12), shown after Launch; the engine's own check has the last word
  const [launchedWarnings, setLaunchedWarnings] = useState<FieldError[]>([]);
  const [prefill, setPrefill] = useState<Prefill | null>(null);
  const [prefillError, setPrefillError] = useState<string | null>(null);
  const [envs, setEnvs] = useState<EnvironmentList | null>(null);
  const [envsFailed, setEnvsFailed] = useState(false);
  const [envName, setEnvName] = useState<string | null>(null);
  // The catalog (ui-spec §4.7.1): the entry chosen in the picker, and the one the loaded pipeline came from
  const [catalog, setCatalog] = useState<CatalogList | null>(null);
  const [catalogFailed, setCatalogFailed] = useState(false);
  const [entryName, setEntryName] = useState<string | null>(null);
  // only the name is kept, so an entry edited or deleted in Manage catalog is read afresh (CR-P3FU87E-01)
  const [fromName, setFromName] = useState<string | null>(null);
  // the params file inspected at Load: its report stays until the next Load or edit (CR-P3FU87E-02)
  const [paramsFile, setParamsFile] = useState<ParamsFile | null>(null);
  // The form key a "Before Launch" link is moving focus to: its sections open (FU-P3-86h)
  const [goTo, setGoTo] = useState<string | null>(null);
  // Resources and the extra config file (api §5.7, FU-P3-110d); the 503 of a file that could not be read
  const [resources, setResources] = useState<Draft>(NO_DRAFT);
  const [configFile, setConfigFile] = useState("");
  const [configDown, setConfigDown] = useState<string | null>(null);
  // What Launch would refuse of that file, asked of inspect before Launch (FU-P3-121); asked again
  // when the window comes back (a chmod in a terminal) and when Launch is pressed while it blocks;
  // kept with what it was asked for (pipeline, engine, path), so a change drops it (CR-P3FU121-02)
  const [configCheck, setConfigCheck] = useState<{ asked: string; found: Inspected["config_file"] } | null>(null);
  const [recheck, setRecheck] = useState(0);
  // A re-ask of the profile's values that failed (api §5.12, CR-06): one muted line says so; the
  // form keeps the previous answer, and Launch's own errors still say what is wrong
  const [profilesDown, setProfilesDown] = useState(false);
  const inFlight = useRef<AbortController | null>(null);
  // What to run (ui-spec §4.15, api §5.10): the whole pipeline, or one module or one rule when the
  // server has single targets on. A module loads as a form of its inputs; a Snakemake pipeline
  // lists its rules, and the chosen rule's dry run is previewed.
  const singleOffered = !!server?.features?.single_target;
  const [single, setSingle] = useState(false);
  const [kind, setKind] = useState<Kind>("module");
  const [version, setVersion] = useState("");
  const [pinned, setPinned] = useState<string | null>(null);
  const [module, setModule] = useState<Extract<TargetInspected, { kind: "module" }> | null>(null);
  const [rules, setRules] = useState<string[] | null>(null);
  const [rule, setRule] = useState("");
  const [plan, setPlan] = useState<Plan | null>(null);
  const planFlight = useRef<AbortController | null>(null);
  const revisionField = useRef<HTMLInputElement>(null);

  const loadEnvs = () =>
    listEnvironments().then(
      (list) => (setEnvs(list), setEnvsFailed(false)),
      () => setEnvsFailed(true),
    );
  const loadCatalog = () =>
    listCatalog().then(
      (list) => (setCatalog(list), setCatalogFailed(false)),
      () => setCatalogFailed(true),
    );
  useEffect(() => {
    document.title = "Launch a workflow · Spectio";
    void loadEnvs();
    void loadCatalog();
    return () => inFlight.current?.abort();
  }, []);
  // The chosen environment: the user's or Copy's, else the default (ui-spec §4.8.1)
  const offered = envs?.items.filter((e) => e.usable) ?? [];
  const chosen: EnvironmentItem | null =
    offered.find((e) => e.name === envName) ?? offered.find((e) => e.name === envs?.default) ?? offered[0] ?? null;
  const entry = catalog?.items.find((e) => e.name === entryName) ?? null;
  const fromEntry = catalog?.items.find((e) => e.name === fromName) ?? null;
  // Profile: the entry's, then the environment's, each when the pipeline has it (§4.7.1, §4.8.1)
  const wanted = chosen && engine ? chosen.profiles[engine] : null;
  const inPipeline = !!wanted && !!loaded?.profiles.includes(wanted);
  const fromCatalog = fromEntry?.profile ?? null;
  const catalogIn = !!fromCatalog && !!loaded?.profiles.includes(fromCatalog);
  const profile = picked ?? (catalogIn ? fromCatalog! : inPipeline ? wanted! : "");
  const profileNote =
    picked !== null || !loaded || catalogIn
      ? null
      : fromCatalog && wanted && !inPipeline
        ? `The catalog's profile ${fromCatalog} and the environment's profile ${wanted} are not in this pipeline: none selected`
        : fromCatalog
          ? `The catalog's profile ${fromCatalog} is not in this pipeline: ${inPipeline ? `the environment's profile ${wanted} is selected` : "none selected"}`
          : wanted && !inPipeline
            ? `The environment's profile ${wanted} is not in this pipeline: none selected`
            : null;

  const targeting = single;
  const oneModule = targeting && kind === "module";
  const moduleName = oneModule && REGISTRY_NAME.test(location.trim());
  const extras = { engine, profile, env: chosen };
  const res = readResources(resources, extras);
  // The Nextflow entry script (#351): offered when the pipeline has another one than main.nf, or
  // none is main.nf; required then, never guessed. main.nf itself is not sent.
  const scripts = loaded ? loaded.main_scripts : [];
  const hasMain = !!loaded?.engine_files.includes("main.nf");
  // a copied script the pipeline no longer lists is shown too, so the user sees it is gone
  const gone = mainScript !== null && !scripts.includes(mainScript);
  const entryChoice = !!loaded && !targeting && engine === "nextflow" && ((scripts.length > 0 && (scripts.length > 1 || !hasMain)) || gone);
  const entryScript = mainScript ?? (hasMain ? "main.nf" : "");
  const sentScript = entryChoice && entryScript && entryScript !== "main.nf" ? entryScript : null;

  const repo = location.trim() !== "" && !location.trim().startsWith("/");
  const github = SHORT_NAME.test(location.trim()) ? `https://github.com/${location.trim()}` : null;
  const skipped: string[] = [];
  // the form's shape follows the engine (guessed at load, then chosen): Snakemake maps become dotted
  // sections (CR-P3PARB-02). Values typed under the other shape stay, unsent, until the engine goes back.
  const rawSections = schemaFields(loaded?.schema ?? null, skipped, engine === "snakemake");
  // The effective defaults (api §5.12): each field's default becomes the sources' value at its
  // path, and the form names the source under the field. The form's `values` keep only what the
  // user typed, so a prefilled default is shown but not sent (§5.12).
  const defaultsMode = !!loaded?.defaults;
  const incomplete = defaultsMode && loaded!.defaults_complete === false;
  const effective: Record<string, EffectiveDefault> = {};
  if (defaultsMode) {
    for (const f of rawSections.flatMap((s) => s.fields)) {
      const found = effectiveDefault(f, loaded!.defaults);
      if (found) effective[f.key] = found;
    }
  }
  const sections = defaultsMode
    ? rawSections.map((s) => ({
        ...s,
        fields: s.fields.map((f) => (own(effective, f.key) ? { ...f, default: own(effective, f.key)!.value, source: own(effective, f.key)!.source } : f)),
      }))
    : rawSections;
  const fields = sections.flatMap((s) => s.fields);
  const keys = fields.map((f) => f.key);
  const hints: Record<string, string> = {};
  if (defaultsMode) for (const [key, found] of Object.entries(effective)) hints[key] = sourceHint(found.source, profile ? [profile] : []);
  const grouped = !!loaded?.schema && ("$defs" in loaded.schema || "definitions" in loaded.schema);
  // with the effective parameters, only the values the user typed are sent: a nested map is never
  // sent whole at its schema defaults, which would put back what the pipeline's config set (§5.12)
  const leaves = (engine === "snakemake" && configFile.trim() !== "") || defaultsMode;
  const changed = fields.filter((f) => isChanged(f, own(values, f.key))).length + rows.filter((r) => r.key.trim()).length;

  /** An edit of a resource or of the extra config file forgets the server's error on it. */
  const dropErrors = (prefix: string) => setErrors((old) => Object.fromEntries(Object.entries(old).filter(([k]) => !k.startsWith(prefix))));

  /** An edit of Pipeline or Revision cancels the inspect in flight and forgets the last one. */
  function edit(set: (v: string) => void, value: string) {
    inFlight.current?.abort();
    inFlight.current = null;
    set(value);
    setLoading(false);
    setLoaded(null);
    setEngine(null);
    setMainScript(null);
    setErrors({});
    setLaunchedWarnings([]);
    setEntryName(null); // the picker goes back to None, and the entry's prefill is forgotten
    setFromName(null);
    setParamsFile(null);
    planFlight.current?.abort();
    setModule(null);
    setRules(null);
    setRule("");
    setPlan(null);
    setPinned(null);
  }

  /** Whole pipeline or Single module / rule: the form starts again from Load. */
  function switchMode(to: boolean) {
    edit(() => setSingle(to), "");
  }

  /** Nextflow module or Snakemake rule: the field keeps its text, and the form starts again from Load. */
  function switchKind(to: Kind) {
    edit(setLocation, location);
    setKind(to);
  }

  /** Single target Load (§4.15): a registry module through `module view`; else the pipeline's
   * inspect, then its rules (Snakemake) or the module of its directory (Nextflow). */
  async function inspectSingle(where: string, rev: string | null, ver: string, want: Kind, signal: AbortSignal): Promise<Inspected> {
    const asModule = async (location: string, pipeline: Inspected | null) => {
      const answer = await inspectTarget({ engine: "nextflow", location, version: pipeline ? null : ver.trim() || null }, signal);
      if (answer.kind !== "module") throw new Error("not a module");
      setModule(answer);
      if (!pipeline && !ver.trim() && answer.version) {
        setVersion(answer.version);
        setPinned(`Pinned to ${answer.version}, the registry's current version`);
      }
      return moduleInspected(answer, location, pipeline);
    };
    if (want === "module" && REGISTRY_NAME.test(where)) return asModule(where, null);
    const pipeline = await inspect(where, rev, signal);
    if (want === "module") return asModule(pipeline.location, pipeline);
    const answer = await inspectTarget({ engine: "snakemake", location: where, revision: rev }, signal);
    setRules(answer.kind === "rule" ? answer.rules : []);
    return pipeline;
  }

  /** A rule chosen: its dry run, from an empty directory, says which jobs it needs (§4.15). */
  function chooseRule(to: string) {
    planFlight.current?.abort();
    setRule(to);
    setPlan(null);
    if (!to || !loaded) return;
    const controller = new AbortController();
    planFlight.current = controller;
    setPlan({ state: "counting" });
    inspectTarget({ engine: "snakemake", location: loaded.location, revision: loaded.revision, rule: to }, controller.signal)
      .then((answer) => {
        if (controller.signal.aborted) return;
        const found = answer.kind === "rule" ? answer : null;
        setPlan(found?.plan ? { state: "ok", ...found.plan } : { state: "failed", error: found?.error ?? "no plan" });
      })
      .catch((e: Error) => controller.signal.aborted || setPlan({ state: "failed", error: e.message }));
  }

  /** An entry chosen in the picker only fills the form; Load inspects it. None keeps the fields. */
  function choose(name: string | null) {
    const found = catalog?.items.find((e) => e.name === name);
    if (!found) {
      if (picked === null) setPicked(profile); // the profile shown stays
      setEntryName(null);
      return;
    }
    edit(setLocation, found.location);
    setRevision(found.revision ?? "");
    setEngine(found.engine); // the user's choice (UX-G2-07), over the guess of the loaded files
    setEntryName(found.name);
    setPicked(null);
    setValues({});
    setRows([]);
  }

  /** Clear and start empty. */
  function clear() {
    edit(setLocation, "");
    setRevision("");
    setPicked(null);
    setValues({});
    setRows([]);
    setResources(NO_DRAFT);
    setConfigFile("");
  }

  async function load(at = location, rev = revision, copy?: Omit<Prefill, "left">, wantSingle = single, ver = version, want = kind) {
    const where = at.trim();
    const isRepo = where !== "" && !where.startsWith("/");
    const isModule = wantSingle && want === "module" && REGISTRY_NAME.test(where);
    if (where === "") {
      setErrors({ location: "Give an absolute path or a repository." });
      return;
    }
    if (isRepo && !isModule && rev.trim() === "") {
      setErrors({ revision: "Give a tag, branch or commit." });
      return;
    }
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;
    setLoading(true);
    setErrors({});
    try {
      const from = !copy && entry?.location === where ? entry : null;
      const found = wantSingle
        ? await inspectSingle(where, isRepo && !isModule ? rev.trim() : null, ver, want, controller.signal)
        : await inspect(where, isRepo ? rev.trim() : null, controller.signal, from?.params_file);
      setLoaded(found);
      setTried(false);
      setProfilesDown(false); // a fresh Load answers for itself (CR-06)
      setFromName(from?.name ?? null);
      setParamsFile(from ? found.params_file : null);
      if (copy) {
        // the run's engine, profile and values, in the form's shape for that engine
        const { engine: was } = copy.template.workflow;
        const shape = schemaFields(found.schema, [], was === "snakemake").flatMap((s) => s.fields);
        const params = copy.template.params;
        const { values: filled, left } = shape.length ? valuesFrom(shape, params) : { values: {}, left: [] };
        setEngine(was);
        setMainScript(copy.template.workflow.main_script ?? null); // the copied run's entry script (#351)
        setPicked(copy.template.profiles[0] ?? ""); // the copied run's profile wins
        setEnvName(copy.template.environment);
        setValues(filled);
        setRows(shape.length ? [] : Object.entries(params).map(([key, v]) => ({ key, value: typeof v === "string" ? v : JSON.stringify(v) })));
        setResources(draftFrom(copy.template.default_resources));
        setConfigFile(copy.template.config_file ?? ""); // read again at this launch (api §5.7)
        setPrefill({ ...copy, left });
      } else {
        // one step's engine is its kind's; else the entry's engine and params file (§4.7.1); every
        // value the form does not place is listed. With the effective defaults (api §5.12) the
        // params file's values are defaults the form shows, not values it sends.
        const was = wantSingle ? KINDS[want].engine : (from?.engine ?? guessEngine(entryFiles(found)));
        const shape = schemaFields(found.schema, [], was === "snakemake").flatMap((s) => s.fields);
        const params = found.params_file?.values ?? {};
        setEngine(was);
        setMainScript(null);
        setPicked(null);
        setValues(shape.length && found.defaults === undefined ? valuesFrom(shape, params).values : {});
        setRows(shape.length ? [] : Object.entries(params).map(([key, v]) => ({ key, value: typeof v === "string" ? v : JSON.stringify(v) })));
      }
    } catch (error) {
      if (controller.signal.aborted) return; // an edit cancelled it: not an error
      const found: Errors =
        error instanceof ApiError && error.errors.length
          ? toErrors(error.errors, [])
          : { location: `Not loaded: ${(error as Error).message}` };
      // an entry whose pipeline is gone (UX-PRE-FU87-04): the picker keeps it
      const at = found.revision && !found.location ? "revision" : "location";
      if (entry?.location === where && !copy) found[at] = `${found[at] ?? ""} From your catalog entry ${entry.name}: edit it in Manage catalog.`.trim();
      setErrors(found);
    } finally {
      if (inFlight.current === controller) {
        inFlight.current = null;
        setLoading(false);
      }
    }
  }

  /** A pipeline picked (Try a test pipeline, /launch?location=): filled in, and loaded when it is a
   * directory; a repository waits for its revision. */
  function pick(at: string) {
    edit(setLocation, at);
    if (at.startsWith("/")) void load(at, "");
    else setTimeout(() => revisionField.current?.focus(), 0);
  }
  useEffect(() => {
    if (initialLocation) pick(initialLocation);
  }, [initialLocation]);
  useEffect(() => {
    if (!copyFrom) return;
    const controller = new AbortController();
    Promise.all([getLaunchTemplate(copyFrom, controller.signal), getRun(copyFrom, controller.signal)])
      .then(([template, run]) => {
        const { location: at, revision: rev } = template.workflow;
        const target = template.target ?? null; // the copy keeps a module or rule target; a file target opens with no rule chosen (§4.15)
        setLocation(at);
        setRevision(rev ?? "");
        const want: Kind = target && target.kind !== "module" ? "rule" : "module";
        setSingle(!!target);
        setKind(want);
        setVersion(target?.version ?? "");
        const copy = { template, run: `${runName(run)} (${shortId(run.id)})`, name: runName(run) };
        void load(at, rev ?? "", copy, !!target, target?.version ?? "", want).then(() => target?.kind === "rule" && setRule(target.name ?? ""));
      })
      .catch((e: Error) => controller.signal.aborted || setPrefillError(e.message));
    return () => controller.abort();
  }, [copyFrom]);

  const configAsked = loaded && engine && configFile.trim() ? JSON.stringify([loaded.location, loaded.revision, engine, configFile.trim()]) : null;
  /** The pre-check of the extra config file; a failed one shows nothing: Launch's own read stays the check. */
  function checkConfig(signal?: AbortSignal) {
    if (!loaded || !engine || !configAsked) return Promise.resolve(null);
    const asked = configAsked;
    return inspect(loaded.location, loaded.revision, signal, null, { path: configFile.trim(), engine }).then(
      (found) => {
        const check = { asked, found: found.config_file ?? null };
        setConfigCheck(check);
        return check;
      },
      () => (signal?.aborted || setConfigCheck(null), null),
    );
  }
  useEffect(() => {
    if (!configAsked) return setConfigCheck(null);
    const controller = new AbortController();
    const timer = setTimeout(() => void checkConfig(controller.signal), 300);
    return () => (clearTimeout(timer), controller.abort());
  }, [configAsked, recheck]);
  useEffect(() => {
    const again = () => setRecheck((n) => n + 1);
    window.addEventListener("focus", again);
    return () => window.removeEventListener("focus", again);
  }, []);
  const configRefused = configCheck && configCheck.asked === configAsked ? (configCheck.found?.error ?? null) : null;

  /** Another profile chosen (api §5.12): inspect asks again with `profiles=`, for that profile's
   * effective defaults; the user's values stay, the shown defaults follow the answer. A failed or
   * cancelled re-ask keeps the last answer — Launch's own errors still say what is wrong. */
  function reaskProfiles(to: string) {
    if (!loaded || loaded.defaults === undefined) return; // a server before §5.12: Load asks again
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;
    inspect(loaded.location, loaded.revision, controller.signal, paramsFile?.path ?? null, undefined, to || null).then(
      (found) => {
        if (controller.signal.aborted) return;
        if (inFlight.current === controller) inFlight.current = null;
        setLoaded(found);
        setParamsFile(found.params_file ?? null);
        setProfilesDown(false);
      },
      () => {
        if (!controller.signal.aborted) setProfilesDown(true); // CR-06: the form keeps the previous answer
      },
    );
  }

  /** Every reason Launch waits, in order (ui-spec §4.6): the list of "Before Launch". */
  function reasons(): Reason[] {
    if (loading) return [{ text: "Wait for the pipeline to load", to: "location" }];
    if (!loaded) return [{ text: "Load a pipeline first", to: "location" }];
    if (entryFiles(loaded).length === 0) {
      return [{ text: "No main.nf or Snakefile in this directory: check the path", to: "location" }];
    }
    const found: Reason[] = [];
    if (!engine) found.push({ text: "Choose the engine", to: "engine" });
    if (!chosen && !envsFailed) found.push({ text: "Choose where it runs", to: "environment" });
    if (engine && !hasEntry(engine, entryFiles(loaded))) {
      const other = engineName(engine === "nextflow" ? "snakemake" : "nextflow");
      const files = ENGINE_FILES[engine].join(" or ");
      // in One step the engine follows the kind of step, so there is no engine button to press
      if (targeting) found.push({ text: `No ${files} in this directory: check the path`, to: "location" });
      else found.push({ text: `No ${files} in this directory: press ${other} or check the path`, to: "engine" });
    }
    for (const [to, wrong] of Object.entries(res.errors)) {
      found.push({ text: `Fix ${RESOURCE_LABELS[to as keyof typeof RESOURCE_LABELS]}: ${wrong.brief}`, to });
    }
    if (entryChoice && !entryScript) found.push({ text: "Choose the entry script", to: "main_script" });
    if (configRefused) found.push({ text: `Fix Extra config file: ${configRefused}`, to: "config_file" });
    for (const field of fields) {
      const wrong = checkValue(field, defaultsMode ? shownValue(field, own(values, field.key)) : own(values, field.key));
      const to = `params.${field.key}`;
      if (wrong === REQUIRED) {
        // api §5.12: while the sources are not complete, a required field no source fills is a
        // warning below, not a blocker: the engine's own check has the last word
        if (incomplete) continue;
        found.push({ text: `Fill the required field: ${field.key}`, to });
      } else if (wrong) found.push({ text: `Fix ${field.key}: ${wrong}`, to });
    }
    if (targeting && engine === "snakemake" && !rule) found.push({ text: "Choose a rule", to: "rule" });
    if (targeting && module?.source === "registry" && !version.trim()) found.push({ text: "Give the module's version", to: "version" });
    if (sending) found.push({ text: "Launching…" });
    return found;
  }

  /** A reason's link: moves focus to its field and scrolls it into view; a field in a folded
   * section is not rendered yet, so the sections open and it is tried again on the next frames
   * (inbox #146 item 11). */
  function focusField(to: string, frames = 10) {
    const at = document.getElementById(targetId(to));
    const control = at?.matches("input, select, textarea, button") ? at : at?.querySelector<HTMLElement>("input, select, textarea, button");
    if (control) {
      control.focus();
      control.scrollIntoView?.({ block: "center" });
      return setGoTo(null);
    }
    setGoTo(frames > 0 ? to : null);
    if (frames > 0) requestAnimationFrame(() => focusField(to, frames - 1));
  }

  async function submit() {
    // a refusal of the pre-check may be stale (a chmod since): asked again, and awaited, before
    // deciding, so the click is not dropped (CR-P3FU121-01)
    const others = reasons().filter((r) => !(configRefused && r.to === "config_file"));
    if (others.length || !loaded || !engine) return setTried(true);
    const params = buildParams(fields, values, rows, leaves);
    const path = oneModule ? "" : configFile.trim(); // none for a module (api §5.10)
    const target: TargetIn | null = !targeting
      ? null
      : module
        ? { kind: "module", version: module.source === "registry" ? version.trim() : module.version }
        : { kind: "rule", name: rule };
    setSending(true);
    if (configRefused && (await checkConfig())?.found?.error) {
      setSending(false);
      return setTried(true);
    }
    setErrors({});
    setConfigDown(null);
    try {
      const run = await launch({
        workflow: { location: loaded.location, revision: loaded.revision, engine, ...(sentScript ? { main_script: sentScript } : {}) },
        ...(name.trim() ? { name: name.trim() } : {}),
        profiles: profile ? [profile] : [],
        ...(chosen ? { environment: chosen.name } : {}),
        params,
        ...(target ? { target } : {}),
        ...(Object.keys(res.sent).length ? { default_resources: res.sent } : {}),
        ...(path ? { config_file: path } : {}),
      });
      onLaunched(run.id);
      setLaunchedWarnings(run.warnings ?? []);
    } catch (error) {
      const fileDown = /^the config file cannot be read: /;
      if (path && error instanceof ApiError && error.status === 503 && fileDown.test(error.message)) {
        // a timeout or an I/O error of the read, not choose()'s own 503 (CR-P3FU110D-01): its reason
        // follows the server's own words (api §5.7)
        setConfigDown(error.message.replace(fileDown, "").replace(/\.$/, ""));
        return;
      }
      const found =
        error instanceof ApiError && error.errors.length ? toErrors(error.errors, keys) : { form: `Not launched: ${(error as Error).message}` };
      setErrors(found);
      if (found.config_file) focusField("config_file");
    } finally {
      setSending(false);
    }
  }

  const copiedOutdir = prefill?.template.params.outdir;
  const notes: Record<string, string> =
    prefill && typeof copiedOutdir === "string" && own(values, "outdir") === copiedOutdir
      ? { outdir: `Warning: same as ${prefill.name}. Change it to keep the two runs' results apart.` }
      : {};
  const missing = reasons();
  const warnings: Reason[] = notes.outdir && prefill ? [{ text: `Warning, not a blocker: outdir is the same as ${prefill.name}`, to: "params.outdir" }] : [];
  // what in the params file, or the file itself, loads code (SEC-PRE-FU87-01): warnings, not blockers;
  // a file's value only while Launch sends it as read, not one left out or changed (SEC-P3FU87E-02)
  let sent: Record<string, unknown> = {};
  try {
    sent = buildParams(fields, values, rows, leaves);
  } catch {
    // a JSON field still being typed: Before Launch already lists it as not valid JSON
  }
  for (const c of paramsFile?.code_loading ?? []) {
    const others = c.writable_by_others ? " · writable by others" : "";
    if (c.field === "params_file") {
      warnings.push({ text: `Warning, not a blocker: ${paramsFile!.path} loads code or configuration${others}` });
    } else if (c.field.startsWith("params.")) {
      if (own(sent, c.field.slice(7)) === c.value) warnings.push({ text: `Warning, not a blocker: ${paramsFile!.path} sets ${c.field.slice(7)}: ${c.value}${others}` });
    } else warnings.push({ text: `Warning, not a blocker: ${loadingLabel(c.field)} ${c.value} loads code or configuration${others}` });
  }
  // api §5.12: a required field no source fills, while the sources are not complete: a warning in
  // Before Launch, and Launch stays enabled — the engine's own check has the last word
  if (incomplete) {
    for (const field of fields) {
      if (field.required && checkValue(field, shownValue(field, own(values, field.key))) === REQUIRED) {
        warnings.push({
          text: `Warning, not a blocker: the required field ${field.key} has no value; the engine's own check has the last word`,
          to: `params.${field.key}`,
        });
      }
    }
  }
  const unplaced = paramsFile?.values && fields.length ? valuesFrom(fields, paramsFile.values).left : [];
  const placed = paramsFile?.values ? Object.keys(paramsFile.values).length - unplaced.length : 0;
  const why = missing[0]?.text ?? null;
  // The pinned bar on the phone says what Launch sends (UX-PAR-34).
  const summary =
    phone && loaded && engine && !why
      ? [
          `${loaded.name}${loaded.version ? ` ${loaded.version}` : ""}`,
          engineName(engine),
          profile,
          chosen && (chosen.label ?? chosen.name),
          `${plural(changed, "value", "values")} changed`,
        ]
          .filter(Boolean)
          .join(" · ")
      : null;
  // One Launch (ui-spec §12.4, UI-13): at the right of the page head on a desktop, in the pinned bar
  // on the phone, described by the "Before Launch" list.
  const launchButton = (
    <Button
      type="button"
      className="launch-button"
      onClick={submit}
      aria-disabled={why ? true : undefined}
      data-disabled={why ? true : undefined}
      aria-describedby={summary ? "launch-missing launch-reason" : "launch-missing"}
      leftSection={<Icon name="runs" size="button" />}
    >
      {sending ? "Launching…" : !targeting ? "Launch" : kind === "module" ? "Launch module" : `Launch ${rule || "rule"}`}
    </Button>
  );
  /** A refused launch: in the phone's pinned bar, under Before Launch on the desktop. */
  const formError = errors.form && (
    <Text size="sm" c="var(--sp-state-failed-fg)" role="alert" mt={4}>
      {errors.form}
    </Text>
  );
  const local = server?.executor === "local";
  const headLine = server ? (local ? `a process on ${server.node}` : `a tmux session on ${server.node}`) : "…";
  const runDirectory = server ? `${server.runs_root}/<run ID>` : "…";
  /** The Tasks row reads the chosen environment, never `GET /version` (ui-spec §4.8.1). */
  const tasksLine = () => {
    const by = engine ? engineName(engine) : "the engine";
    if (!chosen) return envsFailed ? `by ${by}, in the server's default environment` : "…";
    const fromProfile = engine === "snakemake" && profile;
    if (chosen.executor === "slurm") {
      const how = fromProfile
        ? `resources and partition from the profile ${profile} (this environment's are not passed)`
        : chosen.slurm?.partition && `partition ${chosen.slurm.partition}`;
      return [`sent to SLURM by ${by}`, how].filter(Boolean).join(" · ");
    }
    const how = fromProfile ? "concurrency from the profile" : chosen.local?.cpus && `at most ${chosen.local.cpus} CPUs`;
    return [`run on ${server?.node ?? "the server"} by ${by}`, how].filter(Boolean).join(" · ");
  };
  const found = loaded ? entryFiles(loaded) : [];
  const guessed = loaded && guessEngine(found);
  const entryEngine = (fromEntry ?? entry)?.engine;
  const engineNote = engine && engine === entryEngine && (!loaded || hasEntry(engine, found))
    ? `${engineName(engine)}, from the catalog entry`
    : !loaded
    ? "Load the pipeline to guess the engine"
    : found.length === 0
      ? "No main.nf or Snakefile found"
      : !guessed
        ? `No guess: ${found.join(" and ")} found · choose the engine`
        : engine && !hasEntry(engine, found)
          ? `${ENGINE_FILES[engine].join(" or ")} not found: Launch will refuse. Guessed: ${engineName(guessed)}`
          : `Guessed from ${found.join(", ")} · change it if the guess is wrong`;

  return (
    <Stack className="launch-page" gap="xl">
      <PageHead
        section="launch"
        title={targeting ? KINDS[kind].title : "Launch a workflow"}
        sub={targeting ? KINDS[kind].sub : "A directory or a Git repository: Spectio guesses the engine and builds the form from its schema."}
        phoneTitle="title"
        phonePrimary="none"
        primary={
          <span className="launch-head">
            {/* a visual copy of the first reason of "Before Launch", which describes both buttons */}
            {why && (
              <span className="launch-head-reason" aria-hidden="true">
                {why}
              </span>
            )}
            {launchButton}
          </span>
        }
      />
      {prefillError && (
        <Text c="var(--sp-state-failed-fg)" role="alert">
          Not prefilled: {prefillError}
        </Text>
      )}
      {prefill && <PrefillBanner prefill={prefill} onClear={onClear} />}
      {configDown !== null && (
        <div role="alert" className="launch-banner">
          <Icon name="alert" />
          <span className="sp-grow">{`The extra config file could not be read: ${configDown}. Nothing was started and your values are kept.`}</span>
          <Button variant="default" onClick={submit}>
            Launch again
          </Button>
        </div>
      )}
      {launchedWarnings.length > 0 && (
        <div role="status" aria-label="Launched with warnings" className="launch-banner">
          <Icon name="alert" />
          <div className="sp-grow">
            <p>Launched with warnings; the engine's own check has the last word:</p>
            <ul>
              {launchedWarnings.map((w) => (
                <li key={`${w.field}:${w.message}`}>{`${w.field}: ${w.message}`}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
      <div className="launch-grid">
        <Stack gap="lg">
          {singleOffered && (
            <div className="launch-what" role="radiogroup" aria-label="What to run">
              {MODES.map((m, i) => (
                <label key={m.title} className="launch-mode">
                  <span className="launch-mode-icon">
                    <Icon name={m.icon} size="tile" />
                  </span>
                  <span className="sp-grow">
                    <span id={`launch-mode-${i}`} className="launch-mode-title">
                      {m.title}
                    </span>
                    <span id={`launch-mode-${i}-sub`} className="launch-mode-sub">
                      {m.sub}
                    </span>
                  </span>
                  <input
                    type="radio"
                    name="launch-what"
                    aria-labelledby={`launch-mode-${i}`}
                    aria-describedby={`launch-mode-${i}-sub`}
                    checked={single === m.single}
                    onChange={() => switchMode(m.single)}
                  />
                </label>
              ))}
            </div>
          )}
          <FoldSection
            id="launch-pipeline"
            icon="route"
            title={targeting ? (kind === "module" ? "Module" : "Rule") : "Pipeline"}
            card
            reveal={goTo === "location" || goTo === "engine" || goTo === "main_script" || goTo === "rule"}
          >
            {targeting && (
              <div className="launch-seg" role="radiogroup" aria-label="Kind of step">
                {(Object.keys(KINDS) as Kind[]).map((k) => (
                  <label key={k}>
                    <input type="radio" name="launch-kind" className="sp-sr" checked={kind === k} onChange={() => switchKind(k)} />
                    <EngineMark engine={KINDS[k].engine} size={16} named />
                    {KINDS[k].label}
                  </label>
                ))}
              </div>
            )}
            {!targeting && <CatalogPicker data={catalog} failed={catalogFailed} onRetry={loadCatalog} chosen={entry} onChoose={choose} onClear={clear}>
              {paramsFile && (
                <p className="sp-muted" aria-live="polite">
                  {paramsFile.error
                    ? `${paramsFile.path} could not be read: ${paramsFile.error}`
                    : [
                        `${plural(placed, "value", "values")} of ${paramsFile.path} ${placed === 1 ? "fills" : "fill"} the form${defaultsMode ? ", as its effective defaults (api §5.12)" : " and read changed"}.`,
                        unplaced.length > 0 &&
                          `${plural(unplaced.length, "value", "values")} of ${paramsFile.path} ${unplaced.length === 1 ? "has" : "have"} no field in this form, and ${unplaced.length === 1 ? "is" : "are"} not sent: ${unplaced.join(", ")}`,
                      ]
                        .filter(Boolean)
                        .join(" ")}
                </p>
              )}
            </CatalogPicker>}
            {!targeting && <TryPipelines runs={recent} onPick={pick} saved={catalog?.items.filter((e) => e.revision === null).map((e) => e.location)} />}
            <Group align="flex-start" gap="sm" wrap="wrap">
              <TextInput
                style={{ flex: "999 1 280px" }}
                id="launch-location"
                label={!targeting ? "Pipeline" : kind === "module" ? "Module" : "Snakemake pipeline"}
                inputWrapperOrder={["label", "input", "description", "error"]}
                value={location}
                onChange={(e) => edit(setLocation, e.currentTarget.value)}
                error={errors.location}
                description={
                  targeting ? (
                    kind === "module" ? (
                      "A registry module such as nf-core/fastqc, or the absolute path of a module directory."
                    ) : (
                      "An absolute path or a Git repository; Load lists its rules."
                    )
                  ) : (
                  <>
                    An absolute path your account can read, a GitHub or nf-core name such as
                    nf-core/rnaseq, or an https:// or ssh URL.
                    {github && (
                      <>
                        <br />
                        <span>Read as GitHub: {github}</span>
                      </>
                    )}
                  </>
                  )
                }
                spellCheck={false}
                autoComplete="off"
              />
              {moduleName && (
                <TextInput
                  style={{ flex: "1 1 220px", maxWidth: 260 }}
                  id="launch-version"
                  label="Version"
                  inputWrapperOrder={["label", "input", "description", "error"]}
                  value={version}
                  onChange={(e) => edit(setVersion, e.currentTarget.value)}
                  error={errors.version}
                  description={pinned ?? "A pinned version; left empty, Load pins the registry's current one."}
                  spellCheck={false}
                  autoComplete="off"
                />
              )}
              {repo && !moduleName && (
                <TextInput
                  style={{ flex: "1 1 220px", maxWidth: 260 }}
                  ref={revisionField}
                  label="Revision"
                  inputWrapperOrder={["label", "input", "description", "error"]}
                  withAsterisk
                  required
                  value={revision}
                  onChange={(e) => edit(setRevision, e.currentTarget.value)}
                  error={errors.revision}
                  description="Tag, branch or commit; required for a Git repository."
                  spellCheck={false}
                  autoComplete="off"
                />
              )}
              <Button
                type="button"
                variant="default"
                mt={24}
                onClick={() => load()}
                aria-busy={loading || undefined}
              >
                {loading ? (repo ? "Fetching…" : "Loading…") : "Load"}
              </Button>
            </Group>
            {oneModule && (
              <div className="launch-try" role="group" aria-labelledby="launch-try-modules">
                <span id="launch-try-modules" className="launch-try-label">
                  Try:
                </span>
                {TRY_MODULES.map((m) => (
                  <button key={m} type="button" className="launch-chip" aria-label={`Try ${m}`} onClick={() => edit(setLocation, m)}>
                    {m}
                  </button>
                ))}
              </div>
            )}
            {loaded && (
              <Paper bg="var(--sp-surface-subtle)" p="sm" mt="sm" className="launch-loaded" data-loaded>
                <span className="launch-loaded-mark">
                  {markFor(guessed, loaded.name) ? (
                    <PipelineMark engine={guessed} name={loaded.name} size={24} />
                  ) : (
                    <Icon name="folder" size="tile" />
                  )}
                </span>
                <div className="sp-grow">
                  <Text fw={600}>
                    {loaded.name}
                    {loaded.version ? ` ${loaded.version}` : ""}
                  </Text>
                  {module ? (
                    <>
                      {module.description && <Text size="sm">{module.description}</Text>}
                      <div className="launch-chips">
                        <span className="launch-chip" data-tone="accent">
                          {module.source === "registry" ? "from the registry" : "local"}
                        </span>
                        {loaded.engine_versions.nextflow && <span className="launch-chip">{`Nextflow ${loaded.engine_versions.nextflow}`}</span>}
                        {module.source === "registry" && <span className="launch-chip">checksum: after install</span>}
                      </div>
                    </>
                  ) : (
                    <Text size="sm" c="dimmed">
                      {loaded.revision ? `A Git repository at ${loaded.revision}` : "A directory on this machine"}
                      {entryFiles(loaded).length ? ` · ${entryFiles(loaded).join(", ")} found` : ""}
                      {` · ${SOURCES[loaded.schema_source]}`}
                    </Text>
                  )}
                </div>
                <span className="launch-loaded-status">
                  <Icon name="check" />
                  <span>Loaded</span>
                </span>
                {!module && <SaveToCatalog
                  data={catalog}
                  failed={catalogFailed}
                  entry={fromEntry}
                  pipeline={loaded.name}
                  draft={{ engine: engine ?? "nextflow", location: loaded.location, revision: loaded.revision ?? "", profile, params_file: "" }}
                  onSaved={(item) => void loadCatalog().then(() => (setEntryName(item.name), setFromName(item.name)))}
                />}
              </Paper>
            )}
            {targeting && rules !== null && (
              <Stack gap="xs" mt="sm">
                <Text size="sm" fw={500}>
                  <span id="launch-rule-label">Rule</span>
                  <span className="launch-quiet">{` · ${plural(rules.length, "rule", "rules")}; the jobs the rule needs run with it`}</span>
                </Text>
                {/* one toggle button per rule, a radio each (CLAUDE.md: native buttons, named by the rule) */}
                <div
                  id="launch-rule"
                  className="launch-rules"
                  role="radiogroup"
                  aria-labelledby="launch-rule-label"
                  aria-describedby={errors.rule ? "launch-rule-error" : undefined}
                >
                  {rules.map((r) => {
                    const target = r === rule;
                    const needed = !target && plan?.state === "ok" && Object.hasOwn(plan.jobs, r);
                    return (
                      <button key={r} type="button" role="radio" aria-checked={target} data-needed={needed || undefined} className="launch-rule" onClick={() => chooseRule(r)}>
                        <span>{r}</span>
                        {(target || needed) && (
                          <>
                            {" "}
                            <small>{target ? "target" : "needed"}</small>
                          </>
                        )}
                      </button>
                    );
                  })}
                </div>
                {errors.rule && (
                  <Text id="launch-rule-error" size="sm" c="var(--sp-state-failed-fg)" role="alert">
                    {errors.rule}
                  </Text>
                )}
                {plan && (
                  <div role="status" aria-labelledby="launch-plan-title" className="launch-plan">
                    <h3 id="launch-plan-title" className="launch-plan-title">
                      What will run
                      {plan.state === "ok" && <span className="launch-quiet">{` · dry run, ${plural(plan.total, "job", "jobs")}`}</span>}
                    </h3>
                    {plan.state === "counting" && <p>Counting the jobs…</p>}
                    {plan.state === "failed" && <p>{`The dry run failed: ${plan.error}`}</p>}
                    {plan.state === "ok" && (
                      <>
                        <ol className="launch-plan-steps">
                          {Object.entries(plan.jobs).map(([r, n]) => (
                            <li key={r}>
                              <span className="launch-plan-node" data-target={r === rule || undefined}>
                                <span className="sp-mono">{r}</span>
                                <span>{`${plural(n, "job", "jobs")}${r === rule ? " · target" : ""}`}</span>
                              </span>
                            </li>
                          ))}
                        </ol>
                        {rules.some((r) => !Object.hasOwn(plan.jobs, r)) && (
                          <p className="launch-chips">
                            Not run:
                            {rules
                              .filter((r) => !Object.hasOwn(plan.jobs, r))
                              .map((r) => (
                                <Fragment key={r}>
                                  {" "}
                                  <span className="launch-chip">{r}</span>
                                </Fragment>
                              ))}
                          </p>
                        )}
                        <p className="sp-muted">The rule and the jobs it needs, counted from an empty directory</p>
                      </>
                    )}
                  </div>
                )}
                {rule && <span className="sp-mono">snakemake … {rule}</span>}
              </Stack>
            )}
            <Stack gap="md" mt="md">
              {!targeting && (
                <EngineButtons
                  value={engine}
                  onChange={(e) => setEngine(e)}
                  note={engineNote}
                  error={errors.engine}
                />
              )}
              {entryChoice && (
                <NativeSelect
                  id="launch-main-script"
                  label="Entry script"
                  inputWrapperOrder={["label", "input", "description", "error"]}
                  required={!hasMain}
                  withAsterisk={!hasMain}
                  value={entryScript}
                  onChange={(e) => setMainScript(e.currentTarget.value || null)}
                  data={[
                    ...(hasMain ? [] : [{ value: "", label: "(choose one)" }]),
                    ...scripts,
                    // a copied entry script this pipeline no longer lists stays visible, since Launch sends it
                    ...(entryScript && !scripts.includes(entryScript) ? [{ value: entryScript, label: `${entryScript} (not found)` }] : []),
                  ]}
                  description={`The Nextflow script the run starts from · run by its path${hasMain ? "; main.nf when left as is" : ""}`}
                  error={errors.main_script}
                />
              )}
              <SimpleGrid cols={{ base: 1, sm: 2 }}>
                <NativeSelect
                  label="Profile"
                  inputWrapperOrder={["label", "input", "description", "error"]}
                  value={profile}
                  onChange={(e) => {
                    setPicked(e.currentTarget.value);
                    reaskProfiles(e.currentTarget.value);
                  }}
                  data={[
                    { value: "", label: "(none)" },
                    ...(loaded?.profiles ?? []),
                    // a copied profile this pipeline does not list stays visible, since Launch sends it
                    ...(profile && !loaded?.profiles.includes(profile) ? [{ value: profile, label: `${profile} (not in this pipeline)` }] : []),
                  ]}
                  description={
                    <>
                      {engine ? PROFILE_HINTS[engine] : "From the pipeline's own configuration; passed to the engine as its profile."}
                      {profileNote && (
                        <>
                          <br />
                          <span>{profileNote}</span>
                        </>
                      )}
                      {profilesDown && (
                        <>
                          <br />
                          <span>Could not read the profile's values: the form shows the previous ones</span>
                        </>
                      )}
                    </>
                  }
                  error={errors.profile}
                />
                <TextInput
                  label="Run name (optional)"
                  inputWrapperOrder={["label", "input", "description", "error"]}
                  value={name}
                  onChange={(e) => setName(e.currentTarget.value)}
                  description="Left empty, Spectio names the run after the pipeline."
                  error={errors.name}
                  autoComplete="off"
                />
              </SimpleGrid>
            </Stack>
          </FoldSection>
          <FoldSection
            id="launch-where"
            icon="server"
            title="Where it runs"
            card
            reveal={goTo === "environment" || goTo === "config_file" || !!goTo?.startsWith("resources")}
          >
            <EnvironmentRow
              list={envs}
              failed={envsFailed}
              chosen={chosen}
              onChoose={setEnvName}
              onRetry={loadEnvs}
              onCreated={(item) => void loadEnvs().then(() => setEnvName(item.name))}
              error={errors.environment}
            />
            <ResourcesRow
              draft={resources}
              onChange={(d) => {
                setResources(d);
                dropErrors("resources");
              }}
              c={extras}
              errors={errors}
              reveal={goTo?.startsWith("resources") ? "link" : Object.keys(errors).some((k) => k.startsWith("resources"))}
            />
            {/* a module run takes no extra config file: its roots are a pipeline's (api §5.10) */}
            {!oneModule && (
              <ConfigFileRow
                path={configFile}
                onChange={(p) => {
                  setConfigFile(p);
                  dropErrors("config_file");
                }}
                engine={engine}
                error={errors.config_file ?? configRefused ?? undefined}
                reading={sending}
                node={server?.node ?? "the server"}
                reveal={goTo === "config_file" ? "link" : !!errors.config_file}
              />
            )}
            <dl className="facts">
              <dt>Engine head</dt>
              <dd>
                {engine ? (
                  <span className="launch-engine">
                    <EngineMark engine={engine} size={16} named />
                    {`${engineName(engine)} ${loaded?.engine_versions[engine] ?? "(version not found)"}`}
                    {server && `, as ${headLine}`}
                  </span>
                ) : (
                  "Not chosen yet"
                )}
              </dd>
              <dt>Tasks</dt>
              <dd>{tasksLine()}</dd>
              <dt>Run directory</dt>
              <dd>{runDirectory}</dd>
            </dl>
            <Text size="xs" c="dimmed" mt="sm">
              The login node and the run directory are fixed for this server.
            </Text>
          </FoldSection>
          {loaded && (
            <FoldSection
              id="launch-params"
              icon="sliders"
              title={module ? "Module inputs" : "Parameters"}
              status={module ? `${fields.filter((f) => f.required).length} required` : undefined}
              card
              reveal={!!goTo?.startsWith("params.")}
            >
              {sections.length > 1 && (
                <Text size="sm" c="dimmed" mb="sm">
                  {`One section per ${grouped ? "schema group" : "map of the config, its keys dotted"} · ${changed === 1 ? "1 value differs from its default" : `${changed} values differ from their defaults`}`}
                </Text>
              )}
              {skipped.length > 0 && (
                <Text size="sm" c="dimmed" mb="sm">
                  {`Not in the form: ${skipped.join(", ")}. These keys are unsafe or repeat another key's dotted name; set them in the pipeline's own config.`}
                </Text>
              )}
              <Stack gap="sm">
                {sections.length === 1 && (
                  <ParamRows
                    fields={sections[0].fields}
                    notes={notes}
                    hints={hints}
                    values={values}
                    errors={errors}
                    tried={tried}
                    prefill={defaultsMode}
                    incomplete={incomplete}
                    onChange={(key, v) => setValues((old) => ({ ...old, [key]: v }))}
                  />
                )}
                {sections.length > 1 && sections.map((section, i) => (
                  <ParamGroup
                    key={`${loaded.location}:${i}`}
                    id={`params-g${i}`}
                    section={section}
                    reveal={section.fields.some((f) => goTo === `params.${f.key}`)}
                    notes={notes}
                    hints={hints}
                    values={values}
                    errors={errors}
                    tried={tried}
                    prefill={defaultsMode}
                    incomplete={incomplete}
                    onChange={(key, v) => setValues((old) => ({ ...old, [key]: v }))}
                  />
                ))}
              </Stack>
              {sections.length === 0 && <KeyValueRows rows={rows} onChange={setRows} />}
            </FoldSection>
          )}
          {loaded && graphOn && (
            <FoldSection id="launch-map" icon="route" title="Workflow map" defaultOpen={false}>
              <Suspense fallback={<p className="sp-muted">Loading the map…</p>}>
                <LaunchMap location={loaded.location} revision={loaded.revision} name={loaded.name} mainScript={sentScript} />
              </Suspense>
            </FoldSection>
          )}
        </Stack>
        <Stack className="launch-aside" gap="lg" component="aside" aria-label="Launch">
          <section className="sp-card launch-summary" aria-labelledby="launch-summary-title">
            <h3 id="launch-summary-title" className="launch-summary-title">
              Summary
            </h3>
            <dl className="facts">
              <dt>{oneModule ? "Module" : "Pipeline"}</dt>
              <dd>
                {loaded
                  ? [`${loaded.name}${loaded.version ? ` ${loaded.version}` : ""}${fromEntry ? `, from the catalog entry ${fromEntry.name}` : ""}`, profile && `profile ${profile}`]
                      .filter(Boolean)
                      .join(" · ")
                  : "Not loaded yet"}
              </dd>
              {targeting && (
                <>
                  <dt>Runs</dt>
                  <dd>
                    {module
                      ? `Runs module ${module.name} ${(module.source === "registry" ? version.trim() : module.version) || "(no version)"}, ${module.source === "registry" ? "from the registry" : "from a directory"}`
                      : rule
                        ? `Runs rule ${rule} and the jobs it needs`
                        : "One module or one rule, once loaded"}
                  </dd>
                </>
              )}
              <dt>Engine</dt>
              <dd>{engine ? `${engineName(engine)} ${loaded?.engine_versions[engine] ?? "(version not found)"}` : "Not chosen yet"}</dd>
              <dt>Environment</dt>
              <dd>{chosen ? `${envLabel(chosen)} · ${executorLabel(chosen.executor)}` : envsFailed ? "the server's default" : envs === null ? "…" : "Not chosen yet"}</dd>
              <dt>Run resources</dt>
              <dd>{summaryLine(res.sent, extras)}</dd>
              {!oneModule && (
                <>
                  <dt>Extra config</dt>
                  <dd className="sp-mono">{configFile.trim() || "none"}</dd>
                </>
              )}
              <dt>Engine head</dt>
              <dd>{engine ? headLine : "Not chosen yet"}</dd>
              <dt>Tasks</dt>
              <dd>{tasksLine()}</dd>
              <dt>Run directory</dt>
              <dd>{runDirectory}</dd>
            </dl>
            <h3 id="launch-missing-title" className="launch-missing-title">
              Before Launch
            </h3>
            <div id="launch-missing" role="status" aria-labelledby="launch-missing-title" className="launch-missing">
              {missing.length === 0 && <p>Nothing is missing.</p>}
              {missing.length + warnings.length > 0 && (
                <ul>
                  {[...missing, ...warnings].map((r) => (
                    <li key={r.text} data-warning={warnings.includes(r) || undefined}>
                      {r.to ? (
                        <Anchor
                          href={`#${targetId(r.to)}`}
                          onClick={(e) => {
                            e.preventDefault();
                            focusField(r.to!);
                          }}
                        >
                          {r.text}
                        </Anchor>
                      ) : (
                        r.text
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            {!phone && formError}
          </section>
          {loaded && engine && (
            <ParamsPreview
              engine={engine}
              fields={fields}
              values={values}
              rows={rows}
              extra={engine === "snakemake" && configFile.trim() !== "" ? keptAs(engine, configFile) : null}
              effective={defaultsMode}
            />
          )}
          {/* the phone's pinned bar: Launch, then the first reason (a visual copy) or what it sends */}
          {phone && (
            <div className="launch-bar">
              <div className="launch-bar-row">
                {launchButton}
                {(why || summary) && (
                  <Text id={summary ? "launch-reason" : undefined} size="sm" c="dimmed" className="launch-reason" aria-hidden={why ? true : undefined}>
                    {why ?? summary}
                  </Text>
                )}
              </div>
              {formError}
            </div>
          )}
        </Stack>
      </div>
    </Stack>
  );
}

/** Copy to a new launch's banner (no live region): where the values come from and which differ
 * from the defaults, what is not sent, and what loads code or configuration (dev-env §15.3 req. 16). */
function PrefillBanner({ prefill, onClear }: { prefill: Prefill; onClear?: () => void }) {
  const names = prefill.template.non_default;
  const differ = names.length === 1 ? "1 value differs" : `${names.length} values differ`;
  const profiles = prefill.template.profiles;
  return (
    <Paper className="launch-prefill" p="sm" withBorder>
      <Text size="sm">
        {`Prefilled from ${prefill.run}: ${differ} from the pipeline's defaults${names.length ? `: ${names.join(", ")}` : ""}.`}
      </Text>
      {prefill.left.length > 0 && <Text size="sm">{`Not in this pipeline's form, and not sent: ${prefill.left.join(", ")}.`}</Text>}
      {profiles.length > 1 && <Text size="sm">{`Profiles ${profiles.join(", ")}: the form takes one, ${profiles[0]} is kept.`}</Text>}
      {prefill.template.environment_notice && <Text size="sm">{prefill.template.environment_notice}</Text>}
      {prefill.template.code_loading.length > 0 && (
        <ul className="launch-loading">
          {prefill.template.code_loading.map((c) => (
            <li key={c.field}>
              <span>{`${loadingLabel(c.field)}: loads code or configuration${c.writable_by_others ? " · writable by others" : ""}`}</span>{" "}
              <code>{c.value}</code>
            </li>
          ))}
        </ul>
      )}
      {onClear && (
        <Button variant="default" onClick={onClear}>
          Clear and start empty
        </Button>
      )}
    </Paper>
  );
}

/** One schema group as a section that folds (UX-PAR-30): its icon, description and counts, and a
 * status that says what needs doing; open at first when it has an issue or a changed value, and
 * when the server finds an error in it. A form of one section shows its fields alone. */
function ParamGroup({
  id,
  section,
  reveal,
  notes,
  hints,
  values,
  errors,
  tried,
  prefill,
  incomplete,
  onChange,
}: {
  id: string;
  section: Section;
  /** A "Before Launch" link is moving focus to one of its fields. */
  reveal: boolean;
  notes: Record<string, string>;
  /** api §5.12: each field's effective default, in words. */
  hints: Record<string, string>;
  values: Values;
  errors: Errors;
  tried: boolean;
  /** The form prefills the effective defaults: the input shows the default's value. */
  prefill: boolean;
  /** The sources are not complete: an empty required field warns, it does not block. */
  incomplete: boolean;
  onChange: (key: string, value: string | boolean) => void;
}) {
  const required = section.fields.filter((f) => f.required && f.type !== "boolean");
  const empty = required.filter((f) => String((prefill ? shownValue(f, own(values, f.key)) : own(values, f.key)) ?? "").trim() === "").length;
  const changed = section.fields.filter((f) => isChanged(f, own(values, f.key))).length;
  const failed = section.fields.some((f) => errors[`params.${f.key}`]);
  const status = [
    empty
      ? { tone: "issue", text: `${plural(empty, "required field", "required fields")} empty` }
      : required.length
        ? { tone: "ok", text: `${required.length} required · filled` }
        : null,
    changed ? { tone: "changed", text: `${changed} changed` } : null,
  ].filter((s) => s !== null);
  if (!status.length) status.push({ tone: "default", text: "defaults" });
  const sub = [
    section.description,
    plural(section.fields.length, "parameter", "parameters"),
    required.length ? `${required.length} required` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  return (
    <FoldSection
      id={id}
      icon={groupIcon(section.icon)}
      title={section.title}
      sub={sub}
      status={status.map((s, i) => (
        <Fragment key={s.tone}>
          {i > 0 && " "}
          <span className="launch-status" data-tone={s.tone}>
            {s.text}
          </span>
        </Fragment>
      ))}
      defaultOpen={empty > 0 || changed > 0}
      reveal={reveal ? "link" : failed}
      card
    >
      <ParamRows
        fields={section.fields}
        notes={notes}
        hints={hints}
        values={values}
        errors={errors}
        tried={tried}
        prefill={prefill}
        incomplete={incomplete}
        onChange={onChange}
      />
    </FoldSection>
  );
}

/** The parameters one per line (Thomas, 2026-10-31): each a full-width row. */
function ParamRows({
  fields,
  notes = {},
  hints = {},
  values,
  errors,
  tried,
  prefill = false,
  incomplete = false,
  onChange,
}: {
  fields: Field[];
  /** A warning under a field, in words: outdir the same as the copied run's. */
  notes?: Record<string, string>;
  /** api §5.12: the effective default's source, in words, under the field. */
  hints?: Record<string, string>;
  values: Values;
  errors: Errors;
  tried: boolean;
  /** The form prefills the effective defaults: the input shows the default's value. */
  prefill?: boolean;
  /** The sources are not complete (api §5.12): an empty required field warns, it does not block. */
  incomplete?: boolean;
  onChange: (key: string, value: string | boolean) => void;
}) {
  return (
    <div className="launch-params">
      {fields.map((field) => {
        const value = prefill ? shownValue(field, own(values, field.key)) : own(values, field.key);
        // the client's check once the field was touched or Launch pressed, else the server's answer
        let wrong = value !== undefined || tried ? checkValue(field, value) : null;
        if (incomplete && wrong === REQUIRED) wrong = null;
        const note = own(notes, field.key);
        const hint = own(hints, field.key);
        return (
          <Fragment key={field.key}>
            <ParamField
              field={field}
              value={value}
              hint={hint}
              error={wrong ?? errors[`params.${field.key}`]}
              onChange={(v) => onChange(field.key, v)}
            />
            {note && <p className="launch-warning">{note}</p>}
          </Fragment>
        );
      })}
    </div>
  );
}

/** What Launch sends, built by the same `buildParams` as the request (UX-PAR-32). Nextflow reads
 * it as params.json; Snakemake gets the same JSON as a config file, shown here as YAML. With the
 * effective defaults (api §5.12), only the values the user changed. */
function ParamsPreview({
  engine,
  fields,
  values,
  rows,
  extra,
  effective,
}: {
  engine: Engine;
  fields: Field[];
  values: Values;
  rows: Row[];
  extra: string | null;
  effective?: boolean;
}) {
  const snakemake = engine === "snakemake";
  const label = snakemake ? "Config preview, as YAML" : "params.json preview";
  let text: string | null;
  try {
    const params = buildParams(fields, values, rows, extra !== null || !!effective);
    text = snakemake ? toYaml(params) : `${JSON.stringify(params, null, 2)}\n`;
  } catch {
    text = null;
  }
  return (
    <FoldSection id="launch-preview" icon="fileCode" title={label} card className="launch-preview-card" defaultOpen={false}>
      <Text size="sm" className="launch-preview-note" mb="sm">
        {effective
          ? `Only the values you changed${extra ? `, written to the run directory and passed with --configfile, after ${extra}` : ""}; a value a profile, the pipeline's config or the params file sets keeps coming from it (api §5.12).`
          : extra
          ? `Only the keys you set · written to the run directory and passed with --configfile, after ${extra} · other keys come from ${extra}, then the pipeline`
          : snakemake
          ? "Only the values set, and a nested map whole once one of its values is set. Spectio writes them to .spectio/params.json in the run directory, passed with --configfile; shown here as YAML."
          : "Only the values set. Spectio writes them to .spectio/params.json in the run directory, passed with -params-file."}
      </Text>
      {text === null ? (
        <Text size="sm">A JSON field does not parse yet: the preview waits for it.</Text>
      ) : (
        <pre className="launch-preview" aria-label={label}>
          {text}
        </pre>
      )}
    </FoldSection>
  );
}

function ParamField({
  field,
  value,
  hint,
  error,
  onChange,
}: {
  field: Field;
  value: string | boolean | undefined;
  /** api §5.12: where the shown default comes from, in words ("from profile test"). */
  hint?: string;
  error?: string;
  onChange: (value: string | boolean) => void;
}) {
  const shown = field.default === undefined ? "" : `default ${JSON.stringify(field.default)}`;
  const changed = isChanged(field, value);
  const meta = [field.type === "json" ? "JSON" : field.type, field.format, changed ? "changed" : null, changed ? shown || "no default" : shown]
    .filter(Boolean)
    .join(" · ");
  // One row (Thomas, 2026-10-31): the name with the meta on its line, the input, the help under
  // it. The accessible description stays one text, "help · meta" (visually hidden); the visible
  // meta and help are its copy, hidden from assistive technology.
  const description = [field.help, hint, meta].filter(Boolean).join(" · ") || undefined;
  const descriptionId = useId();
  const inputContainer = (input: ReactNode) => (
    <>
      {meta && (
        <span className="launch-param-meta" aria-hidden="true">
          {meta}
        </span>
      )}
      <div className="launch-param-input">{input}</div>
      {hint && (
        <span className="launch-param-source" aria-hidden="true">
          {hint}
        </span>
      )}
      {field.help && (
        <span className="launch-param-help" aria-hidden="true">
          {field.help}
        </span>
      )}
    </>
  );
  const placeholder =
    field.default === undefined || typeof field.default === "boolean"
      ? undefined
      : typeof field.default === "string"
        ? field.default
        : JSON.stringify(field.default);
  // required or optional as text in the label, so in the accessible name (Thomas, 2026-10-31)
  const label = (
    <>
      {field.label} <span className="launch-param-need" data-required={field.required || undefined}>({field.required ? "required" : "optional"})</span>
    </>
  );
  const common = {
    id: paramId(field.key),
    label,
    description,
    error,
    inputContainer,
    withAsterisk: false, // the word "(required)" replaces Mantine's asterisk (CR-P3T32-01)
    classNames: { root: "launch-param", description: "sp-sr" },
  };
  switch (field.type) {
    case "boolean":
      // The same row as the other fields (CR-P3PARC-01): Checkbox has no inputContainer and does
      // not link its description to the input, so the row and the description are drawn here.
      return (
        <div className="launch-param">
          <Checkbox
            id={paramId(field.key)}
            className="launch-param-check"
            label={label}
            aria-describedby={descriptionId}
            error={error}
            checked={typeof value === "boolean" ? value : field.default === true}
            onChange={(e) => onChange(e.currentTarget.checked)}
          />
          <span id={descriptionId} className="sp-sr">
            {description}
          </span>
          <span className="launch-param-meta" aria-hidden="true">
            {meta}
          </span>
          {hint && (
            <span className="launch-param-source" aria-hidden="true">
              {hint}
            </span>
          )}
          {field.help && (
            <span className="launch-param-help" aria-hidden="true">
              {field.help}
            </span>
          )}
        </div>
      );
    case "enum":
      return (
        <NativeSelect
          {...common}
          required={field.required}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.currentTarget.value)}
          data={[{ value: "", label: shown ? `(${shown})` : "(not set)" }, ...(field.options ?? []).map(String)]}
        />
      );
    case "json":
      return (
        <Textarea
          {...common}
          required={field.required}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.currentTarget.value)}
          placeholder="JSON"
          autosize
          minRows={1}
        />
      );
    default:
      return (
        <TextInput
          {...common}
          required={field.required}
          inputMode={numericMode(field)}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.currentTarget.value)}
          placeholder={placeholder}
          spellCheck={false}
          autoComplete="off"
        />
      );
  }
}

/** The phone keyboard of a number field. A checked text input, not type="number": that one empties
 * its value on text it cannot read (so neither check could name the mistake), steps on the scroll
 * wheel and reads decimals by locale. The numeric and decimal keypads have no minus sign on iOS, so
 * a field whose schema allows a negative minimum keeps the full keyboard. */
function numericMode(field: Field): "numeric" | "decimal" | undefined {
  if (field.type !== "integer" && field.type !== "number") return undefined;
  if (field.minimum !== undefined && field.minimum < 0) return undefined;
  return field.type === "integer" ? "numeric" : "decimal";
}

/** Parameters as name and value when the pipeline has no schema (schema_source `none`). */
function KeyValueRows({ rows, onChange }: { rows: Row[]; onChange: (rows: Row[]) => void }) {
  const set = (i: number, row: Row) => onChange(rows.map((r, j) => (j === i ? row : r)));
  return (
    <Stack gap="xs">
      {rows.map((row, i) => (
        <Group key={i} gap="xs" align="flex-end" wrap="wrap">
          <TextInput
            style={{ flex: "1 1 140px" }}
            label={`Name, row ${i + 1}`}
            value={row.key}
            onChange={(e) => set(i, { ...row, key: e.currentTarget.value })}
            spellCheck={false}
            autoComplete="off"
          />
          <TextInput
            style={{ flex: "2 1 180px" }}
            label={`Value, row ${i + 1}`}
            value={row.value}
            onChange={(e) => set(i, { ...row, value: e.currentTarget.value })}
            spellCheck={false}
            autoComplete="off"
          />
          <Button
            type="button"
            variant="default"
            onClick={() => onChange(rows.filter((_, j) => j !== i))}
          >
            Remove row {i + 1}
          </Button>
        </Group>
      ))}
      <div>
        <Button type="button" variant="default" onClick={() => onChange([...rows, { key: "", value: "" }])}>
          Add a parameter
        </Button>
      </div>
    </Stack>
  );
}
