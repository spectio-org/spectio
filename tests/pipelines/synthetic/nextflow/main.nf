#!/usr/bin/env nextflow
/*
 * Spectio synthetic scenario pipeline (Nextflow DSL2).
 * Three stages with two gate points, the same as tests/pipelines/synthetic/snakemake:
 *   qc     : MAKE_READS -> QC_STATS -> QC_REPORT        (gate "qc" after QC_REPORT)
 *   align  : SPLIT (dynamic fan-out) -> ALIGN            (gate "align" after ALIGN)
 *   quant  : MERGE -> COMPARE (per group vs ctrl) -> FINAL_REPORT
 * Every process honours task.ext.when, so Spectio can stop at a gate with a generated config
 * (conf/stop_after_qc.config) and continue with -resume.
 * Failure injection: --fail_mode exit|oom|oom_once|oom_real|timeout|flaky  --fail_process NAME  --fail_sample ID
 */
nextflow.enable.dsl = 2

params.input        = "${projectDir}/../data/samplesheet.csv"
params.outdir       = "results"
params.chunks       = 0          // 0 = dynamic: one chunk per 100 reads
params.scale        = 1          // >1 adds synthetic ctrl samples X0001.. for fan-out stress
params.fail_mode    = "none"
params.fail_process = ""
params.fail_sample  = ""
params.fail_gb      = 2
params.seed         = 42

def failHook(proc, sample) {
    (params.fail_mode != "none" && params.fail_process == proc && (!params.fail_sample || params.fail_sample == sample)) ?
        "synth.py fail ${params.fail_mode} \${SPECTIO_ATTEMPT:-1} ${params.fail_gb}" : "true"
}

process MAKE_READS {
    tag "$sample"
    label 'qc'
    input:  tuple val(sample), val(group), val(n_reads)
    output: tuple val(sample), val(group), path("${sample}.reads.txt")
    when:   task.ext.when == null || task.ext.when
    script:
    """
    export SPECTIO_ATTEMPT=${task.attempt}
    ${failHook('MAKE_READS', sample)}
    synth.py reads ${sample} ${n_reads} ${params.seed} ${sample}.reads.txt
    """
}

process QC_STATS {
    tag "$sample"
    label 'qc'
    publishDir "${params.outdir}/qc/per_sample", mode: 'copy'
    input:  tuple val(sample), val(group), path(reads)
    output: path("${sample}.qc.json")
    when:   task.ext.when == null || task.ext.when
    script:
    """
    export SPECTIO_ATTEMPT=${task.attempt}
    ${failHook('QC_STATS', sample)}
    synth.py stats ${reads} ${sample}.qc.json
    """
}

process QC_REPORT {
    label 'qc'
    publishDir "${params.outdir}/multiqc", mode: 'copy'
    input:  path(jsons)
    output: path("general_stats.tsv"), emit: tsv
            path("multiqc_data.json"), emit: json
            path("multiqc_report.html"), emit: html
    when:   task.ext.when == null || task.ext.when
    script:
    """
    export SPECTIO_ATTEMPT=${task.attempt}
    ${failHook('QC_REPORT', '')}
    synth.py report general_stats.tsv multiqc_data.json multiqc_report.html ${jsons}
    """
}

process SPLIT {
    tag "$sample"
    label 'align'
    input:  tuple val(sample), val(group), path(reads)
    output: tuple val(sample), path("chunks/*.txt")
    when:   task.ext.when == null || task.ext.when
    script:
    // params from the command line arrive as strings: "0" must mean dynamic, not one chunk
    def n = (params.chunks as int) > 0 ? params.chunks : "\$(( (\$(wc -l < ${reads}) + 99) / 100 ))"
    """
    export SPECTIO_ATTEMPT=${task.attempt}
    ${failHook('SPLIT', sample)}
    synth.py split ${reads} ${n} chunks
    """
}

process ALIGN {
    tag "${chunk.baseName}"
    label 'align'
    input:  tuple val(sample), path(chunk)
    output: path("${chunk.baseName}.counts.tsv")
    when:   task.ext.when == null || task.ext.when
    script:
    """
    export SPECTIO_ATTEMPT=${task.attempt}
    ${failHook('ALIGN', sample)}
    synth.py align ${chunk} ${chunk.baseName}.counts.tsv
    """
}

process MERGE {
    label 'quant'
    publishDir "${params.outdir}/quant", mode: 'copy'
    input:  path(counts)
    output: path("counts_matrix.tsv")
    when:   task.ext.when == null || task.ext.when
    script:
    """
    export SPECTIO_ATTEMPT=${task.attempt}
    ${failHook('MERGE', '')}
    synth.py merge counts_matrix.tsv ${counts}
    """
}

process COMPARE {
    tag "${group_b}_vs_ctrl"
    label 'quant'
    publishDir "${params.outdir}/quant/comparisons", mode: 'copy'
    input:  tuple val(group_b), val(samples_b), val(samples_ctrl), path(matrix)
    output: path("${group_b}_vs_ctrl.tsv")
    when:   task.ext.when == null || task.ext.when
    script:
    """
    export SPECTIO_ATTEMPT=${task.attempt}
    ${failHook('COMPARE', group_b)}
    synth.py compare ${matrix} ${samples_b.join(',')} ${samples_ctrl.join(',')} ${group_b}_vs_ctrl.tsv
    """
}

process FINAL_REPORT {
    label 'quant'
    publishDir "${params.outdir}", mode: 'copy'
    input:  path(tables)
    output: path("final_report.html")
    when:   task.ext.when == null || task.ext.when
    script:
    """
    export SPECTIO_ATTEMPT=${task.attempt}
    ${failHook('FINAL_REPORT', '')}
    { echo '<!doctype html><title>Final report</title><h1>Comparisons</h1><pre>'; cat ${tables}; echo '</pre>'; } > final_report.html
    """
}

workflow {
    samples = channel.fromPath(params.input)
        .splitCsv(header: true)
        .map { row -> tuple(row.sample, row.group, row.n_reads as int) }
    if (params.scale as int > 1) {
        extra = channel.of(1..((params.scale as int) - 1) * 12).map { i -> tuple(String.format('X%04d', i), 'ctrl', 400) }
        samples = samples.mix(extra)
    }

    reads = MAKE_READS(samples)
    qc    = QC_STATS(reads)
    QC_REPORT(qc.collect())

    chunks  = SPLIT(reads).transpose()
    aligned = ALIGN(chunks)
    matrix  = MERGE(aligned.collect())

    // one comparison per non-control group against ctrl
    pairs = samples.map { s, g, n -> tuple(g, s) }.groupTuple().toList().flatMap { groups ->
        def ctrl = groups.find { it[0] == 'ctrl' }[1]
        groups.findAll { it[0] != 'ctrl' }.collect { g -> tuple(g[0], g[1], ctrl) }
    }
    comps = COMPARE(pairs.combine(matrix))
    FINAL_REPORT(comps.collect())
}
