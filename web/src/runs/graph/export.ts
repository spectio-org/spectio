// Export of the shown graph as a standalone SVG (and PNG through a canvas), drawn from the
// layout rather than copied from the DOM, so it has no app styles or scripts in it. Names come
// from the pipeline: escaped, never markup.
import type { Placed } from "./layout";
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

export function toSvg(view: View, placed: Placed, title: string): string {
  const all = view.nodes.map((n) => placed.boxes.get(n.id)).filter((b) => !!b);
  const width = Math.max(200, ...all.map((b) => b.x + b.w)) + 32;
  const height = Math.max(100, ...all.map((b) => b.y + b.h), ...placed.lanes.map((l) => l.y + l.h)) + 32;
  const parts: string[] = [];
  parts.push(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="-16 -16 ${width} ${height}" font-family="sans-serif" font-size="12">`);
  parts.push(`<title>${escapeXml(title)}</title><rect x="-16" y="-16" width="${width}" height="${height}" fill="#ffffff"/>`);
  for (const lane of placed.lanes) {
    parts.push(`<rect x="0" y="${lane.y}" width="${width - 32}" height="${lane.h}" rx="8" fill="#f8f9fa" stroke="#dee2e6"/>`);
    parts.push(`<text x="8" y="${lane.y + 18}" fill="#495057" font-weight="600">${escapeXml(lane.label)}</text>`);
  }
  const center = (id: string) => {
    const b = placed.boxes.get(id)!;
    return [b.x + b.w / 2, b.y + b.h / 2];
  };
  for (const e of view.edges) {
    if (!placed.boxes.has(e.source) || !placed.boxes.has(e.target)) continue;
    const [x1, y1] = center(e.source);
    const [x2, y2] = center(e.target);
    parts.push(`<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#868e96" stroke-width="1.5"/>`);
  }
  for (const n of view.nodes) {
    const b = placed.boxes.get(n.id);
    if (!b) continue;
    const status = n.status ?? "pending";
    parts.push(`<rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="${n.kind === "gate" ? 18 : 6}" fill="${FILL[status] ?? "#ffffff"}" stroke="${STROKE[status] ?? "#adb5bd"}"/>`);
    parts.push(`<text x="${b.x + 10}" y="${b.y + 20}" fill="#212529" font-weight="600">${escapeXml(n.label)}</text>`);
    parts.push(`<text x="${b.x + 10}" y="${b.y + 38}" fill="#495057">${escapeXml(status.replace(/_/g, " "))}</text>`);
    for (const j of n.jobs ?? []) {
      const jb = placed.boxes.get(j.id);
      if (!jb) continue;
      parts.push(`<rect x="${b.x + jb.x}" y="${b.y + jb.y}" width="${jb.w}" height="${jb.h}" rx="4" fill="${FILL[j.status ?? "pending"] ?? "#fff"}" stroke="#adb5bd"/>`);
      parts.push(`<text x="${b.x + jb.x + 6}" y="${b.y + jb.y + 19}" fill="#212529">${escapeXml(j.label)}</text>`);
    }
  }
  parts.push("</svg>");
  return parts.join("");
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
