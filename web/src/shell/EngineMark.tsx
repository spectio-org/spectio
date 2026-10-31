import nextflow from "../assets/logos/logo-nextflow.png";
import snakemake from "../assets/logos/logo-snakemake.png";
import { engineName } from "../runs/stateWord";

// The engines' official marks (docs/assets/logos, copied here so Vite bundles them), 16–24 px on
// white and never recoloured (ui-spec §4.3, §9). 0.0.1 shows the engine's mark only: the API has
// no field that proves a pipeline is a genuine nf-core one, and a manifest name starting with
// "nf-core/" is only a claim any fork can make, so the nf-core mark waits (inbox #91).
const MARKS: Record<string, string> = { nextflow, snakemake };

/** The engine's mark; nothing for an unknown engine. `named`: the engine's name is already
 * written beside it, so the image is decorative (`alt=""`). */
export function EngineMark({ engine, size = 20, named = false }: { engine: string | null; size?: number; named?: boolean }) {
  const src = engine ? MARKS[engine] : undefined;
  if (!src) return null;
  return (
    <img className="sp-engine-mark" src={src} width={size} height={size} alt={named ? "" : engineName(engine)} />
  );
}
