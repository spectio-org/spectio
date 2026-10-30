import { expect, test } from "vitest";
import { guessEngine } from "./guessEngine";

test("main.nf → nextflow; Snakefile or workflow/Snakefile → snakemake; both or neither → null", () => {
  expect(guessEngine(["main.nf"])).toBe("nextflow");
  expect(guessEngine(["Snakefile"])).toBe("snakemake");
  expect(guessEngine(["workflow/Snakefile"])).toBe("snakemake");
  expect(guessEngine(["Snakefile", "workflow/Snakefile"])).toBe("snakemake");
  expect(guessEngine(["main.nf", "workflow/Snakefile"])).toBeNull();
  expect(guessEngine([])).toBeNull();
});
