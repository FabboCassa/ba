---
name: optimize
description: Audit a repo for slow tests, architecture drift, dead/duplicated code and performance problems. Proposes fixes with evidence, turns the approved ones into ba issues (then /ba:ship or /ba:auto implements them).
disable-model-invocation: true
argument-hint: "[tests|arch|code|perf ...] [slow=60] [run-tests] [auto]"
allowed-tools: Read Grep Glob Write Edit Agent Skill AskUserQuestion Bash(git *) Bash(gh *) Bash(bash *) Bash(jq *) Bash(npx *) Bash(dotnet *) Bash(python* *) Bash(go *) Bash(cargo *)
---

Args: $ARGUMENTS
Scripts: `S=${CLAUDE_SKILL_DIR}/../../scripts`

Areas = args among `tests arch code perf` (none → all). `SLOW` = `slow=N` seconds per test (default 60; per file/class = 5×SLOW; whole suite target = 10 min). `AUTO` = args contain `auto`.

# Principles
- Every finding needs **evidence** (file:line, measured time, tool output). No evidence → not a finding. Guesses go under "Hypotheses" and become at most a "measure first" issue.
- Nothing is changed in this skill. Output = report + issues. Fixes go through the normal flow (`implement` / `ship` / `auto`).
- Never propose anything that lowers coverage or deletes an assertion to gain speed. Splitting ≠ weakening.
- Heavy analysis runs in agent **ba:auditor** (read-only). Keep in this context only its findings table.

# 0. Context (silent)
`bash $S/detect.sh .`, `git ls-files | head -400`, top-level `ls`, README head, `docs/architecture.md` if present, `.ba/config.json` if present.

# 1. Tests — duration
1. `bash $S/test-times.sh --slow $SLOW` → reads existing reports (junit/trx/go json, CI-style paths). No reports:
   - try latest CI run: `gh run list -L 5 --json databaseId,conclusion,name` then `gh run download <id> -D .ba/logs/ci` and re-run the script with `--dir .ba/logs/ci`;
   - still nothing → need a measured run: `bash $S/test-times.sh --run --slow $SLOW` (writes reports to `.ba/logs/`). If the suite is likely long (many integration dirs, previous logs, user said so) and not `AUTO`/`run-tests`: ask once "La suite può durare a lungo, la lancio ora?" (Consigliato: sì, in background). In `AUTO` run it.
2. Output of the script = slow tests + slow files. For each slow item, dispatch **ba:auditor** (mode `tests`, max 10 items per call) with test file paths + durations. It classifies the cause and proposes a split per `${CLAUDE_SKILL_DIR}/references/test-classifications.md`.
   Also propose **tiers**: fast (PR gate) vs `slow` category (nightly CI job that still runs everything). Tag syntax per framework is in the same reference file.
3. Issue Kind = `test-split`. Acceptance always includes: same or more test ids and assertions; slowest test < SLOW s; file < 5×SLOW s; full suite (all tiers) still green; slow tier wired into CI.

# 2. Architecture
1. If `docs/architecture.md` has `Status: confirmed` → use it, don't ask.
2. Else **ba:auditor** (mode `arch-detect`): folder names, project/module graph, import directions, frameworks → returns hypothesis (Layered/MVC, Clean, Hexagonal, Vertical slice, MVVM, MVI, feature modules, monorepo packages, micro-services…) + confidence + 3-5 evidence lines + main alternatives.
3. Ask with AskUserQuestion (skip in `AUTO`): hypothesis first `(Consigliato)`, then alternatives; a second question for rules if ambiguous (e.g. "Il dominio può dipendere da EF/ORM?"). Write `docs/architecture.md` from `${CLAUDE_SKILL_DIR}/../../templates/architecture.md`, `Status: confirmed`.
   `AUTO` without a confirmed architecture → report the hypothesis only, create NO arch issues (never refactor toward an unconfirmed architecture).
4. **ba:auditor** (mode `arch-check`) with the rules: dependency direction violations, cycles, logic in the wrong layer, god classes/files (> ~500 lines or > ~15 deps), duplicated cross-cutting code. Prefer tools per stack — see `${CLAUDE_SKILL_DIR}/references/tools-by-language.md`.
5. First arch issue (if none exists) = **architecture test** encoding the rules (Kind `feature`: it is red on current violations, green after fixes → real red→green). Violation fixes: Kind `refactor`, depend on it.

# 3. Code — dead, duplicated, improvable
**ba:auditor** (mode `code`). Tools per stack in `${CLAUDE_SKILL_DIR}/references/tools-by-language.md`, else careful Grep.
Complexity hot spots: longest/most-branched functions in files changed often (`git log --format= --name-only | sort | uniq -c | sort -rn | head -30`).
Rules: code reachable via reflection/DI/serialization/public API of a library is NOT dead without proof (grep registrations, config, attribute usage). Kind `refactor` (dead code, duplication, simplification).

# 4. Performance
**ba:auditor** (mode `perf`): N+1 queries, queries in loops, missing indexes vs query filters, sync I/O on async paths, unbounded lists/pagination missing, repeated serialization, O(n²) on collections that grow, allocations in hot loops, missing caching of pure expensive calls, startup work that could be lazy, oversized bundles/images (web), main-thread work (mobile).
Each perf finding either comes with a measurement, or its issue is split in two: (1) add a benchmark (Kind `feature`, benchmark harness of the stack: BenchmarkDotNet, vitest bench / tinybench, pytest-benchmark, `go test -bench`, criterion, JMH) and (2) the optimization (Kind `perf`, `Bench:` = that command, `Target:` = required gain, e.g. `-30% median`).

# 5. Report + approval
Write `docs/audits/optimize-<YYYY-MM-DD>.md`:
```
# Optimize audit <date>   Status: draft
Scope: <areas>   Suite: <total time> (<n> tests)   Architecture: <name> (confirmed|hypothesis)
| ID | Area | Impact | Effort | Kind | Finding (evidence) | Proposal |
| O1 | tests | high | M | test-split | OrdersIT.FullFlow 3412s (trx) - 40 scenarios in 1 test, DB rebuilt each | 1 test per scenario, shared DB fixture, move 3 to slow tier |
## Details  (one ### per ID: evidence ≤10 lines, acceptance bullets, Bench/Target if perf)
## Hypotheses (not issues)
## Not checked (tool missing / not applicable) 
```
Impact order: time saved or risk removed first. Show the user only the table + "Quali trasformo in issue? (tutte / O1 O3 … / nessuna)". In `AUTO`: all with Impact ≥ medium.
Set `Status: approved` and list approved IDs in the file.

# 6. Issues + next
Follow `${CLAUDE_SKILL_DIR}/../issues/SKILL.md` with the audit report as source (its confirmation step is already done): one issue per approved ID (split big ones ≤300 lines), labels `ba` + `optimize`, body contains `Kind:`, acceptance bullets and, for perf, `Bench:`/`Target:`. Ensure `.gitignore` has `.ba/logs/`. Commit `docs: optimize audit <date>`.
Output: issue list + `Next: /ba:ship` or `/ba:auto`. With `AUTO`: invoke skill `ba:auto` directly.
