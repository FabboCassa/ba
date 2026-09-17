---
name: auto
description: Fully autonomous run - implements ALL open ba issues (or a spec) end to end without asking anything. Writer agent codes, separate checker agents verify. Stops only when every issue is done or blocked.
disable-model-invocation: true
argument-hint: "[docs/specs/x.md] [merge] [max=N]"
disallowed-tools: AskUserQuestion
allowed-tools: Read Write Edit Grep Glob Agent Skill Bash(gh *) Bash(git *) Bash(bash *) Bash(jq *)
---

Args: $ARGUMENTS
Scripts: `S=${CLAUDE_SKILL_DIR}/../../scripts`

# Autonomous mode — hard rules
- Add `.ba/auto.lock` to `.gitignore` if missing.
- NEVER ask the user anything. NEVER end your turn until the final report. Ambiguity → choose the option most consistent with the spec + existing code, log it under `Decisions` in `.ba/auto.md`, continue.
- Roles are separated. You (orchestrator) never write product code or tests. **Writer** = agent `ba:implementer`. **Checkers** = agents `ba:verifier` and `ba:reviewer`. A checker never receives the writer's reasoning, only: issue text, file lists, branch.
- A PASS exists only if the checker ran the commands itself in this attempt. Writer claims ("tests pass") are ignored.
- Context budget: keep per-issue only a ≤3-line result. Details go to files.

# 0. Setup
1. `mkdir -p .ba && echo 0 > .ba/auto.lock` (a Stop hook keeps you running while it exists). `gh auth status`, `git status --porcelain` (dirty → `git stash -u -m ba-auto` and log it), `git fetch -q`.
2. If args contain a `.md` spec: follow `${CLAUDE_SKILL_DIR}/../issues/SKILL.md` but **skip its confirmation step** (the approved spec is the confirmation). If spec `Status` isn't `approved`, stop with that error — never invent requirements.
3. Queue = open issues from `.ba/plan.json`, else `gh issue list --label ba --state open --json number,body`. Parse `Depends on`. Topological sort. Drop issues labelled `blocked`. Apply `max=N` if given.
4. Resume: if `.ba/auto.json` exists, skip issues already `done`.
5. `MERGE` = args contain `merge`.

# 1. Per issue (in order)
Skip if any dep ended `blocked` → mark `skipped: dep #d blocked`.

**Base**: MERGE → `origin/<base>` (deps are merged). Else → branch of the nearest unmerged dep (stacked), otherwise `origin/<base>`.

Follow `${CLAUDE_SKILL_DIR}/../implement/SKILL.md` sections 0-3 exactly, with these overrides:
- Base branch as above; PR `--base` = that branch.
- Dependency check passes if each dep is closed OR `done` in this run.
- Red base (gate fails before any change): try ONE writer attempt scoped to "fix the build only", verified by `ba:verifier` (gate only). Still red → mark all remaining issues `blocked: base broken` and go to Final report.
- Attempts: max 3. Each FAIL note (`Why / Evidence / Next`) goes to `.ba/runs/<n>.md` + issue comment, and the FULL note is passed to the next writer attempt.
- After PASS + review OK + PR: if MERGE → `gh pr checks <pr> --watch --fail-fast` (skip if no checks configured), then `gh pr merge <pr> --squash --delete-branch`, `git switch <base> && git pull -q`. Checks red → treat as FAIL for the loop (re-attempt on same branch).
- 3 FAILs → label `blocked`, record reasons, continue with next independent issue.

After each issue update `.ba/auto.json`:
`{"issues":{"14":{"status":"done|blocked|skipped","pr":21,"attempts":2,"reason":""}}}`
and append one line to `.ba/auto.md`.

# 2. Final report (only output of the whole run)
```
ba:auto — <done>/<total> done, <blocked> blocked, <skipped> skipped
#14 | PR #21 | ✓ 1 att
#15 | PR #22 | ✓ 3 att
#16 | -      | blocked: <1-line reason> (.ba/runs/16.md)
Decisions: <n> logged in .ba/auto.md
```
If a stash was made, say so (`git stash pop` to restore).
Then delete `.ba/auto.lock` — only after the report. On a fatal stop (auth missing, spec not approved) delete it too, after printing the error.
