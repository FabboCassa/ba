#!/usr/bin/env bash
# Build + lint + test. Prints only a compact tail per failing step. Exit 0 = green.
# Usage: gate.sh [repo_dir] [--only build|test|lint] [--cached] [--tier fast|full] [--timeout <sec>]
#   --cached: on a clean tree, skip if this exact commit + commands already passed.
#   --tier: fast (default, runs TEST_FAST or unit tier) | full (runs complete TEST suite)
set -uo pipefail
DIR="."; ONLY=""; CACHED=0; TIER="fast"; TIMEOUT="${BA_TEST_TIMEOUT:-600}"
[[ $# -gt 0 && "$1" != --* ]] && { DIR="$1"; shift; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --only) ONLY="${2:-}"; shift 2 ;;
    --cached) CACHED=1; shift ;;
    --tier) TIER="${2:-fast}"; shift 2 ;;
    --timeout) TIMEOUT="${2:-600}"; shift 2 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CMDS="$(bash "$HERE/detect.sh" "$DIR" | tr -d '\r')"
eval "$(sed 's/^\([A-Z_]*\)=\(.*\)$/\1="\2"/' <<<"$CMDS")"
cd "$DIR"
mkdir -p .ba/logs

PY=""
for p in python py python3; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys' >/dev/null 2>&1; then
    PY="$p"; break
  fi
done

# Tier selection for test command
TEST_CMD="${TEST:-}"
if [[ "$TIER" == "fast" ]]; then
  TEST_CMD="${TEST_FAST:-${TEST:-}}"
fi

# Cache lives in the git common dir so every worktree of the repo shares it.
MARK=""
if [[ $CACHED == 1 && -z "$ONLY" ]] && git rev-parse -q --verify HEAD >/dev/null 2>&1 \
   && [[ -z "$(git status --porcelain -- . ':!.ba' 2>/dev/null)" ]]; then
  KEY="$(git rev-parse HEAD)-$(git hash-object --stdin <<<"${CMDS}-${TIER}")"
  MARK="$(git rev-parse --git-common-dir)/ba-gate-cache/$KEY"
  [[ -f "$MARK" ]] && { echo "[gate] OK (cached, $(git rev-parse --short HEAD), tier=$TIER)"; exit 0; }
fi

fail=0
run() {
  local name="$1" cmd="$2" to="${3:-0}"
  [[ -n "$ONLY" && "$ONLY" != "$name" ]] && return
  if [[ -z "$cmd" ]]; then
    [[ "$name" == lint ]] && return
    echo "[$name] NO COMMAND DETECTED - set it in .ba/commands.env"; fail=1; return
  fi
  local log=".ba/logs/$name.log"
  if [[ $to -gt 0 && -n "$PY" ]]; then
    if "$PY" - "$cmd" "$to" "$log" <<'PYEOF'
import sys, subprocess
cmd, to, logpath = sys.argv[1], int(sys.argv[2]), sys.argv[3]
with open(logpath, 'w', encoding='utf-8') as f:
    try:
        proc = subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, timeout=to)
        sys.exit(proc.returncode)
    except subprocess.TimeoutExpired:
        f.write(f"\n[gate] TIMEOUT: Command exceeded {to}s and was killed.\n")
        f.write("[gate] Suite took too long! Use --tier fast, tag slow tests, or split them with /ba:optimize.\n")
        sys.exit(124)
PYEOF
    then
      echo "[$name] OK  ($cmd)"
    else
      local rc=$?
      if [[ $rc -eq 124 ]]; then
        echo "[$name] TIMEOUT (${to}s) ($cmd) - execution killed to prevent hang. Last 40 lines:"
      else
        echo "[$name] FAIL ($cmd) - last 40 lines:"
      fi
      tail -n 40 "$log"; fail=1
    fi
  else
    if bash -c "$cmd" >"$log" 2>&1; then echo "[$name] OK  ($cmd)"
    else echo "[$name] FAIL ($cmd) - last 40 lines:"; tail -n 40 "$log"; fail=1; fi
  fi
}
run build "${BUILD:-}" 0
run lint "${LINT:-}" 0
run test "$TEST_CMD" "$TIMEOUT"
[[ $fail == 0 && -n "$MARK" ]] && mkdir -p "$(dirname "$MARK")" && : > "$MARK"
exit $fail
