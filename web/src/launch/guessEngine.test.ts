import { expect, test } from "vitest";
import { entryFiles, guessEngine } from "./guessEngine";

test("main.nf → nextflow; Snakefile or workflow/Snakefile → snakemake; both or neither → null", () => {
  expect(guessEngine(["main.nf"])).toBe("nextflow");
  expect(guessEngine(["Snakefile"])).toBe("snakemake");
  expect(guessEngine(["workflow/Snakefile"])).toBe("snakemake");
  expect(guessEngine(["Snakefile", "workflow/Snakefile"])).toBe("snakemake");
  expect(guessEngine(["main.nf", "workflow/Snakefile"])).toBeNull();
  expect(guessEngine([])).toBeNull();
});

test("#351: a main script other than main.nf is a Nextflow entry; entryFiles adds them once", () => {
  expect(guessEngine(["main_cellpose.nf"])).toBe("nextflow");
  expect(guessEngine(["main_cellpose.nf", "Snakefile"])).toBeNull();
  expect(entryFiles({ engine_files: ["main.nf"], main_scripts: ["main.nf", "main_x.nf"] })).toEqual(["main.nf", "main_x.nf"]);
  expect(entryFiles({ engine_files: ["Snakefile"], main_scripts: [] })).toEqual(["Snakefile"]);
});
