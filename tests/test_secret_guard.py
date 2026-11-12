"""secret-guard.sh PreToolUse mode: untracked files must not cause a false BLOCK."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_coder import BASH, ROOT

GUARD = ROOT / "scripts" / "secret-guard.sh"
CMD = "git add . && git " + "commit -m x"


class SecretGuardCommitAll(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)

    def tearDown(self):
        shutil.rmtree(self.repo, ignore_errors=True)

    def hook(self) -> subprocess.CompletedProcess:
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": CMD}})
        return subprocess.run([BASH, str(GUARD)], cwd=self.repo, input=payload, capture_output=True, text=True)

    def test_clean_untracked_file_is_allowed(self):
        (self.repo / "app.py").write_text("print('hi')\n")
        r = self.hook()
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_untracked_secret_is_blocked(self):
        (self.repo / "app.py").write_text('aws = "AKIA' + "ABCDEFGHIJKLMNOP" + '"\n')
        r = self.hook()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("BLOCKED", r.stderr)


if __name__ == "__main__":
    unittest.main()
