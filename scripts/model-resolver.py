#!/usr/bin/env python3
"""
scripts/model-resolver.py — Dynamic Model Discovery and Multi-AI Tier Resolver for BetterAI.
Assigns roles dynamically with cross-family asymmetric verification.
Pure Python standard library (no pip packages required).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"


def find_env_file() -> Path | None:
    cwd = Path.cwd().resolve()
    for directory in [cwd, *cwd.parents]:
        env_path = directory / ".env"
        if env_path.is_file():
            return env_path
    return None


def get_env_var(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if val:
        return val
    env_file = find_env_file()
    if env_file:
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == name:
                    return v.strip().strip("\"'")
        except Exception:
            pass
    return ""


def detect_keys() -> dict[str, bool]:
    return {
        "deepseek": bool(get_env_var("DEEPSEEK_API_KEY")),
        "anthropic": bool(get_env_var("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_PROJECT_DIR")),
        "gemini": bool(get_env_var("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")),
    }


def resolve_deepseek_best(category: str = "flagship") -> str:
    bridge = SCRIPTS_DIR / "deepseek-bridge.py"
    if bridge.is_file():
        try:
            res = subprocess.run(
                [sys.executable, str(bridge), "best-model", "--category", category],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
    return "deepseek-chat"


def resolve_matrix(flagship_family: str | None = None) -> dict:
    keys = detect_keys()

    # Determine flagship family
    if not flagship_family:
        if keys["deepseek"]:
            flagship_family = "deepseek"
        elif keys["anthropic"]:
            flagship_family = "claude"
        elif keys["gemini"]:
            flagship_family = "gemini"
        else:
            flagship_family = "deepseek" if get_env_var("DEEPSEEK_API_KEY") else "claude"

    flagship_family = flagship_family.lower()

    # Resolve roles
    if flagship_family in ("deepseek", "ds"):
        writer_model = resolve_deepseek_best("flagship")
        writer_provider = "deepseek"
        # Asymmetric verifier: different family (Claude or Gemini)
        if keys["gemini"]:
            verifier_model = "gemini-3.8-flash"
            verifier_provider = "gemini"
        else:
            verifier_model = "claude-3-7-sonnet"
            verifier_provider = "anthropic"

        reviewer_model = "gemini-3.8-flash-lite" if keys["gemini"] else "deepseek-chat"
        reviewer_provider = "gemini" if keys["gemini"] else "deepseek"

    elif flagship_family in ("claude", "anthropic"):
        writer_model = "claude-3-7-sonnet"
        writer_provider = "anthropic"
        # Asymmetric verifier: DeepSeek or Gemini
        if keys["deepseek"]:
            verifier_model = resolve_deepseek_best("chat")
            verifier_provider = "deepseek"
        else:
            verifier_model = "gemini-3.8-flash"
            verifier_provider = "gemini"

        reviewer_model = "claude-3-5-haiku"
        reviewer_provider = "anthropic"

    elif flagship_family in ("gemini", "agy", "google"):
        writer_model = "gemini-4-argon-high"
        writer_provider = "gemini"
        # Asymmetric verifier: DeepSeek or Claude
        if keys["deepseek"]:
            verifier_model = resolve_deepseek_best("chat")
            verifier_provider = "deepseek"
        else:
            verifier_model = "claude-3-7-sonnet"
            verifier_provider = "anthropic"

        reviewer_model = "gemini-3.8-flash-lite"
        reviewer_provider = "gemini"
    else:
        raise ValueError(f"Unknown flagship family '{flagship_family}'. Supported: deepseek, claude, gemini.")

    return {
        "flagship_family": flagship_family,
        "available_keys": keys,
        "tiers": {
            "architect": {
                "role": "Architect & Spec Lead",
                "provider": writer_provider,
                "model": writer_model,
                "tier": "flagship-reasoning",
            },
            "writer": {
                "role": "Implementer / Writer (TDD)",
                "provider": writer_provider,
                "model": writer_model,
                "tier": "flagship-coding",
            },
            "verifier": {
                "role": "Verifier (Cross-Family Gate)",
                "provider": verifier_provider,
                "model": verifier_model,
                "tier": "checker-asymmetric",
            },
            "reviewer": {
                "role": "Reviewer (Diff Inspector)",
                "provider": reviewer_provider,
                "model": reviewer_model,
                "tier": "fast-lint-diff",
            },
        },
    }


def save_matrix(matrix: dict, target_dir: Path | None = None) -> Path:
    out_dir = target_dir or Path.cwd() / ".ba"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "models.json"
    out_file.write_text(json.dumps(matrix, indent=2), encoding="utf-8")
    return out_file


def format_table(matrix: dict) -> str:
    flagship = matrix["flagship_family"].upper()
    lines = [
        f"BetterAI Dynamic Model Matrix [Flagship: {flagship}]",
        "----------------------------------------------------------------------",
        f"{'ROLE':<12} {'TIER':<20} {'PROVIDER':<12} {'MODEL'}",
        "----------------------------------------------------------------------",
    ]
    tiers = matrix["tiers"]
    for role_key, data in tiers.items():
        lines.append(f"{role_key:<12} {data['tier']:<20} {data['provider']:<12} {data['model']}")
    lines.append("----------------------------------------------------------------------")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="BetterAI Dynamic Model Tier Resolver")
    parser.add_argument("--flagship", "-f", choices=["deepseek", "claude", "gemini"], help="Select flagship family")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--save", action="store_true", help="Save resolved matrix to .ba/models.json")
    parser.add_argument("--get", choices=["writer", "verifier", "reviewer", "architect"], help="Print only specific model")

    args = parser.parse_args()
    matrix = resolve_matrix(args.flagship)

    if args.save:
        saved_path = save_matrix(matrix)
        if not args.json and not args.get:
            sys.stderr.write(f"Saved dynamic matrix to {saved_path}\n")

    if args.get:
        print(matrix["tiers"][args.get]["model"])
        return

    if args.json:
        print(json.dumps(matrix, indent=2))
    else:
        print(format_table(matrix))


if __name__ == "__main__":
    main()
