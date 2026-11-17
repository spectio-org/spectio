import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { Process } from "../api";
import { ACCOUNTING_READS, ACCOUNTING_READ_MS, useAccountingReads } from "./accounting";

// The login1 retest of inbox #146 item 10: Measured stayed 0 on a finished run until a reload,
// as sacct answers on a later read and no stream frame follows (FU-P3-119).

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

// `pending`: the ended jobs sacct has not answered yet (`efficiency.pending_accounting`, CR-P3FU119-01).
const proc = (done: number, measured: number, pending = done - measured) =>
  ({ process: "ALIGN", stage_id: null, counts: { succeeded: done }, retries: 0, efficiency: { jobs: { done, total: done }, measured, pending_accounting: pending } }) as unknown as Process;

test("an ended run with jobs not measured yet is read again, at most ACCOUNTING_READS times", () => {
  const read = vi.fn();
  const { rerender } = renderHook(({ processes }) => useAccountingReads(read, "run_1", true, processes), { initialProps: { processes: [proc(4, 0)] } });
  for (let i = 1; i <= ACCOUNTING_READS + 2; i++) {
    act(() => vi.advanceTimersByTime(ACCOUNTING_READ_MS));
    rerender({ processes: [proc(4, 0)] }); // each read gives a new list
  }
  expect(read).toHaveBeenCalledTimes(ACCOUNTING_READS);
});

test("no read once every ended job is measured, nor while the run is live", () => {
  const read = vi.fn();
  const { rerender } = renderHook(({ ended, processes }) => useAccountingReads(read, "run_1", ended, processes), {
    initialProps: { ended: false, processes: [proc(4, 0)] },
  });
  act(() => vi.advanceTimersByTime(ACCOUNTING_READ_MS * 3));
  expect(read).not.toHaveBeenCalled();
  rerender({ ended: true, processes: [proc(4, 0)] });
  act(() => vi.advanceTimersByTime(ACCOUNTING_READ_MS));
  expect(read).toHaveBeenCalledTimes(1);
  rerender({ ended: true, processes: [proc(4, 4)] });
  act(() => vi.advanceTimersByTime(ACCOUNTING_READ_MS * 3));
  expect(read).toHaveBeenCalledTimes(1);
});

test("CR-P3FU119-01: a resumed run whose cached tasks have no measure is not read again", () => {
  const read = vi.fn();
  renderHook(() => useAccountingReads(read, "run_1", true, [proc(4, 0, 0)])); // 4 cached tasks
  act(() => vi.advanceTimersByTime(ACCOUNTING_READ_MS * 3));
  expect(read).not.toHaveBeenCalled();
});

test("CR-P3FU119-01: a measured failed job does not hide a succeeded job sacct has not answered", () => {
  const read = vi.fn();
  renderHook(() => useAccountingReads(read, "run_1", true, [proc(2, 2, 1)])); // 2 done, 1 failed, 2 measured
  act(() => vi.advanceTimersByTime(ACCOUNTING_READ_MS));
  expect(read).toHaveBeenCalledTimes(1);
});

test("CR-P3FU119-02: a failed read is tried again, within the same bound", () => {
  const read = vi.fn(); // fails: the processes stay as they were
  renderHook(() => useAccountingReads(read, "run_1", true, [proc(4, 0)]));
  for (let i = 0; i < ACCOUNTING_READS + 2; i++) act(() => vi.advanceTimersByTime(ACCOUNTING_READ_MS));
  expect(read).toHaveBeenCalledTimes(ACCOUNTING_READS);
});
