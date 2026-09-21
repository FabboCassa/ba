#!/usr/bin/env bash
# ba — Universal Multi-AI Deterministic CLI Runner
# Usage: ba <command> [arguments...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="0.8.1"

show_help() {
  cat <<EOF
ba v$VERSION — Multi-AI Terse & Verified Coding Engine

Usage: ba <command> [options...]

Deterministic Verification Commands:
  gate [dir] [--only build|test|lint]      Run build, lint, and tests (compact output)
  detect [dir]                             Detect build, test, and lint commands
  prove-test "<test-cmd>" <files...>       Prove test validity via RED->GREEN rollback
  prove-refactor <base> <kind> [options]   Prove behavior preserved for refactor/perf/test-split
  scan secrets|code|deps [options]         Scan secrets, vulnerable code, or dependencies
  secret-guard [options]                   Secret leak prevention check or hook installer
  test-times [options]                     Analyze test durations and bottleneck tests

Multi-AI Setup & Adapters:
  init <platform>                          Initialize adapter for target AI platform:
                                           (gemini, cursor, windsurf, copilot, roo, cline, mcp, all)

General:
  version                                  Print version
  help                                     Print this help message
EOF
}

cmd="${1:-help}"
shift || true

case "$cmd" in
  gate)
    bash "$SCRIPT_DIR/gate.sh" "$@"
    ;;
  detect)
    bash "$SCRIPT_DIR/detect.sh" "$@"
    ;;
  prove-test)
    bash "$SCRIPT_DIR/prove-test.sh" "$@"
    ;;
  prove-refactor)
    bash "$SCRIPT_DIR/prove-refactor.sh" "$@"
    ;;
  scan)
    bash "$SCRIPT_DIR/sec-scan.sh" "$@"
    ;;
  secret-guard)
    bash "$SCRIPT_DIR/secret-guard.sh" "$@"
    ;;
  test-times)
    bash "$SCRIPT_DIR/test-times.sh" "$@"
    ;;
  version|--version|-v)
    echo "ba v$VERSION"
    ;;
  init)
    target="${1:-help}"
    dest="${2:-.}"
    case "$target" in
      gemini)
        cp -v "$ROOT_DIR/templates/adapters/gemini/GEMINI.md" "$dest/GEMINI.md" 2>/dev/null || cp -v "$ROOT_DIR/GEMINI.md" "$dest/GEMINI.md"
        cp -v "$ROOT_DIR/AGENTS.md" "$dest/AGENTS.md"
        echo "Initialized Gemini / Google Antigravity config."
        ;;
      cursor)
        mkdir -p "$dest/.cursor/rules"
        cp -v "$ROOT_DIR/templates/adapters/cursor/.cursorrules" "$dest/.cursorrules"
        cp -v "$ROOT_DIR/templates/adapters/cursor/ba-workflow.mdc" "$dest/.cursor/rules/ba-workflow.mdc"
        cp -v "$ROOT_DIR/AGENTS.md" "$dest/AGENTS.md"
        echo "Initialized Cursor rules."
        ;;
      windsurf)
        cp -v "$ROOT_DIR/templates/adapters/windsurf/.windsurfrules" "$dest/.windsurfrules"
        cp -v "$ROOT_DIR/AGENTS.md" "$dest/AGENTS.md"
        echo "Initialized Windsurf rules."
        ;;
      copilot)
        mkdir -p "$dest/.github"
        cp -v "$ROOT_DIR/templates/adapters/copilot/copilot-instructions.md" "$dest/.github/copilot-instructions.md"
        cp -v "$ROOT_DIR/AGENTS.md" "$dest/AGENTS.md"
        echo "Initialized GitHub Copilot instructions."
        ;;
      roo|cline)
        cp -v "$ROOT_DIR/templates/adapters/cline-roo/.clinerules" "$dest/.clinerules"
        cp -v "$ROOT_DIR/templates/adapters/cline-roo/.roomodes" "$dest/.roomodes"
        cp -v "$ROOT_DIR/AGENTS.md" "$dest/AGENTS.md"
        echo "Initialized Roo Code / Cline rules and 4 agent modes."
        ;;
      mcp)
        mkdir -p "$dest/.ba"
        cp -v "$ROOT_DIR/templates/adapters/mcp/mcp.json" "$dest/.ba/mcp.json"
        echo "Initialized MCP configuration template."
        ;;
      all)
        mkdir -p "$dest/.cursor/rules" "$dest/.github" "$dest/.ba"
        cp -v "$ROOT_DIR/AGENTS.md" "$dest/AGENTS.md"
        cp -v "$ROOT_DIR/templates/adapters/gemini/GEMINI.md" "$dest/GEMINI.md" 2>/dev/null || cp -v "$ROOT_DIR/GEMINI.md" "$dest/GEMINI.md"
        cp -v "$ROOT_DIR/templates/adapters/cursor/.cursorrules" "$dest/.cursorrules"
        cp -v "$ROOT_DIR/templates/adapters/cursor/ba-workflow.mdc" "$dest/.cursor/rules/ba-workflow.mdc"
        cp -v "$ROOT_DIR/templates/adapters/windsurf/.windsurfrules" "$dest/.windsurfrules"
        cp -v "$ROOT_DIR/templates/adapters/copilot/copilot-instructions.md" "$dest/.github/copilot-instructions.md"
        cp -v "$ROOT_DIR/templates/adapters/cline-roo/.clinerules" "$dest/.clinerules"
        cp -v "$ROOT_DIR/templates/adapters/cline-roo/.roomodes" "$dest/.roomodes"
        echo "Initialized all multi-AI templates."
        ;;
      *)
        echo "Usage: ba init <gemini|cursor|windsurf|copilot|roo|cline|mcp|all> [destination_dir]"
        exit 1
        ;;
    esac
    ;;
  help|--help|-h)
    show_help
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    show_help >&2
    exit 1
    ;;
esac
