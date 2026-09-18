---
name: issues
description: Turn an approved spec or an approved audit report (optimize/secure) into small, ordered GitHub issues (one per shippable, testable change) with dependencies and a proof Kind.
disable-model-invocation: true
argument-hint: <docs/specs/file.md | docs/audits/file.md | .ba/security/report-x.md>
allowed-tools: Read Edit Write Bash(gh *) Bash(git *)
---

Source: $ARGUMENTS

Preflight: `gh auth status` must pass, source `Status: approved`. Else stop and say why.
Audit reports: only the approved IDs become issues; their confirmation already happened, so skip step 2.

1. Split into tasks. Each task:
   - one vertical, independently buildable + testable change (≈ ≤300 changed lines);
   - maps to requirement IDs (spec `R1`) or finding IDs (`O3`, `S2`); lists concrete acceptance checks that a test or command can assert;
   - declares `Depends on` by task number. First task sets up build/test harness if missing;
   - has a **Kind**, which decides how it is proven:
     `feature` (default, new behavior) and `security` (the test performs the attack) → red→green test;
     `refactor` / `test-split` / `perf` (no new behavior) → `prove-refactor.sh` (same tests green before/after, nothing lost; perf also needs `Bench:` + `Target:`);
     `dep-upgrade` → scanner no longer reports the advisory; `secret` → secret scan clean + value read from env/secret store; `config` → a check command or test asserting the setting.
2. Show the task table (title, Kind, deps, IDs) and ask once for OK. No issues before OK.
3. Create labels if missing: `ba`, `blocked`, `needs-human`, `optimize`, `security` (`gh label create … --force`).
4. Create issues in dependency order with `gh issue create --label ba[,optimize|security] --title … --body-file -`. Body:
   ```
   Source: <path>#<anchor>   Refs: R1, R3 | O2 | S4
   Kind: feature|security|refactor|test-split|perf|dep-upgrade|secret|config
   Depends on: #<n>, …
   Bench: <cmd printing "BENCH <n>">   Target: <min gain %>      (perf only)
   Advisory: <GHSA/CVE id>                                        (dep-upgrade only)
   ## Acceptance (each must become a test or a check command)
   - [ ] …
   ## Notes
   <files likely touched, gotchas — max 5 bullets>
   ```
   Items only a human can do (rotate a key, fill a store console form): label `needs-human`, checklist of steps, no Kind.
   Security findings on a **public** repo: neutral title/body, `Details: .ba/security/<ID>.md (local)`; never exploit details or secret values.
5. Spec source: fill its Tasks table with issue numbers. Audit source: add the issue number next to each approved ID. Write/extend `.ba/plan.json`:
   `{"spec": "...", "base": "<default branch>", "issues": [{"n": 12, "deps": [11], "kind": "feature"}]}`
6. Ensure `.gitignore` has `.ba/logs/`, `.ba/cache/`, `.ba/security/`. Commit spec/audit + plan + .gitignore on base branch: `docs: plan for <slug>` (never commit `.ba/security/`).
7. Output: issue list (`#n [kind] title`) and next: `/ba:ship` (all), `/ba:auto`, or `/ba:implement <n>`.
