#!/usr/bin/env python3
"""
scripts/deepseek-bridge.py — Lightweight DeepSeek API bridge for BetterAI.
Pure Python standard library (no pip packages required).
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

DEFAULT_BASE_URL = "https://api.deepseek.com"


def find_env_file() -> Path | None:
    """Finds .env in current or parent directories."""
    cwd = Path.cwd().resolve()
    for directory in [cwd, *cwd.parents]:
        env_path = directory / ".env"
        if env_path.is_file():
            return env_path
    return None


def get_api_key() -> str:
    """Gets DEEPSEEK_API_KEY from environment or .env file."""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key
    env_file = find_env_file()
    if env_file:
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "DEEPSEEK_API_KEY":
                    return v.strip().strip("\"'")
        except Exception:
            pass
    return ""


def request_json(endpoint: str, api_key: str, data: dict | None = None, method: str = "GET", timeout: int = 30) -> dict:
    url = f"{DEFAULT_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "BetterAI-DeepSeek-Bridge/0.12.0",
    }
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {url}: {err_msg}")
    except Exception as e:
        raise RuntimeError(f"Network error querying {url}: {e}")


def list_models(api_key: str) -> list[str]:
    """Queries /models endpoint and returns available model IDs."""
    if not api_key:
        return ["deepseek-chat", "deepseek-reasoner"]
    try:
        resp = request_json("models", api_key)
        data = resp.get("data", [])
        models = [m.get("id") for m in data if isinstance(m, dict) and "id" in m]
        return models or ["deepseek-chat", "deepseek-reasoner"]
    except Exception as e:
        sys.stderr.write(f"[deepseek-bridge] Warning fetching models: {e}\n")
        return ["deepseek-chat", "deepseek-reasoner"]


def pick_best_model(models: list[str], category: str = "flagship") -> str:
    """
    Picks the highest versioned / most capable model dynamically from the list.
    Supports future versions (e.g. v4, v5, etc.).
    """
    if category == "reasoner":
        reasoners = [m for m in models if "reasoner" in m.lower() or "r1" in m.lower()]
        if reasoners:
            return sorted(reasoners, key=_version_key, reverse=True)[0]

    # Category flagship / code: search for highest version (e.g. v4 > v3 > base)
    candidates = [m for m in models if "chat" in m.lower() or "coder" in m.lower() or "reasoner" in m.lower()]
    if not candidates:
        candidates = models

    return sorted(candidates, key=_version_key, reverse=True)[0] if candidates else "deepseek-chat"


def _version_key(name: str):
    """Sort key prioritizing higher version numbers (v4 > v3) then reasoner/coder."""
    match = re.search(r"v?(\d+)(?:\.(\d+))?", name.lower())
    version_num = (int(match.group(1)), int(match.group(2) or 0)) if match else (0, 0)
    score = 0
    if "reasoner" in name.lower():
        score += 3
    elif "coder" in name.lower():
        score += 2
    elif "chat" in name.lower():
        score += 1
    return (version_num, score, name)


def chat_completion(api_key: str, prompt: str, system: str = "", model: str = "", temperature: float = 0.2) -> str:
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is missing. Add it to environment or .env file.")
    if not model:
        models = list_models(api_key)
        model = pick_best_model(models, "flagship")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    resp = request_json("chat/completions", api_key, data=payload, method="POST", timeout=120)
    choices = resp.get("choices", [])
    if choices and "message" in choices[0]:
        return choices[0]["message"].get("content", "")
    return ""


def main():
    parser = argparse.ArgumentParser(description="BetterAI DeepSeek Bridge CLI")
    subparsers = parser.add_subparsers(dest="command")

    # list-models
    subparsers.add_parser("list-models", help="List available DeepSeek models")

    # best-model
    best_p = subparsers.add_parser("best-model", help="Get dynamically detected best model")
    best_p.add_argument("--category", choices=["flagship", "reasoner", "chat", "code"], default="flagship")

    # chat
    chat_p = subparsers.add_parser("chat", help="Send prompt to DeepSeek")
    chat_p.add_argument("--prompt", "-p", required=True, help="Prompt string or '-' to read stdin")
    chat_p.add_argument("--system", "-s", default="", help="Optional system instruction")
    chat_p.add_argument("--model", "-m", default="", help="Model name (default: auto-detected best)")
    chat_p.add_argument("--temp", type=float, default=0.2, help="Temperature (default: 0.2)")

    args = parser.parse_args()
    api_key = get_api_key()

    if args.command == "list-models":
        models = list_models(api_key)
        print(json.dumps(models, indent=2))
        return

    if args.command == "best-model":
        models = list_models(api_key)
        best = pick_best_model(models, args.category)
        print(best)
        return

    if args.command == "chat":
        prompt_text = sys.stdin.read() if args.prompt == "-" else args.prompt
        try:
            result = chat_completion(api_key, prompt_text, system=args.system, model=args.model, temperature=args.temp)
            print(result)
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")
            sys.exit(1)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
