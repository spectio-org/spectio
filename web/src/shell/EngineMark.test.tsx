import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { PipelineMark, markFor } from "./EngineMark";

// Inbox #91, option (b) (Thomas, 2026-10-31): a pipeline whose manifest name starts with
// "nf-core/" shows the nf-core mark; any other shows its engine's.

test("an nf-core/ name on Nextflow shows the nf-core mark", () => {
  expect(markFor("nextflow", "nf-core/rnaseq")?.name).toBe("nf-core");
});

test("a Snakemake run shows the Snakemake mark", () => {
  expect(markFor("snakemake", "wgs-germline")?.name).toBe("Snakemake");
  expect(markFor("nextflow", null)?.name).toBe("Nextflow");
});

test("an unknown engine shows no mark", () => {
  expect(markFor("cwl", "lab/pipeline")).toBeNull();
  expect(markFor(null, null)).toBeNull();
});

test("a name that only contains nf-core does not change the mark", () => {
  expect(markFor("nextflow", "lab/nf-core-rnaseq")?.name).toBe("Nextflow");
  expect(markFor("nextflow", "my-nf-core/rnaseq")?.name).toBe("Nextflow");
  expect(markFor("nextflow", "NF-CORE/rnaseq")?.name).toBe("Nextflow");
});

test("the pipeline mark's alt text is the mark's name", () => {
  render(<PipelineMark engine="nextflow" name="nf-core/rnaseq" size={18} />);
  const img = screen.getByRole("img", { name: "nf-core" });
  expect(img).toHaveClass("sp-engine-mark");
  expect(img).toHaveAttribute("src", expect.stringContaining("logo-nf-core"));
});
