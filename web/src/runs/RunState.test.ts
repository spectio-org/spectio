// shortFailure (inbox #161): a failed run's long engine message, short and actionable.
import { describe, expect, test } from "vitest";
import { shortFailure } from "./RunState";

const COMMON = "/scratch/x/data/pipelines/github.com/org/repo/main/workflow/rules/common.smk";

describe("shortFailure", () => {
  test("Snakemake's KeyError keeps the error and one file:line, the path relative to the pipeline", () => {
    const message = `KeyError in file "${COMMON}", line 8: 'sample_sheet' File "${COMMON}", line 8, in <module>`;
    expect(shortFailure(message)).toBe("KeyError 'sample_sheet' · workflow/rules/common.smk:8");
  });

  test("the pipeline directory given shortens a path no /pipelines/ store mentions", () => {
    const message = `KeyError in file "/home/amartin/wgs/workflow/rules/common.smk", line 8: 'sample_sheet'\nFile "/home/amartin/wgs/workflow/rules/common.smk", line 8, in <module>`;
    expect(shortFailure(message, "/home/amartin/wgs")).toBe("KeyError 'sample_sheet' · workflow/rules/common.smk:8");
  });

  test("a path in the run's launch directory is made relative to the pipeline in it", () => {
    const message = `KeyError in file "/scratch/amartin/spectio-runs/run_1/launch/workflow/rules/common.smk", line 8: 'sample_sheet'`;
    expect(shortFailure(message, "/scratch/amartin/spectio-runs/run_1/launch")).toBe(
      "KeyError 'sample_sheet' · workflow/rules/common.smk:8",
    );
  });

  test("a Nextflow process error without a path comes back as its first line", () => {
    const message =
      "Process `NFCORE:RNASEQ:ALIGN (S01)` terminated with an error exit status (137)\n\nCommand error:\n  bwa: command not found";
    expect(shortFailure(message)).toBe("Process `NFCORE:RNASEQ:ALIGN (S01)` terminated with an error exit status (137)");
  });

  test("a message without a path keeps its first meaningful line", () => {
    expect(shortFailure("\n\nSLURM job 8812402 was killed by signal 9\nmore detail follows")).toBe(
      "SLURM job 8812402 was killed by signal 9",
    );
  });

  test("a repeated File …, line N trace collapses to one file:line", () => {
    const message = `Traceback (most recent call last):\n  File "${COMMON}", line 8, in <module>\n  File "${COMMON}", line 22, in <module>\nKeyError: 'sample_sheet'`;
    expect(shortFailure(message)).toBe("KeyError: 'sample_sheet' · workflow/rules/common.smk:8");
  });

  test("a very long message is capped at about 160 characters with an ellipsis", () => {
    const short = shortFailure(`Boom: ${"x".repeat(300)}`);
    expect(short.startsWith("Boom: ")).toBe(true);
    expect(short.endsWith("…")).toBe(true);
    expect(short.length).toBeLessThanOrEqual(160);
  });

  test("no message, no short failure", () => {
    expect(shortFailure("")).toBe("");
    expect(shortFailure("  \n ")).toBe("");
  });
});
