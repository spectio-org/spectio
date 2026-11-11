import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { Process } from "../api";
import { ACCOUNTING_READS, ACCOUNTING_READ_MS, useAccountingReads } from "./accounting";

// The login1 retest of inbox #146 item 10: Measured stayed 0 on a finished run until a reload,
// as sacct answers on a later read and no stream frame follows (FU-P3-119).

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

const proc = (done: number, measured: number) =>
  ({ process: "ALIGN", stage_id: null, counts: { succeeded: done }, retries: 0, efficiency: { jobs: { done, total: done }, measured } }) as unknown as Process;

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
