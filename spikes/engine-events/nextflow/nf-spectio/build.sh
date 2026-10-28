#!/usr/bin/env bash
# Spike T2: build nf-spectio without Gradle and install it as an unpacked plugin directory,
# the layout the registry-downloaded nf-tower uses (~/.nextflow/plugins/nf-tower-1.32.2/classes/
# META-INF/{MANIFEST.MF,extensions.idx}).
# usage: build.sh NEXTFLOW_BIN PLUGINS_DIR [REQUIRES]
set -eu
NF=$1 DEST=$2 REQ=${3:->=25.10.0}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$DEST/nf-spectio-0.0.1
rm -rf "$OUT"; mkdir -p "$OUT/classes/META-INF" "$OUT/lib"
java -cp "$NF" org.codehaus.groovy.tools.FileSystemCompiler -d "$OUT/classes" "$HERE"/src/spectio/*.groovy
printf 'Manifest-Version: 1.0\nPlugin-Id: nf-spectio\nPlugin-Version: 0.0.1\nPlugin-Class: spectio.SpectioPlugin\nPlugin-Provider: spectio-spike\nPlugin-Requires: %s\n' "$REQ" > "$OUT/classes/META-INF/MANIFEST.MF"
echo spectio.SpectioFactory > "$OUT/classes/META-INF/extensions.idx"
find "$OUT" -type f | sed "s|$DEST/||" | sort
