#!/usr/bin/env bash
# Every start of the codespace: serve the docs on :8000 (and, once it exists, Spectio in demo mode on :8080).
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"
nohup mkdocs serve -a 0.0.0.0:8000 >/tmp/mkdocs.log 2>&1 &
echo "Docs: port 8000 (log /tmp/mkdocs.log)."
