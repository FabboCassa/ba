#!/usr/bin/env bash
# Per-test durations from existing reports (JUnit XML, .trx, go test -json, jest json),
# or from a measured run with --run. Prints slowest tests/files and totals.
# Usage: test-times.sh [--run] [--dir <path>] [--slow <sec>] [--top <n>] [--out <tsv>]
# TSV out columns: seconds  status  file_or_class  test_name
set -uo pipefail
RUN=0; DIR=.; SLOW=60; TOP=30; OUT=.ba/logs/test-times.tsv
while [[ $# -gt 0 ]]; do case "$1" in
  --run) RUN=1;; --dir) DIR="$2"; shift;; --slow) SLOW="$2"; shift;;
  --top) TOP="$2"; shift;; --out) OUT="$2"; shift;; *) echo "unknown arg $1"; exit 2;;
esac; shift; done

PY=$(command -v python3 || command -v python || command -v py || true)
[[ -n "$PY" ]] || { echo "NEED python3 to parse test reports"; exit 2; }
mkdir -p .ba/logs "$(dirname "$OUT")"

if [[ $RUN == 1 ]]; then
  R=.ba/logs/reports; rm -rf "$R"; mkdir -p "$R"; START=$(date +%s)
  if [[ -n "$(git ls-files '*.sln' '*.slnx' '*.csproj' 2>/dev/null | head -1)" ]]; then
    dotnet test --logger "trx;LogFilePrefix=ba" --results-directory "$R" > .ba/logs/test-run.log 2>&1
  elif [[ -f package.json ]] && grep -q '"vitest"' package.json; then
    npx vitest run --reporter=junit --outputFile="$R/junit.xml" > .ba/logs/test-run.log 2>&1
  elif [[ -f package.json ]] && grep -q '"jest"' package.json; then
    npx jest --json --outputFile="$R/jest.json" > .ba/logs/test-run.log 2>&1
  elif [[ -f pyproject.toml || -f pytest.ini || -f setup.cfg || -d tests ]] && command -v pytest >/dev/null; then
    pytest -q --junitxml="$R/junit.xml" > .ba/logs/test-run.log 2>&1
  elif [[ -f go.mod ]]; then
    go test -json ./... > "$R/go-test.json" 2>.ba/logs/test-run.log
  elif [[ -f gradlew ]]; then
    ./gradlew test > .ba/logs/test-run.log 2>&1
  elif [[ -f pom.xml ]]; then
    mvn -q test > .ba/logs/test-run.log 2>&1
  elif [[ -f Cargo.toml ]] && command -v cargo-nextest >/dev/null; then
    cargo nextest run --message-format libtest-json > "$R/nextest.json" 2>.ba/logs/test-run.log || true
  else
    echo "NO RUNNER with per-test timing detected. Configure a JUnit reporter and pass --dir."; exit 3
  fi
  RC=$?
  echo "run exit=$RC wall=$(( $(date +%s) - START ))s log=.ba/logs/test-run.log"
  [[ -n "$(ls -A "$R")" ]] && DIR="$R"   # gradle/maven: reports stay in build/ or target/, scan repo
fi

"$PY" - "$DIR" "$SLOW" "$TOP" "$OUT" <<'PYEOF'
import sys, os, json, re, xml.etree.ElementTree as ET
from collections import defaultdict
root, slow, top, out = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
SKIP = {'node_modules', '.git', 'bin', 'obj', '.venv', 'venv', 'dist'}
rows, files = [], []
def secs(v):
    try: return float(v)
    except: pass
    m = re.match(r'(\d+):(\d+):([\d.]+)', v or '')   # trx hh:mm:ss.fffffff
    return int(m[1])*3600+int(m[2])*60+float(m[3]) if m else 0.0
for d, dirs, fs in os.walk(root):
    dirs[:] = [x for x in dirs if x not in SKIP]
    for f in fs:
        p = os.path.join(d, f); lf = f.lower()
        if lf.endswith('.trx') or (lf.endswith('.xml') and ('test' in lf or 'junit' in lf or 'surefire' in d or 'test-results' in d)) \
           or lf in ('go-test.json', 'jest.json', 'nextest.json'):
            files.append(p)
for p in files:
    try:
        if p.endswith('.trx'):
            t = ET.parse(p).getroot(); ns = {'t': t.tag.split('}')[0].strip('{')}
            defs = {u.get('id'): (u.find('t:TestMethod', ns).get('className') if u.find('t:TestMethod', ns) is not None else '')
                    for u in t.iterfind('.//t:UnitTest', ns)}
            for r in t.iterfind('.//t:UnitTestResult', ns):
                rows.append((secs(r.get('duration')), r.get('outcome', ''), defs.get(r.get('testId'), ''), r.get('testName', '')))
        elif p.endswith('.xml'):
            t = ET.parse(p).getroot()
            for c in t.iter('testcase'):
                st = 'failed' if c.find('failure') is not None or c.find('error') is not None else ('skipped' if c.find('skipped') is not None else 'passed')
                rows.append((secs(c.get('time', '0')), st, c.get('classname') or c.get('file') or '', c.get('name', '')))
        elif p.endswith('jest.json'):
            j = json.load(open(p, encoding='utf-8'))
            for tr in j.get('testResults', []):
                for a in tr.get('assertionResults', []):
                    rows.append(((a.get('duration') or 0)/1000, a.get('status', ''), os.path.relpath(tr.get('name', '')), a.get('fullName', '')))
        else:  # go test -json / nextest libtest json: one JSON object per line
            for line in open(p, encoding='utf-8', errors='ignore'):
                try: e = json.loads(line)
                except: continue
                if e.get('Action') in ('pass', 'fail', 'skip') and e.get('Test'):
                    rows.append((e.get('Elapsed', 0), e['Action'], e.get('Package', ''), e['Test']))
                elif e.get('type') == 'test' and e.get('event') in ('ok', 'failed', 'ignored'):
                    rows.append((e.get('exec_time', 0), e['event'], '', e.get('name', '')))
    except Exception as ex:
        print(f'WARN cannot parse {p}: {ex}', file=sys.stderr)
if not rows:
    print(f'NO REPORTS found under {root} (junit xml / trx / go json / jest json). Use --run or --dir.'); sys.exit(3)
rows.sort(key=lambda r: -r[0])
with open(out, 'w', encoding='utf-8') as fh:
    for r in rows: fh.write(f'{r[0]:.3f}\t{r[1]}\t{r[2]}\t{r[3]}\n')
agg = defaultdict(lambda: [0.0, 0])
for r in rows: agg[r[2]][0] += r[0]; agg[r[2]][1] += 1
total = sum(r[0] for r in rows)
print(f'TESTS {len(rows)}  SUM {total:.0f}s ({total/60:.1f} min, sequential sum)  reports {len(files)}  tsv {out}')
print(f'SLOW TESTS (> {slow:.0f}s): {sum(1 for r in rows if r[0] > slow)}')
for r in rows[:top]:
    if r[0] <= slow and r is not rows[0]: break
    print(f'  {r[0]:8.1f}s  {r[1]:7}  {r[2]} :: {r[3]}')
print(f'SLOW FILES/CLASSES (> {5*slow:.0f}s):')
for k, (s, n) in sorted(agg.items(), key=lambda kv: -kv[1][0])[:top]:
    if s <= 5*slow: break
    print(f'  {s:8.1f}s  {n:4} tests  {k}')
PYEOF
