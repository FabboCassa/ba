#!/usr/bin/env bash
# Delegates pure code writing to an external coder (colibri | deepseek), then proves it:
# prove-test.sh (when --tests given) + gate.sh --tier fast. On failure the last 40 log
# lines go straight back to the coder (max --retries, default 2) without involving the PM.
# Usage:
#   delegate-coder.sh --detect [--coder X] [--json] [--warm]
#   delegate-coder.sh --issue <n> --coder colibri|deepseek --brief <file> --files "a,b"
#                     [--tests "t1,t2" --test-cmd "<cmd>"] [--retries 2] [--tier flash|pro]
# Last line + exit: RESULT: PASS (0) | FAIL (3) | CODER_UNAVAILABLE (4); usage error 2.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY=""
for p in python py python3; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; assert sys.version_info >= (3, 10)' >/dev/null 2>&1; then
    PY="$p"; break
  fi
done
[[ -n "$PY" ]] || { echo "python >= 3.10 not found"; echo "RESULT: CODER_UNAVAILABLE"; exit 4; }

if [[ "${1:-}" == "--detect" ]]; then
  shift; exec "$PY" "$HERE/coder.py" detect "$@"
fi

ISSUE=""; CODER=""; BRIEF=""; FILES=""; TESTS=""; TEST_CMD=""; RETRIES=2; TIER=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue) ISSUE="${2:-}"; shift 2 ;;
    --coder) CODER="${2:-}"; shift 2 ;;
    --brief) BRIEF="${2:-}"; shift 2 ;;
    --files) FILES="${2:-}"; shift 2 ;;
    --tests) TESTS="${2:-}"; shift 2 ;;
    --test-cmd) TEST_CMD="${2:-}"; shift 2 ;;
    --retries) RETRIES="${2:-2}"; shift 2 ;;
    --tier) TIER="${2:-}"; shift 2 ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done
[[ -n "$ISSUE" && -n "$BRIEF" && -n "$FILES" ]] || { echo "usage: delegate-coder.sh --issue <n> --coder colibri|deepseek --brief <file> --files \"a,b\" [--tests \"t\" --test-cmd \"cmd\"]"; exit 2; }
[[ "$CODER" == colibri || "$CODER" == deepseek ]] || { echo "--coder must be colibri or deepseek (native = PM's implementer agent)"; exit 2; }
[[ -z "$TIER" || "$TIER" == flash || "$TIER" == pro ]] || { echo "--tier must be flash or pro"; exit 2; }
[[ -f "$BRIEF" ]] || { echo "missing brief: $BRIEF"; exit 2; }
[[ -z "$TESTS" || -n "$TEST_CMD" ]] || { echo "--tests requires --test-cmd"; exit 2; }

mkdir -p .ba/runs .ba/logs
LOG=".ba/logs/$ISSUE-coder.log"
FB=".ba/logs/$ISSUE-coder-feedback.txt"
OUT=".ba/logs/$ISSUE-coder-step.txt"
: > "$FB"
IFS=',' read -r -a TEST_ARR <<<"$TESTS"
ALL_FILES="$FILES${TESTS:+,$TESTS}"
echo "## $(date -u +%FT%TZ) coder=$CODER${TIER:+ tier=$TIER} files=$ALL_FILES" >> "$LOG"

# Snapshot targets so a FAIL/UNAVAILABLE leaves the tree as it was for the next coder in the chain.
SNAP=$(mktemp -d)
IFS=',' read -r -a ALL_ARR <<<"$ALL_FILES"
for f in "${ALL_ARR[@]}"; do
  [[ -e "$f" ]] && { mkdir -p "$SNAP/$(dirname "$f")"; cp -a "$f" "$SNAP/$f"; }
done
SNAP_ARG="$SNAP"; command -v cygpath >/dev/null 2>&1 && SNAP_ARG="$(cygpath -w "$SNAP")"
rm -f .ba/logs/"$ISSUE"-coder-raw-*.txt
rollback() {
  for f in "${ALL_ARR[@]}"; do
    if [[ -e "$SNAP/$f" ]]; then cp -a "$SNAP/$f" "$f"; else rm -f "$f"; fi
  done
  rm -rf "$SNAP"
}

for ((try = 0; try <= RETRIES; try++)); do
  # Prompt = pre-run snapshot + (retry) previous output + error tail: stable prefix for the coder's cache.
  "$PY" "$HERE/coder.py" generate --coder "$CODER" --brief "$BRIEF" --files "$ALL_FILES" \
    --base-dir "$SNAP_ARG" --prev-out ".ba/logs/$ISSUE-coder-raw-$((try - 1)).txt" \
    --feedback "$FB" --raw-out ".ba/logs/$ISSUE-coder-raw-$try.txt" ${TIER:+--tier "$TIER"} > "$OUT" 2>&1
  rc=$?
  cat "$OUT" >> "$LOG"
  if [[ $rc -eq 10 ]]; then
    cat "$OUT"; rollback; echo "RESULT: CODER_UNAVAILABLE coder=$CODER"; exit 4
  fi
  if [[ $rc -ne 0 ]]; then
    echo "try $try: coder output rejected"
    cp "$OUT" "$FB"; continue
  fi
  echo "try $try: $(tail -n 1 "$OUT")"

  if [[ -n "$TESTS" ]] && ! bash "$HERE/prove-test.sh" "$TEST_CMD" "${TEST_ARR[@]}" > "$OUT" 2>&1; then
    cat "$OUT" >> "$LOG"; echo "try $try: prove-test FAIL"
    tail -n 40 "$OUT" > "$FB"; continue
  fi
  if ! bash "$HERE/gate.sh" . --tier fast > "$OUT" 2>&1; then
    cat "$OUT" >> "$LOG"; echo "try $try: gate FAIL"
    tail -n 40 "$OUT" > "$FB"; continue
  fi
  rm -rf "$SNAP"
  echo "PASS try=$try" >> "$LOG"
  echo "RESULT: PASS coder=$CODER tries=$((try + 1)) files=$ALL_FILES"
  exit 0
done

rollback
echo "last failure (full log: $LOG):"; tail -n 40 "$FB"
echo "RESULT: FAIL coder=$CODER tries=$((RETRIES + 1))"
exit 3
