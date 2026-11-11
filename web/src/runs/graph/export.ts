// Export of the shown graph as a standalone SVG (and PNG through a canvas), drawn from the
// layout rather than copied from the DOM, so it has no app styles or scripts in it. Names come
// from the pipeline: escaped, never markup.
import type { Box, Placed } from "./layout";
import type { View } from "./model";

const FILL: Record<string, string> = {
  failed: "#fde2e1",
  running: "#dbe8ff",
  done: "#e0f2e9",
  up_to_date: "#e8eef5",
  pending: "#f1f3f5",
  awaiting_checkpoint: "#fff3d6",
  stopped: "#f1f3f5",
  not_needed: "#f8f9fa",
  no_tasks: "#f8f9fa",
};
const STROKE: Record<string, string> = { failed: "#c92a2a", running: "#1c6ed4", done: "#2b8a3e", awaiting_checkpoint: "#b7791f" };

export function escapeXml(text: string): string {
  return text.replace(/[<>&"']/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&apos;" })[c]!);
}

/** Where the line from box `a`'s centre to box `b`'s centre leaves `a`. */
function border(a: Box, b: Box): [number, number] {
  const [cx, cy] = [a.x + a.w / 2, a.y + a.h / 2];
  const [dx, dy] = [b.x + b.w / 2 - cx, b.y + b.h / 2 - cy];
  if (dx === 0 && dy === 0) return [cx, cy];
  const t = Math.min(dx ? a.w / 2 / Math.abs(dx) : Infinity, dy ? a.h / 2 / Math.abs(dy) : Infinity);
  return [cx + dx * t, cy + dy * t];
}

export function toSvg(view: View, placed: Placed, title: string): string {
  const all = view.nodes.map((n) => placed.boxes.get(n.id)).filter((b) => !!b);
  const width = Math.max(200, ...all.map((b) => b.x + b.w)) + 32;
  const height = Math.max(100, ...all.map((b) => b.y + b.h), ...placed.lanes.map((l) => l.y + l.h)) + 32;
  const parts: string[] = [];
  parts.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="-16 -16 ${width} ${height}" font-family="sans-serif" font-size="12">`);
  parts.push(`<title>${escapeXml(title)}</title><rect x="-16" y="-16" width="${width}" height="${height}" fill="#ffffff"/>`);
  parts.push(`<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#868e96"/></marker></defs>`);
  for (const lane of placed.lanes) {
    parts.push(`<rect x="${lane.x ?? 0}" y="${lane.y}" width="${lane.w ?? width - 32}" height="${lane.h}" rx="8" fill="#f8f9fa" stroke="#dee2e6"/>`);
    parts.push(`<text x="${(lane.x ?? 0) + 8}" y="${lane.y + 18}" fill="#495057" font-weight="600">${escapeXml(lane.label)}</text>`);
  }
  for (const e of view.edges) {
    const a = placed.boxes.get(e.source);
    const b = placed.boxes.get(e.target);
    if (!a || !b) continue;
    const [x1, y1] = border(a, b);
    const [x2, y2] = border(b, a);
    const dash = e.conditions.length ? ` stroke-dasharray="5 4"` : "";
    parts.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#868e96" stroke-width="1.5"${dash} marker-end="url(#arrow)"><title>${escapeXml(e.conditions.length ? `if ${e.conditions.join(" or ")}` : "link")}</title></line>`);
  }
  for (const n of view.nodes) {
    const b = placed.boxes.get(n.id);
    if (!b) continue;
    const status = n.status ?? "pending";
    parts.push(`<g><title>${escapeXml(`${n.step ? `${n.step} · ` : ""}${n.label} · ${n.kind} · ${status.replace(/_/g, " ")}`)}</title>`);
    parts.push(`<rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="${n.kind === "gate" ? 18 : 6}" fill="${FILL[status] ?? "#ffffff"}" stroke="${STROKE[status] ?? "#adb5bd"}"/>`);
    parts.push(`<text x="${b.x + 10}" y="${b.y + 20}" fill="#212529" font-weight="600">${escapeXml(n.label)}</text>`);
    const sub = n.kind === "job" ? `${n.step ?? ""} · ${status.replace(/_/g, " ")}` : status.replace(/_/g, " ");
    parts.push(`<text x="${b.x + 10}" y="${b.y + 38}" fill="#495057">${escapeXml(sub)}</text></g>`);
  }
  parts.push("</svg>");
  return parts.join("");
}

/** A standalone HTML page: the drawing, then the steps as a table with their links, for a
 * report or an e-mail. No script; every pipeline name is escaped. */
export function toHtml(view: View, placed: Placed, title: string, engine: string): string {
  const byId = new Map(view.nodes.map((n) => [n.id, n]));
  const rows = view.nodes
    .map((n) => {
      const after = view.edges.filter((e) => e.target === n.id).map((e) => byId.get(e.source)?.label ?? e.source);
      const counts = Object.entries(n.counts).map(([k, v]) => `${v} ${k}`).join(", ");
      return `<tr><td>${escapeXml(n.step ? `${n.step} · ${n.label}` : n.label)}</td><td>${escapeXml(n.kind)}</td><td>${escapeXml((n.status ?? "not run").replace(/_/g, " "))}</td><td>${escapeXml(counts || "—")}</td><td>${escapeXml((n.flags ?? []).join(", ") || "—")}</td><td>${escapeXml(after.join(", ") || "—")}</td></tr>`;
    })
    .join("\n");
  const when = new Date().toISOString().replace("T", " ").slice(0, 16);
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${escapeXml(title)} · workflow graph</title>
<style>body{margin:24px;font:14px/1.45 system-ui,sans-serif;color:#212529;background:#fff}.map{overflow:auto;border:1px solid #dee2e6;border-radius:8px}table{border-collapse:collapse;margin-top:16px;width:100%}th,td{border-bottom:1px solid #e9ecef;padding:4px 8px;text-align:left;vertical-align:top}th{background:#f8f9fa}small{color:#868e96}</style>
</head><body>
<h1>${escapeXml(title)}</h1>
<p><small>Workflow graph exported from Spectio on ${when} UTC · ${escapeXml(engine)} · ${view.nodes.length} boxes, ${view.edges.length} links. Hover a box for its state.</small></p>
<div class="map">${toSvg(view, placed, title)}</div>
<table><thead><tr><th>Step</th><th>Kind</th><th>State</th><th>Jobs</th><th>Marks</th><th>Runs after</th></tr></thead><tbody>
${rows}
</tbody></table>
</body></html>
`;
}

/** Saves a file the browser downloads. */
export function download(name: string, blob: Blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** The SVG drawn on a canvas at twice its size, as a PNG blob. */
export function svgToPng(svg: string): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.width * 2;
      canvas.height = img.height * 2;
      const ctx = canvas.getContext("2d");
      if (!ctx) return reject(new Error("no canvas"));
      ctx.scale(2, 2);
      ctx.drawImage(img, 0, 0);
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("no PNG"))), "image/png");
    };
    img.onerror = () => reject(new Error("the SVG could not be drawn"));
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  });
}
