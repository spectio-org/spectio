#!/bin/bash
n=$1; d=repos/$n
[ -d $d ] && exit 0
git clone -q --depth 1 --filter=blob:none --sparse https://github.com/nf-core/$n.git $d 2>/dev/null || { echo "FAIL $n"; exit 0; }
cd $d && git sparse-checkout set --no-cone /modules.json /docs/output.md /assets/schema_input.json /nextflow_schema.json /assets/multiqc_config.yml /README.md 2>/dev/null
