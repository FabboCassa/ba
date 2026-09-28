#!/usr/bin/env bash
# Build + lint + test. Prints only a compact tail per failing step. Exit 0 = green.
# Usage: gate.sh [repo_dir] [--only build|test|lint] [--cached]
#   --cached: on a clean tree, skip if this exact commit + commands already passed.
set -uo pipefail
DIR="."; ONLY=""; CACHED=0
[[ $# -gt 0 && "$1" != --* ]] && { DIR="$1"; shift; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --only) ONLY="${2:-}"; shift 2 ;;
    --cached) CACHED=1; shift ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CMDS="$(bash "$HERE/detect.sh" "$DIR" | tr -d '\r')"
eval "$(sed 's/^\([A-Z]*\)=\(.*\)$/\1="\2"/' <<<"$CMDS")"
cd "$DIR"
mkdir -p .ba/logs

# Cache lives in the git common dir so every worktree of the repo shares it.
MARK=""
if [[ $CACHED == 1 && -z "$ONLY" ]] && git rev-parse -q --verify HEAD >/dev/null 2>&1 \
   && [[ -z "$(git status --porcelain -- . ':!.ba' 2>/dev/null)" ]]; then
  KEY="$(git rev-parse HEAD)-$(git hash-object --stdin <<<"$CMDS")"
  MARK="$(git rev-parse --git-common-dir)/ba-gate-cache/$KEY"
  [[ -f "$MARK" ]] && { echo "[gate] OK (cached, $(git rev-parse --short HEAD))"; exit 0; }
fi

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
[[ $fail == 0 && -n "$MARK" ]] && mkdir -p "$(dirname "$MARK")" && : > "$MARK"
exit $fail
