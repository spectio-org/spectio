// Spike: a toy pipeline with the nf-core shape (wrapper workflow -> pipeline workflow ->
// nested subworkflows, plus a process called directly), to check the fully qualified names a
// real (non-preview) run reports in the trace file and to nf-spectio.
process STEP {
    tag "$x"
    input:
    val x
    output:
    val x
    script:
    "echo $x"
}

process REPORT {
    input:
    val xs
    output:
    val 'done'
    script:
    "echo report"
}

process SKIPPED {
    input:
    val x
    output:
    val x
    when:
    params.never
    script:
    "echo $x"
}

workflow QC_INNER {
    take:
    ch
    main:
    STEP(ch)
    emit:
    STEP.out
}

workflow QC {
    take:
    ch
    main:
    QC_INNER(ch)
    emit:
    QC_INNER.out
}

workflow ALIGN {
    take:
    ch
    main:
    STEP(ch)
    SKIPPED(ch)
    emit:
    STEP.out
}

workflow TOY {
    main:
    ch = channel.of('s1', 's2')
    QC(ch)
    ALIGN(QC.out)
    REPORT(ALIGN.out.collect())
}

workflow NFCORE_TOY {
    main:
    TOY()
}

workflow {
    NFCORE_TOY()
}
