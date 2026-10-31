import { describe, expect, test } from "vitest";
import { buildParams, schemaFields, toYaml } from "./schemaFields";

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
    const sections = schemaFields(smk);
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

  test("UX-PAR-31/32: the params rebuild nested maps from dotted keys, and only values set", () => {
    const [ref] = schemaFields({
      type: "object",
      properties: { ref: { type: "object", properties: { species: { type: "string" }, release: { type: "integer" } } } },
    });
    expect(buildParams(ref.fields, { "ref.release": "114", "ref.species": "" }, [])).toEqual({ ref: { release: 114 } });
    expect(buildParams([], {}, [{ key: " outdir ", value: "r" }, { key: "", value: "x" }])).toEqual({ outdir: "r" });
  });

  test("UX-PAR-32: the YAML of a config preview", () => {
    expect(
      toYaml({ units: "/g/x units.tsv", ref: { species: "homo_sapiens", release: 113 }, on: true, tags: ["a", "1"], none: {}, n: null }),
    ).toBe(
      'units: "/g/x units.tsv"\nref:\n  species: homo_sapiens\n  release: 113\n"on": true\ntags:\n  - a\n  - "1"\nnone: {}\n"n": null\n',
    );
  });
});
