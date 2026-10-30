# Spike first-look

Throwaway demo: synthetic `nf-spectio` spools, read by the real spool reader, projected by the
real projector into a real SQLite store, shown on a read-only page. Not product code.

```bash
uv run python spikes/first-look/demo.py   # then open http://127.0.0.1:8765/
```

Findings, what is faked and all commands: `docs/research/2026-10-30-first-look-spike.md`.
