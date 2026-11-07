#!/usr/bin/env bash
# The release packages of both engine bridges, dry run only (P1 Task 26; dev-env §12 Publishing,
# §15.3 req. 12; architecture §13.4).
#
#   bash tests/packaging/test_bridges_release.sh   prints `RESULT bridges-release dry-run pass`,
#                                                  or `RESULT bridges-release dry-run fail`
#
# nf-spectio: builds the plugin zip with its Gradle wrapper (distributionSha256Sum, the
# io.nextflow.nextflow-plugin version pinned) and a fresh, empty GRADLE_USER_HOME, from a copy of
# the tracked files only; checks the zip's manifest (ID, version, requires, class) against
# build.sh, then loads the zip into Nextflow ($NEXTFLOW) for the synthetic `happy`.
# snakemake-logger-plugin-spectio: `uv build` (the wheel is built from the sdist), `twine check
# --strict`, the file lists of both, then the wheel installed with no PYTHONPATH into a fresh
# venv holding the hash-locked Snakemake 9 of dev/snakemake.lock.txt, which runs the synthetic
# `happy` with `--logger spectio`.
# No artefact may hold a secret (`npr.apiKey`, a PyPI token, a gradle.properties). Publishes
# nothing: no `make release`, no Gradle release task, no `twine upload`, no registry key; it
# refuses to start when one is set in its environment. Needs network for the Gradle and Maven
# repositories and PyPI, Java 21, Nextflow and uv.
set -euo pipefail

repo=$(cd "$(dirname "$0")/../.." && pwd)
. "$repo/dev/versions.env"
nf_dir=$repo/engine-bridges/nf-spectio
smk_dir=$repo/engine-bridges/snakemake-logger-plugin-spectio
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
RUN_ID=run_01K8T7RE1EA5E0000000000000 # a valid ULID: Crockford base32, 26 characters
# The upstream checksums of Gradle 8.14.3, the version the wrapper names (read 2026-11-07):
# https://services.gradle.org/distributions/gradle-8.14.3-{bin.zip,wrapper.jar}.sha256
DIST_SHA256=bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531
WRAPPER_JAR_SHA256=7d3a4ac4de1c32b59bc6a4eb8ecb8e612ccd0cf1ae1e99f66902da64df296172

fail() { echo "FAIL $*" >&2; echo "RESULT bridges-release dry-run fail"; exit 1; }

echo "== No registry key or PyPI token in the environment"
while IFS= read -r -d '' kv; do
  name=${kv%%=*} value=${kv#*=}
  shopt -s nocasematch
  case $name in
  *npr*api*key* | *npr_api* | twine_password | uv_publish_token | uv_publish_password | *pypi*token* | *pypi*password*)
    [ -z "$value" ] || { shopt -u nocasematch; fail "$name is set: a dry run holds no publishing secret"; } ;;
  esac
  shopt -u nocasematch
  if [[ $value =~ pypi-[A-Za-z0-9_-]{16,} ]]; then fail "$name holds a PyPI token"; fi
done < <(env -0)

# Every member of the archive $1 (zip, wheel or tar.gz): no gradle.properties, no npr.apiKey,
# no PyPI token, in a name or in the bytes.
no_secrets() {
  python3 -I - "$1" <<'PY' || fail "$(basename "$1") holds a secret"
import re, sys, tarfile, zipfile
path = sys.argv[1]
pat = re.compile(rb"npr\.apiKey|NPR_API_KEY|pypi-[A-Za-z0-9_-]{16,}")
if path.endswith(".tar.gz"):
    with tarfile.open(path) as t:
        items = [(m.name, t.extractfile(m).read()) for m in t if m.isfile()]
else:
    with zipfile.ZipFile(path) as z:
        items = [(n, z.read(n)) for n in z.namelist() if not n.endswith("/")]
bad = [n for n, data in items if n.endswith("gradle.properties") or pat.search(n.encode() + b"\n" + data)]
for n in bad:
    print(f"  {n}", file=sys.stderr)
sys.exit(1 if bad else 0)
PY
}

echo "== nf-spectio: the Gradle wrapper is pinned"
props=$nf_dir/gradle/wrapper/gradle-wrapper.properties
[ -f "$props" ] || fail "no $props"
grep -qx "distributionSha256Sum=$DIST_SHA256" "$props" || fail "$props: distributionSha256Sum is not Gradle's"
grep -Eq '^distributionUrl=https\\://services\.gradle\.org/distributions/gradle-8\.14\.3-bin\.zip$' "$props" ||
  fail "$props does not name the Gradle 8.14.3 bin distribution"
jar_sha=$(sha256sum "$nf_dir/gradle/wrapper/gradle-wrapper.jar" | cut -d' ' -f1)
[ "$jar_sha" = "$WRAPPER_JAR_SHA256" ] || fail "gradle-wrapper.jar is not Gradle's ($jar_sha)"
grep -Eq "id 'io\.nextflow\.nextflow-plugin' version '[0-9][^'+]*'" "$nf_dir/build.gradle" ||
  fail "build.gradle does not pin io.nextflow.nextflow-plugin by version"
# Gradle refuses any plugin, POM or jar whose sha256 is not in this file (dependency verification).
grep -q '<verify-metadata>true</verify-metadata>' "$nf_dir/gradle/verification-metadata.xml" ||
  fail "no gradle/verification-metadata.xml that verifies metadata"
if git -C "$repo" ls-files -- engine-bridges/nf-spectio | grep -q 'gradle\.properties$'; then
  fail "a gradle.properties is tracked in engine-bridges/nf-spectio"
fi
if grep -rqiE 'apiKey|registry *\{' "$nf_dir"/*.gradle; then fail "the Gradle build names a registry or a key"; fi

echo "== nf-spectio: gradlew packagePlugin (fresh GRADLE_USER_HOME, tracked files only)"
mkdir -p "$tmp/nf"
git -C "$repo" ls-files -z -- engine-bridges/nf-spectio | (cd "$repo" && xargs -0 cp --parents -t "$tmp/nf")
build=$tmp/nf/engine-bridges/nf-spectio
export GRADLE_USER_HOME=$tmp/gradle-home
mkdir "$GRADLE_USER_HOME"
# Maven Central answers 429 (Too Many Requests) to a burst of fresh downloads: up to 3 attempts,
# only for that; the home keeps what the earlier attempts verified.
for attempt in 1 2 3; do
  if (cd "$build" && ./gradlew --no-daemon --quiet --console=plain packagePlugin) >"$tmp/gradle.log" 2>&1; then
    break
  fi
  if [ $attempt = 3 ] || ! grep -q 'status code 429' "$tmp/gradle.log"; then
    tail -40 "$tmp/gradle.log" >&2
    fail "gradlew packagePlugin (attempt $attempt)"
  fi
  echo "   attempt $attempt: Maven Central answered 429, retrying in 30 s"
  sleep 30
done
[ ! -e "$GRADLE_USER_HOME/gradle.properties" ] || fail "the build wrote $GRADLE_USER_HOME/gradle.properties"
version=$(sed -n 's/^VERSION=//p' "$nf_dir/build.sh")
requires=$(sed -n "s/^REQUIRES='\(.*\)'$/\1/p" "$nf_dir/build.sh")
[ "$requires" = ">=25.04.0" ] || fail "build.sh REQUIRES is '$requires', not architecture §13.4's >=25.04.0"
zip=$build/build/distributions/nf-spectio-$version.zip
[ -f "$zip" ] || fail "no $(basename "$zip") ($(ls "$build/build/distributions" 2>/dev/null | tr '\n' ' '))"
no_secrets "$zip"

echo "== nf-spectio: the zip's manifest"
manifest=$(unzip -p "$zip" classes/META-INF/MANIFEST.MF | tr -d '\r') || fail "no classes/META-INF/MANIFEST.MF in the zip"
for want in "Plugin-Id: nf-spectio" "Plugin-Version: $version" "Plugin-Requires: $requires" \
  "Plugin-Class: spectio.SpectioPlugin" "Plugin-Provider: spectio"; do
  grep -qxF "$want" <<<"$manifest" || fail "the manifest lacks '$want': $manifest"
done
[ "$(unzip -p "$zip" classes/META-INF/extensions.idx | tr -d '\r')" = spectio.SpectioFactory ] ||
  fail "classes/META-INF/extensions.idx is not spectio.SpectioFactory"
if unzip -Z1 "$zip" | grep -q '^lib/.'; then fail "the zip bundles libraries: $(unzip -Z1 "$zip" | grep '^lib/.')"; fi

echo "== nf-spectio: Nextflow loads the zip (synthetic happy)"
plugins=$tmp/nxf-plugins
mkdir -p "$plugins/nf-spectio-$version" "$tmp/nf-run/.spectio"
chmod 700 "$tmp/nf-run/.spectio"
unzip -q "$zip" -d "$plugins/nf-spectio-$version"
(cd "$tmp/nf-run" && env -u NXF_PLUGINS_DEFAULT NXF_PLUGINS_DIR="$plugins" NXF_ANSI_LOG=false \
  NXF_HOME="$tmp/nxf-home" SPECTIO_RUN_ID=$RUN_ID SPECTIO_LAUNCH_N=1 \
  SPECTIO_SPOOL_DIR="$tmp/nf-run/.spectio/events" \
  "${NEXTFLOW:-nextflow}" -q run "$repo/tests/pipelines/synthetic/nextflow/main.nf" \
  -profile test,local --outdir results -plugins "nf-spectio@$version") >"$tmp/nf-run.log" 2>&1 ||
  { tail -40 "$tmp/nf-run.log" >&2; fail "nextflow run with the released zip"; }
grep -qh '"type":"nextflow.onFlowComplete"' "$tmp"/nf-run/.spectio/events/*.jsonl 2>/dev/null ||
  fail "the released nf-spectio wrote no onFlowComplete to the spool"

echo "== snakemake-logger-plugin-spectio: uv build (sdist, then the wheel from it)"
pydist=$tmp/pydist
(cd "$smk_dir" && uv build --quiet --python "$PYTHON_VERSION" --out-dir "$pydist") || fail "uv build"
name=snakemake_logger_plugin_spectio-0.0.1
whl=$pydist/$name-py3-none-any.whl sdist=$pydist/$name.tar.gz
[ -f "$whl" ] && [ -f "$sdist" ] || fail "uv build made $(ls "$pydist" | tr '\n' ' ')"
uvx --quiet "twine==$TWINE_VERSION" check --strict "$sdist" "$whl" >"$tmp/twine.log" 2>&1 ||
  { cat "$tmp/twine.log" >&2; fail "twine check --strict"; }
no_secrets "$whl"
no_secrets "$sdist"

echo "== snakemake-logger-plugin-spectio: the files and the metadata"
got=$(unzip -Z1 "$whl" | grep -v '/$' | sort | tr '\n' ' ')
want="$name.dist-info/METADATA $name.dist-info/RECORD $name.dist-info/WHEEL "
want+="snakemake_logger_plugin_spectio/__init__.py "
[ "$got" = "$want" ] || fail "the wheel holds: $got"
got=$(python3 -I -c 'import sys, tarfile; [print(m.name) for m in tarfile.open(sys.argv[1]) if m.isfile()]' \
  "$sdist" | sort | tr '\n' ' ')
want="$name/PKG-INFO $name/README.md $name/pyproject.toml "
want+="$name/snakemake_logger_plugin_spectio/__init__.py "
[ "$got" = "$want" ] || fail "the sdist holds: $got"
meta=$(unzip -p "$whl" "$name.dist-info/METADATA")
for want in "Name: snakemake-logger-plugin-spectio" "Version: 0.0.1" \
  "Requires-Dist: snakemake-interface-logger-plugins>=1.1.0,<3" "License-Expression: MIT" \
  "Project-URL: Repository, https://github.com/spectio-org/spectio" \
  "Description-Content-Type: text/markdown"; do
  grep -qxF "$want" <<<"$meta" || fail "METADATA lacks '$want'"
done

echo "== snakemake-logger-plugin-spectio: installed into a fresh Snakemake 9 (synthetic happy)"
venv=$tmp/smk
uv venv --quiet --python "$PYTHON_VERSION" "$venv"
uv pip install --quiet --python "$venv/bin/python" --require-hashes -r "$repo/dev/snakemake.lock.txt" ||
  fail "the hash-locked Snakemake"
uv pip install --quiet --python "$venv/bin/python" --no-deps "$whl" || fail "installing the wheel"
uv pip check --quiet --python "$venv/bin/python" || fail "uv pip check: the wheel's requirements"
where=$(cd "$tmp" && env -u PYTHONPATH "$venv/bin/python" -I -c \
  'import snakemake_logger_plugin_spectio as m; print(m.__file__)')
[[ $where == "$venv"/lib/*/site-packages/* ]] || fail "the plugin loads from $where"
launch=$tmp/smk-run
mkdir -p "$launch/.spectio"
chmod 700 "$launch/.spectio"
synthetic=$repo/tests/pipelines/synthetic
(cd "$launch" && env -u PYTHONPATH SPECTIO_RUN_ID=$RUN_ID SPECTIO_LAUNCH_N=1 \
  SPECTIO_SPOOL_DIR="$launch/.spectio/events" \
  "$venv/bin/snakemake" -s "$synthetic/snakemake/workflow/Snakefile" --directory "$launch" \
  --logger spectio --cores 2 \
  --config outdir=results "samples=$synthetic/data/samplesheet.csv" chunks=2) >"$tmp/smk-run.log" 2>&1 ||
  { tail -40 "$tmp/smk-run.log" >&2; fail "snakemake --logger spectio with the installed wheel"; }
for type in workflow_started job_finished; do
  grep -Eqh "\"type\": ?\"snakemake\.$type\"" "$launch"/.spectio/events/*.jsonl 2>/dev/null ||
    fail "the installed plugin wrote no snakemake.$type to the spool"
done

echo "RESULT bridges-release dry-run pass"
