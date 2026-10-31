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
  Title,
} from "@mantine/core";
import { Fragment, useEffect, useRef, useState } from "react";
import {
  ApiError,
  ENGINE_FILES,
  type Engine,
  type FieldError,
  type Inspected,
  inspect,
  launch,
} from "../api";
import { ICONS, Icon, groupIcon } from "../icons";
import { executorLabel, plural } from "../runs/stateWord";
import { useServer } from "../server";
import { EngineMark } from "../shell/EngineMark";
import { FoldSection } from "../shell/FoldSection";
import { PageHead } from "../shell/PageHead";
import { usePhone } from "../shell/layout";
import { EngineButtons } from "./EngineButtons";
import { guessEngine } from "./guessEngine";
import {
  type Field,
  type Row,
  type Section,
  type Values,
  buildParams,
  isChanged,
  own,
  schemaFields,
  toYaml,
} from "./schemaFields";

// The 0.0.1 launch form (P1 Task 19; ui-spec §4.6 note 2026-10-29; boards LiteLaunch and
// LiteLaunchSnakemake, of which 0.0.1 shows less, UX-227). Native inputs and buttons only, a label
// on every field; a 422 lands on its field through Mantine's error, which sets aria-invalid and
// aria-describedby. Each schema group is a section that folds, open when it has an issue or a
// changed value (UX-PAR-30); the params preview and the request come from one `buildParams`
// (UX-PAR-32).

const SHORT_NAME = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9_][A-Za-z0-9._-]{0,99}$/;
const NAMES: Record<Engine, string> = { nextflow: "Nextflow", snakemake: "Snakemake" };
const SOURCES: Record<Inspected["schema_source"], string> = {
  "nextflow_schema.json": "form from nextflow_schema.json",
  "config.schema.yaml": "form from config.schema.yaml",
  inferred: "form inferred from config/config.yaml (its types are not checked)",
  none: "no parameter schema: add parameters as name and value",
};

type Errors = Record<string, string>; // by form key: location, revision, engine, name, profile, params.<key>, form

/** Where a 422 error of `POST /runs` or of inspect is shown (fields are dotted, inbox #86): a
 * param error lands on the field of the longest key that names it or a value inside it
 * (`params.ref.release` on `ref.release`, UX-PAR-31). */
function formKey(field: string, keys: string[]): string {
  const bare = field.replace(/^workflow\./, "");
  if (["location", "revision", "engine", "name"].includes(bare)) return bare;
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

function jsonError(text: unknown): boolean {
  if (typeof text !== "string" || text.trim() === "") return false;
  try {
    JSON.parse(text);
    return false;
  } catch {
    return true;
  }
}

/** The line under the Profile select: where the engine finds the profiles, and how it gets one. */
const PROFILE_HINTS: Record<Engine, string> = {
  nextflow: "From the pipeline's nextflow.config · passed as -profile",
  snakemake: "From the pipeline's profiles/ directory · passed as --workflow-profile",
};

export function LaunchPage({ onLaunched }: { onLaunched: (id: string) => void }) {
  const server = useServer();
  const phone = usePhone();
  const [location, setLocation] = useState("");
  const [revision, setRevision] = useState("");
  const [loaded, setLoaded] = useState<Inspected | null>(null);
  const [loading, setLoading] = useState(false);
  const [engine, setEngine] = useState<Engine | null>(null);
  const [profile, setProfile] = useState("");
  const [name, setName] = useState("");
  const [values, setValues] = useState<Values>({});
  const [rows, setRows] = useState<Row[]>([]);
  const [errors, setErrors] = useState<Errors>({});
  const [sending, setSending] = useState(false);
  const inFlight = useRef<AbortController | null>(null);

  useEffect(() => {
    document.title = "Launch a workflow · Spectio";
    return () => inFlight.current?.abort();
  }, []);

  const repo = location.trim() !== "" && !location.trim().startsWith("/");
  const github = SHORT_NAME.test(location.trim()) ? `https://github.com/${location.trim()}` : null;
  const skipped: string[] = [];
  const sections = schemaFields(loaded?.schema ?? null, skipped, engine === "snakemake");
  const fields = sections.flatMap((s) => s.fields);
  const keys = fields.map((f) => f.key);
  const grouped = !!loaded?.schema && ("$defs" in loaded.schema || "definitions" in loaded.schema);
  const changed = fields.filter((f) => isChanged(f, own(values, f.key))).length + rows.filter((r) => r.key.trim()).length;

  /** An edit of Pipeline or Revision cancels the inspect in flight and forgets the last one. */
  function edit(set: (v: string) => void, value: string) {
    inFlight.current?.abort();
    inFlight.current = null;
    set(value);
    setLoading(false);
    setLoaded(null);
    setEngine(null);
    setErrors({});
  }

  async function load() {
    if (location.trim() === "") {
      setErrors({ location: "Give an absolute path or a repository." });
      return;
    }
    if (repo && revision.trim() === "") {
      setErrors({ revision: "Give a tag, branch or commit." });
      return;
    }
    inFlight.current?.abort();
    const controller = new AbortController();
    inFlight.current = controller;
    setLoading(true);
    setErrors({});
    try {
      const found = await inspect(location.trim(), repo ? revision.trim() : null, controller.signal);
      setLoaded(found);
      setEngine(guessEngine(found.engine_files));
      setProfile("");
      setValues({});
      setRows([]);
    } catch (error) {
      if (controller.signal.aborted) return; // an edit cancelled it: not an error
      setErrors(
        error instanceof ApiError && error.errors.length
          ? toErrors(error.errors, [])
          : { location: `Not loaded: ${(error as Error).message}` },
      );
    } finally {
      if (inFlight.current === controller) {
        inFlight.current = null;
        setLoading(false);
      }
    }
  }

  function reason(): string | null {
    if (loading) return "Wait for the pipeline to load";
    if (!loaded) return "Load a pipeline first";
    if (loaded.engine_files.length === 0) {
      return "No main.nf or Snakefile in this directory: check the path";
    }
    if (!engine) return "Choose the engine";
    if (!ENGINE_FILES[engine].some((f) => loaded.engine_files.includes(f))) {
      const other = NAMES[engine === "nextflow" ? "snakemake" : "nextflow"];
      return `No ${ENGINE_FILES[engine].join(" or ")} in this directory: press ${other} or check the path`;
    }
    const missing = fields.find(
      (f) => f.required && f.type !== "boolean" && String(own(values, f.key) ?? "").trim() === "",
    );
    if (missing) return `Fill the required field: ${missing.key}`;
    const badJson = fields.find((f) => f.type === "json" && jsonError(own(values, f.key)));
    if (badJson) return `${badJson.key} is not valid JSON`;
    if (sending) return "Launching…";
    return null;
  }

  async function submit() {
    if (reason() || !loaded || !engine) return;
    const params = buildParams(fields, values, rows);
    setSending(true);
    setErrors({});
    try {
      const run = await launch({
        workflow: { location: loaded.location, revision: loaded.revision, engine },
        ...(name.trim() ? { name: name.trim() } : {}),
        profiles: profile ? [profile] : [],
        params,
      });
      onLaunched(run.id);
    } catch (error) {
      setErrors(
        error instanceof ApiError && error.errors.length
          ? toErrors(error.errors, keys)
          : { form: `Not launched: ${(error as Error).message}` },
      );
    } finally {
      setSending(false);
    }
  }

  const why = reason();
  // The pinned bar on the phone says what Launch sends (UX-PAR-34).
  const summary =
    phone && loaded && engine && !why
      ? [
          `${loaded.name}${loaded.version ? ` ${loaded.version}` : ""}`,
          NAMES[engine],
          profile,
          `${plural(changed, "value", "values")} changed`,
        ]
          .filter(Boolean)
          .join(" · ")
      : null;
  const local = server?.executor === "local";
  const guessed = loaded && guessEngine(loaded.engine_files);
  const engineNote = !loaded
    ? "Load the pipeline to guess the engine"
    : loaded.engine_files.length === 0
      ? "No main.nf or Snakefile found"
      : !guessed
        ? `No guess: ${loaded.engine_files.join(" and ")} found · choose the engine`
        : engine && !ENGINE_FILES[engine].some((f) => loaded.engine_files.includes(f))
          ? `${ENGINE_FILES[engine].join(" or ")} not found: Launch will refuse. Guessed: ${NAMES[guessed]}`
          : `Guessed from ${loaded.engine_files.join(", ")} · change it if the guess is wrong`;

  return (
    <Stack className="launch-page" gap="md">
      <PageHead
        section="launch"
        title="Launch a workflow"
        sub="A directory or a Git repository: Spectio guesses the engine and builds the form from its schema."
        phoneBar="title"
      />
      <div className="launch-grid">
        <Stack gap="md">
          <Paper withBorder p="md" component="section" aria-labelledby="pipeline-title">
            <Title order={2} size="h4" id="pipeline-title" mb="sm">
              Pipeline
            </Title>
            <Group align="flex-start" gap="sm" wrap="wrap">
              <TextInput
                style={{ flex: "999 1 280px" }}
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
                onClick={load}
                aria-busy={loading || undefined}
              >
                {loading ? (repo ? "Fetching…" : "Loading…") : "Load"}
              </Button>
            </Group>
            {loaded && (
              <Paper bg="var(--sp-surface-subtle)" p="sm" mt="sm" className="launch-loaded" data-loaded>
                <span className="launch-loaded-mark">
                  {guessed ? <EngineMark engine={guessed} size={24} /> : <Icon path={ICONS.folder} size={20} />}
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
                  <Icon path={ICONS.check} size={14} stroke={2.4} />
                  <span>Loaded</span>
                </span>
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
                  onChange={(e) => setProfile(e.currentTarget.value)}
                  data={[{ value: "", label: "(none)" }, ...(loaded?.profiles ?? [])]}
                  description={engine ? PROFILE_HINTS[engine] : "From the pipeline's own configuration; passed to the engine as its profile."}
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
          </Paper>
          {loaded && (
            <Paper withBorder p="md" component="section" aria-labelledby="params-title">
              <Title order={2} size="h4" id="params-title" mb="xs">
                Parameters
              </Title>
              {sections.length > 1 && (
                <Text size="sm" c="dimmed" mb="sm">
                  {`One section per ${grouped ? "schema group" : "map of the config, its keys dotted"} · ${changed === 1 ? "1 value differs from its default" : `${changed} values differ from their defaults`}`}
                </Text>
              )}
              {skipped.length > 0 && (
                <Text size="sm" c="dimmed" mb="sm">
                  {`Not in the form: ${skipped.join(", ")}. Spectio refuses these key names; set them in the pipeline's own config.`}
                </Text>
              )}
              <Stack gap="sm">
                {sections.length === 1 && (
                  <ParamGrid
                    fields={sections[0].fields}
                    values={values}
                    errors={errors}
                    onChange={(key, v) => setValues((old) => ({ ...old, [key]: v }))}
                  />
                )}
                {sections.length > 1 && sections.map((section, i) => (
                  <ParamGroup
                    key={`${loaded.location}:${i}`}
                    id={`params-g${i}`}
                    section={section}
                    values={values}
                    errors={errors}
                    onChange={(key, v) => setValues((old) => ({ ...old, [key]: v }))}
                  />
                ))}
              </Stack>
              {sections.length === 0 && <KeyValueRows rows={rows} onChange={setRows} />}
            </Paper>
          )}
        </Stack>
        <Stack className="launch-aside" gap="md" component="aside" aria-label="Where it runs and launch">
          <Paper withBorder p="md">
            <Title order={2} size="h4" mb="sm">
              Where it runs
            </Title>
            <dl className="facts">
              <dt>Executor</dt>
              <dd>{server ? executorLabel(server.executor) : "…"}</dd>
              <dt>Node</dt>
              <dd>{server?.node ?? "…"}</dd>
              <dt>Engine</dt>
              <dd>
                {engine ? (
                  <span className="launch-engine">
                    <EngineMark engine={engine} size={16} named />
                    {`${NAMES[engine]} ${loaded?.engine_versions[engine] ?? "(version not found)"}`}
                    {server && (local ? `, as a process on ${server.node}` : `, in a tmux session on ${server.node}`)}
                  </span>
                ) : (
                  "Not chosen yet"
                )}
              </dd>
              <dt>Tasks</dt>
              <dd>
                {!server
                  ? "…"
                  : local
                    ? `run on ${server.node} by ${engine ? NAMES[engine] : "the engine"}`
                    : `sent to ${executorLabel(server.executor)} by ${engine ? NAMES[engine] : "the engine"}${
                        engine === "snakemake" ? " (--executor slurm)" : engine === "nextflow" ? " (executor slurm)" : ""
                      }`}
              </dd>
              <dt>Run directory</dt>
              <dd>{server ? `${server.runs_root}/<run ID>` : "…"}</dd>
            </dl>
            <Text size="xs" c="dimmed" mt="sm">
              The executor, the login node and the run directory are fixed for this server: there is nothing
              to choose in 0.0.1.
            </Text>
          </Paper>
          {loaded && engine && <ParamsPreview engine={engine} fields={fields} values={values} rows={rows} />}
          <div className="launch-bar">
            <div className="launch-bar-row">
              <Button
                type="button"
                className="launch-button"
                onClick={submit}
                aria-disabled={why ? true : undefined}
                data-disabled={why ? true : undefined}
                aria-describedby={why || summary ? "launch-reason" : undefined}
              >
                Launch
              </Button>
              {(why || summary) && (
                <Text id="launch-reason" size="sm" c="dimmed" className="launch-reason">
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

/** One schema group as a section that folds (UX-PAR-30): its icon, description and counts, and a
 * status that says what needs doing; open at first when it has an issue or a changed value, and
 * when the server finds an error in it. A form of one section shows its fields alone. */
function ParamGroup({
  id,
  section,
  values,
  errors,
  onChange,
}: {
  id: string;
  section: Section;
  values: Values;
  errors: Errors;
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
      reveal={failed}
      card
    >
      <ParamGrid fields={section.fields} values={values} errors={errors} onChange={onChange} />
    </FoldSection>
  );
}

function ParamGrid({
  fields,
  values,
  errors,
  onChange,
}: {
  fields: Field[];
  values: Values;
  errors: Errors;
  onChange: (key: string, value: string | boolean) => void;
}) {
  return (
    <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
      {fields.map((field) => (
        <ParamField
          key={field.key}
          field={field}
          value={own(values, field.key)}
          error={errors[`params.${field.key}`]}
          onChange={(v) => onChange(field.key, v)}
        />
      ))}
    </SimpleGrid>
  );
}

/** What Launch sends, built by the same `buildParams` as the request (UX-PAR-32). Nextflow reads
 * it as params.json; Snakemake gets the same JSON as a config file, shown here as YAML. */
function ParamsPreview({ engine, fields, values, rows }: { engine: Engine; fields: Field[]; values: Values; rows: Row[] }) {
  const snakemake = engine === "snakemake";
  const label = snakemake ? "Config preview, as YAML" : "params.json preview";
  let text: string | null;
  try {
    const params = buildParams(fields, values, rows);
    text = snakemake ? toYaml(params) : `${JSON.stringify(params, null, 2)}\n`;
  } catch {
    text = null;
  }
  return (
    <Paper withBorder p="md" component="section" aria-labelledby="preview-title">
      <Title order={2} size="h4" id="preview-title">
        {label}
      </Title>
      <Text size="sm" c="dimmed" mb="sm">
        {snakemake
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
    </Paper>
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
  const description =
    [
      field.help,
      field.type === "json" ? "JSON" : field.type,
      field.format,
      changed ? "changed" : null,
      changed ? shown || "no default" : shown,
    ]
      .filter(Boolean)
      .join(" · ") || undefined;
  const placeholder =
    field.default === undefined || typeof field.default === "boolean"
      ? undefined
      : typeof field.default === "string"
        ? field.default
        : JSON.stringify(field.default);
  const common = { label: field.label, description, error, withAsterisk: field.required };
  switch (field.type) {
    case "boolean":
      return (
        <Checkbox
          label={field.label}
          description={field.help ?? undefined}
          error={error}
          checked={typeof value === "boolean" ? value : field.default === true}
          onChange={(e) => onChange(e.currentTarget.checked)}
        />
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
          inputMode={field.type === "string" ? undefined : "decimal"}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.currentTarget.value)}
          placeholder={placeholder}
          spellCheck={false}
          autoComplete="off"
        />
      );
  }
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
