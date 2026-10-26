#!/usr/bin/env bash
# SessionStart hook for both Claude Code and Google Antigravity (agy).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULES_FILE="$SCRIPT_DIR/../templates/terse-rules.md"
[[ -f "$RULES_FILE" ]] || exit 0

payload=$(cat 2>/dev/null || true)
if grep -q '"conversationId"' <<<"$payload"; then
  if command -v jq >/dev/null 2>&1; then
    jq -Rs '{injectSteps:[{systemMessage:{systemMessage:.}}]}' < "$RULES_FILE"
  elif command -v python3 >/dev/null 2>&1; then
    python3 -c 'import json,sys; print(json.dumps({"injectSteps":[{"systemMessage":{"systemMessage":open(sys.argv[1],encoding="utf-8").read()}}]}))' "$RULES_FILE"
  else
    echo "{}"
  fi
else
  cat "$RULES_FILE"
fi
