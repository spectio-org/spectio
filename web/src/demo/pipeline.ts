// The demo's pipeline (issue #160): an nf-core/rnaseq-shaped workflow, made up for the demo. Its
// steps, subworkflows, stages and links are what a GraphDocument of producer `nf-dag` carries.

export const ROOT = "NFCORE_RNASEQ:RNASEQ";
export const SAMPLES = ["WT_REP1", "WT_REP2", "WT_REP3", "KO_REP1", "KO_REP2", "KO_REP3"];

export interface Step {
  /** The qualified name, as `session.dag` gives it. */
  id: string;
  stage: string;
  /** One task per sample, or one for the whole run. */
  perSample: boolean;
  /** Seconds of simulated time for one task. */
  seconds: number;
  cpu: number;
  mem: number;
  params: string[];
  file: string;
  /** What each task writes, `{s}` being the sample. */
  outputs: string[];
}

const step = (path: string, stage: string, perSample: boolean, seconds: number, over: Partial<Step> = {}): Step => {
  const name = path.split(":").at(-1)!.toLowerCase();
  return {
    id: `${ROOT}:${path}`,
    stage,
    perSample,
    seconds,
    cpu: 0.7,
    mem: 0.4,
    params: [],
    file: `modules/nf-core/${name.replace(/_/g, "/")}/main.nf`,
    outputs: [],
    ...over,
  };
};

export const STEPS: Step[] = [
  step("PREPARE_GENOME:GUNZIP_FASTA", "prepare", false, 40, { params: ["fasta"], outputs: ["genome/genome.fa"] }),
  step("PREPARE_GENOME:GTF2BED", "prepare", false, 20, { params: ["gtf"], outputs: ["genome/genes.bed"] }),
  step("PREPARE_GENOME:STAR_GENOMEGENERATE", "prepare", false, 300, { cpu: 0.95, mem: 0.9, params: ["star_index"], outputs: ["genome/index/star/SA"] }),
  step("PREPARE_GENOME:SALMON_INDEX", "prepare", false, 180, { cpu: 0.9, mem: 0.6, outputs: ["genome/index/salmon/pos.bin"] }),
  step("FASTQ_QC_TRIM:FASTQC", "qc", true, 60, { cpu: 0.5, mem: 0.2, outputs: ["fastqc/{s}_fastqc.html"] }),
  step("FASTQ_QC_TRIM:TRIMGALORE", "qc", true, 90, { params: ["clip_r1", "skip_trimming"], outputs: ["trimgalore/{s}_trimmed.fq.gz"] }),
  step("ALIGN_STAR:STAR_ALIGN", "align", true, 240, { cpu: 0.92, mem: 0.85, params: ["aligner", "star_ignore_sjdbgtf"], outputs: ["star_salmon/{s}.Aligned.out.bam"] }),
  step("ALIGN_STAR:SAMTOOLS_SORT", "align", true, 70, { cpu: 0.6, mem: 0.5, outputs: ["star_salmon/{s}.sorted.bam"] }),
  step("ALIGN_STAR:SAMTOOLS_INDEX", "align", true, 20, { cpu: 0.3, mem: 0.1, outputs: ["star_salmon/{s}.sorted.bam.bai"] }),
  step("QUANTIFY_SALMON:SALMON_QUANT", "quant", true, 150, { cpu: 0.85, mem: 0.5, params: ["salmon_quant_libtype"], outputs: ["star_salmon/{s}/quant.sf"] }),
  step("QUANTIFY_SALMON:TXIMPORT", "quant", false, 45, { mem: 0.3, outputs: ["star_salmon/salmon.merged.gene_counts.tsv"] }),
  step("BAM_QC:QUALIMAP_RNASEQ", "qc-bam", true, 110, { cpu: 0.4, mem: 0.7, params: ["skip_qualimap"], outputs: ["star_salmon/qualimap/{s}/qualimapReport.html"] }),
  step("BAM_QC:RSEQC_INFEREXPERIMENT", "qc-bam", true, 50, { cpu: 0.3, mem: 0.2, params: ["skip_rseqc"], outputs: ["star_salmon/rseqc/{s}.infer_experiment.txt"] }),
  step("MULTIQC", "report", false, 60, { params: ["multiqc_title", "outdir"], file: "modules/nf-core/multiqc/main.nf", outputs: ["multiqc/multiqc_report.html", "multiqc/multiqc_data/multiqc.log"] }),
];

export const STAGES: Record<string, string> = {
  prepare: "Prepare genome",
  qc: "Read QC and trimming",
  align: "Alignment",
  quant: "Quantification",
  "qc-bam": "Alignment QC",
  report: "Report",
};

const at = (p: string) => `${ROOT}:${p}`;
const LINKS: [string, string][] = [
  ["PREPARE_GENOME:GUNZIP_FASTA", "PREPARE_GENOME:STAR_GENOMEGENERATE"],
  ["PREPARE_GENOME:GUNZIP_FASTA", "PREPARE_GENOME:SALMON_INDEX"],
  ["PREPARE_GENOME:GTF2BED", "BAM_QC:RSEQC_INFEREXPERIMENT"],
  ["PREPARE_GENOME:STAR_GENOMEGENERATE", "ALIGN_STAR:STAR_ALIGN"],
  ["PREPARE_GENOME:SALMON_INDEX", "QUANTIFY_SALMON:SALMON_QUANT"],
  ["FASTQ_QC_TRIM:FASTQC", "MULTIQC"],
  ["FASTQ_QC_TRIM:TRIMGALORE", "ALIGN_STAR:STAR_ALIGN"],
  ["FASTQ_QC_TRIM:TRIMGALORE", "QUANTIFY_SALMON:SALMON_QUANT"],
  ["FASTQ_QC_TRIM:TRIMGALORE", "MULTIQC"],
  ["ALIGN_STAR:STAR_ALIGN", "ALIGN_STAR:SAMTOOLS_SORT"],
  ["ALIGN_STAR:SAMTOOLS_SORT", "ALIGN_STAR:SAMTOOLS_INDEX"],
  ["ALIGN_STAR:SAMTOOLS_INDEX", "BAM_QC:QUALIMAP_RNASEQ"],
  ["ALIGN_STAR:SAMTOOLS_INDEX", "BAM_QC:RSEQC_INFEREXPERIMENT"],
  ["QUANTIFY_SALMON:SALMON_QUANT", "QUANTIFY_SALMON:TXIMPORT"],
  ["QUANTIFY_SALMON:TXIMPORT", "MULTIQC"],
  ["BAM_QC:QUALIMAP_RNASEQ", "MULTIQC"],
  ["BAM_QC:RSEQC_INFEREXPERIMENT", "MULTIQC"],
];
export const EDGES = LINKS.map(([a, b]) => ({ source: at(a), target: at(b) }));

export const PARAMS = {
  input: "samplesheet.csv",
  outdir: "results",
  genome: "GRCh38",
  fasta: "genome/GRCh38.fa.gz",
  gtf: "genome/gencode.v46.gtf",
  aligner: "star_salmon",
  salmon_quant_libtype: "A",
  clip_r1: 0,
  skip_trimming: false,
  skip_qualimap: false,
  skip_rseqc: false,
  star_ignore_sjdbgtf: false,
  multiqc_title: "Knock-out vs wild type",
};
