---
name: issues
description: Turn an approved spec into small, ordered GitHub issues (one per shippable, testable change) with dependencies.
disable-model-invocation: true
argument-hint: <docs/specs/file.md>
allowed-tools: Read Edit Write Bash(gh *) Bash(git *)
---

Spec: $ARGUMENTS

Preflight: `gh auth status` must pass, spec `Status: approved`. Else stop and say why.

1. Split into tasks. Each task:
   - one vertical, independently buildable + testable change (≈ ≤300 changed lines);
   - maps to requirement IDs; lists concrete acceptance checks that a test can assert;
   - declares `Depends on` by task number. First task sets up build/test harness if missing.
2. Show the task table (title, deps, R-ids) and ask once for OK. No issues before OK.
3. Create labels if missing: `ba`, `blocked` (`gh label create … --force`).
4. Create issues in dependency order with `gh issue create --label ba --title … --body-file -`. Body:
   ```
   Spec: <path>#<anchor>   Requirements: R1, R3
   Depends on: #<n>, …
   ## Acceptance (each must become a test)
   - [ ] …
   ## Notes
   <files likely touched, gotchas — max 5 bullets>
   ```
5. Fill the spec's Tasks table with issue numbers; write `.ba/plan.json`:
   `{"spec": "...", "base": "<default branch>", "issues": [{"n": 12, "deps": [11]}]}`
6. Ensure `.gitignore` has `.ba/logs/`. Commit spec + plan + .gitignore on base branch: `docs: spec + plan for <slug>`.
7. Output: issue list (`#n title`) and next: `/ba:ship` (all) or `/ba:implement <n>`.
