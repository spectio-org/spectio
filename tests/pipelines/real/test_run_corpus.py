"""Unit tests for run_corpus.py: clone cleanup and corpus entry validation.

  python3 -m unittest tests/pipelines/real/test_run_corpus.py
"""
import copy, subprocess, sys, tempfile, unittest
from pathlib import Path

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

    def test_a_shared_or_linked_workdir_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            shared = Path(tmp) / "shared"; shared.mkdir(); shared.chmod(0o777)
            link = Path(tmp) / "link"; link.symlink_to(Path(tmp))
            under_shared = shared / "wd"
            for bad in (shared, link, under_shared):
                with self.assertRaises(SystemExit):
                    run_corpus.make_workdir(str(bad))


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
