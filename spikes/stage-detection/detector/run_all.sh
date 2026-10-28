#!/usr/bin/env bash
# Spike: run the detector on every capture (uncapped and capped at 8). usage: run_all.sh SRC_ROOT
cd "$(dirname "$0")/.."; SRC=$1
for r in "rnaseq-3.27.0_star_salmon nf-core/rnaseq rnaseq" "rnaseq-3.27.0_hisat2 nf-core/rnaseq rnaseq" \
         "sarek-3.11.0 nf-core/sarek sarek" "methylseq-4.2.0_bismark nf-core/methylseq methylseq" \
         "methylseq-4.2.0_bwameth nf-core/methylseq methylseq"; do
  set -- $r; f=out/$1_preview_events.jsonl
  python3 detector/detect_nf.py $f $2 $SRC/$3 --max 99; python3 detector/detect_nf.py $f $2 $SRC/$3; echo
  python3 detector/detect_nf.py $f $2 $SRC/$3 --json > out/$1_detected.json
done
python3 detector/detect_nf.py out/toy_run_events.jsonl -
echo "# flat synthetic pipeline (spike T2 fixture), no subworkflows:"
python3 detector/detect_nf.py ../engine-events/fixtures/nextflow-26.10.4_plugin_flaky.jsonl - 2>/dev/null || echo "(fixture only on branch spike/engine-events)"
