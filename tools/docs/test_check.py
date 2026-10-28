"""Tests for tools/docs/check.py: the progress-hook part of the build check, and the annotation format.
Run: python3 -m unittest tools/docs/test_check.py"""
import contextlib
import importlib.util
import io
import pathlib
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("docs_check", pathlib.Path(__file__).with_name("check.py"))
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)

STRIP = "<!-- spectio:progress-strip -->"
TABLE = "<!-- spectio:progress-table -->"
RENDERED_STRIP = '<div class="sp-waves"><a class="sp-wave" href="progress/#w0">W0</a></div>'
RENDERED_TABLE = "<table><thead><tr><th>Step</th><th>Kind</th><th>Status</th><th>Page</th></tr></thead></table>"


class ProgressHookOutput(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.docs = pathlib.Path(self.tmp.name, "docs")
        self.site = pathlib.Path(self.tmp.name, "site")
        self.page("index.md", f"# Home\n\n{STRIP}\n", "index.html", f"<h1>Home</h1>{RENDERED_STRIP}")
        self.page("progress/index.md", f"# Progress\n\n{TABLE}\n", "progress/index.html", RENDERED_TABLE)
        self.page("guide.md", "# Guide\n", "guide/index.html", "<h1>Guide</h1>")
        check.failures.clear()

    def tearDown(self):
        self.tmp.cleanup()
        check.failures.clear()

    def page(self, md, md_text, html, html_text):
        for path, text in ((self.docs / md, md_text), (self.site / html, html_text)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def run_check(self):
        with contextlib.redirect_stdout(io.StringIO()):
            check.check_progress_hook(self.site, self.docs)
        return check.failures

    def test_rendered_pages_pass(self):
        self.assertEqual(self.run_check(), [])

    def test_unrendered_placeholder_in_any_built_page_fails(self):
        (self.site / "guide/index.html").write_text(f"<h1>Guide</h1>{TABLE}")
        self.assertTrue(any("guide/index.html" in f and "placeholder" in f for f in self.run_check()))

    def test_page_with_strip_placeholder_but_no_strip_fails(self):
        (self.site / "index.html").write_text("<h1>Home</h1>")
        self.assertTrue(any("index.html" in f and "progress strip" in f for f in self.run_check()))

    def test_page_with_table_placeholder_but_no_table_fails(self):
        (self.site / "progress/index.html").write_text("<h1>Progress</h1>")
        self.assertTrue(any("progress/index.html" in f and "progress table" in f for f in self.run_check()))

    def test_missing_built_page_fails(self):
        (self.site / "progress/index.html").unlink()
        self.assertTrue(any("progress/index.html" in f for f in self.run_check()))

    def test_page_url_follows_directory_urls(self):
        self.assertEqual(check.built_page(pathlib.PurePosixPath("roadmap/index.md")), "roadmap/index.html")
        self.assertEqual(check.built_page(pathlib.PurePosixPath("roadmap/plan.md")), "roadmap/plan/index.html")
        self.assertEqual(check.built_page(pathlib.PurePosixPath("index.md")), "index.html")


class Annotation(unittest.TestCase):
    def tearDown(self):
        check.failures.clear()

    def test_newlines_and_percent_are_escaped_in_the_error_command(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            check.fail("build", "50% done\nnext\rline", "a%b\nc")
        self.assertEqual(out.getvalue(), "::error file=a%25b%0Ac::[build] 50%25 done%0Anext%0Dline\n")
        self.assertEqual(check.failures, ["build: 50% done\nnext\rline"])


if __name__ == "__main__":
    unittest.main()
