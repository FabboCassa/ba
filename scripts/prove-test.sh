#!/usr/bin/env bash
# Proves the new tests are REAL: they must FAIL with the implementation reverted
# and PASS with it applied. Works on uncommitted changes vs HEAD.
# Usage: prove-test.sh <test-cmd> <test-file>...   (run from repo root)
set -uo pipefail
CMD="$1"; shift
[[ $# -gt 0 ]] || { echo "usage: prove-test.sh <test-cmd> <test-file>..."; exit 2; }
TESTS=("$@")
for t in "${TESTS[@]}"; do [[ -e "$t" ]] || { echo "missing test file: $t"; exit 2; }; done

mapfile -t IMPL < <( { git diff --name-only HEAD; git ls-files --others --exclude-standard; } | sort -u | grep -vxF -f <(printf '%s\n' "${TESTS[@]}") | grep -v '^\.ba/' || true)
[[ ${#IMPL[@]} -gt 0 ]] || { echo "NO IMPLEMENTATION CHANGES found besides tests"; exit 3; }

mkdir -p .ba/logs
STASH=$(mktemp -d)
restore() { cp -a "$STASH/." . 2>/dev/null; rm -rf "$STASH"; }
trap restore EXIT

# Save impl files, then revert them to HEAD (or remove if new).
for f in "${IMPL[@]}"; do
  [[ -e "$f" ]] && { mkdir -p "$STASH/$(dirname "$f")"; cp -a "$f" "$STASH/$f"; }
  if git cat-file -e "HEAD:$f" 2>/dev/null; then git show "HEAD:$f" > "$f"; else rm -f "$f"; fi
done
if bash -c "$CMD" > .ba/logs/red.log 2>&1; then
  echo "FAKE TEST: tests pass WITHOUT the implementation. Reverted files: ${IMPL[*]}"
  exit 4
fi
echo "RED ok: tests fail without implementation"
restore; trap - EXIT

if bash -c "$CMD" > .ba/logs/green.log 2>&1; then
  echo "GREEN ok: tests pass with implementation"
else
  echo "GREEN FAIL - last 40 lines:"; tail -n 40 .ba/logs/green.log; exit 5
fi
