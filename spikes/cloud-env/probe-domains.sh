#!/bin/bash
# Probe outbound HTTPS from the cloud session through the agent proxy.
# Prints: url, HTTP status (000 = no response), curl exit code, first bytes of a 403 body.
# A 403 with a JSON "GitHub access ... not enabled" body is the per-repository GitHub policy,
# not the domain allowlist. Usage: bash probe-domains.sh > fixtures/domains-<date>.tsv
urls=(
  https://get.nextflow.io/
  https://www.nextflow.io/
  https://registry.nextflow.io/
  https://github.com/nextflow-io/nextflow/releases/download/v26.10.0/nextflow-26.10.0-dist
  https://raw.githubusercontent.com/nextflow-io/plugins/main/plugins.json
  https://objects.githubusercontent.com/
  https://release-assets.githubusercontent.com/
  https://api.github.com/repos/nextflow-io/nextflow/releases/latest
  https://codeload.github.com/
  https://repo1.maven.org/maven2/
  https://nf-co.re/
  https://quay.io/v2/
  https://ghcr.io/v2/
  https://registry-1.docker.io/v2/
  https://auth.docker.io/token
  https://production.cloudflare.docker.com/
  https://mirror.gcr.io/v2/
  https://registry.k8s.io/v2/
  https://dl.k8s.io/release/stable.txt
  https://community.wave.seqera.io/
  https://wave.seqera.io/
  https://api.cloud.seqera.io/
  https://conda.anaconda.org/bioconda/noarch/repodata.json.bz2
  https://repo.anaconda.com/
  https://prefix.dev/
  https://pypi.org/simple/snakemake/
  https://files.pythonhosted.org/
  https://registry.npmjs.org/playwright
  https://cdn.playwright.dev/
  https://playwright.download.prss.microsoft.com/
  https://proxy.golang.org/
  https://sum.golang.org/lookup/sigs.k8s.io/kind@v0.33.0
  https://storage.googleapis.com/
  https://gsi-hpc.github.io/sind/
  https://schedmd.com/
  https://download.schedmd.com/slurm/
  https://archive.ubuntu.com/ubuntu/
  https://deb.debian.org/debian/
  https://dl-cdn.alpinelinux.org/alpine/
  https://get.sdkman.io/
  https://api.adoptium.net/v3/info/available_releases
  https://cloudflare.com/
  https://example.com/
)
for u in "${urls[@]}"; do
  body=$(mktemp)
  code=$(curl -sS -o "$body" -w '%{http_code}' --max-time 15 "$u" 2>/dev/null); rc=$?
  note=""
  if [ "$code" = "403" ] || [ "$code" = "000" ]; then note=$(head -c 90 "$body" | tr '\n\t' '  '); fi
  printf '%s\t%s\t%s\t%s\n' "$u" "$code" "$rc" "$note"
  rm -f "$body"
done
