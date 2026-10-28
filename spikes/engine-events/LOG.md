# Spike T2 — engine event capture: log (2026-10-28)

Every command run for the spike, in order, with its output (abridged where huge). `$S` is the session
scratch directory, `$R` the repository worktree. Machine: Claude Code cloud session, Linux 6.18, OpenJDK 21.

## 1. Engines (pins of `dev/versions.env`, installed the way `dev/bootstrap.sh` does)

```console
$ bash $S/install.sh     # curl the -dist assets + sha256sum -c; uv venv + uv pip sync --require-hashes dev/snakemake.lock.txt
nextflow-26.10.4: OK
nextflow-25.10.9: OK
9.27.1
```

`snakemake-interface-logger-plugins` in the lock: **2.1.0** (`pip METADATA`, `Version: 2.1.0`).

## 2. Snakemake logger plugin

Interface read from the installed package: `snakemake_interface_logger_plugins/base.py` (class
`LogHandlerBase`: `emit` plus the abstract properties `writes_to_stream`, `writes_to_file`,
`has_filter`, `has_formatter`, `needs_rulegraph`), `common.py` (`LogEvent`, 14 members; module prefix
`snakemake_logger_plugin_`), `registry/__init__.py` (`LogHandler` required, `LogHandlerSettings` optional).
The plugin is `snakemake/snakemake_logger_plugin_spectio/__init__.py`, found through `PYTHONPATH`.

First run failed:

```console
$ bash snakemake/run.sh $S/eng/smk/bin/snakemake $S/smk/flaky flaky fail_mode=flaky fail_rule=align fail_sample=S07
exit=1
$ tail flaky.out
  File ".../snakemake/logging.py", line 663, in _setup_plugins
    self.logfile_handlers[handler] = handler.baseFilename
AttributeError: 'LogHandler' object has no attribute 'baseFilename'
```

Fix: set `self.baseFilename` (Snakemake reads it for every handler with `writes_to_file = True`; the
interface does not declare it). Second fix: `resources` arrives as a `snakemake.io.Namedlist`, serialised
as a list without names; the plugin now converts any object with `_names` and `items()` to a dict.

```console
$ bash snakemake/runs.sh $S/eng/smk/bin/snakemake $S
exit=1      # tool error run: compare treatA fails 3 times (expected)
exit=0      # flaky run: align S07 fails at attempt 1, passes at attempt 2
exit=0      # rerun after the tool error, no fault
fixtures/snakemake-9.27.1_checkpoint_flaky_retry.jsonl: 469 lines, 160773 bytes
fixtures/snakemake-9.27.1_tool_error.jsonl: 460 lines, 158665 bytes
fixtures/snakemake-9.27.1_tool_error_rerun.jsonl: 29 lines, 9591 bytes
```

```console
$ python3 analyse_snakemake.py fixtures/snakemake-9.27.1_*.jsonl     (abridged)
##### snakemake-9.27.1_checkpoint_flaky_retry.jsonl {'None': 122, 'workflow_started': 1, 'rulegraph': 1, 'resources_info': 2,
      'run_info': 1, 'job_started': 66, 'job_info': 69, 'shellcmd': 69, 'job_finished': 67, 'progress': 67, 'error': 2, 'job_error': 2}
 untyped (event None) messages: Select jobs to execute... 66, DAG of jobs will be updated after completion. 12,
      Updating checkpoint dependencies. 12, Removing temporary output results/work/reads/<S>.reads.txt. 2 per sample
 progress totals seen: [32] -> [32, 33, ..., 43, 67]
 run_info stats total: [32]
 checkpoint job_info: 12 [(28, 'split'), (36, 'split')]
 job_info keys: benchmark indent input is_checkpoint is_handover jobid local log output printshellcmd priority reason
      resources rule_msg rule_name shellcmd threads wildcards
 job_info resources example: {'_cores': 1, '_nodes': 1, 'attempt': 1, 'mem': '512 MB', 'mem_mb': 512, 'mem_mib': 489,
      'runtime': 2, 'time_limit_s': 120, 'tmpdir': '/tmp'}
 job_error keys: aux conda_env container_img indent input jobid log output rule_msg rule_name shellcmd
 workflow_started keys: basedir cmd config_md5 configfiles cwd datetime host platform python_version quietness rundir
      snakefile snakefile_main snakemake_version user workflow_id   workflow_id: UUID 316d8ce0-...
 jobids with >1 job_info (retries): {103: 2, 104: 2}
  job 103 sequence: job_started, job_info, job_error, None 'Trying to restart job 103.', job_started, job_info, job_finished
##### snakemake-9.27.1_tool_error.jsonl
 jobids with >1 job_info (retries): {30: 3}   (job_info, job_error, 'Trying to restart job 30.') x3, no job_finished
 error events: 3 x 'RuleException: CalledProcessError ... returned non-zero exit status 1.', then 'WorkflowError: At least one job did not complete successfully.'
##### snakemake-9.27.1_tool_error_rerun.jsonl
 run_info total 3, 3 jobs, new workflow_id 88d1b16b-... (the failed run had 6a5d370a-...)
```

## 3. Nextflow, Tower protocol

```console
$ bash nextflow/runs.sh $S/eng/nextflow-26.10.4 $S 8765      # Tower only, first pass
flaky exit=0
toolerr exit=1
resume exit=0
$ bash nextflow/runs.sh $S/eng/nextflow-25.10.9 $S 8766
flaky exit=0
toolerr exit=1
resume exit=0
```

`nf-tower` was downloaded from the registry on first use: `~/.nextflow/plugins/nf-tower-1.32.2` (26.10.4,
`Plugin-Requires: >=26.10.2`) and `nf-tower-1.17.8` (25.10.9). The 26.10.4 log lists the core plugins:
`nf-tower@1.32.2`, `nf-seqera@0.26.1`, `nf-wave@1.22.4`, ... (`PluginsFacade - Setting up plugin manager`).

```console
$ python3 analyse_tower.py fixtures/nextflow-26.10.4_tower_flaky.jsonl     (abridged; first pass, same shape in the final pass)
 counts: POST /trace/create 1, PUT /trace/{id}/begin 1, PUT /trace/{id}/progress 7, PUT /trace/{id}/complete 1
 agent: Nextflow/26.10.4   auth header on all: True
 create body: instant, projectName 'main.nf', repository None, runName, sessionId, workflowId None -> reply {'workflowId': 'wf...'}
 begin keys: dag instant processNames towerLaunch workflow      (25.10.9: no 'dag')
 task statuses: COMPLETED 65, RUNNING 9, NEW 57, SUBMITTED 1, FAILED 2
 failed/retried tasks: ALIGN S07.chunk0000 FAILED exit 1 attempt 1 errorAction RETRY; ... COMPLETED attempt 2
 complete progress: failed 2, retries 2, succeeded 65, cached 0
```

No `GET` request and no `/heartbeat` (runs shorter than a minute). The capture server answered only
`{"workflowId": ...}` to create and `{}` elsewhere, and no run aborted.

## 4. nf-spectio (TraceObserverV2), built without Gradle

```console
$ javap -cp $S/eng/nextflow-26.10.4 nextflow.trace.TraceObserverV2 nextflow.trace.TraceObserverFactoryV2
public interface nextflow.trace.TraceObserverV2 {
  onFlowCreate(Session); onFlowBegin(); onFlowComplete(); onProcessCreate(TaskProcessor); onProcessTerminate(TaskProcessor);
  onTaskPending(TaskEvent); onTaskSubmit(TaskEvent); onTaskStart(TaskEvent); onTaskComplete(TaskEvent); onTaskCached(TaskEvent);
  boolean enableMetrics(); onFlowError(TaskEvent); onWorkflowOutput(WorkflowOutputEvent); onFilePublish(FilePublishEvent);
}
public interface nextflow.trace.TraceObserverFactoryV2 extends org.pf4j.ExtensionPoint {
  Collection<TraceObserverV2> create(Session);
}
$ javap -cp $S/eng/nextflow-25.10.9 nextflow.trace.TraceObserverV2     # identical method list
$ bash nextflow/nf-spectio/build.sh $S/eng/nextflow-26.10.4 ~/.nextflow/plugins
nf-spectio-0.0.1/classes/META-INF/MANIFEST.MF
nf-spectio-0.0.1/classes/META-INF/extensions.idx
nf-spectio-0.0.1/classes/spectio/SpectioFactory.class
nf-spectio-0.0.1/classes/spectio/SpectioObserver.class (+ closures)
nf-spectio-0.0.1/classes/spectio/SpectioPlugin.class
```

The Groovy compiler inside the Nextflow `-dist` jar (`org.codehaus.groovy.tools.FileSystemCompiler`)
compiles the plugin; the directory layout copies the registry-installed `nf-tower-1.32.2`. Probe:

```console
$ SPECTIO_ENDPOINT=http://localhost:8770/spectio/events nextflow-26.10.4 run main.nf -profile test,local -plugins nf-spectio@0.0.1
[SUCCESS] completed=65 failed=0 cached=0
$ wc -l cap.jsonl
298
$ grep plugin .nextflow.log
PluginsFacade - Setting up plugin manager > mode=prod; embedded=false; plugins-dir=/root/.nextflow/plugins; ...
PluginsFacade - Plugins declared=[nf-spectio@0.0.1]
```

The same class files, built against 26.10.4, also load on 25.10.9.

## 5. Final pass: Tower and nf-spectio in the same runs

```console
$ PLUGIN=1 bash nextflow/runs.sh $S/eng/nextflow-26.10.4 $S 8765
flaky exit=0
toolerr exit=1
resume exit=0
fixtures/nextflow-26.10.4_tower_flaky.jsonl: 10 lines, 199689 bytes
fixtures/nextflow-26.10.4_plugin_flaky.jsonl: 306 lines, 392188 bytes      (before --slim; 258074 after)
fixtures/nextflow-26.10.4_tower_toolerr.jsonl: 15 lines, 219027 bytes
fixtures/nextflow-26.10.4_plugin_toolerr.jsonl: 293 lines, 371879 bytes
fixtures/nextflow-26.10.4_tower_resume.jsonl: 6 lines, 127086 bytes
fixtures/nextflow-26.10.4_plugin_resume.jsonl: 109 lines, 143908 bytes
$ PLUGIN=1 bash nextflow/runs.sh $S/eng/nextflow-25.10.9 $S 8766
flaky exit=0 / toolerr exit=1 / resume exit=0
$ bash $S/renorm.sh       # plugin fixtures again with --slim (trace record dropped from pending/submit/start)
2.6M fixtures            # 15 files: 12 Nextflow, 3 Snakemake
```

Review fixes (doc review, same day): the Snakemake `platform` string (kernel version) is now replaced by
`<platform>` (`normalise.py --token-key platform`, passed by `snakemake/runs.sh`); the three Snakemake
fixtures were normalised again from the raw captures, a one-line change each, and `analyse_snakemake.py`
prints the same summaries as above.

```console
$ python3 analyse_tower.py fixtures/nextflow-26.10.4_tower_flaky.jsonl | grep "task statuses"
 task statuses: {'RUNNING': 8, 'COMPLETED': 65, 'NEW': 59, 'SUBMITTED': 3, 'FAILED': 2}
$ python3 analyse_tower.py fixtures/nextflow-25.10.9_tower_toolerr.jsonl | grep "counts\|final statuses"
 counts: {('POST', '/trace/create'): 1, ('PUT', '/trace/{id}/begin'): 1, ('PUT', '/trace/{id}/progress'): 7, ('PUT', '/trace/{id}/complete'): 2}
 distinct taskIds: 64 final statuses: {'COMPLETED': 62, 'FAILED': 1, 'ABORTED': 1}
$ python3 tools/media/cast.py tools/media/casts/t2-engine-events.yaml
-> docs/assets/casts/t2-engine-events.cast  (16.3 s, 519 events, 14 KB)
```

```console
$ python3 analyse_plugin.py fixtures/nextflow-<v>_plugin_<run>.jsonl fixtures/nextflow-<v>_tower_<run>.jsonl   (abridged)
26.10.4 flaky   hooks: onFlowCreate 1, onProcessCreate 8, onFlowBegin 1, onTaskPending/Submit/Start/Complete 67 each,
                onProcessTerminate 8, onFilePublish 19, onFlowComplete 1
                onProcessTerminate order: MAKE_READS, QC_STATS, SPLIT, QC_REPORT, ALIGN, MERGE, COMPARE, FINAL_REPORT
                task events AFTER their process's onProcessTerminate: QC_STATS 1, ALIGN 1, MERGE 1, COMPARE 2 (all onTaskComplete)
                onTaskComplete QC_STATS outputs: {'fileoutparam<0>': FileOutParam, name None, '<launch>/work/c5/9654ea.../S03.qc.json'}
                onTaskComplete SPLIT outputs: {'fileoutparam<0:1>': [.../chunks/S04.chunk0000.txt, ...chunk0001.txt],
                                               'valueoutparam<0:0>': name 'sample', 'S04'}
                failed attempt: handler status COMPLETED, trace status FAILED, exit 1, errorAction RETRY; retry = new taskId (49 -> 63)
                onFilePublish: source <launch>/work/..., target <launch>/results/qc/per_sample/S03.qc.json, labels None
                SAME RUN: True (intergalactic_montalcini, d138a5c4-...)   taskIds tower 67, plugin 67, equal
26.10.4 toolerr onProcessTerminate 7 (no FINAL_REPORT); onTaskPending 65, onTaskSubmit 64 (FINAL_REPORT never submitted)
                onFlowComplete (success False, exit 1) THEN onFlowError, whose TaskEvent has no handler
                SAME RUN: True (soggy_payne, 38960569-...)
26.10.4 resume  onTaskCached 63 (handler status NEW, outputs present), 2 executed; onFilePublish 19 (cached tasks republished)
                SAME RUN: True (irreverent_yalow, same session 38960569-... as toolerr)
25.10.9 flaky   same hooks and counts as 26.10.4; every process has one onTaskComplete after its onProcessTerminate
                SAME RUN: True (pedantic_gauss, ea241900-...)
25.10.9 toolerr onProcessTerminate 6; onFlowComplete TWICE (onFlowComplete, onFlowError, onFlowComplete); one onTaskComplete with handler status RUNNING
                SAME RUN: True (scruffy_hodgkin, ac71c9a0-...)
25.10.9 resume  onTaskCached 62, 3 executed; SAME RUN: True (fervent_mendel, session ac71c9a0-...)
```

## 6. Figure and docs

```console
$ PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers uv run --no-project --with playwright==1.63.0 python3 tools/diagrams/t2_engine_events.py
-> docs/assets/diagrams/t2-engine-events_light.svg / _light.png / _dark.svg / _dark.png
$ python3 tools/docs/check.py
(see the Progress page for the last line)
```
