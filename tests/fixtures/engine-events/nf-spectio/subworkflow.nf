// A minimal pipeline with one subworkflow, for the process-level DAG nf-spectio sends at
// onFlowBegin (#160): INNER:B is a qualified process name, and A -> C goes through `mix`.
//
// The spools beside it are real nf-spectio output (Nextflow 26.10.4, 2026-11-10), with the launch
// directory replaced by `<launch>`:
//   nextflow-26.10.4_plugin_dag.spool.jsonl              engine-bridges/nf-spectio/tests/run_local.sh
//                                                        (the synthetic pipeline, happy run)
//   nextflow-26.10.4_plugin_dag_subworkflow.spool.jsonl  this file, run with -plugins nf-spectio@0.0.1
// Both with SPECTIO_RUN_ID=run_01K8T2F1XTVRES000000000000 and launch 1, as the T2 fixtures.
process A {
    output: val 1
    script: "echo a"
}
process B {
    input: val x
    output: val x
    script: "echo b"
}
process C {
    input: val x
    script: "echo c"
}
workflow INNER {
    take: ch
    main: B(ch.map { it + 1 })
    emit: B.out
}
workflow {
    A()
    INNER(A.out)
    C(INNER.out.mix(A.out))
}
