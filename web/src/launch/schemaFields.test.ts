import { describe, expect, test } from "vitest";
import { schemaFields } from "./schemaFields";

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
});
