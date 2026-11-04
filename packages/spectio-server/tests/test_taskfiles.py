"""Each job's files and the work directory (P1 Task 28; architecture §13.7, checking-scenarios
§11.1, dev-env §15.3 req. 13).

The confined walk, the `.command.run` hiding, the file lists per engine, the paths the projector
keeps from events, and the head script's engine log. The routes are in
`api/test_taskfiles_api.py`. Snakemake events are synthetic lines in the shape of api §14.1: the
logger plugin that sends them (P1 Task 7) is not built yet.
"""

import os
import stat
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import pytest
from sqlalchemy import select

from spectio.config import Settings, SlurmOpts
from spectio.runner.headscript import engine_args, engine_env, render_head_script
from spectio.runner.rundir import make_run_dirs
from spectio.runner.types import LaunchSpec, SpoolBatch
from spectio_sdk.events import SpoolEvent
from spectio_server.api.taskfiles import load_attempt
from spectio_server.files import confine
from spectio_server.files.confine import NotAllowed, NotFound, Root, list_confined, open_confined
from spectio_server.files.redact import HIDDEN, redact_command_run, strip_escapes
from spectio_server.files.taskfiles import AttemptFiles, list_task_files, read_task_file
from spectio_server.projector.ingest import ingest
from spectio_server.projector.snakemake import MAX_LOGS
from spectio_server.stages.freeze import StageSources
from spectio_server.store.schema import attempts, spool_drops, tasks
from spectio_server.store.writer import Writer

from .api.conftest import add_run, writer  # noqa: F401 (the fixture)

RUN = "run_01K8T2F1XTVRES0000000000T8"
HASH = ("ab", "0123456789abcdef0123456789abcd")
NF_NAMES = [
    ".command.sh",
    ".command.run",
    ".command.out",
    ".command.err",
    ".command.log",
    ".exitcode",
    ".command.begin",
    ".command.trace",
]
COMMAND_RUN = """#!/bin/bash
#SBATCH -J nf-ALIGN_(S01)
#SBATCH -o /work/ab/cd/.command.log
#SBATCH --no-requeue
NXF_DEBUG=${NXF_DEBUG:=0}; [[ $NXF_DEBUG > 1 ]] && set -x
nxf_date() {
    local s n
    read s n < <(date '+%s %N')
    echo "$((s * 1000 + 10#${n:0:3}))"
}
nxf_main() {
    trap on_exit EXIT
    export TOKEN="abc"
    export PLAIN=visible_value
    (set -o pipefail; (nxf_launch | tee .command.out) 3>&1 1>&2 2>&3 | tee .command.err) &
}
$NXF_ENTRY
"""


def private(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.chmod(0o700)
    return path


@dataclass
class NfTree:
    runs_root: Path
    work_root: Path
    task_dir: Path

    @property
    def work_dir(self) -> str:
        return str(self.task_dir)

    def attempt(self, state: str = "succeeded", native_id: str | None = "8812345") -> AttemptFiles:
        return AttemptFiles(
            run_id=RUN,
            engine="nextflow",
            state=state,
            work_dir=self.work_dir,
            native_id=native_id,
            logs=(),
            runs_root=self.runs_root,
        )


@pytest.fixture
def nf_workdir(tmp_path: Path) -> NfTree:
    """A finished Nextflow task's work directory, with the files a SLURM task leaves."""
    runs_root = private(tmp_path / "runs")
    paths = make_run_dirs(runs_root, RUN)
    task_dir = paths.work_dir.joinpath(*HASH)
    task_dir.mkdir(parents=True)
    files = {
        ".command.sh": "#!/bin/bash -ue\nsynth.py align S01\n",
        ".command.run": COMMAND_RUN,
        ".command.out": "aligned\n",
        ".command.err": "warning: low quality\n",
        ".command.log": "aligned\nwarning: low quality\n",
        ".exitcode": "0",
        ".command.begin": "",
        ".command.trace": "nextflow.trace/v2\nrealtime=1200\n%cpu=98\n",
        ".command.env": "SECRET=s3cr3t\n",
        ".command.in": "stdin\n",
        ".command.stage": "ln -s /x y\n",
    }
    for name, text in files.items():
        (task_dir / name).write_text(text)
    (task_dir / "reads.fq").symlink_to("/etc/hostname")  # a staged input: an absolute link out
    return NfTree(runs_root, paths.work_dir, task_dir)


# --- Nextflow: the allow-list, the hiding of .command.run ------------------------------------


def test_nf_allow_list(nf_workdir: NfTree) -> None:
    found = list_task_files(nf_workdir.attempt())
    assert [f.name for f in found] == NF_NAMES
    assert [f.kind for f in found] == [
        "script",
        "wrapper",
        "stdout",
        "stderr",
        "job_log",
        "exit",
        "marker",
        "trace",
    ]
    assert {f.state for f in found} == {"present"}
    sizes = {f.name: f.size for f in found}
    assert sizes[".exitcode"] == 1 and sizes[".command.begin"] == 0
    assert all(f.mtime is not None for f in found)
    for name in (
        ".command.env",
        ".command.in",
        ".command.stage",
        "reads.fq",
        "../x",
        "/etc/passwd",
    ):
        with pytest.raises(NotAllowed):
            read_task_file(nf_workdir.attempt(), name)


def test_req13_job_file_symlink_in_work_refused(nf_workdir: NfTree) -> None:
    """A job file is never read through a link, even one into the run's work directory: the
    read agrees with the listing (CR-P3T28-02, SEC-P3T28-02)."""
    sibling = nf_workdir.work_root / "de" / "fedcba9876543210fedcba98765432"
    sibling.mkdir(parents=True)
    (sibling / ".command.env").write_text("SECRET=s1bl1ng\n")
    err, sh = nf_workdir.task_dir / ".command.err", nf_workdir.task_dir / ".command.sh"
    err.unlink()
    err.symlink_to("../../de/fedcba9876543210fedcba98765432/.command.env")
    sh.unlink()
    sh.symlink_to(".command.run")
    for name in (".command.err", ".command.sh"):
        with pytest.raises(NotAllowed):
            read_task_file(nf_workdir.attempt(), name)
    notes = {f.name: f.note for f in list_task_files(nf_workdir.attempt())}
    assert notes[".command.err"] and notes[".command.err"].startswith("Not served")
    assert notes[".command.sh"] and notes[".command.sh"].startswith("Not served")


def test_req13_command_run_redacted(nf_workdir: NfTree) -> None:
    served = read_task_file(nf_workdir.attempt(), ".command.run").text
    assert f"export TOKEN={HIDDEN}" in served
    assert f"export PLAIN={HIDDEN}" in served
    assert "abc" not in served and "visible_value" not in served
    for kept in ("#SBATCH -J nf-ALIGN_(S01)", "#SBATCH --no-requeue", "$NXF_ENTRY", "nxf_date()"):
        assert kept in served
    assert served.count("\n") == COMMAND_RUN.count("\n")  # nothing dropped, lines kept


def test_req13_redact_lexer() -> None:
    text = (
        'export MULTI="first line\nsecond $(echo "nested )") line"\n'
        "export ANSI=$'a\\nb\\'c'\n"
        "export SINGLE='it''s'\n"
        'FOO=bar BAZ="q" some_tool --flag=value\n'
        "export \"QUOTED=dq1\" 'SQ=sq1'\n"
        "declare -a arr=(sec1 'sec 2' \"$(echo ')')\")\n"
        "arr+=(sec3)\n"
        "echo after\n"
    )
    served = redact_command_run(text)
    assert served == (
        f"export MULTI={HIDDEN}\n"
        f"export ANSI={HIDDEN}\n"
        f"export SINGLE={HIDDEN}\n"
        f"FOO={HIDDEN} BAZ={HIDDEN} some_tool --flag=value\n"
        f"export QUOTED={HIDDEN} SQ={HIDDEN}\n"
        f"declare -a arr={HIDDEN}\n"
        f"arr+={HIDDEN}\n"
        "echo after\n"
    )


def test_req13_redact_container_env() -> None:
    """The container forms, as `BashWrapperBuilder` writes them for Docker and Singularity
    (nextflow v26.10.4); the other engines' wrappers are [to be validated] (req. 13, SEC-155)."""
    text = (
        "nxf_container_env() {\n"
        "cat << EOF\n"
        'export DB_PASS="hunter2"\n'
        "EOF\n"
        "}\n"
        'docker run -i -e "NXF_TASK_WORKDIR" -e "API_KEY=k3y" --env OTHER=o1 --env=THIRD=t1 img\n'
        'SINGULARITYENV_TOKEN="s1" APPTAINERENV_TOKEN=a1 singularity exec img bash\n'
        'env - PATH="$PATH" SECRET=e1 bash -c true\n'
    )
    served = redact_command_run(text)
    for value in ("hunter2", "k3y", "o1", "t1", "s1", "a1", "e1"):
        assert value not in served, value
    assert '-e "NXF_TASK_WORKDIR"' in served  # a name alone has no value to hide
    assert f"export DB_PASS={HIDDEN}" in served
    assert f"SINGULARITYENV_TOKEN={HIDDEN}" in served
    assert "cat << EOF" in served and "\nEOF\n" in served


def test_req13_redact_review_gaps() -> None:
    """The forms the reviews found served (SEC-P3T28-03 r1 to r3, CR-P3T28-03 r2): a value is
    hidden wherever an assignment word stands, not only at a command's start."""
    lines = {
        'export "TOKEN"=abc1': f"export TOKEN={HIDDEN}",
        'export TOKEN"=abc2"': f"export TOKEN={HIDDEN}",
        "export 'T'='abc3'": f"export T={HIDDEN}",
        "exec env T=v1 cmd": f"exec env T={HIDDEN} cmd",
        "command export T=v2": f"command export T={HIDDEN}",
        "builtin export T=v3": f"builtin export T={HIDDEN}",
        "nohup env T=v4 cmd": f"nohup env T={HIDDEN} cmd",
        "sudo T=v5 cmd": f"sudo T={HIDDEN} cmd",
        "sudo env T=v6 cmd": f"sudo env T={HIDDEN} cmd",
        "docker run -eT=v7 img": f"docker run -eT={HIDDEN} img",
        "docker run -eTOKEN=v8 img": f"docker run -eTOKEN={HIDDEN} img",
        "ch-run --set-env=T=v9 img": f"ch-run --set-env=T={HIDDEN} img",
        "2>/dev/null T=v10 cmd": f"2>/dev/null T={HIDDEN} cmd",
        ">log T=v11 cmd": f">log T={HIDDEN} cmd",
        "function f { T=v12; }": f"function f {{ T={HIDDEN}; }}",
        "f() { local T=v13; }": f"f() {{ local T={HIDDEN}; }}",
        "java -Dnxf.token=v14 x": f"java -Dnxf.token={HIDDEN} x",
        "export TOKEN\\=abc4": f"export TOKEN={HIDDEN}",  # CR-P3T31-05: `\\=` is the `=`
        "env T\\=abc5 cmd": f"env T={HIDDEN} cmd",
        "docker run -e T\\=v15 img": f"docker run -e T={HIDDEN} img",
        "tool --flag=value": "tool --flag=value",  # an option's value: kept
        "[[ $A == b ]] && echo ${X:=d}": "[[ $A == b ]] && echo ${X:=d}",
        "#SBATCH --export=ALL,TOKEN=s1,B=s2": f"#SBATCH --export=ALL,TOKEN={HIDDEN},B={HIDDEN}",
        "#SBATCH --export TOKEN=s3": f"#SBATCH --export TOKEN={HIDDEN}",
        "#SBATCH --mem=4G --export=NONE": "#SBATCH --mem=4G --export=NONE",
        "#PBS -v TOKEN=s4,B=s5": f"#PBS -v TOKEN={HIDDEN},B={HIDDEN}",
        "#$ -v TOKEN=s6": f"#$ -v TOKEN={HIDDEN}",
        '#BSUB -env "all, TOKEN=s7"': f"#BSUB -env {HIDDEN}",
        '#SBATCH --export="T=s8 x"': f"#SBATCH --export={HIDDEN}",
        "#SBATCH --export='T=s9": f"#SBATCH --export={HIDDEN}",
        "#SBATCH -J name": "#SBATCH -J name",
        "# a comment T=c1": "# a comment T=c1",
    }
    for line, expected in lines.items():
        assert redact_command_run(line + "\n") == expected + "\n", line
    whole = "".join(f"{line}\n" for line in lines)
    served = redact_command_run(whole)
    for secret in ("abc", "s1", "s3", "s4", "s7", "s8", "s9", "v1", "v12", "v14"):
        assert f"={secret}" not in served and f"={secret}," not in served, secret
    assert served.count("\n") == len(lines)


def test_req13_directive_quoted_values() -> None:
    """A directive value with a quote in it is hidden to the end of the line, so neither the
    tail of a quoted value nor an item after a closing quote is shown (SEC-P3T31-02)."""
    lines = {
        "#SBATCH --export=TOKEN='a b'": f"#SBATCH --export={HIDDEN}",
        '#SBATCH --export="TOKEN=abc",B=c': f"#SBATCH --export={HIDDEN}",
        '#SBATCH --export=A=x,TOKEN="a,b c"': f"#SBATCH --export={HIDDEN}",
        "#SBATCH --export=T=a\\ b": f"#SBATCH --export={HIDDEN}",
        "#SBATCH --export=A=x,B=y -J job": f"#SBATCH --export=A={HIDDEN},B={HIDDEN} -J job",
    }
    for line, expected in lines.items():
        assert redact_command_run(line + "\n") == expected + "\n", line


def test_req13_strip_bidi_and_8bit_escapes() -> None:
    """Bidi and other format controls, and the 8-bit CSI and OSC with their parameters, are
    removed (SEC-P3T28-07 r1, SEC-P3T28-08 r3)."""
    text = "a\u202eb\u2066c\u200bd\ufeffe\x9b31mf\x9d8;;http://x.example\x07g\x9b1;2Hh\n"
    assert strip_escapes(text) == "abcdefgh\n"
    assert strip_escapes("tab\tkept, é kept\n") == "tab\tkept, é kept\n"


def test_req13_redact_fails_closed() -> None:
    text = 'echo one\nexport TOKEN="abc\necho two\necho three\n'
    served = redact_command_run(text)
    assert served == f"echo one\n{HIDDEN}\n{HIDDEN}\n{HIDDEN}\n"
    unterminated_heredoc = 'echo one\ncat << EOF\nexport X="y"\n'
    assert "y" not in redact_command_run(unterminated_heredoc).replace("«hidden»", "")
    open_quote_in_heredoc = (
        'echo one\ncat << EOF\nexport A="va1"\nexport B=vb2\nexport C="open\nEOF\necho two\n'
    )
    served = redact_command_run(open_quote_in_heredoc)
    assert "va1" not in served and "vb2" not in served, served
    assert served.startswith("echo one\ncat << EOF\n")


def test_req13_redact_deep_nesting_hidden() -> None:
    """Constructs nested past `MAX_NESTING` are unreadable: hidden from their line, never a
    `RecursionError` (SEC-P3T28-04)."""
    for opener, closer in (("$(", ")"), ("${", "}"), ('"${', '}"')):
        deep = "X=" + opener * 2000 + "v" + closer * 2000
        served = redact_command_run(f"echo one\n{deep}\necho two\n")
        assert served == f"echo one\n{HIDDEN}\n{HIDDEN}\n", opener
    heredocs = "".join(f"cat << E{n}\n" for n in range(300)) + "export X=y\n"
    heredocs += "".join(f"E{n}\n" for n in reversed(range(300)))
    served = redact_command_run(heredocs)
    assert "y" not in served.replace(HIDDEN, "") and "export" not in served


# --- Nextflow: states ---------------------------------------------------------------------


def test_array_task_has_no_log(nf_workdir: NfTree) -> None:
    (nf_workdir.task_dir / ".command.log").unlink()
    found = {f.name: f for f in list_task_files(nf_workdir.attempt(native_id="8812345_3"))}
    assert found[".command.log"].state == "absent"
    assert "array" in (found[".command.log"].note or "")
    with pytest.raises(NotFound):
        read_task_file(nf_workdir.attempt(native_id="8812345_3"), ".command.log")


def test_not_written_yet_listed(nf_workdir: NfTree) -> None:
    (nf_workdir.task_dir / ".exitcode").unlink()
    found = {f.name: f for f in list_task_files(nf_workdir.attempt(state="running"))}
    assert found[".exitcode"].state == "not_yet"
    assert found[".command.err"].state == "present"


def test_cleaned_workdir_listed(nf_workdir: NfTree) -> None:
    for child in nf_workdir.task_dir.iterdir():
        child.unlink()
    nf_workdir.task_dir.rmdir()
    found = list_task_files(nf_workdir.attempt())
    assert {f.state for f in found} == {"cleaned"}


# --- Snakemake: the paths from events, through the projector --------------------------------

SMK_LOG = "logs/bwa_mem/WGS-07.log"
SLURM_LOG = ".snakemake/slurm_logs/rule_bwa_mem/WGS-07/48731209.log"


def smk_event(n: int, type_: str, **data: Any) -> SpoolEvent:
    return SpoolEvent.model_validate(
        {
            "v": 1,
            "id": f"evt_t28_{n}",
            "run": RUN,
            "launch": 1,
            "producer": "snakemake-logger-spectio/0.0.1",
            "seq": n,
            "time": "2026-10-31T09:00:00Z",
            "type": f"snakemake.{type_}",
            "data": data,
        }
    )


@dataclass
class SmkRun:
    writer: Writer
    settings: Settings
    launch_id: str
    launch_dir: Path

    def ingest(self, *events: SpoolEvent) -> Counter[str]:
        sources = StageSources(None, self.settings.runs_root)
        batch = SpoolBatch(list(events), {}, Counter())
        self.writer.submit(lambda c: ingest(c, self.launch_id, batch, sources)).result()
        with self.writer.engine.connect() as conn:
            rows = conn.execute(select(spool_drops.c.reason, spool_drops.c.count)).all()
        return Counter(dict(rows))

    def attempt(self, rule: str = "bwa_mem", n: int = 1) -> AttemptFiles:
        with self.writer.engine.connect() as conn:
            task_id = conn.execute(
                select(tasks.c.id).where(tasks.c.process_or_rule == rule)
            ).scalar_one()
            found = load_attempt(conn, task_id, n, self.settings.runs_root)
        assert found is not None
        return found


@pytest.fixture
def smk_run(settings: Settings, writer: Writer) -> SmkRun:  # noqa: F811 (the fixture)
    launch_id = add_run(writer, settings, RUN, "smk", "running", engine="snakemake")
    launch_dir = make_run_dirs(settings.runs_root, RUN).launch_dir
    (launch_dir / "logs" / "bwa_mem").mkdir(parents=True)
    (launch_dir / SMK_LOG).write_text("bwa mem: 1000 reads\n")
    (launch_dir / Path(SLURM_LOG).parent).mkdir(parents=True)
    (launch_dir / SLURM_LOG).write_text("slurmstepd: done\n")
    return SmkRun(writer, settings, launch_id, launch_dir)


def job_info(n: int, jobid: int, rule: str = "bwa_mem", **extra: Any) -> SpoolEvent:
    return smk_event(
        n, "job_info", jobid=jobid, rule_name=rule, wildcards={"sample": "WGS-07"}, **extra
    )


def test_smk_rule_and_slurm_logs(smk_run: SmkRun) -> None:
    submitted = "Job 1 has been submitted with SLURM jobid 48731209"
    smk_run.ingest(
        job_info(1, 1, log=[SMK_LOG]),
        smk_event(2, "slurm_submitted", jobid=1, external_jobid="48731209", log=SLURM_LOG),
    )
    attempt = smk_run.attempt()
    assert attempt.native_id == "48731209", submitted
    assert attempt.logs == ((SMK_LOG, "rule_log"), (SLURM_LOG, "slurm_log"))
    found = {f.name: f for f in list_task_files(attempt)}
    assert found[SMK_LOG].kind == "rule_log" and found[SMK_LOG].state == "present"
    assert found[SLURM_LOG].kind == "slurm_log" and found[SLURM_LOG].state == "present"
    assert read_task_file(attempt, SLURM_LOG).text == "slurmstepd: done\n"


def test_smk_job_error_paths(smk_run: SmkRun) -> None:
    other = ".snakemake/slurm_logs/rule_bwa_mem/WGS-07/48731210.log"
    smk_run.ingest(
        job_info(1, 1, log=[SMK_LOG]),
        smk_event(
            2,
            "job_error",
            jobid=1,
            log=[SMK_LOG, str(smk_run.launch_dir / other)],  # the plugin's absolute path
            aux={"external_jobid": "48731210"},
        ),
    )
    attempt = smk_run.attempt()
    assert attempt.state == "failed"
    assert attempt.native_id == "48731210"
    assert attempt.logs == ((SMK_LOG, "rule_log"), (other, "slurm_log"))


def test_smk_deleted_after_success(smk_run: SmkRun) -> None:
    gone = ".snakemake/slurm_logs/rule_bwa_mem/WGS-07/48731299.log"
    smk_run.ingest(
        job_info(1, 1, log=[SMK_LOG]),
        smk_event(2, "slurm_submitted", jobid=1, external_jobid="48731299", log=gone),
        smk_event(3, "job_finished", job_id=1),
    )
    found = {f.name: f for f in list_task_files(smk_run.attempt())}
    assert found[gone].state == "deleted_after_success"
    assert "after success" in (found[gone].note or "")


def test_req13_forged_paths_dropped(smk_run: SmkRun, settings: Settings) -> None:
    """Paths from events are untrusted (req. 6): a work directory outside the run's, a log
    path out of the launch directory, a SLURM log outside it, `.spectio/` files: not stored,
    counted."""
    drops = smk_run.ingest(
        job_info(1, 1, log=["../../.ssh/id_rsa", "/etc/passwd", ".spectio/manifest.json", SMK_LOG]),
        smk_event(2, "slurm_submitted", jobid=1, external_jobid="1", log="/tmp/elsewhere/1.log"),  # noqa: S108 (a forged path)
        smk_event(3, "slurm_submitted", jobid=1, external_jobid="$(id)", log=SLURM_LOG),
    )
    attempt = smk_run.attempt()
    assert attempt.logs == ((SMK_LOG, "rule_log"), (SLURM_LOG, "slurm_log"))
    assert attempt.native_id == "1"  # the forged ID of event 3 is not kept
    assert drops["path_outside_run"] == 4
    assert drops["bad_native_id"] == 1


def test_req13_long_log_names_dropped(smk_run: SmkRun) -> None:
    """A recorded name the file system cannot open (a component over 255 bytes, or over 4096
    bytes in all) is dropped by the projector, never served as a 500 (SEC-P3T28-04)."""
    long_part = f"logs/{'a' * 300}.log"
    long_path = "/".join(["d" * 200] * 21)
    absolute = str(smk_run.launch_dir / long_part)
    drops = smk_run.ingest(job_info(1, 1, log=[long_part, long_path, absolute, SMK_LOG]))
    assert smk_run.attempt().logs == ((SMK_LOG, "rule_log"),)
    assert drops["path_outside_run"] == 3


def test_req13_logs_capped(smk_run: SmkRun) -> None:
    """The paths an attempt keeps from events are capped, each kept once, without a quadratic
    check on the writer: past `MAX_LOGS` they are counted, not kept (SEC-P3T28-05 r1, r2)."""
    many = [f"logs/bwa_mem/{i}.log" for i in range(5000)]
    drops = smk_run.ingest(
        job_info(1, 1, log=[SMK_LOG, SMK_LOG, *many]),
        smk_event(2, "slurm_submitted", jobid=1, external_jobid="1", log=SLURM_LOG),
    )
    logs = smk_run.attempt().logs
    assert len(logs) == MAX_LOGS
    assert logs[0] == (SMK_LOG, "rule_log") and len({p for p, _ in logs}) == MAX_LOGS
    assert SLURM_LOG not in {p for p, _ in logs}
    assert drops["logs_capped"] == 5000 - (MAX_LOGS - 1) + 1


def test_req13_lone_surrogate_name_dropped(smk_run: SmkRun) -> None:
    """A recorded name that is not UTF-8 is dropped, so the listing never fails on it
    (SEC-P3T28-07 r4)."""
    drops = smk_run.ingest(job_info(1, 1, log=["logs/\udcff.log", SMK_LOG]))
    assert smk_run.attempt().logs == ((SMK_LOG, "rule_log"),)
    assert drops["path_outside_run"] == 1
    assert [f.name for f in list_task_files(smk_run.attempt())] == [SMK_LOG]


def test_req13_spectio_dir_any_case(smk_run: SmkRun) -> None:
    """`.spectio/` is compared without case, on a file system that folds it (SEC-P3T28-07 r2)."""
    drops = smk_run.ingest(job_info(1, 1, log=[".SPECTIO/run.json", ".Spectio/spool", SMK_LOG]))
    assert smk_run.attempt().logs == ((SMK_LOG, "rule_log"),)
    assert drops["path_outside_run"] == 2


def test_req13_forged_nextflow_workdir_dropped(settings: Settings, writer: Writer) -> None:  # noqa: F811
    launch_id = add_run(writer, settings, RUN, "nf", "running")
    work = make_run_dirs(settings.runs_root, RUN).work_dir
    sources = StageSources(None, settings.runs_root)

    def task(n: int, workdir: str) -> SpoolEvent:
        return SpoolEvent.model_validate(
            {
                "v": 1,
                "id": f"evt_nf{n}",
                "run": RUN,
                "launch": 1,
                "producer": "nf-spectio/0.0.1",
                "seq": n,
                "time": "2026-10-31T09:00:00Z",
                "type": "nextflow.onTaskSubmit",
                "data": {
                    "process": "ALIGN",
                    "tag": f"S{n}",
                    "attempt": 1,
                    "workDir": workdir,
                    "trace": {"native_id": "77", "workdir": workdir},
                },
            }
        )

    good = str(work.joinpath(*HASH))
    events = [
        task(1, "/etc"),
        task(2, str(work / "ab")),  # one level only
        task(3, str(work / "ab" / ".." / ".." / "x" / HASH[1])),
        task(4, good),
    ]
    batch = SpoolBatch(events, {}, Counter())
    writer.submit(lambda c: ingest(c, launch_id, batch, sources)).result()
    with writer.engine.connect() as conn:
        stored = conn.execute(select(attempts.c.work_dir, attempts.c.native_id)).all()
        drops = dict(conn.execute(select(spool_drops.c.reason, spool_drops.c.count)).all())
    assert sorted(stored, key=str) == sorted([(None, "77")] * 3 + [(good, "77")], key=str)
    assert drops == {"path_outside_run": 3}


# --- The walk of checking-scenarios §11.1 ------------------------------------------------------


@pytest.fixture
def tree(tmp_path: Path) -> Iterator[tuple[Root, Root, Path]]:
    """A run root with `results/`, and its work directory with one task's file."""
    base = private(tmp_path / "run")
    (base / "results").mkdir()
    work = private(base / "work")
    work.joinpath(*HASH).mkdir(parents=True)
    work.joinpath(*HASH, "x.bam").write_bytes(b"BAM\x01")
    run_fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY)
    work_fd = os.open(work, os.O_RDONLY | os.O_DIRECTORY)
    try:
        yield Root(run_fd, PurePosixPath(base)), Root(work_fd, PurePosixPath(work)), base
    finally:
        os.close(run_fd)
        os.close(work_fd)


def test_req13_symlink_fifo_refused(tree: tuple[Root, Root, Path], tmp_path: Path) -> None:
    run, work, base = tree
    bashrc = tmp_path / ".bashrc"
    bashrc.write_text("export TOKEN=x\n")
    (base / "results" / ".command.err").symlink_to(bashrc)
    os.mkfifo(base / "results" / "fifo")
    for name in (".command.err", "fifo"):
        with pytest.raises(NotAllowed):
            open_confined(run, PurePosixPath("results", name), work=work)  # never blocks
    if os.geteuid() == 0:  # a device node needs root
        os.mknod(base / "results" / "null", stat.S_IFCHR | 0o600, os.makedev(1, 3))
        with pytest.raises(NotAllowed):
            open_confined(run, PurePosixPath("results/null"), work=work)


def test_req13_dir_swapped_mid_request(
    tree: tuple[Root, Root, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run, work, base = tree
    (base / "results" / "sub").mkdir()
    (base / "results" / "sub" / "a.txt").write_text("mine\n")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "a.txt").write_text("not the run's\n")
    real_open = os.open

    def swapping(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        fd = real_open(path, flags, *args, **kwargs)
        if path == "results":  # between this openat and the next: sub becomes a symlink
            os.rename(base / "results" / "sub", tmp_path / "moved")
            (base / "results" / "sub").symlink_to(elsewhere)
        return fd

    monkeypatch.setattr(os, "open", swapping)  # the module's `os.open`
    with pytest.raises(NotAllowed):
        open_confined(run, PurePosixPath("results/sub/a.txt"), work=work)


def test_req13_published_symlink_served(tree: tuple[Root, Root, Path]) -> None:
    run, work, base = tree
    (base / "results" / "x.bam").symlink_to(Path(work.path).joinpath(*HASH, "x.bam"))
    with open_confined(run, PurePosixPath("results/x.bam"), work=work) as f:
        assert f.read() == b"BAM\x01"
    (base / "results" / "rel.bam").symlink_to(
        f"../work/{HASH[0]}/{HASH[1]}/x.bam"
    )  # relative, as ln -r makes
    with open_confined(run, PurePosixPath("results/rel.bam"), work=work) as f:
        assert f.read() == b"BAM\x01"
    Path(work.path).joinpath(*HASH, "hop").symlink_to(Path(work.path).joinpath(*HASH, "x.bam"))
    (base / "results" / "two.bam").symlink_to(Path(work.path).joinpath(*HASH, "hop"))
    with pytest.raises(NotAllowed):  # a second symlink is refused
        open_confined(run, PurePosixPath("results/two.bam"), work=work)


def test_req13_symlink_to_home_refused(tree: tuple[Root, Root, Path], tmp_path: Path) -> None:
    run, work, base = tree
    (base / "results" / "x").symlink_to(tmp_path)
    (base / "results" / "x.bam").symlink_to(Path(work.path).joinpath(*HASH, "x.bam"))
    with pytest.raises(NotAllowed):
        open_confined(run, PurePosixPath("results/x"), work=work)
    listing = list_confined(run, PurePosixPath("results"), cap=100, work=work)
    types = {e.name: e.type for e in listing.entries}
    assert types == {"x": "link_outside", "x.bam": "file"}
    assert not listing.truncated
    assert list_confined(run, PurePosixPath("results"), cap=1, work=work).truncated


@dataclass
class Foreign:
    """Files that `os.stat` and `os.fstat` show as another user's, by inode: the owner checks
    are tested without root, so they run on CI too (SEC-P3T28-07 r3)."""

    inodes: set[int]

    def mark(self, path: Path) -> None:
        self.inodes.add(path.lstat().st_ino)


@pytest.fixture
def foreign(monkeypatch: pytest.MonkeyPatch) -> Foreign:
    found = Foreign(set())
    real_stat, real_fstat = os.stat, os.fstat

    def theirs(st: os.stat_result) -> os.stat_result:
        if st.st_ino not in found.inodes:
            return st
        fields = list(st[:10])
        fields[4] = os.geteuid() + 1  # st_uid
        return os.stat_result(fields)

    monkeypatch.setattr(os, "stat", lambda *a, **k: theirs(real_stat(*a, **k)))
    monkeypatch.setattr(os, "fstat", lambda fd: theirs(real_fstat(fd)))
    return found


def test_req13_foreign_uid(tree: tuple[Root, Root, Path], foreign: Foreign) -> None:
    run, work, base = tree
    (base / "results" / "theirs.txt").write_text("someone else's\n")
    foreign.mark(base / "results" / "theirs.txt")
    (base / "results" / "mine.txt").write_text("mine\n")
    (base / "results" / "their_dir").mkdir()
    (base / "results" / "their_dir" / "x.txt").write_text("x\n")
    foreign.mark(base / "results" / "their_dir")
    for rel in ("results/theirs.txt", "results/their_dir/x.txt"):  # every folder on the way too
        with pytest.raises(NotAllowed):
            open_confined(run, PurePosixPath(rel), work=work)
    names = [e.name for e in list_confined(run, PurePosixPath("results"), 100, work=work).entries]
    assert names == ["mine.txt"]


def test_walk_refuses_names() -> None:
    for name in ("/etc/passwd", "../x", "a/../b", "a//b", "./a", "", "a\x00b", "a\x07b"):
        with pytest.raises(NotAllowed):
            confine.safe_rel(name)


# --- The head script's engine log (Task 9) --------------------------------------------------


def spec(tmp_path: Path, engine: str, slurm: SlurmOpts | None) -> LaunchSpec:
    launch = tmp_path / "launch"
    return LaunchSpec(
        run_id=RUN,
        launch_n=1,
        engine=engine,  # type: ignore[arg-type]
        location=tmp_path / "pipeline",
        launch_dir=launch,
        work_dir=tmp_path / "work",
        params={},
        profiles=[],
        engine_cmd=engine,
        slurm=slurm,
    )


def test_engine_log_per_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NXF_HOME", str(tmp_path / "nxf"))
    nf = spec(tmp_path, "nextflow", None)
    assert engine_env(nf)["NXF_LOG_FILE"] == str(tmp_path / "launch" / ".spectio" / "nextflow.log")
    script = render_head_script(nf)
    assert "unset NXF_DEBUG" in script
    assert "NXF_LOG_FILE=" in script
    slurm = SlurmOpts(partition=None, account=None)
    assert "--slurm-keep-successful-logs" in engine_args(spec(tmp_path, "snakemake", slurm))
    assert "--slurm-keep-successful-logs" not in engine_args(spec(tmp_path, "snakemake", None))
