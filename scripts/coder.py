#!/usr/bin/env python3
"""
scripts/coder.py — external "Pure Coder" client (Colibri local / DeepSeek API).
Stdlib only. Subcommands:
  detect [--coder X] [--json] [--warm]  availability of colibri / deepseek / native (+ pref, chain)
  save <coder>                  store per-repo preference in .ba/config.json
  generate --coder X --brief F --files a,b [--feedback F] [--base-dir D] [--prev-out F]
                                ask the coder for full file contents and write them
  warm [--coder X]              load the model + cache the system prompt (detect --warm runs it detached)
Exit codes for generate: 0 applied, 10 CODER_UNAVAILABLE, 11 bad output.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

CODERS = ("auto", "colibri", "deepseek", "native")
# colibri serves OpenAI API on :8000/v1. 127.0.0.1, not localhost: on Windows localhost tries ::1 first (+0.8s).
DEFAULT_COLIBRI_BASE = "http://127.0.0.1:8000/v1"
DEFAULT_DEEPSEEK_BASE = "https://api.deepseek.com"
CONFIG = Path(".ba/config.json")
EXIT_UNAVAILABLE = 10
EXIT_BAD_OUTPUT = 11
MAX_FILE_BYTES = 200_000

SYSTEM_PROMPT = """You are a PURE CODER. A tech lead gives you a brief and the current target files.
Write the code and tests the brief asks for. No explanations, no prose.
Output ONLY file blocks, each with the COMPLETE new content of one file:
<<<FILE relative/path>>>
...full file content...
<<<END>>>
Rules: only paths listed as targets; never truncate or write "rest unchanged";
no markdown fences around blocks; real tests (no tautologies, mock only external boundaries);
comments only for a non-obvious WHY (never narrate what the code does);
no secrets, no new dependencies unless the brief allows them."""


def load_config() -> dict:
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def read_env_file(path: Path, name: str) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == name:
                return v.strip().strip("\"'")
    except OSError:
        pass
    return ""


def get_secret(name: str) -> str:
    # Keys never live in .ba/ (config.json may be committed, commands.env is echoed by detect.sh).
    val = os.environ.get(name, "").strip()
    if val:
        return val
    cwd = Path.cwd().resolve()
    for d in [cwd, *cwd.parents]:
        if (d / ".env").is_file():
            val = read_env_file(d / ".env", name)
            if val:
                return val
    return read_env_file(Path.home() / ".ba" / "credentials.env", name)


def colibri_base(cfg: dict) -> str:
    return (os.environ.get("COLIBRI_API_BASE") or cfg.get("colibri_base") or DEFAULT_COLIBRI_BASE).rstrip("/")


def http_json(url: str, data: dict | None = None, key: str = "", timeout: float = 30) -> dict:
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "ba-coder"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def colibri_models(cfg: dict, timeout: float) -> list[str] | None:
    try:
        data = http_json(f"{colibri_base(cfg)}/models", timeout=timeout).get("data", [])
        return [m["id"] for m in data if isinstance(m, dict) and "id" in m]
    except Exception:
        return None


def pick_colibri_model(cfg: dict, models: list[str]) -> str:
    explicit = os.environ.get("COLIBRI_MODEL") or cfg.get("colibri_model")
    if explicit:
        return explicit
    def size(m: str) -> float:
        hit = re.search(r"(\d+(?:\.\d+)?)b\b", m.lower())
        return float(hit.group(1)) if hit else 0.0
    coders = sorted((m for m in models if "coder" in m.lower()), key=size, reverse=True)
    return (coders or models or [""])[0]


def chain_for(choice: str, colibri_up: bool, deepseek_ready: bool) -> list[str]:
    order = {"auto": ["colibri", "deepseek"], "colibri": ["colibri"], "deepseek": ["deepseek"]}.get(choice, [])
    up = {"colibri": colibri_up, "deepseek": deepseek_ready}
    return [c for c in order if up[c]] + ["native"]


def detect(cfg: dict, timeout: float) -> dict:
    models = colibri_models(cfg, timeout)
    colibri_up = models is not None
    deepseek_ready = bool(get_secret("DEEPSEEK_API_KEY"))
    if colibri_up and deepseek_ready:
        rec = "auto"
    elif colibri_up:
        rec = "colibri"
    elif deepseek_ready:
        rec = "deepseek"
    else:
        rec = "native"
    pref = cfg.get("coder") if cfg.get("coder") in CODERS else ""
    pref_ok = bool(pref) and (
        pref == "native" or (pref == "auto" and (colibri_up or deepseek_ready))
        or (pref == "colibri" and colibri_up) or (pref == "deepseek" and deepseek_ready))
    return {
        "colibri": "UP" if colibri_up else "DOWN",
        "colibri_base": colibri_base(cfg),
        "colibri_model": pick_colibri_model(cfg, models or []) if colibri_up else "",
        "deepseek": "READY" if deepseek_ready else "MISSING_KEY",
        "native": "READY",
        "pref": pref or "none",
        "pref_status": ("ok" if pref_ok else "unavailable") if pref else "none",
        "recommend": rec,
    }


def cmd_detect(args) -> int:
    cfg = load_config()
    info = detect(cfg, args.timeout)
    choice = args.coder or (info["pref"] if info["pref_status"] == "ok" else info["recommend"])
    info["choice"] = choice
    info["chain"] = ",".join(chain_for(choice, info["colibri"] == "UP", info["deepseek"] == "READY"))
    if args.warm and info["chain"].startswith("colibri"):
        flags = {"creationflags": 0x00000008 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
        subprocess.Popen([sys.executable, __file__, "warm", "--coder", "colibri"], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.getcwd(), **flags)
        info["warm"] = "started"
    if args.json:
        print(json.dumps(info, indent=2))
        return 0
    model = f" model={info['colibri_model']}" if info["colibri_model"] else ""
    print(f"colibri={info['colibri']} base={info['colibri_base']}{model}")
    print(f"deepseek={info['deepseek']}")
    print("native=READY")
    print(f"pref={info['pref']} ({info['pref_status']})")
    print(f"recommend={info['recommend']}")
    print(f"chain={info['chain']}")
    if info.get("warm"):
        print("warm=started (colibri loads model + caches system prompt in background)")
    return 0


def cmd_save(args) -> int:
    cfg = load_config()
    cfg["coder"] = args.coder
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"saved coder={args.coder} -> {CONFIG}")
    return 0


def safe_path(p: str) -> Path | None:
    path = Path(p)
    if path.is_absolute() or ".." in path.parts or p.startswith(".git/") or p.startswith(".ba/"):
        return None
    return path


def build_prompt(brief: str, files: list[str], feedback: str, base_dir: str = "", prev_out: str = "") -> str:
    # Cache-friendly order: everything before the retry section is byte-identical across retries
    # (targets come from the pre-run snapshot), so DeepSeek / local prefix caches hit on it.
    parts = ["# Brief", brief.strip(), "", "# Target files (content before your work)"]
    for f in files:
        p = Path(base_dir) / f if base_dir else Path(f)
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_BYTES]
            parts += [f"<<<FILE {f}>>>", text, "<<<END>>>"]
        else:
            parts.append(f"{f}: (new file)")
    if prev_out.strip():
        parts += ["", "# Your previous attempt", prev_out.strip()]
    if feedback.strip():
        parts += ["", "# Previous attempt FAILED - fix the root cause. Last log lines:", feedback.strip()]
    return "\n".join(parts)


FILE_RE = re.compile(r"<<<FILE\s+(.+?)>>>\r?\n(.*?)<<<END>>>", re.S)


def parse_blocks(text: str) -> list[tuple[str, str]]:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    blocks = []
    for path, body in FILE_RE.findall(text):
        body = re.sub(r"\A```[\w+-]*\r?\n", "", body)
        body = re.sub(r"\r?\n```\s*\Z", "\n", body)
        blocks.append((path.strip(), body))
    return blocks


def endpoint(coder: str, cfg: dict) -> tuple[str, str, str]:
    if coder == "deepseek":
        key = get_secret("DEEPSEEK_API_KEY")
        if not key:
            raise ConnectionError("DEEPSEEK_API_KEY missing")
        base = (os.environ.get("DEEPSEEK_API_BASE") or DEFAULT_DEEPSEEK_BASE).rstrip("/")
        model = os.environ.get("DEEPSEEK_CODER_MODEL") or cfg.get("deepseek_model") or "deepseek-chat"
    else:
        key = ""
        base = colibri_base(cfg)
        models = colibri_models(cfg, 2)
        if models is None:
            raise ConnectionError(f"colibri not reachable at {base}")
        model = pick_colibri_model(cfg, models)
    return base, key, model


def call_coder(coder: str, cfg: dict, prompt: str, max_tokens: int = 0) -> tuple[str, dict]:
    base, key, model = endpoint(coder, cfg)
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        "temperature": 0,
        "stream": False,
        "max_tokens": max_tokens or int(os.environ.get("BA_CODER_MAX_TOKENS", "8192")),
    }
    timeout = float(os.environ.get("BA_CODER_TIMEOUT", "600"))
    resp = http_json(f"{base}/chat/completions", payload, key=key, timeout=timeout)
    choices = resp.get("choices") or [{}]
    return (choices[0].get("message") or {}).get("content") or "", resp.get("usage") or {}


def usage_line(u: dict) -> str:
    cached = u.get("prompt_cache_hit_tokens")
    if cached is None:
        cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", "?")
    return f"tokens in={u.get('prompt_tokens', '?')} cached={cached} out={u.get('completion_tokens', '?')}"


def cmd_warm(args) -> int:
    # Loads the model and caches the system-prompt prefix while the PM is still writing the brief.
    try:
        call_coder(args.coder, load_config(), "Reply with: ok", max_tokens=1)
    except Exception as e:
        print(f"warm failed: {e}")
        return 1
    print("warm ok")
    return 0


def cmd_generate(args) -> int:
    cfg = load_config()
    allowed = [f.strip().replace("\\", "/") for f in args.files.split(",") if f.strip()]
    if not allowed:
        print("no target files", file=sys.stderr)
        return 2
    feedback = Path(args.feedback).read_text(encoding="utf-8", errors="replace") if args.feedback else ""
    prev_out = ""
    if args.prev_out and Path(args.prev_out).is_file():
        prev_out = Path(args.prev_out).read_text(encoding="utf-8", errors="replace")
    prompt = build_prompt(Path(args.brief).read_text(encoding="utf-8"), allowed, feedback, args.base_dir, prev_out)
    try:
        out, usage = call_coder(args.coder, cfg, prompt)
    except urllib.error.HTTPError as e:
        print(f"CODER_UNAVAILABLE {args.coder}: HTTP {e.code} {e.read()[:200]!r}")
        return EXIT_UNAVAILABLE
    except (OSError, ValueError) as e:
        print(f"CODER_UNAVAILABLE {args.coder}: {e}")
        return EXIT_UNAVAILABLE
    if args.raw_out:
        Path(args.raw_out).write_text(out, encoding="utf-8")
    blocks = parse_blocks(out)
    if not blocks:
        print(f"{usage_line(usage)}")
        print("BAD_OUTPUT: no <<<FILE path>>> ... <<<END>>> blocks in coder reply")
        return EXIT_BAD_OUTPUT
    rejected = [p for p, _ in blocks if p not in allowed or safe_path(p) is None]
    if rejected:
        print(f"BAD_OUTPUT: paths outside targets: {', '.join(rejected)}")
        return EXIT_BAD_OUTPUT
    for p, body in blocks:
        path = Path(p)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8", newline="")
    print(f"WROTE: {' '.join(p for p, _ in blocks)} | {usage_line(usage)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="ba external coder client")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect")
    d.add_argument("--coder", choices=CODERS)
    d.add_argument("--json", action="store_true")
    d.add_argument("--warm", action="store_true")
    d.add_argument("--timeout", type=float, default=float(os.environ.get("BA_DETECT_TIMEOUT", "0.8")))
    s = sub.add_parser("save")
    s.add_argument("coder", choices=CODERS)
    g = sub.add_parser("generate")
    g.add_argument("--coder", choices=("colibri", "deepseek"), required=True)
    g.add_argument("--brief", required=True)
    g.add_argument("--files", required=True)
    g.add_argument("--feedback", default="")
    g.add_argument("--raw-out", default="")
    g.add_argument("--base-dir", default="")
    g.add_argument("--prev-out", default="")
    w = sub.add_parser("warm")
    w.add_argument("--coder", choices=("colibri", "deepseek"), default="colibri")
    args = ap.parse_args()
    return {"detect": cmd_detect, "save": cmd_save, "generate": cmd_generate, "warm": cmd_warm}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
