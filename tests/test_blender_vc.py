"""Tests for scripts/blender-vc.sh. Skipped when bash or git-lfs is unavailable."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VC = ROOT / "scripts" / "blender-vc.sh"
BASH = shutil.which("bash")


def lfs_available():
    if not shutil.which("git"):
        return False
    return subprocess.run(["git", "lfs", "version"], capture_output=True).returncode == 0


def sh(*args, cwd):
    return subprocess.run([BASH, str(VC), *args], cwd=cwd, capture_output=True, text=True, timeout=60)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=60)


@unittest.skipUnless(BASH and lfs_available(), "bash or git-lfs missing")
class BlenderVc(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_init_outside_repo_fails_with_code_2(self):
        r = sh("init", self.tmp, cwd=self.tmp)
        self.assertEqual(r.returncode, 2)

    def test_init_tracks_blend_in_lfs_and_is_idempotent(self):
        git("init", "-q", cwd=self.tmp)
        Path(self.tmp, ".gitignore").write_text("node_modules/", encoding="utf-8")
        for _ in range(2):
            r = sh("init", self.tmp, cwd=self.tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
        attrs = Path(self.tmp, ".gitattributes").read_text(encoding="utf-8")
        self.assertEqual(attrs.count("*.blend filter=lfs"), 1)
        ignore = Path(self.tmp, ".gitignore").read_text(encoding="utf-8")
        self.assertIn("node_modules/\n# ba:blender", ignore)
        for f, want in (("art/x/x.blend", "lfs"), ("art/x/review/v1/front.png", "lfs"),
                        ("docs/logo.png", "unspecified")):
            out = git("check-attr", "filter", "--", f, cwd=self.tmp).stdout
            self.assertTrue(out.strip().endswith(want), out)
        self.assertEqual(git("check-ignore", "art/x/x.blend1", cwd=self.tmp).returncode, 0)

    def test_status_reports_keys(self):
        git("init", "-q", cwd=self.tmp)
        out = sh("status", self.tmp, cwd=self.tmp).stdout
        self.assertIn("git=yes", out)
        self.assertIn("attributes=missing", out)
        sh("init", self.tmp, cwd=self.tmp)
        self.assertIn("attributes=ok", sh("status", self.tmp, cwd=self.tmp).stdout)


if __name__ == "__main__":
    unittest.main()
