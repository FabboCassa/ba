#!/usr/bin/env bash
# Proof for changes WITHOUT new behavior (Kind refactor / perf / test-split).
# Runs the suite on <base> (in a temporary worktree outside the repo, cached per commit)
# and on the working tree, then checks: nothing lost, all green, and the kind-specific goal.
# Usage: prove-refactor.sh <base-ref> <kind> [--slow <sec>] [--bench "<cmd>" --target <pct>]
#   kind: refactor | perf | test-split
#   --bench cmd must print a line "BENCH <number>" (lower is better, e.g. ms). Run 3x per side, median.
#   Tests intentionally removed (e.g. they only covered deleted dead code) must be listed, one
#   "<class> :: <name>" per line, in .ba/removed-tests.txt - the verifier judges each one.
set -uo pipefail
BASE="$1"; KIND="$2"; shift 2
SLOW=60; BENCH=""; TARGET=0
while [[ $# -gt 0 ]]; do case "$1" in
  --slow) SLOW="$2"; shift;; --bench) BENCH="$2"; shift;; --target) TARGET="$2"; shift;;
  *) echo "unknown arg $1"; exit 2;; esac; shift; done
S="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(git rev-parse --show-toplevel)"; cd "$ROOT"
SHA=$(git rev-parse "$BASE") || exit 2
mkdir -p .ba/cache .ba/logs
BASE_TSV=".ba/cache/tests-$SHA.tsv"

if [[ ! -s $BASE_TSV ]]; then
  WT="$(dirname "$ROOT")/$(basename "$ROOT")-ba/base-${SHA:0:10}"
  [[ -d $WT ]] || git worktree add -q --detach "$WT" "$SHA" || exit 2
  ( cd "$WT" && bash "$S/test-times.sh" --run --slow "$SLOW" --out "$ROOT/$BASE_TSV" ) > .ba/logs/refactor-base.log 2>&1
  echo "base suite measured on ${SHA:0:10}"
  [[ $KIND == perf ]] || git worktree remove --force "$WT"
fi
bash "$S/test-times.sh" --run --slow "$SLOW" --out .ba/logs/tests-head.tsv > .ba/logs/refactor-head.log 2>&1

FAIL=0
PY=$(command -v python3 || command -v python || command -v py)
"$PY" - "$BASE_TSV" .ba/logs/tests-head.tsv "$KIND" "$SLOW" <<'PYEOF' || FAIL=1
import sys, os
b, h, kind, slow = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
def load(p):
    d = {}
    for l in open(p, encoding='utf-8'):
        s, st, c, n = (l.rstrip('\n').split('\t') + ['', '', '', ''])[:4]
        d[f'{c} :: {n}'] = (float(s), st.lower())
    return d
B, H = load(b), load(h)
removed = set()
if os.path.exists('.ba/removed-tests.txt'):
    removed = {l.strip() for l in open('.ba/removed-tests.txt', encoding='utf-8') if l.strip()}
bad = 0
failed = [k for k, (_, st) in H.items() if st.startswith('fail')]
if failed: bad = 1; print(f'HEAD FAILING TESTS ({len(failed)}):'); [print('  ' + k) for k in failed[:20]]
missing = [k for k in B if k not in H and k not in removed]
if kind != 'test-split' and missing:
    bad = 1; print(f'TESTS LOST ({len(missing)}) - not in .ba/removed-tests.txt:'); [print('  ' + k) for k in missing[:20]]
if kind == 'test-split':
    # renamed/split tests are expected: count must not drop
    if len(H) < len(B) - len(removed): bad = 1; print(f'TEST COUNT DROPPED {len(B)} -> {len(H)}')
    mx = max((v[0] for v in H.values()), default=0)
    if mx > slow: bad = 1; print(f'STILL SLOW: max test {mx:.0f}s > {slow:.0f}s')
sb, sh = sum(v[0] for v in B.values()), sum(v[0] for v in H.values())
print(f'tests base={len(B)} head={len(H)} removed(justified)={len(removed)}  sum base={sb:.0f}s head={sh:.0f}s')
if kind == 'test-split' and sh > sb * 1.10: bad = 1; print('TOTAL TIME WORSE by >10%')
print('SUITE ok' if not bad else 'SUITE FAIL')
sys.exit(bad)
PYEOF

if [[ $KIND == perf ]]; then
  [[ -n $BENCH ]] || { echo "PERF needs --bench"; exit 2; }
  WT="$(dirname "$ROOT")/$(basename "$ROOT")-ba/base-${SHA:0:10}"
  [[ -d $WT ]] || git worktree add -q --detach "$WT" "$SHA"
  med() { local d="$1" v=(); for i in 1 2 3; do v+=("$(cd "$d" && bash -c "$BENCH" 2>/dev/null | awk '/^BENCH /{print $2}' | tail -1)"); done
          printf '%s\n' "${v[@]}" | sort -g | sed -n 2p; }
  MB=$(med "$WT"); MH=$(med "$ROOT")
  [[ -n $MB && -n $MH ]] || { echo "BENCH FAIL: no 'BENCH <n>' line (base='$MB' head='$MH')"; exit 6; }
  GAIN=$(awk -v b="$MB" -v h="$MH" 'BEGIN{printf "%.1f", (b-h)/b*100}')
  echo "bench median base=$MB head=$MH gain=${GAIN}% target=${TARGET}%"
  awk -v g="$GAIN" -v t="$TARGET" 'BEGIN{exit !(g+0 >= t+0)}' || { echo "PERF FAIL: gain below target"; FAIL=1; }
  git worktree remove --force "$WT"
fi
[[ $FAIL == 0 ]] && echo "REFACTOR PROOF ok ($KIND)" || { echo "REFACTOR PROOF FAIL ($KIND) - logs .ba/logs/refactor-*.log"; exit 5; }
