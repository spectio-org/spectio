// The grid's text comparator (ui-spec §4.13), apart from DataGrid so the page that uses it does not
// pull AG Grid into the main chunk.
const words = new Intl.Collator(undefined, { numeric: true });

/** Two cell texts: as numbers when both are numbers, else as words ("a2" before "a10"). */
export function compareText(a: unknown, b: unknown): number {
  const [x, y] = [String(a ?? ""), String(b ?? "")];
  const [m, n] = [Number(x), Number(y)];
  return x.trim() !== "" && y.trim() !== "" && Number.isFinite(m) && Number.isFinite(n) ? m - n : words.compare(x, y);
}
