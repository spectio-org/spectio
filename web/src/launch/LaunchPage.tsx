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
import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  ENGINE_FILES,
  type Engine,
  type FieldError,
  type Inspected,
  inspect,
  launch,
} from "../api";
import { useServer } from "../server";
import { EngineButtons } from "./EngineButtons";
import { guessEngine } from "./guessEngine";
import { type Field, schemaFields } from "./schemaFields";

// The 0.0.1 launch form (P1 Task 19; ui-spec §4.6 note 2026-10-29; boards LiteLaunch and
// LiteLaunchSnakemake, of which 0.0.1 shows less, UX-227). Native inputs and buttons only, a label
// on every field; a 422 lands on its field through Mantine's error, which sets aria-invalid and
// aria-describedby.

const SHORT_NAME = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9_][A-Za-z0-9._-]{0,99}$/;
const NAMES: Record<Engine, string> = { nextflow: "Nextflow", snakemake: "Snakemake" };
const SOURCES: Record<Inspected["schema_source"], string> = {
  "nextflow_schema.json": "form from nextflow_schema.json",
  "config.schema.yaml": "form from config.schema.yaml",
  inferred: "form inferred from config/config.yaml (its types are not checked)",
  none: "no parameter schema: add parameters as name and value",
};

type Errors = Record<string, string>; // by form key: location, revision, engine, name, profile, params.<key>, form
type Values = Record<string, string | boolean>;
interface Row {
  key: string;
  value: string;
}

/** Where a 422 error of `POST /runs` or of inspect is shown (fields are dotted, inbox #86). */
function formKey(field: string, keys: string[]): string {
  const bare = field.replace(/^workflow\./, "");
  if (["location", "revision", "engine", "name"].includes(bare)) return bare;
  if (bare.startsWith("profiles")) return "profile";
  const param = bare.match(/^params\.([^.]+)/)?.[1];
  return param && keys.includes(param) ? `params.${param}` : "form";
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

function paramValue(field: Field, value: string | boolean | undefined): unknown {
  if (field.type === "boolean") return value === (field.default === true) ? undefined : value;
  if (field.type === "enum") return value ? field.options?.find((o) => String(o) === value) : undefined;
  const text = typeof value === "string" ? value.trim() : "";
  if (text === "") return undefined;
  if (field.type === "integer" || field.type === "number") {
    return Number.isFinite(Number(text)) ? Number(text) : text; // the server says what is wrong
  }
  if (field.type === "json") return JSON.parse(text);
  return text;
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

export function LaunchPage({ onLaunched }: { onLaunched: (id: string) => void }) {
  const server = useServer();
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
  const sections = schemaFields(loaded?.schema ?? null);
  const fields = sections.flatMap((s) => s.fields);
  const keys = fields.map((f) => f.key);

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
      (f) => f.required && f.type !== "boolean" && String(values[f.key] ?? "").trim() === "",
    );
    if (missing) return `Fill the required field: ${missing.key}`;
    const badJson = fields.find((f) => f.type === "json" && jsonError(values[f.key]));
    if (badJson) return `${badJson.key} is not valid JSON`;
    if (sending) return "Launching…";
    return null;
  }

  async function submit() {
    if (reason() || !loaded || !engine) return;
    const params: Record<string, unknown> = {};
    for (const field of fields) {
      const value = paramValue(field, values[field.key]);
      if (value !== undefined) params[field.key] = value;
    }
    for (const row of rows) if (row.key.trim()) params[row.key.trim()] = row.value;
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
      <div>
        <Title order={1}>Launch a workflow</Title>
        <Text c="dimmed">
          A directory or a Git repository: Spectio guesses the engine and builds the form from its
          schema.
        </Text>
      </div>
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
              <Paper bg="var(--sp-surface-subtle)" p="sm" mt="sm">
                <Text fw={600}>
                  {loaded.name}
                  {loaded.version ? ` ${loaded.version}` : ""}
                </Text>
                <Text size="sm" c="dimmed">
                  {loaded.revision ? `A Git repository at ${loaded.revision}` : "A directory on this machine"}
                  {loaded.engine_files.length ? ` · ${loaded.engine_files.join(", ")} found` : ""}
                  {` · ${SOURCES[loaded.schema_source]}`}
                </Text>
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
                  value={profile}
                  onChange={(e) => setProfile(e.currentTarget.value)}
                  data={[{ value: "", label: "(none)" }, ...(loaded?.profiles ?? [])]}
                  description="From the pipeline's own configuration; passed to the engine as its profile."
                  error={errors.profile}
                />
                <TextInput
                  label="Run name (optional)"
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
              <Title order={2} size="h4" id="params-title" mb="sm">
                Parameters
              </Title>
              {sections.map((section) => (
                <fieldset key={section.title} className="param-section">
                  <legend>{section.title}</legend>
                  <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
                    {section.fields.map((field) => (
                      <ParamField
                        key={field.key}
                        field={field}
                        value={values[field.key]}
                        error={errors[`params.${field.key}`]}
                        onChange={(v) => setValues((old) => ({ ...old, [field.key]: v }))}
                      />
                    ))}
                  </SimpleGrid>
                </fieldset>
              ))}
              {sections.length === 0 && (
                <KeyValueRows rows={rows} onChange={setRows} />
              )}
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
              <dd>{server?.executor ?? "…"}</dd>
              <dt>Node</dt>
              <dd>{server?.node ?? "…"}</dd>
              <dt>Engine</dt>
              <dd>
                {engine
                  ? `${NAMES[engine]} ${loaded?.engine_versions[engine] ?? "(version not found)"}`
                  : "Not chosen yet"}
              </dd>
              <dt>Run directory</dt>
              <dd>{server ? `${server.runs_root}/<run ID>` : "…"}</dd>
            </dl>
          </Paper>
          <div className="launch-bar">
            <Group gap="sm" wrap="nowrap" align="center">
              <Button
                type="button"
                onClick={submit}
                aria-disabled={why ? true : undefined}
                data-disabled={why ? true : undefined}
                aria-describedby={why ? "launch-reason" : undefined}
              >
                Launch
              </Button>
              {why && (
                <Text id="launch-reason" size="sm" c="dimmed">
                  {why}
                </Text>
              )}
            </Group>
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
  const description = [field.help, shown].filter(Boolean).join(" · ") || undefined;
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
