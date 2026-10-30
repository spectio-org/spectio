import type { JSONSchema } from "../api";

// The launch form from the pipeline's parameter schema (P1 Task 19; ui-spec §4.6): one section per
// nf-core group (`$defs` or `definitions`, in `allOf` order), else one section of the top-level
// properties (config.schema.yaml, or the schema inferred from config/config.yaml).

export type FieldType = "string" | "integer" | "number" | "boolean" | "enum" | "json";

export interface Field {
  key: string;
  label: string;
  type: FieldType;
  required: boolean;
  default: unknown;
  help: string | null;
  options?: unknown[]; // the raw enum values: an integer enum sends integers (CR-P3T19-02)
}

export interface Section {
  title: string;
  fields: Field[];
}

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const SIMPLE = ["string", "integer", "number", "boolean"];

function field(key: string, prop: Obj, required: boolean): Field {
  const enumValues = Array.isArray(prop.enum) ? prop.enum : null;
  const type = enumValues
    ? "enum"
    : SIMPLE.includes(prop.type as string)
      ? (prop.type as FieldType)
      : "json";
  const help = prop.help_text ?? prop.description;
  return {
    key,
    label: key,
    type,
    required,
    default: prop.default,
    help: typeof help === "string" ? help : null,
    ...(enumValues ? { options: enumValues } : {}),
  };
}

function section(title: string, group: Obj): Section {
  const required = Array.isArray(group.required) ? group.required : [];
  const props = isObj(group.properties) ? group.properties : {};
  const fields = Object.entries(props)
    .filter(([, p]) => isObj(p) && p.hidden !== true)
    .map(([key, p]) => field(key, p as Obj, required.includes(key)));
  return { title, fields };
}

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
      if (isObj(group)) sections.push(section(String(group.title ?? name), group));
    }
  }
  if (isObj(schema.properties)) sections.push(section(defs ? "Other parameters" : "Parameters", schema));
  return sections.filter((s) => s.fields.length > 0);
}
