#!/usr/bin/env bash
# Build nf-spectio without Gradle: compile src/spectio/*.groovy with the Groovy compiler inside
# the Nextflow jar, into the unpacked plugin layout Nextflow loads from its plugins directory
# (nf-spectio-0.0.1/classes/META-INF/{MANIFEST.MF,extensions.idx}), as spike T2 did
# (docs/research/spike-engine-events-2026-10-28.md). architecture §13.4: the floor is 25.04.
#
#   build.sh OUT_DIR        write OUT_DIR/nf-spectio-0.0.1/
#   build.sh --classpath    print the Nextflow jar it compiles against
#
# Nextflow is $NEXTFLOW (default: nextflow on the PATH): a -dist launcher is itself the jar;
# a plain launcher's jar is $NXF_HOME/framework/<version>/nextflow-<version>-one.jar.
set -euo pipefail
VERSION=0.0.1
REQUIRES='>=25.04.0'
HERE=$(cd "$(dirname "$0")" && pwd)

nextflow_jar() {
  local nf ver jar
  nf=$(command -v "${NEXTFLOW:-nextflow}") || { echo "build.sh: Nextflow not found" >&2; return 1; }
  ver=$("$nf" -version 2>/dev/null | sed -n 's/.*version \([0-9][0-9.]*\).*/\1/p' | head -1)
  jar=${NXF_HOME:-$HOME/.nextflow}/framework/$ver/nextflow-$ver-one.jar
  if [ -n "$ver" ] && [ -f "$jar" ]; then echo "$jar"; else echo "$nf"; fi
}

if [ "${1:-}" = --classpath ]; then nextflow_jar; exit; fi
[ $# -eq 1 ] || { echo "usage: build.sh OUT_DIR | --classpath" >&2; exit 2; }
OUT=$1/nf-spectio-$VERSION
JAR=$(nextflow_jar)
rm -rf "$OUT"
mkdir -p "$OUT/classes/META-INF"
java -cp "$JAR" org.codehaus.groovy.tools.FileSystemCompiler -d "$OUT/classes" "$HERE"/src/spectio/*.groovy
printf 'Manifest-Version: 1.0\nPlugin-Id: nf-spectio\nPlugin-Version: %s\nPlugin-Class: spectio.SpectioPlugin\nPlugin-Provider: spectio\nPlugin-Requires: %s\n' \
  "$VERSION" "$REQUIRES" > "$OUT/classes/META-INF/MANIFEST.MF"
echo spectio.SpectioFactory > "$OUT/classes/META-INF/extensions.idx"
