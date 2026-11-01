import { describe, expect, test } from "vitest";
import { type Field, buildParams, checkValue, isChanged, own, schemaFields, toYaml } from "./schemaFields";

// The nf-core shape: groups under $defs (draft 2020-12) or definitions (draft 7), in allOf order.
const nfDefs = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  type: "object",
  $defs: {
    options: {
      title: "Options",
      type: "object",
      properties: {
        aligner: { type: "string", enum: ["star_salmon", "hisat2"], default: "star_salmon" },
        min_mapped_reads: { type: "number", default: 5, description: "Minimum % mapped." },
        skip_qc: { type: "boolean" },
        max_cpus: { type: "integer", hidden: true },
        extra: { type: "object" },
      },
    },
    input_output: {
      title: "Input/output",
      description: "Where the data is.",
      fa_icon: "fas fa-folder-open",
      type: "object",
      required: ["input"],
      properties: {
        input: { type: "string", format: "file-path", help_text: "A samplesheet." },
        outdir: { type: "string" },
      },
    },
  },
  allOf: [{ $ref: "#/$defs/input_output" }, { $ref: "#/$defs/options" }],
};
const draft7 = { ...nfDefs, $defs: undefined, definitions: nfDefs.$defs, allOf: [
  { $ref: "#/definitions/input_output" }, { $ref: "#/definitions/options" }] };

describe("schemaFields", () => {
  test("groups from $defs and definitions", () => {
    expect(schemaFields(nfDefs).map((s) => s.title)).toEqual(["Input/output", "Options"]);
    expect(schemaFields(draft7).map((s) => s.title)).toEqual(["Input/output", "Options"]);
  });

  test("hidden fields skipped, enums kept", () => {
    const options = schemaFields(nfDefs)[1].fields;
    expect(options.map((f) => f.key)).toEqual([
      "aligner", "min_mapped_reads", "skip_qc", "extra",
    ]);
    expect(options[0]).toMatchObject({ type: "enum", options: ["star_salmon", "hisat2"], default: "star_salmon" });
    expect(options[1]).toMatchObject({ type: "number", help: "Minimum % mapped.", required: false });
    expect(options[2].type).toBe("boolean");
    expect(options[3].type).toBe("json");
    expect(schemaFields(nfDefs)[0].fields[0]).toMatchObject({
      key: "input", label: "input", type: "string", required: true, help: "A samplesheet.",
    });
  });

  test("no schema → empty sections (key/value rows)", () => expect(schemaFields(null)).toEqual([]));

  test("top-level properties (config.schema.yaml, inferred) → one section", () => {
    const smk = { type: "object", required: ["samples"], properties: {
      samples: { type: "string" }, threads: { type: "integer", default: 4 }, ref: { type: "object" } } };
    const [section] = schemaFields(smk);
    expect(section.title).toBe("Parameters");
    expect(section.fields.map((f) => [f.key, f.type, f.required])).toEqual([
      ["samples", "string", true], ["threads", "integer", false], ["ref", "json", false],
    ]);
  });
  test("UX-PAR-30: a group keeps its description and its fa_icon; a field its format", () => {
    const [io, options] = schemaFields(nfDefs);
    expect(io).toMatchObject({ title: "Input/output", description: "Where the data is.", icon: "fas fa-folder-open" });
    expect(options).toMatchObject({ description: null, icon: null });
    expect(io.fields[0]).toMatchObject({ format: "file-path", path: ["input"] });
  });

  test("UX-PAR-31: a nested map is a section of dotted keys, from its properties or its default", () => {
    const smk = {
      type: "object",
      required: ["samples"],
      properties: {
        samples: { type: "string" },
        ref: {
          type: "object",
          description: "Reference genome",
          required: ["species"],
          properties: { species: { type: "string", default: "homo_sapiens" }, release: { type: "integer", default: 113 } },
        },
        // inferred from config/config.yaml: an object with its value as default, no properties
        pca: { type: "object", default: { activate: false, labels: ["condition"], deep: { k: 1 } } },
        free: { type: "object" },
      },
    };
    // CR-P3PARB-02: Nextflow (no nest) keeps each map as one JSON field
    expect(schemaFields(smk).flatMap((s) => s.fields).map((f) => [f.key, f.type])).toEqual([
      ["samples", "string"], ["ref", "json"], ["pca", "json"], ["free", "json"],
    ]);
    const sections = schemaFields(smk, [], true);
    expect(sections.map((s) => s.title)).toEqual(["Parameters", "ref", "pca"]);
    expect(sections[0].fields.map((f) => [f.key, f.type])).toEqual([["samples", "string"], ["free", "json"]]);
    expect(sections[1].description).toBe("Reference genome");
    expect(sections[1].fields.map((f) => [f.key, f.type, f.required, f.default])).toEqual([
      ["ref.species", "string", true, "homo_sapiens"],
      ["ref.release", "integer", false, 113],
    ]);
    expect(sections[2].fields.map((f) => [f.key, f.type, f.default])).toEqual([
      ["pca.activate", "boolean", false],
      ["pca.labels", "json", ["condition"]],
      ["pca.deep.k", "integer", 1],
    ]);
    expect(sections[2].fields[2].path).toEqual(["pca", "deep", "k"]);
  });

  test("UX-PAR-31/32: the params rebuild nested maps from dotted keys; a map with one value set is sent whole", () => {
    const schema = {
      type: "object",
      properties: {
        ref: { type: "object", properties: { species: { type: "string", default: "homo_sapiens" }, release: { type: "integer" }, build: { type: "string" } } },
        pca: { type: "object", properties: { activate: { type: "boolean", default: false } } },
      },
    };
    const [ref, pca] = schemaFields(schema, [], true);
    const all = [...ref.fields, ...pca.fields];
    // CR-P3PARB-04 r2: species goes at its default; build has none and stays out; pca is untouched
    expect(buildParams(all, { "ref.release": "114", "ref.species": "" }, [])).toEqual({ ref: { species: "homo_sapiens", release: 114 } });
    expect(buildParams(all, {}, [])).toEqual({});
    const [m] = schemaFields({ type: "object", properties: { m: { type: "object", properties: { j: { type: "array", default: [1] } } } } }, [], true);
    expect(buildParams(m.fields, { "m.j": "null" }, [])).toEqual({ m: { j: null } }); // a typed null is a value
    expect(buildParams([], {}, [{ key: " outdir ", value: "r" }, { key: "", value: "x" }])).toEqual({ outdir: "r" });
  });

  test("SEC-P3PARB-03: two fields with one dotted key keep the first, the second is named", () => {
    const skipped: string[] = [];
    const sections = schemaFields({ type: "object", properties: { "a.b": { type: "integer" }, a: { type: "object", default: { b: 2 } } } }, skipped, true);
    expect(sections.flatMap((s) => s.fields).map((f) => f.path)).toEqual([["a.b"]]);
    expect(skipped).toEqual(["a.b"]);
  });

  test("CR-P3PARB-03: a string with a leading dot is quoted, as PyYAML would read it as a float", () => {
    expect(toYaml({ a: ".5", b: "._1", c: "./data" })).toBe('a: ".5"\nb: "._1"\nc: "./data"\n');
  });

  test("UX-PAR-32: the YAML of a config preview", () => {
    expect(
      toYaml({ units: "/g/x units.tsv", ref: { species: "homo_sapiens", release: 113 }, on: true, tags: ["a", "1"], none: {}, n: null }),
    ).toBe(
      'units: "/g/x units.tsv"\nref:\n  species: homo_sapiens\n  release: 113\n"on": true\ntags:\n  - a\n  - "1"\nnone: {}\n"n": null\n',
    );
  });
});

// SEC-P3PARB-01: schema and config keys come from the pipeline. `__proto__`, `constructor` and
// `prototype` are refused (and named), never written through, so Object.prototype stays clean.
describe("untrusted keys", () => {
  // JSON.parse makes `__proto__` an own key, as the inspect response does
  const schema = JSON.parse(`{
    "type": "object",
    "properties": {
      "__proto__": { "type": "object", "properties": { "polluted": { "type": "string" } } },
      "constructor": { "type": "object", "default": { "prototype": { "polluted": "yes" } } },
      "toString": { "type": "boolean" },
      "ok": { "type": "string" }
    }
  }`);

  test("the keys are skipped and named, Object.prototype stays clean", () => {
    const skipped: string[] = [];
    const fields = schemaFields(schema, skipped).flatMap((s) => s.fields);
    expect(fields.map((f) => f.key)).toEqual(["toString", "ok"]);
    expect(skipped).toEqual(["__proto__", "constructor"]);
    const params = buildParams(fields, { ok: "a" }, [{ key: "__proto__", value: "x" }]);
    expect(JSON.stringify(params)).toBe('{"ok":"a","__proto__":"x"}');
    expect(({} as Record<string, unknown>).polluted).toBeUndefined();
    const nested: string[] = [];
    expect(schemaFields(schema, nested, true).flatMap((s) => s.fields).map((f) => f.key)).toEqual(["toString", "ok"]);
    expect(nested).toEqual(["__proto__", "constructor"]);
  });

  test("a nested map path cannot reach Object.prototype", () => {
    const field = { key: "__proto__.polluted", path: ["__proto__", "polluted"], label: "", type: "string" as const, required: false, default: undefined, help: null, format: null };
    expect(() => buildParams([field], { "__proto__.polluted": "yes" }, [])).not.toThrow();
    expect(({} as Record<string, unknown>).polluted).toBeUndefined();
  });

  test("an inherited name in the values is not a value", () => {
    const [toString] = schemaFields(schema).flatMap((s) => s.fields);
    expect(buildParams([toString], {}, [])).toEqual({});
    expect(isChanged(toString, own({}, "toString"))).toBe(false);
  });
});

// The client check before Launch (Thomas, 2026-10-31, todo.md UI; P1 Task 32): one test per rule.
describe("checkValue", () => {
  const f = (over: Partial<Field>): Field => ({ key: "x", path: ["x"], label: "x", type: "string", required: false, default: undefined, help: null, format: null, ...over });

  test("an empty optional field is valid; an empty required one is not", () => {
    expect(checkValue(f({}), undefined)).toBeNull();
    expect(checkValue(f({}), "  ")).toBeNull();
    expect(checkValue(f({ type: "integer" }), "")).toBeNull();
    expect(checkValue(f({ required: true }), "")).toBe("Required: give a value.");
    expect(checkValue(f({ required: true, type: "enum", options: ["a"] }), undefined)).toBe("Required: give a value.");
  });

  test("integer: a whole number, sign allowed", () => {
    expect(checkValue(f({ type: "integer" }), "-12")).toBeNull();
    expect(checkValue(f({ type: "integer" }), "1.5")).toBe("Must be a whole number, such as 10.");
    expect(checkValue(f({ type: "integer" }), "1e3")).toBe("Must be a whole number, such as 10.");
    expect(checkValue(f({ type: "integer" }), "ten")).toBe("Must be a whole number, such as 10.");
  });

  test("number (float): decimals and exponents, not hex or words", () => {
    for (const ok of ["0.5", ".5", "-3", "1e-3", "10."]) expect(checkValue(f({ type: "number" }), ok)).toBeNull();
    for (const bad of ["0x10", "1,5", "Infinity", "abc"]) expect(checkValue(f({ type: "number" }), bad)).toBe("Must be a number, such as 0.5.");
  });

  test("string: any text", () => {
    expect(checkValue(f({}), "anything at all")).toBeNull();
  });

  test("boolean: true or false only", () => {
    expect(checkValue(f({ type: "boolean" }), true)).toBeNull();
    expect(checkValue(f({ type: "boolean", required: true }), undefined)).toBeNull(); // a checkbox always has a value
    expect(checkValue(f({ type: "boolean" }), "yes")).toBe("Must be true or false.");
  });

  test("enum: one of the listed values", () => {
    expect(checkValue(f({ type: "enum", options: [1, 2] }), "2")).toBeNull();
    expect(checkValue(f({ type: "enum", options: ["star", "hisat2"] }), "bowtie")).toBe("Must be one of: star, hisat2.");
  });

  test("minimum and maximum, inclusive", () => {
    const depth = f({ type: "integer", minimum: 1, maximum: 10 });
    expect(checkValue(depth, "1")).toBeNull();
    expect(checkValue(depth, "10")).toBeNull();
    expect(checkValue(depth, "0")).toBe("Must be at least 1.");
    expect(checkValue(depth, "11")).toBe("Must be at most 10.");
    expect(checkValue(f({ type: "number", minimum: 0.5 }), "0.4")).toBe("Must be at least 0.5.");
  });

  test("pattern: matched anywhere, as JSON Schema says; an invalid regex is skipped, never thrown", () => {
    const csv = f({ pattern: "^\\S+\\.csv$" });
    expect(checkValue(csv, "/data/s.csv")).toBeNull();
    expect(checkValue(csv, "/data/s.tsv")).toBe("Must match the pattern ^\\S+\\.csv$.");
    expect(checkValue(f({ pattern: "[unclosed" }), "anything")).toBeNull();
  });

  test("JSON: a value that parses", () => {
    expect(checkValue(f({ type: "json" }), "[1, 2]")).toBeNull();
    expect(checkValue(f({ type: "json" }), "[1,")).toBe("Not valid JSON.");
  });
});

describe("constraints and required from the schema", () => {
  test("minimum, maximum and pattern are read; required comes from the group's list and the top level", () => {
    const schema = {
      type: "object",
      required: ["outdir"],
      $defs: {
        io: {
          title: "IO",
          required: ["input"],
          properties: {
            input: { type: "string", pattern: "\\.csv$" },
            outdir: { type: "string" },
            depth: { type: "integer", minimum: 1, maximum: 9 },
          },
        },
      },
      allOf: [{ $ref: "#/$defs/io" }],
    };
    const [io] = schemaFields(schema);
    const by = Object.fromEntries(io.fields.map((x) => [x.key, x]));
    expect([by.input.required, by.outdir.required, by.depth.required]).toEqual([true, true, false]);
    expect(by.input.pattern).toBe("\\.csv$");
    expect([by.depth.minimum, by.depth.maximum]).toEqual([1, 9]);
  });
});
