// Single-module fixture (#161, api §5.9): one process, run alone with `nextflow module run`.
// Counts the reads of one synthetic sample (tests/pipelines/synthetic/bin/synth.py writes them).
process SYNTH_STATS {
    tag "${meta.id}"

    input:
    tuple val(meta), path(reads)

    output:
    tuple val(meta), path("${meta.id}.stats.json"), emit: stats

    script:
    """
    n=\$(wc -l < ${reads})
    printf '{"sample": "%s", "reads": %d}\\n' "${meta.id}" "\$n" > ${meta.id}.stats.json
    """

    stub:
    """
    echo '{}' > ${meta.id}.stats.json
    """
}
