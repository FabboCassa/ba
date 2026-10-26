#!/usr/bin/env bash
# ba — Universal Multi-AI Deterministic CLI Runner
# Usage: ba <command> [arguments...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="0.11.0"

show_help() {
  cat <<EOF
ba v$VERSION — Multi-AI Terse & Verified Coding Engine

Usage: ba <command> [options...]

Deterministic Verification Commands:
  gate [dir] [options]                     Run build, lint, and tests (compact output)
                                           Options: [--only build|test|lint] [--cached] [--tier fast|full] [--timeout <sec>]
  detect [dir]                             Detect build, test, and fast/full test tier commands
  prove-test "<test-cmd>" <files...>       Prove test validity via RED->GREEN rollback
  prove-refactor <base> <kind> [options]   Prove behavior preserved for refactor/perf/test-split
                                           Options: [--slow <sec>] [--bench <cmd>] [--target <%>] [--timeout <sec>] [--tier fast|full]
  scan secrets|code|deps [options]         Scan secrets, vulnerable code, or dependencies
  secret-guard [options]                   Secret leak prevention check or hook installer
  test-times [options]                     Analyze test durations and bottleneck tests
                                           Options: [--run] [--slow <sec>] [--timeout <sec>] [--tier fast|full] [--dir <dir>]

Multi-AI Setup & Adapters:
  init <platform>                          Initialize adapter for target AI platform:
                                           (gemini, cursor, windsurf, copilot, roo, cline, mcp, all)

AI Workflow Skills:
  /ba:architect <idea>                     Full system architecture, C4 diagrams, ERD, hosting & cloud topology
  /ba:spec <idea>                          Interview user until feature is fully specified -> docs/specs/<slug>.md
  /ba:issues <spec|audit>                  Break spec/audit into small GitHub issues with proof kind
  /ba:implement <n>                        Implement one issue test-first with real proof
  /ba:auto [spec] [merge]                  Fully autonomous execution of all issues
  /ba:optimize [tests|arch|code|perf]      Audit for slow tests (tiering), arch drift, dead code, perf
  /ba:secure [secrets|code|deps|platform]  Security audit across code, dependencies, and cloud platforms

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
      gemini|agy)
        cp -v "$ROOT_DIR/templates/adapters/gemini/GEMINI.md" "$dest/GEMINI.md" 2>/dev/null || cp -v "$ROOT_DIR/GEMINI.md" "$dest/GEMINI.md"
        cp -v "$ROOT_DIR/AGENTS.md" "$dest/AGENTS.md"
        if [[ -d "$HOME/.gemini/config/plugins/ba" ]]; then
          mkdir -p "$HOME/.gemini/config/plugins/ba/rules" "$HOME/.gemini/config/plugins/ba/agents"
          cp -f "$ROOT_DIR/GEMINI.md" "$HOME/.gemini/config/plugins/ba/rules/GEMINI.md"
          cp -f "$ROOT_DIR/AGENTS.md" "$HOME/.gemini/config/plugins/ba/rules/AGENTS.md"
          cp -f "$ROOT_DIR/templates/adapters/gemini/agents/"*.md "$HOME/.gemini/config/plugins/ba/agents/" 2>/dev/null || true
        fi
        echo "Initialized Gemini / Google Antigravity config (pro=Gemini 4 Argon for implementer, flash=Gemini 3.8 Flash for verifier/auditor, flash_lite=Gemini 3.8 Flash Low for reviewer)."
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
