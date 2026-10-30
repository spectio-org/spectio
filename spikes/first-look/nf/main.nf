#!/usr/bin/env nextflow
/*
 * Spike first-look: a dummy pipeline. FASTQC -> TRIM -> ALIGN per sample, then MULTIQC.
 * Each task writes a small text file and sleeps a few seconds. No container, no conda.
 *   --samples N   number of samples S01..SNN (default 3)
 *   --fail        ALIGN of the last sample exits 1 on every attempt: retried once, then the run fails
 *   --sleep S     seconds per task (default 3)
 */
nextflow.enable.dsl = 2

params.samples = 3
params.fail    = false
params.sleep   = 3

process FASTQC {
    tag "$sample"
    input:  val sample
    output: tuple val(sample), path("${sample}.fastq")
    script:
    """
    sleep ${params.sleep}
    echo "@${sample} reads" > ${sample}.fastq
    """
}

process TRIM {
    tag "$sample"
    input:  tuple val(sample), path(reads)
    output: tuple val(sample), path("${sample}.trimmed.fastq")
    script:
    """
    sleep ${params.sleep}
    cat ${reads} > ${sample}.trimmed.fastq
    """
}

process ALIGN {
    tag "$sample"
    errorStrategy { task.attempt < 2 ? 'retry' : 'terminate' }
    maxRetries 1
    input:  tuple val(sample), path(reads)
    output: path("${sample}.bam.txt")
    script:
    def fail = params.fail && sample == String.format('S%02d', params.samples as int)
    """
    sleep ${params.sleep}
    ${fail ? 'echo "injected failure" >&2; exit 1' : ''}
    echo "${sample} aligned" > ${sample}.bam.txt
    """
}

process MULTIQC {
    input:  path(bams)
    output: path("multiqc.txt")
    script:
    """
    sleep ${params.sleep}
    cat ${bams} > multiqc.txt
    """
}

workflow {
    samples = channel.of(1..(params.samples as int)).map { String.format('S%02d', it) }
    MULTIQC(ALIGN(TRIM(FASTQC(samples))).collect())
}
