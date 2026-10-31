import type { JSONSchema } from "../api";

// The launch form from the pipeline's parameter schema (P1 Task 19; ui-spec §4.6): one section per
// nf-core group (`$defs` or `definitions`, in `allOf` order). Without groups (config.schema.yaml, or
// the schema inferred from config/config.yaml): one section of the top-level values, then one per
// nested map, whose fields have dotted keys (`ref.species`, UX-PAR-31). An inferred nested map has
// no `properties`, only its value as `default`: its keys are read from that value.

export type FieldType = "string" | "integer" | "number" | "boolean" | "enum" | "json";

export interface Field {
  /** The dotted path: the field's form key, and the name a 422 gives (`params.<key>`). */
  key: string;
  /** Where the value goes in the params: `["ref", "species"]`. */
  path: string[];
  label: string;
  type: FieldType;
  required: boolean;
  default: unknown;
  help: string | null;
  format: string | null;
  options?: unknown[]; // the raw enum values: an integer enum sends integers (CR-P3T19-02)
}

export interface Section {
  title: string;
  description: string | null;
  /** The group's `fa_icon` (nf-core), mapped to a line icon by `groupIcon`. */
  icon: string | null;
  fields: Field[];
}

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const SIMPLE = ["string", "integer", "number", "boolean"];
const text = (v: unknown) => (typeof v === "string" ? v : null);

/** A value's schema, as the server infers it from config/config.yaml (`workflows.py` `_type`). */
function inferred(value: unknown): Obj {
  const type =
    typeof value === "boolean" ? "boolean"
    : Number.isInteger(value) ? "integer"
    : typeof value === "number" ? "number"
    : typeof value === "string" ? "string"
    : Array.isArray(value) ? "array"
    : "object";
  return { type, default: value };
}

/** A map's own properties, or, for an inferred map, those of its default value. */
function propertiesOf(prop: Obj): Obj | null {
  if (isObj(prop.properties)) return prop.properties;
  if (prop.type === "object" && isObj(prop.default) && Object.keys(prop.default).length) {
    return Object.fromEntries(Object.entries(prop.default).map(([k, v]) => [k, inferred(v)]));
  }
  return null;
}

function field(path: string[], prop: Obj, required: boolean): Field {
  const enumValues = Array.isArray(prop.enum) ? prop.enum : null;
  const type = enumValues
    ? "enum"
    : SIMPLE.includes(prop.type as string)
      ? (prop.type as FieldType)
      : "json";
  const key = path.join(".");
  return {
    key,
    path,
    label: key,
    type,
    required,
    default: prop.default,
    help: text(prop.help_text) ?? text(prop.description),
    format: text(prop.format),
    ...(enumValues ? { options: enumValues } : {}),
  };
}

/** The fields of a map, its nested maps flattened to dotted keys when `nest`. */
function fields(group: Obj, prefix: string[], nest: boolean): Field[] {
  const required = Array.isArray(group.required) ? group.required : [];
  const props = propertiesOf(group) ?? {};
  const parentDefault = isObj(group.default) ? group.default : {};
  return Object.entries(props).flatMap(([key, p]) => {
    if (!isObj(p) || p.hidden === true) return [];
    const prop = p.default === undefined && key in parentDefault ? { ...p, default: parentDefault[key] } : p;
    const path = [...prefix, key];
    if (nest && propertiesOf(prop)) return fields(prop, path, true);
    return [field(path, prop, required.includes(key))];
  });
}

const section = (title: string, group: Obj, prefix: string[], nest: boolean): Section => ({
  title,
  description: text(group.description),
  icon: text(group.fa_icon),
  fields: fields(group, prefix, nest),
});

export function schemaFields(schema: JSONSchema | null): Section[] {
  if (!schema) return [];
  const defs = isObj(schema.$defs) ? schema.$defs : isObj(schema.definitions) ? schema.definitions : null;
  const sections: Section[] = [];
  if (defs) {
    const refs = (Array.isArray(schema.allOf) ? schema.allOf : [])
      .map((a) => (isObj(a) && typeof a.$ref === "string" ? a.$ref.split("/").pop() : undefined))
      .filter((name): name is string => !!name && name in defs);
    const names = [...new Set([...refs, ...Object.keys(defs)])];
    for (const name of names) {
      const group = defs[name];
      if (isObj(group)) sections.push(section(String(group.title ?? name), group, [], false));
    }
    if (isObj(schema.properties)) sections.push({ ...section("Other parameters", schema, [], false), description: null });
    return sections.filter((s) => s.fields.length > 0);
  }
  if (!isObj(schema.properties)) return [];
  const props = schema.properties;
  const maps = Object.keys(props).filter((k) => isObj(props[k]) && propertiesOf(props[k] as Obj));
  const top = { ...schema, properties: Object.fromEntries(Object.entries(props).filter(([k]) => !maps.includes(k))) };
  sections.push({ ...section("Parameters", top, [], false), description: null, icon: null });
  for (const key of maps) {
    const map = props[key] as Obj;
    sections.push(section(key, map, [key], true));
  }
  return sections.filter((s) => s.fields.length > 0);
}

// --- The params a launch sends (UX-PAR-32: the preview and the request are built here, once) ---

export type Values = Record<string, string | boolean>;
export interface Row {
  key: string;
  value: string;
}

/** The value a field sends, or undefined: an empty field, or a checkbox left at its default. A
 * JSON field that does not parse throws; Launch refuses it first. */
export function paramValue(field: Field, value: string | boolean | undefined): unknown {
  if (field.type === "boolean") return value === undefined || value === (field.default === true) ? undefined : value;
  if (field.type === "enum") return value ? field.options?.find((o) => String(o) === value) : undefined;
  const typed = typeof value === "string" ? value.trim() : "";
  if (typed === "") return undefined;
  if (field.type === "integer" || field.type === "number") {
    return Number.isFinite(Number(typed)) ? Number(typed) : typed; // the server says what is wrong
  }
  if (field.type === "json") return JSON.parse(typed);
  return typed;
}

/** True when the field sends a value that differs from its default ("changed"). */
export function isChanged(field: Field, value: string | boolean | undefined): boolean {
  try {
    const sent = paramValue(field, value);
    return sent !== undefined && JSON.stringify(sent) !== JSON.stringify(field.default);
  } catch {
    return true; // JSON that does not parse yet: not the default
  }
}

/** The params of `POST /runs`: only the values set, nested maps rebuilt from dotted keys, then the
 * name and value rows of a pipeline with no schema. */
export function buildParams(fields: Field[], values: Values, rows: Row[]): Record<string, unknown> {
  const params: Record<string, unknown> = {};
  for (const field of fields) {
    const value = paramValue(field, values[field.key]);
    if (value === undefined) continue;
    let at = params;
    for (const part of field.path.slice(0, -1)) at = (at[part] ??= {}) as Record<string, unknown>;
    at[field.path[field.path.length - 1]] = value;
  }
  for (const row of rows) if (row.key.trim()) params[row.key.trim()] = row.value;
  return params;
}

// A string YAML reads back as itself, unquoted: no number, boolean or null look-alike (YAML 1.1,
// as PyYAML reads it: yes, no, on, off too), no indicator or space.
const PLAIN = /^[A-Za-z_/.][\w./@+-]*$/;
const RESERVED = /^(true|false|yes|no|y|n|on|off|null|~|\.inf|\.nan)$/i;
const scalar = (v: unknown) =>
  typeof v === "string" ? (PLAIN.test(v) && !RESERVED.test(v) ? v : JSON.stringify(v)) : JSON.stringify(v ?? null);

/** The params as YAML, for the Snakemake preview: block maps and lists, two spaces a level. */
export function toYaml(value: unknown, indent = ""): string {
  if (Array.isArray(value)) {
    if (!value.length) return "[]\n";
    // an item that is itself a map or a list stays in flow style: JSON is YAML
    return value.map((v) => `${indent}- ${isObj(v) || Array.isArray(v) ? JSON.stringify(v) : scalar(v)}\n`).join("");
  }
  if (isObj(value)) {
    if (!Object.keys(value).length) return "{}\n";
    return Object.entries(value)
      .map(([k, v]) => {
        const nested = (isObj(v) && Object.keys(v).length) || (Array.isArray(v) && v.length);
        return nested ? `${indent}${scalar(k)}:\n${toYaml(v, `${indent}  `)}` : `${indent}${scalar(k)}: ${toYaml(v, "").trimEnd()}\n`;
      })
      .join("");
  }
  return `${scalar(value)}\n`;
}
