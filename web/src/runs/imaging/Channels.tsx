// The OME-TIFF viewer's channel list (FU-P3-102f; ui-spec §4.4.1 Channels and Contrast; board
// LiteImageViewer): "Channels · n of m on", a switch per channel, and only on the rows that are on
// the two contrast ranges and Reset, so a 40-channel image keeps about 6 × 4 tab stops. At most 6
// on (CHANNELS_ON); two channels that are on never share a colour (inbox #140, choice (a)).
import { Button, TextInput } from "@mantine/core";
import { useState } from "react";
import { CHANNELS_ON } from "./url-state";
import type { Rgb, Stats } from "./viv";

export type ChannelState = { on: number[]; colours: Record<number, Rgb>; limits: Record<number, [number, number]> };

const PALETTE: [string, Rgb][] = [["Blue", [0, 0, 255]], ["Green", [0, 255, 0]], ["Magenta", [255, 0, 255]], ["Yellow", [255, 255, 0]], ["Cyan", [0, 255, 255]], ["Orange", [255, 128, 0]]];
const same = (a: Rgb, b: Rgb) => a.every((v, i) => v === b[i]);
const hex = (c: Rgb) => `#${c.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
const colourName = (c: Rgb) => PALETTE.find(([, p]) => same(p, c))?.[0] ?? hex(c);
const text = (v: number) => v.toLocaleString("en-US", { maximumFractionDigits: 2 });

/** The metadata's colour, else the first palette colour that no channel that is on uses. */
function pickColour(meta: Rgb | null | undefined, used: Rgb[]): Rgb {
  const free = (c: Rgb) => !used.some((u) => same(u, c));
  if (meta && free(meta)) return meta;
  return PALETTE.map(([, c]) => c).find(free) ?? PALETTE[0][1];
}

function switchOn(state: ChannelState, c: number, meta: (Rgb | null)[]): ChannelState {
  const colour = pickColour(meta[c], state.on.map((o) => state.colours[o]));
  return { ...state, on: [...state.on, c], colours: { ...state.colours, [c]: colour } };
}

/** The channels on at open: those of the URL, else the first `first`. */
export function initialChannels(meta: (Rgb | null)[], fromUrl: number[] | null, first: number): ChannelState {
  const on = fromUrl ?? Array.from({ length: first }, (_, c) => c);
  return on.reduce((s, c) => switchOn(s, c, meta), { on: [], colours: {}, limits: {} } as ChannelState);
}

interface Props {
  names: string[];
  meta: (Rgb | null)[];
  state: ChannelState;
  stats: Record<number, Stats>; // per channel: the computed percentiles and the domain
  onChange: (state: ChannelState) => void;
}

export function Channels({ names, meta, state, stats, onChange }: Props) {
  const [filter, setFilter] = useState("");
  const [full, setFull] = useState(false);
  const toggle = (c: number) => {
    const on = state.on.includes(c);
    if (!on && state.on.length >= CHANNELS_ON) return setFull(true);
    setFull(false);
    onChange(on ? { ...state, on: state.on.filter((o) => o !== c) } : switchOn(state, c, meta));
  };
  const setLimits = (c: number, limits: [number, number] | undefined) => {
    const { [c]: _, ...rest } = state.limits;
    onChange({ ...state, limits: limits ? { ...rest, [c]: limits } : rest });
  };
  const shown = names.map((name, c) => ({ name, c })).filter(({ name }) => name.toLowerCase().includes(filter.trim().toLowerCase()));

  return (
    <section className="sp-ome-channels" aria-label="Channels">
      <h3 className="sp-file-cap">{`Channels · ${state.on.length} of ${names.length} on`}</h3>
      {names.length > 12 && <TextInput label="Filter channels" placeholder="By name, such as CD" value={filter} onChange={(e) => setFilter(e.currentTarget.value)} />}
      <p className="sp-ome-full" aria-live="polite">{full ? `At most ${CHANNELS_ON} channels at once: switch one off first.` : ""}</p>
      <ul className="sp-ome-list">
        {shown.map(({ name, c }) => {
          const on = state.on.includes(c);
          const s = stats[c];
          const label = `Channel ${c + 1}, ${name}`;
          const [lo, hi] = state.limits[c] ?? s?.limits ?? [0, 0];
          const range = (which: "low" | "high", value: number) => (
            <label className="sp-ome-range">
              {which === "low" ? "Low" : "High"}
              <input type="range" aria-label={`${label}, contrast ${which}`} min={s.domain[0]} max={s.domain[1]} step={(s.domain[1] - s.domain[0]) / 256 || 1} value={value}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setLimits(c, which === "low" ? [Math.min(v, hi), hi] : [lo, Math.max(v, lo)]);
                }} />
              <span>{text(value)}</span>
            </label>
          );
          return (
            <li key={c} className="sp-ome-row">
              <div className="sp-file-line">
                <span className="sp-ome-swatch" style={{ background: on ? hex(state.colours[c]) : "#9a9cab" }} />
                <span className="sp-ome-name">{`${c + 1} ${name}`}<br /><small>{on ? colourName(state.colours[c]) : "Off"}</small></span>
                <button type="button" role="switch" aria-checked={on} aria-label={`Show channel ${c + 1}, ${name}`} className="sp-ome-switch" onClick={() => toggle(c)} />
              </div>
              {on && s && (
                <>
                  {range("low", lo)}
                  {range("high", hi)}
                  <div className="sp-file-line">
                    <span className="sp-muted">{`Range ${text(s.domain[0])} to ${text(s.domain[1])}`}</span>
                    <Button variant="default" size="xs" aria-label={`Reset channel ${c + 1}, ${name} contrast`} onClick={() => setLimits(c, undefined)}>Reset contrast</Button>
                  </div>
                </>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
