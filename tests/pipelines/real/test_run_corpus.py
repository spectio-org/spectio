"""Unit tests for run_corpus.py: clone cleanup, workdir checks, the Nextflow retry and corpus entry validation.

  python3 -m unittest tests/pipelines/real/test_run_corpus.py
"""
import copy, os, stat, subprocess, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_corpus  # noqa: E402


class CloneTest(unittest.TestCase):
    def test_failed_sha_clone_leaves_no_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "repo"
            with self.assertRaises(subprocess.CalledProcessError):
                run_corpus.clone(f"file://{tmp}/no-such-repo", "0" * 40, dest)
            self.assertFalse(dest.exists())


class WorkdirTest(unittest.TestCase):
    def test_default_workdir_is_fresh_and_private(self):
        a, b = run_corpus.make_workdir(None), run_corpus.make_workdir(None)
        self.addCleanup(a.rmdir); self.addCleanup(b.rmdir)
        self.assertNotEqual(a, b)
        self.assertEqual(a.stat().st_mode & 0o777, 0o700)

    def test_an_explicit_workdir_is_created_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            wd = run_corpus.make_workdir(f"{tmp}/a/b")
            self.assertEqual(wd.stat().st_mode & 0o777, 0o700)

    def test_a_workdir_under_a_sticky_shared_directory_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            sticky = Path(tmp) / "sticky"; sticky.mkdir(); sticky.chmod(0o1777)
            self.assertEqual(run_corpus.make_workdir(str(sticky / "wd")), sticky / "wd")

    def test_a_workdir_through_a_linked_parent_is_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"; target.mkdir()
            (Path(tmp) / "link").symlink_to(target)
            self.assertEqual(run_corpus.make_workdir(str(Path(tmp) / "link" / "wd")), target / "wd")

    def test_missing_parents_are_created_private_under_a_group_umask(self):
        old = os.umask(0o002)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                wd = run_corpus.make_workdir(str(Path(tmp) / "a" / "b"))
                self.assertEqual(stat.S_IMODE((Path(tmp) / "a").stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(wd.stat().st_mode), 0o700)
        finally:
            os.umask(old)

    def test_a_shared_or_linked_workdir_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            shared = Path(tmp) / "shared"; shared.mkdir(); shared.chmod(0o777)
            link = Path(tmp) / "link"; link.symlink_to(Path(tmp))
            under_shared = shared / "wd"
            for bad in (shared, link, under_shared):
                with self.assertRaises(SystemExit):
                    run_corpus.make_workdir(str(bad))


class RetryTest(unittest.TestCase):
    """A failed Nextflow entry is retried once with -resume; Snakemake entries are not retried."""

    def run_with(self, eng, exits):
        spec = {"cmd": ["engine", "run"], "cwd": "/", "env": {}}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(run_corpus.subprocess, "run",
                                  side_effect=[subprocess.CompletedProcess([], rc) for rc in exits]) as run:
            result = run_corpus.run_engine(eng, spec, Path(tmp) / "run.log")
        return result, [c.args[0] for c in run.call_args_list]

    def test_a_failed_nextflow_run_that_passes_on_resume_is_a_retried_pass(self):
        result, cmds = self.run_with("nextflow", [125, 0])
        self.assertEqual(result, (0, True))
        self.assertEqual(cmds, [["engine", "run"], ["engine", "run", "-resume"]])

    def test_a_passing_nextflow_run_is_not_retried(self):
        self.assertEqual(self.run_with("nextflow", [0]), ((0, False), [["engine", "run"]]))

    def test_snakemake_is_run_once(self):
        self.assertEqual(self.run_with("snakemake", [1]), ((1, False), [["engine", "run"]]))

    def test_two_failures_keep_the_failure(self):
        result, cmds = self.run_with("nextflow", [125, 1])
        self.assertEqual(result, (1, True))
        self.assertEqual(len(cmds), 2)

    def test_the_retry_appends_to_the_same_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "run.log"
            spec = {"cmd": [sys.executable, "-c", "import os, sys; print('attempt'); sys.exit(0 if '-resume' in sys.argv else 3)"],
                    "cwd": tmp, "env": dict(os.environ)}
            self.assertEqual(run_corpus.run_engine("nextflow", spec, log), (0, True))
            text = log.read_text()
            self.assertEqual(text.count("attempt"), 2)
            self.assertIn("retrying once with -resume", text)


class ValidateTest(unittest.TestCase):
    def test_current_corpus_is_valid(self):
        self.assertEqual(run_corpus.validate(run_corpus.CORPUS), [])

    def bad(self, section, i, key, value):
        c = copy.deepcopy(run_corpus.CORPUS)
        c[section][i][key] = value
        return run_corpus.validate(c)

    def test_branch_refs_are_rejected(self):
        errs = self.bad("nfcore", 0, "version", "dev")
        self.assertEqual(len(errs), 1)
        self.assertIn("demo", errs[0])
        self.assertTrue(self.bad("snakemake_catalog", 0, "tag", "main"))

    def test_unsafe_paths_and_args_are_rejected(self):
        self.assertTrue(self.bad("snakemake_catalog", 0, "repo", "a/b c"))
        self.assertTrue(self.bad("snakemake_catalog", 0, "directory", ".test;rm"))
        self.assertTrue(self.bad("snakemake_catalog", 0, "snakefile", "$(id)"))
        errs = self.bad("snakemake_catalog", 0, "args", "--cores 2 $(id)")
        self.assertEqual(len(errs), 1)
        self.assertIn("rna-seq-star-deseq2", errs[0])
        self.assertTrue(self.bad("nfcore", 0, "args", "--x `id`"))

    def test_matrix_names_catalog_entries(self):
        nf, smk = run_corpus.matrix(run_corpus.CORPUS, "pr")
        self.assertIn("demo", [e["name"] for e in nf])
        self.assertIn("snakemake-ms-proteomics", [e["name"] for e in smk])
        self.assertTrue(all(e["tier"] == "pr" for e in nf + smk))


if __name__ == "__main__":
    unittest.main()
