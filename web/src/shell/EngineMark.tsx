import nextflow from "../assets/logos/logo-nextflow.png";
import nfcore from "../assets/logos/logo-nf-core.png";
import snakemake from "../assets/logos/logo-snakemake.png";

// The official marks (docs/assets/logos, byte copies here so Vite bundles them), 16–24 px on
// white and never recoloured (ui-spec §4.3, §9). A pipeline shows the nf-core mark when its
// manifest name, as the API serves it, starts with "nf-core/", and its engine's mark otherwise
// (inbox #91, option (b), Thomas 2026-10-31). The engine's own places (the Engine fact, the
// engine buttons) always show the engine's mark.

type Mark = { src: string; name: string };
const MARKS: Record<string, Mark> = {
  nextflow: { src: nextflow, name: "Nextflow" },
  snakemake: { src: snakemake, name: "Snakemake" },
};
const NF_CORE: Mark = { src: nfcore, name: "nf-core" };

/** The pipeline's mark: nf-core for a name starting "nf-core/", else the engine's; null for an
 * unknown engine. */
export function markFor(engine: string | null, name: string | null): Mark | null {
  if (name?.startsWith("nf-core/")) return NF_CORE;
  return (engine && Object.hasOwn(MARKS, engine) && MARKS[engine]) || null;
}

function MarkImage({ mark, size, named }: { mark: Mark | null; size: number; named: boolean }) {
  if (!mark) return null;
  return <img className="sp-engine-mark" src={mark.src} width={size} height={size} alt={named ? "" : mark.name} />;
}

/** The engine's mark; nothing for an unknown engine. `named`: the engine's name is already
 * written beside it, so the image is decorative (`alt=""`). */
export function EngineMark({ engine, size = 20, named = false }: { engine: string | null; size?: number; named?: boolean }) {
  return <MarkImage mark={markFor(engine, null)} size={size} named={named} />;
}

/** The pipeline's mark (`markFor`); its alt text is the mark's name. */
export function PipelineMark({ engine, name, size = 20 }: { engine: string | null; name: string | null; size?: number }) {
  return <MarkImage mark={markFor(engine, name)} size={size} named={false} />;
}
