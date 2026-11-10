// The target of a run as the screens write it (ui-spec §4.15; api §5.9).
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import type { RunTarget } from "../api";
import { TargetLine, targetText } from "./target";

const NONE = { version: null, hash: null, source: null, path: null, flag: null, more: 0, checksum_changed: null };
const target = (over: Partial<RunTarget>): RunTarget => ({ ...NONE, kind: "rule", name: "x", ...over });
const fastqc = target({ kind: "module", name: "nf-core/fastqc", version: "0.0.0-6d1763b", source: "registry" });

test.each([
  [fastqc, "module nf-core/fastqc 0.0.0-6d1763b"],
  [target({ kind: "module", name: "spectio/hello", version: "1.0.0", source: "local", path: "/m" }), "module spectio/hello 1.0.0 · local"],
  [target({ kind: "module", name: "hello", source: "local" }), "module hello (no version) · local"],
  [target({ name: "qc_report", flag: "target" }), "rule qc_report"],
  [target({ kind: "file", name: "results/x.txt", more: 2 }), "file results/x.txt + 2 more targets"],
  [target({ name: "merge", flag: "until" }), "rule merge (--until)"],
  [target({ name: "merge", flag: "allowed_rules", more: 1 }), "rule merge + 1 more target (--allowed-rules)"],
])("%o reads %s", (t, text) => {
  expect(targetText(t)).toBe(text);
});

const show = (t: RunTarget) =>
  render(
    <MantineProvider>
      <TargetLine target={t} />
    </MantineProvider>,
  );

test("a registry module shows its checksum, or that it comes after install", () => {
  const { unmount } = show({ ...fastqc, hash: "b64b18ed0123456789abcdef0123456789abcdef0123456789abcdef01234567" });
  expect(screen.getByText("module nf-core/fastqc 0.0.0-6d1763b")).toBeInTheDocument();
  expect(screen.getByText("checksum b64b18ed…")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Copy the module checksum" })).toBeInTheDocument();
  expect(screen.queryByText(/checksum differs/)).not.toBeInTheDocument();
  unmount();
  show(fastqc);
  expect(screen.getByText("checksum: after install")).toBeInTheDocument();
});

test("a changed checksum is a status line naming the module and its version", () => {
  show({ ...fastqc, hash: "c".repeat(64), checksum_changed: true });
  const warning = screen.getByText("This version's checksum differs from an earlier run of nf-core/fastqc 0.0.0-6d1763b");
  expect(warning).toHaveAttribute("role", "status");
});

test("a rule or a local module has no checksum part", () => {
  show(target({ name: "qc_report", flag: "target" }));
  expect(screen.queryByText(/checksum/)).not.toBeInTheDocument();
});
