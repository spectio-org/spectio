"""Tests for check_frontmatter.py. Run: python3 -m unittest tools/claude/test_check_frontmatter.py"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).with_name("check_frontmatter.py")
REPO = SCRIPT.parents[2]

GOOD_AGENT = "---\nname: helper\ndescription: Helps.\ntools: Read, Grep\nmodel: opus\n---\nBody.\n"
GOOD_SKILL = "---\nname: tidy\ndescription: Tidies.\ndisable-model-invocation: true\n---\nBody.\n"


class CheckFrontmatter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.agent("helper.md", GOOD_AGENT)
        self.skill("tidy", GOOD_SKILL)

    def tearDown(self):
        self.tmp.cleanup()

    def agent(self, filename, text):
        path = self.root / "agents" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def skill(self, dirname, text):
        (self.root / "skills" / dirname).mkdir(parents=True, exist_ok=True)
        (self.root / "skills" / dirname / "SKILL.md").write_text(text)

    def check(self, root=None):
        r = subprocess.run([sys.executable, str(SCRIPT), str(root or self.root)], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def assert_fails(self, needle):
        code, out = self.check()
        self.assertEqual(code, 1, out)
        self.assertIn(needle, out)

    def test_valid_files_pass(self):
        code, out = self.check()
        self.assertEqual(code, 0, out)
        self.assertIn("1 agent(s), 1 skill(s)", out)

    def test_repository_files_pass(self):
        code, out = self.check(REPO / ".claude")
        self.assertEqual(code, 0, out)

    def test_agent_without_frontmatter(self):
        self.agent("bare.md", "Just text.\n")
        self.assert_fails("bare.md: no frontmatter")

    def test_agent_frontmatter_not_on_first_line(self):
        self.agent("late.md", "\n" + GOOD_AGENT.replace("helper", "late"))
        self.assert_fails("late.md: no frontmatter")

    def test_agent_unclosed_frontmatter(self):
        self.agent("open.md", "---\nname: open\ndescription: x\n")
        self.assert_fails("open.md: frontmatter is not closed")

    def test_agent_yaml_does_not_parse(self):
        self.agent("broken.md", '---\nname: broken\ndescription: "unterminated\n---\n')
        self.assert_fails("broken.md: YAML does not parse")

    def test_agent_frontmatter_not_a_mapping(self):
        self.agent("list.md", "---\n- name\n---\n")
        self.assert_fails("list.md: frontmatter is not a mapping")

    def test_agent_without_name(self):
        self.agent("anon.md", "---\ndescription: x\n---\n")
        self.assert_fails("anon.md: `name` is missing")

    def test_agent_without_description(self):
        self.agent("mute.md", "---\nname: mute\n---\n")
        self.assert_fails("mute.md: `description` is missing")

    def test_agent_name_with_colon(self):
        self.agent("colon.md", "---\nname: 'a:b'\ndescription: x\n---\n")
        self.assert_fails("colon.md: `name`")

    def test_agent_name_starting_with_dash(self):
        self.agent("dash.md", "---\nname: '-x'\ndescription: x\n---\n")
        self.assert_fails("dash.md: `name`")

    def test_agent_unknown_field(self):
        self.agent("typo.md", "---\nname: typo\ndescription: x\nallowedTools: Read\n---\n")
        self.assert_fails("typo.md: unknown field `allowedTools`")

    def test_agent_in_subfolder(self):
        self.agent("sub/deep.md", "---\ndescription: x\n---\n")
        self.assert_fails("sub/deep.md: `name` is missing")

    def test_duplicate_agent_names(self):
        self.agent("twin.md", GOOD_AGENT)
        self.assert_fails("twin.md: `name` helper is also used by")

    def test_skill_yaml_does_not_parse(self):
        self.skill("bad", '---\nname: bad\ndescription: "unterminated\n---\n')
        self.assert_fails("bad/SKILL.md: YAML does not parse")

    def test_skill_without_description(self):
        self.skill("quiet", "---\nname: quiet\n---\n")
        self.assert_fails("quiet/SKILL.md: `description` is missing")

    def test_skill_unknown_field(self):
        self.skill("odd", "---\nname: odd\ndescription: x\nallowed_tools: Read\n---\n")
        self.assert_fails("odd/SKILL.md: unknown field `allowed_tools`")

    def test_skill_directory_without_skill_md(self):
        (self.root / "skills" / "empty").mkdir()
        self.assert_fails("empty: no SKILL.md")


if __name__ == "__main__":
    unittest.main()
