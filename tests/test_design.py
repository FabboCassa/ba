"""Tests for scripts/design-deal.py and scripts/design-lint.py.
Run: python -m unittest discover -s tests -q
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEAL = ROOT / "scripts" / "design-deal.py"
LINT = ROOT / "scripts" / "design-lint.py"
AXES = ("palette", "type", "layout", "motion", "surface")


def run(script, *args, cwd=None):
    return subprocess.run([sys.executable, "-I", str(script), *args], cwd=cwd,
                          capture_output=True, text=True, timeout=60)


def deal(*args, cwd=None):
    r = run(DEAL, "deal", "--json", *args, cwd=cwd)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class Deal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_directions_share_no_item(self):
        dirs = deal("--n", "3", "--seed", "7", cwd=self.tmp)
        self.assertEqual(len(dirs), 3)
        for axis in AXES:
            ids = [d[axis]["id"] for d in dirs]
            self.assertEqual(len(ids), len(set(ids)), f"{axis} repeated: {ids}")

    def test_same_seed_same_deal_other_seed_differs(self):
        a = deal("--seed", "1", cwd=self.tmp)
        b = deal("--seed", "1", cwd=self.tmp)
        self.assertEqual(a, b)
        others = [deal("--seed", str(s), cwd=self.tmp) for s in range(2, 7)]
        self.assertTrue(any(o != a for o in others))

    def test_recorded_choice_is_avoided_next_time(self):
        first = deal("--n", "1", "--seed", "3", cwd=self.tmp)[0]
        r = run(DEAL, "record", "proj", "--palette", first["palette"]["id"],
                "--type", first["type"]["id"], "--layout", first["layout"]["id"],
                "--motion", first["motion"]["id"], "--surface", first["surface"]["id"], cwd=self.tmp)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((Path(self.tmp) / ".ba" / "design" / "history.json").is_file())
        for seed in range(10):
            d = deal("--n", "3", "--seed", str(seed), cwd=self.tmp)
            for axis in AXES:
                self.assertNotIn(first[axis]["id"], [x[axis]["id"] for x in d], axis)

    def test_mood_biases_choice(self):
        hits = 0
        for seed in range(10):
            d = deal("--n", "1", "--mood", "playful", "--seed", str(seed), cwd=self.tmp)[0]
            hits += "playful" in d["palette"]["tags"]
        self.assertGreaterEqual(hits, 7)

    def test_unknown_record_id_fails(self):
        r = run(DEAL, "record", "p", "--palette", "nope", cwd=self.tmp)
        self.assertNotEqual(r.returncode, 0)


SLOP_HTML = """<html><head><style>
body { font-family: 'Inter', sans-serif; background: #F4F1EA; }
.hero { background: linear-gradient(135deg, #6366f1, #a855f7); }
@keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } }
.eyebrow { text-transform: uppercase; letter-spacing: .2em; }
</style></head><body>
<h1>Unlock the power of seamless workflows</h1>
<a class="btn">Get started →</a>
</body></html>
"""

CLEAN_HTML = """<html><head><style>
:root { --ink: #1d2a3a; --paper: #e9eef2; --signal: #ff6b4a; }
body { font-family: 'Familjen Grotesk', sans-serif; background: var(--paper); color: var(--ink); }
h1 { font-family: 'Newsreader', serif; }
.reveal { animation: wipe .6s ease-out; }
@keyframes wipe { from { clip-path: inset(0 100% 0 0); } }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
</style></head><body>
<h1>Book a lane at Bellwater pool</h1>
<a class="btn">Book a lane</a>
</body></html>
"""


class Lint(unittest.TestCase):
    def write(self, body, name="p.html"):
        d = Path(tempfile.mkdtemp())
        f = d / name
        f.write_text(body, encoding="utf-8")
        return f

    def findings(self, f, *args):
        r = run(LINT, "--json", *args, str(f))
        return r, json.loads(r.stdout)

    def test_slop_page_flags_tells(self):
        r, out = self.findings(self.write(SLOP_HTML))
        rules = {x["rule"] for x in out}
        for rule in ("cream-terracotta", "ai-gradient", "default-font", "fade-up",
                     "eyebrow-caps", "arrow-cta", "hype-copy", "no-reduced-motion"):
            self.assertIn(rule, rules)
        self.assertEqual(r.returncode, 1)

    def test_finding_has_file_and_line(self):
        _, out = self.findings(self.write(SLOP_HTML))
        grad = next(x for x in out if x["rule"] == "ai-gradient")
        self.assertEqual(grad["line"], 3)
        self.assertTrue(grad["file"].endswith("p.html"))

    def test_clean_page_passes(self):
        r, out = self.findings(self.write(CLEAN_HTML))
        self.assertEqual(out, [])
        self.assertEqual(r.returncode, 0)

    def test_warnings_only_pass_unless_strict(self):
        f = self.write("<button>Elevate your game →</button>\n")
        r, out = self.findings(f)
        self.assertTrue(out)
        self.assertTrue(all(x["severity"] == "warn" for x in out))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(run(LINT, "--strict", str(f)).returncode, 1)

    def test_directory_scan_skips_node_modules(self):
        f = self.write(SLOP_HTML)
        nm = f.parent / "node_modules"
        nm.mkdir()
        (nm / "x.css").write_text(".a{background:linear-gradient(#6366f1,#a855f7)}", encoding="utf-8")
        _, out = self.findings(f.parent)
        self.assertFalse(any("node_modules" in x["file"] for x in out))


if __name__ == "__main__":
    unittest.main()
