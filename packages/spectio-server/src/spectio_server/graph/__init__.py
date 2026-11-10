"""The workflow graph of issue #160 (api §5.8; spikes/metroflow/graph-contract.md).

`document` builds the engine-neutral GraphDocument from what the store already holds (Snakemake's
rule graphs, Nextflow's `onFlowBegin` DAG, the stages) or from a static analysis (`bioflow`,
`static`). Behind the `graph_view` feature (dev-env §15.1: no graphs in 0.0.1).
"""
