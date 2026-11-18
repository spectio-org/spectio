// The OME-TIFF viewer's channel list (FU-P3-102f; ui-spec §4.4.1 Channels and Contrast): switches
// named by channel, contrast ranges and Reset only on the rows that are on, at most 6 on, two
// channels that are on never share a colour, the filter above 12 channels.
import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { expect, test } from "vitest";
import { type ChannelState, Channels, initialChannels } from "./Channels";

const names = (n: number) => Array.from({ length: n }, (_, c) => (c === 1 ? "A very long marker name, Histone H3 (In113)" : `Channel ${c + 1}`));
const stats = (n: number) => Object.fromEntries(Array.from({ length: n }, (_, c) => [c, { limits: [10, 200] as [number, number], domain: [0, 256] as [number, number] }]));

function Panel({ n, meta = [] }: { n: number; meta?: ([number, number, number] | null)[] }) {
  const [state, setState] = useState<ChannelState>(() => initialChannels(meta, null, Math.min(6, n)));
  return (
    <MantineProvider>
      <Channels names={names(n)} meta={meta} state={state} stats={stats(n)} onChange={setState} />
    </MantineProvider>
  );
}

test("each row that is on: its switch, two named ranges, their values as text and Reset", () => {
  render(<Panel n={3} />);
  expect(screen.getByRole("heading", { name: "Channels · 3 of 3 on" })).toBeInTheDocument();
  const sw = screen.getByRole("switch", { name: "Show channel 2, A very long marker name, Histone H3 (In113)" });
  expect(sw.tagName).toBe("BUTTON");
  expect(sw).toHaveAttribute("aria-checked", "true");
  const low = screen.getByRole("slider", { name: "Channel 1, Channel 1, contrast low" });
  expect(low).toHaveAttribute("step", "1"); // a 256th of the domain
  fireEvent.change(low, { target: { value: "250" } });
  expect(low).toHaveValue("200"); // the low value is never above the high one
  fireEvent.change(screen.getByRole("slider", { name: "Channel 1, Channel 1, contrast high" }), { target: { value: "220" } });
  fireEvent.change(low, { target: { value: "30" } });
  expect(screen.getAllByText("30")).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "Reset channel 1, Channel 1 contrast" }));
  expect(low).toHaveValue("10"); // back to the computed percentiles
  expect(screen.getByText("Blue")).toBeInTheDocument();
});

test("an off row has no colour and no ranges; switched on it takes a colour no channel that is on uses", () => {
  render(<Panel n={3} meta={[[0, 0, 255], [0, 0, 255], null]} />); // two channels with the same colour in the metadata
  expect(screen.getAllByText("Blue")).toHaveLength(1);
  const sw = screen.getByRole("switch", { name: "Show channel 1, Channel 1" });
  fireEvent.click(sw);
  expect(sw).toHaveAttribute("aria-checked", "false");
  expect(screen.queryByRole("slider", { name: /^Channel 1,/ })).toBeNull();
  expect(screen.getByText("Off")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Channels · 2 of 3 on" })).toBeInTheDocument();
});

test("40 channels: 6 on, a 7th says so and stays off, the filter finds by name", () => {
  render(<Panel n={40} />);
  expect(screen.getByRole("heading", { name: "Channels · 6 of 40 on" })).toBeInTheDocument();
  expect(screen.getAllByRole("slider")).toHaveLength(12);
  const seventh = screen.getByRole("switch", { name: "Show channel 7, Channel 7" });
  fireEvent.click(seventh);
  expect(seventh).toHaveAttribute("aria-checked", "false");
  expect(screen.getByText("At most 6 channels at once: switch one off first.")).toBeInTheDocument();
  fireEvent.change(screen.getByRole("textbox", { name: "Filter channels" }), { target: { value: "HISTONE" } });
  expect(screen.getAllByRole("switch")).toHaveLength(1);
  expect(screen.getByRole("region", { name: "Channels" })).toBeInTheDocument();
});

test("12 channels or fewer: no filter", () => {
  render(<Panel n={12} />);
  expect(screen.queryByRole("textbox", { name: "Filter channels" })).toBeNull();
});
