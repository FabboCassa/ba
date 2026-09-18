---
name: implement
description: Use only when the user or /ba:ship asks to implement a specific GitHub issue number. Implements ONE issue end to end - branch, real proof (red->green test, or no-regression proof for refactor/perf/test-split, or scanner proof for dependency/secret fixes), build, review, commit "closes #n", PR. Retries with written failure reasons.
argument-hint: <issue-number>
allowed-tools: Read Grep Glob Edit Write Agent Bash(gh *) Bash(git *) Bash(bash *)
---

Issue: #$ARGUMENTS
Scripts: `S=${CLAUDE_SKILL_DIR}/../../scripts`

## 0. Preflight
- `gh issue view $ARGUMENTS --json title,body,state,labels`. Closed → stop. Label `needs-human` → stop: "richiede un'azione manuale" + its checklist.
- `KIND` = `Kind:` line of the body (missing → `feature`).
- Deps (from body or `.ba/plan.json`) must be merged/closed; else stop and name them.
- Clean tree required. Base = plan.base or default branch. `git fetch -q && git switch -c feat/$ARGUMENTS-<slug> origin/<base>` (reuse branch if exists). Prefix: `fix/` for security/secret/dep-upgrade, `refactor/` for refactor/test-split, `perf/` for perf.
- `bash $S/gate.sh .` on the fresh branch. If already red: stop, report — never build on a broken base.

## 1. Loop (max 3 attempts)
For attempt k:
a. Delegate to agent **ba:implementer** with: issue title/body, `KIND`, acceptance list, branch, `$S` path, `docs/architecture.md` if present, and (k>1) the full failure notes from `.ba/runs/$ARGUMENTS.md`.
   It must return: `TESTS: <files>`, `IMPL: <files>`, one-line summary.
b. Delegate to agent **ba:verifier** with the same issue, `KIND`, base ref and returned file lists. Proof by `KIND`:
   - `feature`, `security`: `bash $S/prove-test.sh "<TEST cmd>" <test files>` → RED ok + GREEN ok;
   - `refactor`, `test-split`: `bash $S/prove-refactor.sh origin/<base> <KIND> [--slow N]` → REFACTOR PROOF ok;
   - `perf`: `bash $S/prove-refactor.sh origin/<base> perf --bench "<Bench>" --target <Target>`;
   - `dep-upgrade`: `bash $S/sec-scan.sh deps --id <Advisory>` → RESOLVED;
   - `secret`: `bash $S/sec-scan.sh secrets --tree` clean for the files + prove-test on the config-loading test;
   - `config`: the acceptance check commands/tests pass, and fail on `origin/<base>` (prove-test when it is a test).
   Then always `bash $S/gate.sh .` (full build + lint + tests green) and the acceptance-to-assertion check.
   Returns `PASS` or `FAIL: <reason>` + evidence (≤40 log lines).
c. PASS → go to 2.
   FAIL → append to `.ba/runs/$ARGUMENTS.md`:
   `## Attempt k - FAIL` / `Why:` root cause in 1-3 lines (not the symptom) / `Evidence:` trimmed log / `Next:` what to change.
   Also `gh issue comment $ARGUMENTS` with the same block (label `security` on a public repo: comment only `Attempt k failed, details in .ba/runs/`). Then next attempt.
After 3 FAILs: `gh issue edit $ARGUMENTS --add-label blocked`, keep branch, report the 3 reasons, stop.

## 2. Review
Agent **ba:reviewer** on `git diff origin/<base>`. Blocking findings → treat as FAIL (loop step c). Nits → ignore.

## 3. Ship
- `git add -A -- . ':!.ba/logs' ':!.ba/cache' ':!.ba/security'` ; commit: `<type>(<scope>): <title>` + blank line + `Closes #$ARGUMENTS` (Conventional Commits, ≤72 char subject, body only if non-obvious; type from KIND: feat / fix / refactor / perf / test / chore(deps) / build). The secret-guard hook scans it.
- `git push -u origin HEAD`
- `gh pr create --base <base> --title "<same subject>" --body "Closes #$ARGUMENTS\n\nVerified: <build cmd> ✓ <test cmd> ✓ <proof line by KIND> ✓"`
- Output 3 lines: PR url, tests added (or proof used), attempts used.

Never: skip/disable/weaken tests, mock the unit under test, `--no-verify`, force-push to base, commit secrets.
