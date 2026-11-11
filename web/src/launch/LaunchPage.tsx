import {
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
import { Fragment, type ReactNode, useEffect, useId, useRef, useState } from "react";
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
  getLaunchTemplate,
  getRun,
  inspect,
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
import { usePhone } from "../shell/layout";
import { CatalogPicker, SaveToCatalog } from "./CatalogPicker";
import { EngineButtons } from "./EngineButtons";
import { EnvironmentRow } from "./EnvironmentRow";
import { guessEngine } from "./guessEngine";
import { ConfigFileRow, type Draft, NO_DRAFT, RESOURCE_LABELS, ResourcesRow, draftFrom, keptAs, readResources, summaryLine } from "./RunExtras";
import { TryPipelines } from "./TryPipelines";
import {
  type Field,
  type Row,
  type Section,
  type Values,
  REQUIRED,
  buildParams,
  checkValue,
  isChanged,
  own,
  schemaFields,
  toYaml,
  valuesFrom,
} from "./schemaFields";

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
  if (to === "config_file") return "launch-config-file";
  if (to.startsWith("resources.")) return { "resources.cpus": "res-cpus", "resources.mem": "res-mem" }[to] ?? "res-time-h";
  return paramId(to.slice("params.".length));
}

/** Where a 422 error of `POST /runs` or of inspect is shown (fields are dotted, inbox #86): a
 * param error lands on the field of the longest key that names it or a value inside it
 * (`params.ref.release` on `ref.release`, UX-PAR-31). */
function formKey(field: string, keys: string[]): string {
  const bare = field.replace(/^workflow\./, "");
  if (["location", "revision", "engine", "name", "environment", "config_file"].includes(bare)) return bare;
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
  const [loading, setLoading] = useState(false);
  const [engine, setEngine] = useState<Engine | null>(null);
  // Profile as the user set it; until then, the chosen environment's default profile (§4.8.1)
  const [picked, setPicked] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [values, setValues] = useState<Values>({});
  const [rows, setRows] = useState<Row[]>([]);
  const [errors, setErrors] = useState<Errors>({});
  const [sending, setSending] = useState(false);
  // Launch pressed while a field is wrong: empty required fields then say so on the field too
  const [tried, setTried] = useState(false);
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
  const inFlight = useRef<AbortController | null>(null);
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

  const extras = { engine, profile, env: chosen };
  const res = readResources(resources, extras);
  // with a Snakemake extra file, only the keys set: the file's other keys stay (api §5.7)
  const leaves = engine === "snakemake" && configFile.trim() !== "";

  const repo = location.trim() !== "" && !location.trim().startsWith("/");
  const github = SHORT_NAME.test(location.trim()) ? `https://github.com/${location.trim()}` : null;
  const skipped: string[] = [];
  // the form's shape follows the engine (guessed at load, then chosen): Snakemake maps become dotted
  // sections (CR-P3PARB-02). Values typed under the other shape stay, unsent, until the engine goes back.
  const sections = schemaFields(loaded?.schema ?? null, skipped, engine === "snakemake");
  const fields = sections.flatMap((s) => s.fields);
  const keys = fields.map((f) => f.key);
  const grouped = !!loaded?.schema && ("$defs" in loaded.schema || "definitions" in loaded.schema);
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
    setErrors({});
    setEntryName(null); // the picker goes back to None, and the entry's prefill is forgotten
    setFromName(null);
    setParamsFile(null);
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

  async function load(at = location, rev = revision, copy?: Omit<Prefill, "left">) {
    const where = at.trim();
    const isRepo = where !== "" && !where.startsWith("/");
    if (where === "") {
      setErrors({ location: "Give an absolute path or a repository." });
      return;
    }
    if (isRepo && rev.trim() === "") {
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
      const found = await inspect(where, isRepo ? rev.trim() : null, controller.signal, from?.params_file);
      setLoaded(found);
      setTried(false);
      setFromName(from?.name ?? null);
      setParamsFile(from ? found.params_file : null);
      if (copy) {
        // the run's engine, profile and values, in the form's shape for that engine
        const { engine: was } = copy.template.workflow;
        const shape = schemaFields(found.schema, [], was === "snakemake").flatMap((s) => s.fields);
        const params = copy.template.params;
        const { values: filled, left } = shape.length ? valuesFrom(shape, params) : { values: {}, left: [] };
        setEngine(was);
        setPicked(copy.template.profiles[0] ?? ""); // the copied run's profile wins
        setEnvName(copy.template.environment);
        setValues(filled);
        setRows(shape.length ? [] : Object.entries(params).map(([key, v]) => ({ key, value: typeof v === "string" ? v : JSON.stringify(v) })));
        setResources(draftFrom(copy.template.default_resources));
        setConfigFile(copy.template.config_file ?? ""); // read again at this launch (api §5.7)
        setPrefill({ ...copy, left });
      } else {
        // the entry's engine and params file (§4.7.1); every value the form does not place is listed
        const was = from?.engine ?? guessEngine(found.engine_files);
        const shape = schemaFields(found.schema, [], was === "snakemake").flatMap((s) => s.fields);
        const params = found.params_file?.values ?? {};
        setEngine(was);
        setPicked(null);
        setValues(shape.length ? valuesFrom(shape, params).values : {});
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
        setLocation(at);
        setRevision(rev ?? "");
        void load(at, rev ?? "", { template, run: `${runName(run)} (${shortId(run.id)})`, name: runName(run) });
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

  /** Every reason Launch waits, in order (ui-spec §4.6): the list of "Before Launch". */
  function reasons(): Reason[] {
    if (loading) return [{ text: "Wait for the pipeline to load", to: "location" }];
    if (!loaded) return [{ text: "Load a pipeline first", to: "location" }];
    if (loaded.engine_files.length === 0) {
      return [{ text: "No main.nf or Snakefile in this directory: check the path", to: "location" }];
    }
    const found: Reason[] = [];
    if (!engine) found.push({ text: "Choose the engine", to: "engine" });
    if (!chosen && !envsFailed) found.push({ text: "Choose where it runs", to: "environment" });
    if (engine && !ENGINE_FILES[engine].some((f) => loaded.engine_files.includes(f))) {
      const other = engineName(engine === "nextflow" ? "snakemake" : "nextflow");
      found.push({ text: `No ${ENGINE_FILES[engine].join(" or ")} in this directory: press ${other} or check the path`, to: "engine" });
    }
    for (const [to, wrong] of Object.entries(res.errors)) {
      found.push({ text: `Fix ${RESOURCE_LABELS[to as keyof typeof RESOURCE_LABELS]}: ${wrong.brief}`, to });
    }
    if (configRefused) found.push({ text: `Fix Extra config file: ${configRefused}`, to: "config_file" });
    for (const field of fields) {
      const wrong = checkValue(field, own(values, field.key));
      const to = `params.${field.key}`;
      if (wrong === REQUIRED) found.push({ text: `Fill the required field: ${field.key}`, to });
      else if (wrong) found.push({ text: `Fix ${field.key}: ${wrong}`, to });
    }
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
    const path = configFile.trim();
    setSending(true);
    if (configRefused && (await checkConfig())?.found?.error) {
      setSending(false);
      return setTried(true);
    }
    setErrors({});
    setConfigDown(null);
    try {
      const run = await launch({
        workflow: { location: loaded.location, revision: loaded.revision, engine },
        ...(name.trim() ? { name: name.trim() } : {}),
        profiles: profile ? [profile] : [],
        ...(chosen ? { environment: chosen.name } : {}),
        params,
        ...(Object.keys(res.sent).length ? { default_resources: res.sent } : {}),
        ...(path ? { config_file: path } : {}),
      });
      onLaunched(run.id);
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
  const sent = buildParams(fields, values, rows);
  for (const c of paramsFile?.code_loading ?? []) {
    const others = c.writable_by_others ? " · writable by others" : "";
    if (c.field === "params_file") {
      warnings.push({ text: `Warning, not a blocker: ${paramsFile!.path} loads code or configuration${others}` });
    } else if (c.field.startsWith("params.")) {
      if (own(sent, c.field.slice(7)) === c.value) warnings.push({ text: `Warning, not a blocker: ${paramsFile!.path} sets ${c.field.slice(7)}: ${c.value}${others}` });
    } else warnings.push({ text: `Warning, not a blocker: ${loadingLabel(c.field)} ${c.value} loads code or configuration${others}` });
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
  // One action in two places on a desktop (LiteLaunch: the page head and under the aside), both
  // described by the "Before Launch" list; the phone has the pinned bar only.
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
      {sending ? "Launching…" : "Launch"}
    </Button>
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
  const guessed = loaded && guessEngine(loaded.engine_files);
  const entryEngine = (fromEntry ?? entry)?.engine;
  const engineNote = engine && engine === entryEngine && (!loaded || ENGINE_FILES[engine].some((f) => loaded.engine_files.includes(f)))
    ? `${engineName(engine)}, from the catalog entry`
    : !loaded
    ? "Load the pipeline to guess the engine"
    : loaded.engine_files.length === 0
      ? "No main.nf or Snakefile found"
      : !guessed
        ? `No guess: ${loaded.engine_files.join(" and ")} found · choose the engine`
        : engine && !ENGINE_FILES[engine].some((f) => loaded.engine_files.includes(f))
          ? `${ENGINE_FILES[engine].join(" or ")} not found: Launch will refuse. Guessed: ${engineName(guessed)}`
          : `Guessed from ${loaded.engine_files.join(", ")} · change it if the guess is wrong`;

  return (
    <Stack className="launch-page" gap="md">
      <PageHead
        section="launch"
        title="Launch a workflow"
        sub="A directory or a Git repository: Spectio guesses the engine and builds the form from its schema."
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
        <Text c="red" role="alert">
          Not prefilled: {prefillError}
        </Text>
      )}
      {prefill && <PrefillBanner prefill={prefill} onClear={onClear} />}
      {configDown !== null && (
        <div role="alert" className="launch-banner">
          <Icon name="alert" />
          <span className="sp-grow">{`The extra config file could not be read: ${configDown}. Nothing was started and your values are kept.`}</span>
          <Button size="xs" onClick={submit}>
            Launch again
          </Button>
        </div>
      )}
      <div className="launch-grid">
        <Stack gap="md">
          <FoldSection id="launch-pipeline" icon="route" title="Pipeline" card reveal={goTo === "location" || goTo === "engine"}>
            <CatalogPicker data={catalog} failed={catalogFailed} onRetry={loadCatalog} chosen={entry} onChoose={choose} onClear={clear}>
              {paramsFile && (
                <p className="sp-muted" aria-live="polite">
                  {paramsFile.error
                    ? `${paramsFile.path} could not be read: ${paramsFile.error}`
                    : [
                        `${plural(placed, "value", "values")} of ${paramsFile.path} ${placed === 1 ? "fills" : "fill"} the form and read changed.`,
                        unplaced.length > 0 &&
                          `${plural(unplaced.length, "value", "values")} of ${paramsFile.path} ${unplaced.length === 1 ? "has" : "have"} no field in this form, and ${unplaced.length === 1 ? "is" : "are"} not sent: ${unplaced.join(", ")}`,
                      ]
                        .filter(Boolean)
                        .join(" ")}
                </p>
              )}
            </CatalogPicker>
            <TryPipelines runs={recent} onPick={pick} saved={catalog?.items.filter((e) => e.revision === null).map((e) => e.location)} />
            <Group align="flex-start" gap="sm" wrap="wrap">
              <TextInput
                style={{ flex: "999 1 280px" }}
                id="launch-location"
                label="Pipeline"
                inputWrapperOrder={["label", "input", "description", "error"]}
                value={location}
                onChange={(e) => edit(setLocation, e.currentTarget.value)}
                error={errors.location}
                description={
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
                }
                spellCheck={false}
                autoComplete="off"
              />
              {repo && (
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
                  <Text size="sm" c="dimmed">
                    {loaded.revision ? `A Git repository at ${loaded.revision}` : "A directory on this machine"}
                    {loaded.engine_files.length ? ` · ${loaded.engine_files.join(", ")} found` : ""}
                    {` · ${SOURCES[loaded.schema_source]}`}
                  </Text>
                </div>
                <span className="launch-loaded-status">
                  <Icon name="check" />
                  <span>Loaded</span>
                </span>
                <SaveToCatalog
                  data={catalog}
                  failed={catalogFailed}
                  entry={fromEntry}
                  pipeline={loaded.name}
                  draft={{ engine: engine ?? "nextflow", location: loaded.location, revision: loaded.revision ?? "", profile, params_file: "" }}
                  onSaved={(item) => void loadCatalog().then(() => (setEntryName(item.name), setFromName(item.name)))}
                />
              </Paper>
            )}
            <Stack gap="md" mt="md">
              <EngineButtons
                value={engine}
                onChange={(e) => setEngine(e)}
                note={engineNote}
                error={errors.engine}
              />
              <SimpleGrid cols={{ base: 1, sm: 2 }}>
                <NativeSelect
                  label="Profile"
                  inputWrapperOrder={["label", "input", "description", "error"]}
                  value={profile}
                  onChange={(e) => setPicked(e.currentTarget.value)}
                  data={[{ value: "", label: "(none)" }, ...(loaded?.profiles ?? [])]}
                  description={
                    <>
                      {engine ? PROFILE_HINTS[engine] : "From the pipeline's own configuration; passed to the engine as its profile."}
                      {profileNote && (
                        <>
                          <br />
                          <span>{profileNote}</span>
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
            <FoldSection id="launch-params" icon="sliders" title="Parameters" reveal={!!goTo?.startsWith("params.")}>
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
                    values={values}
                    errors={errors}
                    tried={tried}
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
                    values={values}
                    errors={errors}
                    tried={tried}
                    onChange={(key, v) => setValues((old) => ({ ...old, [key]: v }))}
                  />
                ))}
              </Stack>
              {sections.length === 0 && <KeyValueRows rows={rows} onChange={setRows} />}
            </FoldSection>
          )}
        </Stack>
        <Stack className="launch-aside" gap="md" component="aside" aria-label="Launch">
          <section className="sp-card launch-summary" aria-labelledby="launch-summary-title">
            <h2 id="launch-summary-title" className="launch-summary-title">
              Summary
            </h2>
            <dl className="facts">
              <dt>Pipeline</dt>
              <dd>
                {loaded
                  ? [`${loaded.name}${loaded.version ? ` ${loaded.version}` : ""}${fromEntry ? `, from the catalog entry ${fromEntry.name}` : ""}`, profile && `profile ${profile}`]
                      .filter(Boolean)
                      .join(" · ")
                  : "Not loaded yet"}
              </dd>
              <dt>Engine</dt>
              <dd>{engine ? `${engineName(engine)} ${loaded?.engine_versions[engine] ?? "(version not found)"}` : "Not chosen yet"}</dd>
              <dt>Environment</dt>
              <dd>{chosen ? `${envLabel(chosen)} · ${executorLabel(chosen.executor)}` : envsFailed ? "the server's default" : envs === null ? "…" : "Not chosen yet"}</dd>
              <dt>Resources</dt>
              <dd>{summaryLine(res.sent, extras)}</dd>
              <dt>Extra config</dt>
              <dd className="sp-mono">{configFile.trim() || "none"}</dd>
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
                        <a
                          href={`#${targetId(r.to)}`}
                          onClick={(e) => {
                            e.preventDefault();
                            focusField(r.to!);
                          }}
                        >
                          {r.text}
                        </a>
                      ) : (
                        r.text
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
          {loaded && engine && <ParamsPreview engine={engine} fields={fields} values={values} rows={rows} extra={leaves ? keptAs(engine, configFile) : null} />}
          <div className="launch-bar">
            <div className="launch-bar-row">
              {launchButton}
              {/* the phone's bar: the first reason (a visual copy), or what Launch sends */}
              {phone && (why || summary) && (
                <Text id={summary ? "launch-reason" : undefined} size="sm" c="dimmed" className="launch-reason" aria-hidden={why ? true : undefined}>
                  {why ?? summary}
                </Text>
              )}
            </div>
            {errors.form && (
              <Text size="sm" c="red" role="alert" mt={4}>
                {errors.form}
              </Text>
            )}
          </div>
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
        <Button variant="default" size="xs" onClick={onClear}>
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
  values,
  errors,
  tried,
  onChange,
}: {
  id: string;
  section: Section;
  /** A "Before Launch" link is moving focus to one of its fields. */
  reveal: boolean;
  notes: Record<string, string>;
  values: Values;
  errors: Errors;
  tried: boolean;
  onChange: (key: string, value: string | boolean) => void;
}) {
  const required = section.fields.filter((f) => f.required && f.type !== "boolean");
  const empty = required.filter((f) => String(own(values, f.key) ?? "").trim() === "").length;
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
      <ParamRows fields={section.fields} notes={notes} values={values} errors={errors} tried={tried} onChange={onChange} />
    </FoldSection>
  );
}

/** The parameters one per line (Thomas, 2026-10-31): each a full-width row. */
function ParamRows({
  fields,
  notes = {},
  values,
  errors,
  tried,
  onChange,
}: {
  fields: Field[];
  /** A warning under a field, in words: outdir the same as the copied run's. */
  notes?: Record<string, string>;
  values: Values;
  errors: Errors;
  tried: boolean;
  onChange: (key: string, value: string | boolean) => void;
}) {
  return (
    <div className="launch-params">
      {fields.map((field) => {
        const value = own(values, field.key);
        // the client's check once the field was touched or Launch pressed, else the server's answer
        const wrong = value !== undefined || tried ? checkValue(field, value) : null;
        const note = own(notes, field.key);
        return (
          <Fragment key={field.key}>
            <ParamField field={field} value={value} error={wrong ?? errors[`params.${field.key}`]} onChange={(v) => onChange(field.key, v)} />
            {note && <p className="launch-warning">{note}</p>}
          </Fragment>
        );
      })}
    </div>
  );
}

/** What Launch sends, built by the same `buildParams` as the request (UX-PAR-32). Nextflow reads
 * it as params.json; Snakemake gets the same JSON as a config file, shown here as YAML. */
function ParamsPreview({ engine, fields, values, rows, extra }: { engine: Engine; fields: Field[]; values: Values; rows: Row[]; extra: string | null }) {
  const snakemake = engine === "snakemake";
  const label = snakemake ? "Config preview, as YAML" : "params.json preview";
  let text: string | null;
  try {
    const params = buildParams(fields, values, rows, extra !== null);
    text = snakemake ? toYaml(params) : `${JSON.stringify(params, null, 2)}\n`;
  } catch {
    text = null;
  }
  return (
    <FoldSection id="launch-preview" icon="fileCode" title={label} card className="launch-preview-card" defaultOpen={false}>
      <Text size="sm" className="launch-preview-note" mb="sm">
        {extra
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
  error,
  onChange,
}: {
  field: Field;
  value: string | boolean | undefined;
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
  const description = [field.help, meta].filter(Boolean).join(" · ") || undefined;
  const descriptionId = useId();
  const inputContainer = (input: ReactNode) => (
    <>
      {meta && (
        <span className="launch-param-meta" aria-hidden="true">
          {meta}
        </span>
      )}
      <div className="launch-param-input">{input}</div>
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
