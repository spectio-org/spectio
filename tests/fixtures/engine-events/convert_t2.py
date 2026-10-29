"""Convert the spike T2 bridge captures into spool files (api-and-data-model.md §14.1).

    python3 tests/fixtures/engine-events/convert_t2.py [CAPTURES_DIR] [OUT_DIR]

Defaults: spikes/engine-events/fixtures/ and this directory. Each bridge capture
`<name>.jsonl` becomes `<name>.spool.jsonl`; the Tower-protocol captures (`*_tower_*`) are
another protocol, not spool events, and are skipped. Captured values are kept as they are,
`<launch>` placeholders and denylisted fields included: the allow-lists must drop them.
The output is deterministic: every file gets RUN_ID, launch 1, and event IDs built from
the event time and a hash of (file, seq). A capture that matches the credential guard of
tests/slurm/fixture.py (SECRET) stops the run with exit 1 before any file is written.

- Nextflow (`nf-spectio` capture server lines): `body.hook` gives the type, `body.seq`
  the seq, `body.instant` (epoch ms) the time, and the rest of `body` the data.
- Snakemake (`LogRecord` lines): `event` gives the type (`snakemake.log` when it is "None"),
  `seq` and `t` (epoch s) the seq and time, and `level`, `msg` and `extra` the data.
  Non-JSON values the spike wrote as `{"__type__": ..., "repr": ...}` become their repr.
"""

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests" / "slurm"))
from fixture import SECRET  # noqa: E402

RUN_ID = "run_01K8T2F1XTVRES000000000000"
LAUNCH = 1
PRODUCERS = {"nextflow": "nf-spectio/0.0.1", "snakemake": "snakemake-logger-spectio/0.0.1"}
CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid(ms: int, salt: str) -> str:
    rand = int.from_bytes(hashlib.sha256(salt.encode()).digest()[:10], "big")
    n = (ms << 80) | rand
    return "".join(CROCKFORD[(n >> (5 * i)) & 31] for i in reversed(range(26)))


def unwrap(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {"__type__", "repr"}:
            return value["repr"]
        return {k: unwrap(v) for k, v in value.items()}
    if isinstance(value, list):
        return [unwrap(v) for v in value]
    return value


def convert_line(engine: str, name: str, line: str) -> dict[str, Any]:
    rec = json.loads(line)
    if engine == "nextflow":
        body = rec["body"]
        type_, seq, ms = f"nextflow.{body['hook']}", body["seq"], body["instant"]
        data = {k: v for k, v in body.items() if k not in ("hook", "seq", "instant")}
    else:
        event = rec["event"]
        type_ = "snakemake.log" if event == "None" else f"snakemake.{event}"
        seq, ms = rec["seq"], round(rec["t"] * 1000)
        data = {"level": rec["level"], "msg": rec["msg"], **unwrap(rec["extra"])}
    time = datetime.fromtimestamp(ms / 1000, UTC).isoformat(timespec="milliseconds")
    return {
        "v": 1,
        "id": "evt_" + ulid(ms, f"{name}:{seq}"),
        "run": RUN_ID,
        "launch": LAUNCH,
        "producer": PRODUCERS[engine],
        "seq": seq,
        "time": time.replace("+00:00", "Z"),
        "type": type_,
        "data": data,
    }


def convert(captures: Path, out: Path) -> list[Path]:
    outputs: dict[Path, str] = {}
    for src in sorted(captures.glob("*.jsonl")):
        if "_tower_" in src.name:
            continue
        engine = src.name.split("-", 1)[0]
        dest = out / (src.name.removesuffix(".jsonl") + ".spool.jsonl")
        lines = [
            json.dumps(convert_line(engine, src.name, line), ensure_ascii=False) + "\n"
            for line in src.read_text(encoding="utf-8").splitlines()
        ]
        outputs[dest] = "".join(lines)
    for dest, text in outputs.items():
        if SECRET.search(text):  # never print the match itself
            sys.exit(f"credential-like text in the capture for {dest.name}: nothing written")
    for dest, text in outputs.items():
        dest.write_text(text, encoding="utf-8")
    return list(outputs)


def main(argv: list[str]) -> None:
    captures = Path(argv[1]) if len(argv) > 1 else ROOT / "spikes" / "engine-events" / "fixtures"
    out = Path(argv[2]) if len(argv) > 2 else Path(__file__).resolve().parent
    for path in convert(captures, out):
        print(path)


if __name__ == "__main__":
    main(sys.argv)
