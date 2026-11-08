import { type ReactNode, useState } from "react";
import type { Process, ProcessEfficiency } from "../api";
import { usePhone } from "../shell/layout";
import { bytes, isLow, isNear, percent, seconds } from "./resources";
import { Low, NearLimit, ProcessName } from "./RunState";
import { lastSegment, type words } from "./stateWord";

// The By process (Snakemake: By rule) view of the Tasks tab (ui-spec §4.4 note 2026-11-07; boards
// LiteRunEfficiency, MLiteRunEfficiency): one row per process or rule from `/processes`
// `efficiency`, over each task's last attempt (schedulers §3.6). Every header sorts with a native
// button; the row's name opens the task list filtered to it. On the phone, one card per process
// with the same facts as label and value rows, and a Sort by select. No plot in 0.0.1.

type Words = ReturnType<typeof words>;
type Key = "name" | "jobs" | "measured" | "cpu_mean" | "cpu_max" | "mem_mean" | "mem_max" | "cpus" | "mem" | "time" | "peak" | "longest";

/** A ratio and its badges: "low" under 25 %, and for memory "near limit" above 90 %. */
function Ratio({ value, memory = false }: { value: number | null; memory?: boolean }) {
  return (
    <>
      {percent(value)}
      <Low on={isLow(value)} />
      <NearLimit on={memory && isNear(value)} />
    </>
  );
}

/** One requested value; "varies" when the jobs asked for different values. */
const asked = (e: ProcessEfficiency, text: string): string => (e.requested.varies ? `${text}, varies` : text);
const cpus = (e: ProcessEfficiency): string => asked(e, e.requested.cpus === null ? "—" : String(e.requested.cpus));
const memory = (e: ProcessEfficiency): string => asked(e, bytes(e.requested.mem_bytes));
const limit = (e: ProcessEfficiency): string => asked(e, seconds(e.requested.time_limit_s));

const COLUMNS: { key: Key; label: (w: Words) => string; sort: (p: Process) => number | string | null; num?: boolean }[] = [
  { key: "name", label: (w) => w.Group, sort: (p) => lastSegment(p.process) },
  { key: "jobs", label: (w) => `${w.Units} done`, sort: (p) => p.efficiency?.jobs.done ?? null, num: true },
  { key: "measured", label: () => "Measured", sort: (p) => p.efficiency?.measured ?? null, num: true },
  { key: "cpu_mean", label: () => "CPU eff. mean", sort: (p) => p.efficiency?.cpu_mean ?? null, num: true },
  { key: "cpu_max", label: () => "CPU eff. max", sort: (p) => p.efficiency?.cpu_max ?? null, num: true },
  { key: "mem_mean", label: () => "Mem eff. mean", sort: (p) => p.efficiency?.mem_mean ?? null, num: true },
  { key: "mem_max", label: () => "Mem eff. max", sort: (p) => p.efficiency?.mem_max ?? null, num: true },
  { key: "cpus", label: () => "CPUs asked", sort: (p) => p.efficiency?.requested.cpus ?? null, num: true },
  { key: "mem", label: () => "Memory asked", sort: (p) => p.efficiency?.requested.mem_bytes ?? null, num: true },
  { key: "time", label: () => "Time limit", sort: (p) => p.efficiency?.requested.time_limit_s ?? null, num: true },
  { key: "peak", label: () => "Peak memory", sort: (p) => p.efficiency?.used.peak_rss_bytes_max ?? null },
  { key: "longest", label: () => "Longest", sort: (p) => p.efficiency?.used.elapsed_s_max ?? null, num: true },
];

/** The cells of one process, in the columns' order after the name. */
function cells(e: ProcessEfficiency | undefined): ReactNode[] {
  if (!e) return COLUMNS.slice(1).map(() => "—");
  return [
    `${e.jobs.done} / ${e.jobs.total}`,
    e.measured,
    <Ratio value={e.cpu_mean} />,
    <Ratio value={e.cpu_max} />,
    <Ratio value={e.mem_mean} memory />,
    <Ratio value={e.mem_max} memory />,
    cpus(e),
    memory(e),
    limit(e),
    bytes(e.used.peak_rss_bytes_max),
    seconds(e.used.elapsed_s_max),
  ];
}

/** The process sheet and the phone cards: the same facts as label and value rows. */
export function efficiencyFacts(e: ProcessEfficiency | undefined, w: Words): [string, ReactNode][] {
  if (!e) return [];
  return [
    [`${w.Units} done · measured`, `${e.jobs.done} / ${e.jobs.total} · ${e.measured}`],
    ["CPU eff. mean · max", <><Ratio value={e.cpu_mean} /> · <Ratio value={e.cpu_max} /></>],
    ["Mem eff. mean · max", <><Ratio value={e.mem_mean} memory /> · <Ratio value={e.mem_max} memory /></>],
    ["CPUs · memory · time limit asked", `${cpus(e)} · ${memory(e)} · ${limit(e)}`],
    ["Peak memory · longest", `${bytes(e.used.peak_rss_bytes_max)} · ${seconds(e.used.elapsed_s_max)}`],
  ];
}

/** "48 tasks of FASTQC used under 25 % of their memory.": every measured job of a process whose
 * highest memory efficiency is under 25 % (schedulers §3.5). */
export function wasteLines(processes: Process[], w: Words): string[] {
  return processes
    .filter((p) => p.efficiency && p.efficiency.measured > 0 && isLow(p.efficiency.mem_max))
    .map((p) => `${p.efficiency!.measured} ${p.efficiency!.measured === 1 ? w.unit : w.units} of ${lastSegment(p.process)} used under 25 % of their memory.`);
}

function sorted(processes: Process[], key: Key, ascending: boolean): Process[] {
  const by = COLUMNS.find((c) => c.key === key)!.sort;
  return [...processes].sort((a, b) => {
    const x = by(a);
    const y = by(b);
    if (x === y) return 0;
    if (x === null) return 1; // unknown last, whatever the direction
    if (y === null) return -1;
    return (x < y ? -1 : 1) * (ascending ? 1 : -1);
  });
}

function Show({ process, w, onShow }: { process: string; w: Words; onShow: (process: string) => void }) {
  return (
    <button type="button" className="sp-link-button sp-open" aria-label={`Show the ${w.units} of ${w.group} ${process}`} onClick={() => onShow(process)}>
      <ProcessName name={process} />
    </button>
  );
}

export function ByProcess({ processes, w, onShow }: { processes: Process[]; w: Words; onShow: (process: string) => void }) {
  const phone = usePhone();
  // lowest mean memory efficiency first: the processes that waste the most (LiteRunEfficiency)
  const [key, setKey] = useState<Key>("mem_mean");
  const [ascending, setAscending] = useState(true);
  const label = `${w.Units} by ${w.group}`;
  const rows = sorted(processes, key, ascending);
  const waste = wasteLines(processes, w);
  const sortBy = (k: Key) => {
    setAscending(k === key ? !ascending : true);
    setKey(k);
  };
  const foot = (
    <>
      {waste.map((line) => (
        <p key={line} className="sp-note">
          {line}
        </p>
      ))}
      <p className="sp-muted">
        Over each {w.unit}'s last attempt: from sacct once a {w.unit} has ended, before that from the engine's trace or
        benchmark. Asked: the most common value; "varies" when the {w.units} asked for different values.
      </p>
    </>
  );
  if (phone) {
    return (
      <section className="sp-runs" aria-label={label}>
        <label className="sp-select">
          Sort by{" "}
          <select
            value={`${key}:${ascending ? "asc" : "desc"}`}
            onChange={(e) => {
              const [k, dir] = e.currentTarget.value.split(":");
              setKey(k as Key);
              setAscending(dir === "asc");
            }}
          >
            {COLUMNS.filter((c) => c.num).flatMap((c) => [
              <option key={`${c.key}:asc`} value={`${c.key}:asc`}>
                {c.label(w)}, lowest first
              </option>,
              <option key={`${c.key}:desc`} value={`${c.key}:desc`}>
                {c.label(w)}, highest first
              </option>,
            ])}
            <option value="name:asc">{w.Group} name</option>
          </select>
        </label>
        {foot}
        <ul className="sp-cards-list" aria-label={label}>
          {rows.map((p) => (
            <li key={p.process} className="sp-row-card">
              <Show process={p.process} w={w} onShow={onShow} />
              {p.efficiency ? (
                <dl className="sp-facts sp-card-facts">
                  {efficiencyFacts(p.efficiency, w).map(([name, value]) => (
                    <div key={name}>
                      <dt>{name}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <span className="sp-muted">Not measured yet.</span>
              )}
            </li>
          ))}
        </ul>
      </section>
    );
  }
  return (
    <section className="sp-runs" aria-label={label}>
      <div className="sp-table-wrap">
        <table className="sp-table" aria-label={label}>
          <thead>
            <tr>
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  scope="col"
                  className={c.num ? "sp-num" : undefined}
                  aria-sort={c.key === key ? (ascending ? "ascending" : "descending") : undefined}
                >
                  <button type="button" className="sp-sort" aria-label={`Sort by ${c.label(w)}`} onClick={() => sortBy(c.key)}>
                    {c.label(w)}
                    {c.key === key && <span aria-hidden="true">{ascending ? " ↑" : " ↓"}</span>}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.process}>
                <td>
                  <Show process={p.process} w={w} onShow={onShow} />
                </td>
                {cells(p.efficiency).map((cell, i) => (
                  <td key={COLUMNS[i + 1].key} className={COLUMNS[i + 1].num ? "sp-num sp-nowrap-cell" : "sp-nowrap-cell"}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {foot}
    </section>
  );
}
