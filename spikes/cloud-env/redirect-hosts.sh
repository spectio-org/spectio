#!/bin/bash
# Print the hosts a download really touches (redirect chains), so the Custom allowlist covers them.
# Registry blobs: fetch an anonymous pull token, read the manifest, then follow one layer blob's redirect.
chain() { curl -sS -o /dev/null -L --max-time 30 -w '%{url_effective}\n' "$@" 2>&1 | sed -E 's#^(https?://[^/]+).*#\1#'; }
hops() { curl -sS -o /dev/null -D - --max-time 30 "$@" 2>/dev/null | grep -i '^location:' | sed -E 's#^[Ll]ocation: *(https?://[^/]+).*#\1#' | tr -d '\r'; }

echo "dl.k8s.io kubectl -> $(chain https://dl.k8s.io/release/v1.37.1/bin/linux/amd64/kubectl.sha256)"
echo "get.nextflow.io -> $(chain https://get.nextflow.io)"
echo "github release asset -> $(hops https://github.com/nextflow-io/nextflow/releases/download/v26.10.0/nextflow-26.10.0-dist)"

blob() { # registry repo tag tokenurl
  local reg=$1 repo=$2 tag=$3 tokurl=$4 tok auth=() dg
  if [ -n "$tokurl" ]; then tok=$(curl -sS "$tokurl" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("token") or d.get("access_token"))'); auth=(-H "Authorization: Bearer $tok"); fi
  dg=$(curl -sS "${auth[@]}" -H 'Accept: application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json' "https://$reg/v2/$repo/manifests/$tag" \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); m=d.get("manifests"); print((m[0] if m else d["layers"][0])["digest"], "manifests" if m else "blobs")')
  set -- $dg
  if [ "$2" = "manifests" ]; then
    dg=$(curl -sS "${auth[@]}" -H 'Accept: application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json' "https://$reg/v2/$repo/manifests/$1" | python3 -c 'import json,sys; print(json.load(sys.stdin)["layers"][0]["digest"])')
  else dg=$1; fi
  echo "$reg/$repo:$tag blob -> $(hops "${auth[@]}" "https://$reg/v2/$repo/blobs/$dg")"
}
blob ghcr.io gsi-hpc/sind-node latest "https://ghcr.io/token?scope=repository:gsi-hpc/sind-node:pull"
blob registry-1.docker.io kindest/node v1.34.0 "https://auth.docker.io/token?service=registry.docker.io&scope=repository:kindest/node:pull"
blob quay.io biocontainers/fastqc 0.12.1--hdfd78af_0 ""
blob registry.k8s.io kueue/kueue v0.15.0 ""
blob community.wave.seqera.io library/fastqc 0.12.1--af7a5314d5015c29 ""
