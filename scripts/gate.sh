#!/usr/bin/env bash
# Build + lint + test. Prints only a compact tail per failing step. Exit 0 = green.
# Usage: gate.sh [repo_dir] [--only build|test|lint]
set -uo pipefail
DIR="${1:-.}"; ONLY="${3:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
eval "$(bash "$HERE/detect.sh" "$DIR" | sed 's/^\([A-Z]*\)=\(.*\)$/\1="\2"/')"
cd "$DIR"
mkdir -p .ba/logs
fail=0
run() {
  local name="$1" cmd="$2"
  [[ -n "$ONLY" && "$ONLY" != "$name" ]] && return
  if [[ -z "$cmd" ]]; then
    [[ "$name" == lint ]] && return
    echo "[$name] NO COMMAND DETECTED - set it in .ba/commands.env"; fail=1; return
  fi
  local log=".ba/logs/$name.log"
  if bash -c "$cmd" >"$log" 2>&1; then echo "[$name] OK  ($cmd)"
  else echo "[$name] FAIL ($cmd) - last 40 lines:"; tail -n 40 "$log"; fail=1; fi
}
run build "${BUILD:-}"
run lint "${LINT:-}"
run test "${TEST:-}"
exit $fail
