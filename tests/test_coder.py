"""Tests for scripts/coder.py + scripts/delegate-coder.sh against a fake OpenAI-compatible server.
Run: python -m unittest discover -s tests -q
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODER = ROOT / "scripts" / "coder.py"
DELEGATE = ROOT / "scripts" / "delegate-coder.sh"


def find_bash() -> str:
    if sys.platform == "win32":
        for c in (r"C:\Program Files\Git\bin\bash.exe",
                  os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\bash.exe")):
            if os.path.isfile(c):
                return c
    return shutil.which("bash") or "bash"


BASH = find_bash()


def block(path: str, body: str) -> str:
    return f"<<<FILE {path}>>>\n{body}<<<END>>>\n"


IMPL_OK = block("calc.py", "def add(a, b):\n    return a + b\n")
IMPL_BAD = block("calc.py", "def add(a, b):\n    return a - b\n")
TEST = block("test_calc.py", "import unittest\nfrom calc import add\n\n\nclass T(unittest.TestCase):\n"
             "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n")


class FakeCoder:
    """OpenAI-compatible stub: GET /v1/models, POST /v1/chat/completions from a reply queue."""

    def __init__(self, replies=None, status=200):
        self.replies = list(replies or [])
        self.status = status
        self.requests = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, obj):
                data = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._send(200, {"data": [{"id": "tiny-chat"}, {"id": "qwen-coder-7b"}]})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append({"body": body, "auth": self.headers.get("Authorization", "")})
                if outer.status != 200:
                    return self._send(outer.status, {"error": "quota"})
                content = outer.replies.pop(0) if outer.replies else ""
                usage = {"prompt_tokens": 100, "completion_tokens": 20, "prompt_cache_hit_tokens": 64}
                self._send(200, {"choices": [{"message": {"content": content}}], "usage": usage})

        self.server = HTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def closed_port_base() -> str:
    srv = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    port = srv.server_port
    srv.server_close()
    return f"http://127.0.0.1:{port}/v1"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.home = self.tmp / "home"
        self.repo = self.tmp / "repo"
        self.home.mkdir()
        self.repo.mkdir()
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("DEEPSEEK_", "COLIBRI_", "BA_"))}
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home), PYTHONDONTWRITEBYTECODE="1")
        self.servers = []

    def tearDown(self):
        for s in self.servers:
            s.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake(self, **kw) -> FakeCoder:
        s = FakeCoder(**kw)
        self.servers.append(s)
        return s

    def detect(self, *extra) -> dict:
        out = subprocess.run([sys.executable, str(CODER), "detect", "--json", *extra], cwd=self.repo,
                             env=self.env, capture_output=True, text=True, check=True).stdout
        return json.loads(out)


class DetectTests(Base):
    def test_colibri_up_deepseek_missing(self):
        self.env["COLIBRI_API_BASE"] = self.fake().base
        info = self.detect()
        self.assertEqual((info["colibri"], info["deepseek"], info["native"]), ("UP", "MISSING_KEY", "READY"))
        self.assertEqual(info["colibri_model"], "qwen-coder-7b")
        self.assertEqual((info["recommend"], info["chain"]), ("colibri", "colibri,native"))

    def test_both_available_recommends_auto(self):
        self.env["COLIBRI_API_BASE"] = self.fake().base
        (self.home / ".ba").mkdir()
        (self.home / ".ba" / "credentials.env").write_text("DEEPSEEK_API_KEY=sk-test\n")
        info = self.detect()
        self.assertEqual((info["deepseek"], info["recommend"]), ("READY", "auto"))
        self.assertEqual(info["chain"], "colibri,deepseek,native")

    def test_nothing_available_falls_back_to_native_and_flags_saved_pref(self):
        self.env["COLIBRI_API_BASE"] = closed_port_base()
        subprocess.run([sys.executable, str(CODER), "save", "deepseek"], cwd=self.repo, env=self.env, check=True,
                       capture_output=True)
        info = self.detect()
        self.assertEqual((info["colibri"], info["deepseek"]), ("DOWN", "MISSING_KEY"))
        self.assertEqual((info["pref"], info["pref_status"]), ("deepseek", "unavailable"))
        self.assertEqual((info["recommend"], info["choice"], info["chain"]), ("native", "native", "native"))

    def test_key_in_ba_config_is_ignored(self):
        self.env["COLIBRI_API_BASE"] = closed_port_base()
        (self.repo / ".ba").mkdir()
        (self.repo / ".ba" / "config.json").write_text(json.dumps({"DEEPSEEK_API_KEY": "sk-leak"}))
        self.assertEqual(self.detect()["deepseek"], "MISSING_KEY")


class WarmTests(Base):
    def test_warm_sends_system_prompt_with_one_token(self):
        srv = self.fake(replies=["ok"])
        self.env["COLIBRI_API_BASE"] = srv.base
        subprocess.run([sys.executable, str(CODER), "warm"], cwd=self.repo, env=self.env, check=True,
                       capture_output=True)
        body = srv.requests[0]["body"]
        self.assertEqual(body["max_tokens"], 1)
        self.assertIn("PURE CODER", body["messages"][0]["content"])


class DelegateTests(Base):
    def setUp(self):
        super().setUp()
        git = lambda *a: subprocess.run(["git", *a], cwd=self.repo, check=True, capture_output=True)
        git("init", "-q")
        git("config", "user.email", "t@t")
        git("config", "user.name", "t")
        (self.repo / ".gitignore").write_text(".ba/\n__pycache__/\n")
        (self.repo / "README.md").write_text("x\n")
        git("add", ".")
        git("commit", "-qm", "init")
        (self.repo / ".ba" / "runs").mkdir(parents=True)
        (self.repo / ".ba" / "commands.env").write_text("BUILD=true\nTEST=python -m unittest test_calc\n")
        (self.repo / ".ba" / "runs" / "1-brief.md").write_text("Add calc.add(a, b) returning the sum.\n")

    def delegate(self, coder="colibri"):
        return subprocess.run(
            [BASH, str(DELEGATE), "--issue", "1", "--coder", coder, "--brief", ".ba/runs/1-brief.md",
             "--files", "calc.py", "--tests", "test_calc.py", "--test-cmd", "python -m unittest test_calc"],
            cwd=self.repo, env=self.env, capture_output=True, text=True)

    def test_pass_first_try(self):
        self.env["COLIBRI_API_BASE"] = self.fake(replies=[IMPL_OK + TEST]).base
        r = self.delegate()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("RESULT: PASS coder=colibri tries=1", r.stdout)
        self.assertIn("tokens in=100 cached=64 out=20", r.stdout)
        self.assertIn("return a + b", (self.repo / "calc.py").read_text())

    def test_retry_sends_error_tail_back_to_coder(self):
        srv = self.fake(replies=[IMPL_BAD + TEST, IMPL_OK + TEST])
        self.env.update(DEEPSEEK_API_BASE=srv.base, DEEPSEEK_API_KEY="sk-test")
        r = self.delegate("deepseek")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("tries=2", r.stdout)
        self.assertEqual(srv.requests[0]["auth"], "Bearer sk-test")
        first_prompt = srv.requests[0]["body"]["messages"][1]["content"]
        retry_prompt = srv.requests[1]["body"]["messages"][1]["content"]
        self.assertTrue(retry_prompt.startswith(first_prompt), "retry must extend the first prompt (cache prefix)")
        self.assertIn("return a - b", retry_prompt[len(first_prompt):])
        self.assertIn("Previous attempt FAILED", retry_prompt)
        self.assertIn("GREEN FAIL", retry_prompt)

    def test_exhausted_retries_fail_and_roll_back(self):
        self.env["COLIBRI_API_BASE"] = self.fake(replies=[IMPL_BAD + TEST] * 3).base
        r = self.delegate()
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("RESULT: FAIL", r.stdout)
        self.assertFalse((self.repo / "calc.py").exists())

    def test_http_error_is_coder_unavailable(self):
        srv = self.fake(status=402)
        self.env.update(DEEPSEEK_API_BASE=srv.base, DEEPSEEK_API_KEY="sk-test")
        r = self.delegate("deepseek")
        self.assertEqual(r.returncode, 4, r.stdout)
        self.assertIn("RESULT: CODER_UNAVAILABLE coder=deepseek", r.stdout)

    def test_colibri_down_is_coder_unavailable(self):
        self.env["COLIBRI_API_BASE"] = closed_port_base()
        r = self.delegate()
        self.assertEqual(r.returncode, 4, r.stdout)

    def test_paths_outside_targets_are_rejected(self):
        evil = block("../evil.py", "x = 1\n") + block("other.py", "x = 1\n")
        self.env["COLIBRI_API_BASE"] = self.fake(replies=[evil] * 3).base
        r = self.delegate()
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertFalse((self.repo / "other.py").exists())
        self.assertFalse((self.tmp / "evil.py").exists())


if __name__ == "__main__":
    unittest.main()
