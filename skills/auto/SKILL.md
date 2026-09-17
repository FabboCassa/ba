---
name: auto
description: Fully autonomous run - implements ALL open ba issues (or a spec) end to end without asking anything. Writer agent codes, separate checker agents verify. Stops only when every issue is done or blocked.
disable-model-invocation: true
argument-hint: "[docs/specs/x.md] [merge] [max=N] [par=N] [no-worktree]"
disallowed-tools: AskUserQuestion
allowed-tools: Read Write Edit Grep Glob Agent Skill Bash(gh *) Bash(git *) Bash(bash *) Bash(jq *)
---

Args: $ARGUMENTS
Scripts: `S=${CLAUDE_SKILL_DIR}/../../scripts`

# Autonomous mode — hard rules
- Add `.ba/auto.lock`, `.ba/auto.count` and `.ba/logs/` to `.gitignore` if missing.
- The branch must contain ONLY this issue's changes: files already modified before the run (the user's own work in progress) are never committed — list them in the report instead.
- NEVER ask the user anything. NEVER end your turn until the final report. Ambiguity → choose the option most consistent with the spec + existing code, log it under `Decisions` in `.ba/auto.md`, continue.
- Roles are separated. You (orchestrator) never write product code or tests. **Writer** = agent `ba:implementer`. **Checkers** = agents `ba:verifier` and `ba:reviewer`. A checker never receives the writer's reasoning, only: issue text, file lists, branch.
- A PASS exists only if the checker ran the commands itself in this attempt. Writer claims ("tests pass") are ignored.
- Context budget: keep per-issue only a ≤3-line result. Details go to files.
- NEVER poll or sleep waiting for an agent (`sleep`, `seq ... sleep`, watch loops). An Agent call already returns when the agent is done. Waiting loops burn wall clock and tokens for nothing.
- If you notice the conversation was compacted or you're unsure where you are: re-read this file (`${CLAUDE_SKILL_DIR}/SKILL.md`) and `.ba/auto.json`, then resume per step 0.4.

# 0. Setup
1. `mkdir -p .ba && echo "${CLAUDE_SESSION_ID}" > .ba/auto.lock && echo 0 > .ba/auto.count` (a Stop hook keeps THIS session running while the lock holds its id; a lock left by another session is ignored). `gh auth status`, `git status --porcelain` (dirty → `git stash -u -m ba-auto` and log it), `git fetch -q`.
2. If args contain a `.md` spec: follow `${CLAUDE_SKILL_DIR}/../issues/SKILL.md` but **skip its confirmation step** (the approved spec is the confirmation). If spec `Status` isn't `approved`, stop with that error — never invent requirements.
3. Queue = open issues from `.ba/plan.json`, else `gh issue list --label ba --state open --json number,body`. Parse `Depends on`. Topological sort. Drop issues labelled `blocked`. Apply `max=N` if given.
4. Resume (after compaction, crash, Ctrl+C or a new session): if `.ba/auto.json` exists, it is the ONLY source of truth — not your memory.
   - `done` / `blocked` / `skipped` → skip.
   - `in_progress` → re-attach its worktree (`git worktree list`; recreate with the recorded branch if missing) or, without worktrees, `git switch` to its `branch`; read `.ba/runs/<n>.md`. If uncommitted or committed changes exist, first run the checkers (`ba:verifier`, then `ba:reviewer`) on them: PASS → go straight to Ship; FAIL → continue the loop at `attempt + 1`. If a PR already exists (`gh pr list --head <branch>`), don't open another.
5. `MERGE` = args contain `merge`. `PAR` = `par=N` (default 3, max 4; 1 = sequential). `WT` = worktrees on unless `no-worktree`.
6. Worktrees (`WT`): every issue gets its own checkout OUTSIDE the repo, so the user's IDE and index are never touched:
   `git worktree add ../<repo>-ba/<n> -b feat/<n>-slug origin/<base>` (reuse it if present; `git worktree list` to check).
   Every command for that issue — writer, checkers, `gate.sh`, `prove-test.sh`, git — runs with that directory as cwd. Each agent is TOLD its worktree path and must not touch any other path.
   After a merged PR: `git worktree remove ../<repo>-ba/<n>`. On `blocked`: leave it and name it in the report.
   `.ba/` state files always live in the MAIN repo, never in a worktree.

# 1. Waves (parallel)
Repeat until the queue is empty:
1. READY = queued issues whose deps are all `done` (or closed). Deps `blocked`/`skipped` → mark the issue `skipped: dep #d blocked`.
2. Take the first `min(PAR, |READY|)` issues. With `PAR=1` or `no-worktree`, take exactly 1.
3. Create each issue's worktree, then dispatch ALL their writers **in one message, one Agent call each** (that is what makes them parallel). Never dispatch a writer for an issue whose worktree is missing.
4. When the writers return, dispatch the checkers the same way (one `ba:verifier` per issue in a single message, then `ba:reviewer`).
5. Handle each issue's result (ship / retry / block) per the rules below. Retries of different issues in the same wave are dispatched together too.
6. Merge (if `MERGE`) strictly one at a time, in queue order: `gh pr checks` → `gh pr merge --squash --delete-branch` → `git -C <main repo> switch <base> && git pull -q`. If a later PR in the wave no longer merges cleanly, rebase its worktree on the new base and re-run its checkers; still failing → that issue takes a FAIL attempt with reason `conflict after #<n>`.

# 1b. Per issue
Skip if any dep ended `blocked` → mark `skipped: dep #d blocked`.

**Base**: MERGE → `origin/<base>` (deps are merged). Else → branch of the nearest unmerged dep (stacked), otherwise `origin/<base>`.

Follow `${CLAUDE_SKILL_DIR}/../implement/SKILL.md` sections 0-3 exactly, with these overrides:
- Base branch as above; PR `--base` = that branch.
- Dependency check passes if each dep is closed OR `done` in this run.
- Red base (gate fails before any change): try ONE writer attempt scoped to "fix the build only", verified by `ba:verifier` (gate only). Still red → mark all remaining issues `blocked: base broken` and go to Final report.
- Attempts: max 3. Each FAIL note (`Why / Evidence / Next`) goes to `.ba/runs/<n>.md` + issue comment, and the FULL note is passed to the next writer attempt.
- After PASS + review OK + PR: if MERGE → `gh pr checks <pr> --watch --fail-fast` (skip if no checks configured), then `gh pr merge <pr> --squash --delete-branch`, `git switch <base> && git pull -q`. Checks red → treat as FAIL for the loop (re-attempt on same branch).
- 3 FAILs → label `blocked`, record reasons, continue with next independent issue.

**Writing `.ba/auto.json` is a HARD GATE, not bookkeeping.** Before dispatching any writer, and before every merge, the state file must already contain that issue's current entry — if you are about to call an agent and have not written it, write it first. A run that ends with `{"issues":{}}` is a bug: it means nothing can be resumed.

Record `wave` and `worktree` per issue. Checkpoint `.ba/auto.json` at EVERY step change (branch created, each writer attempt, each check result, PR opened, merged), not only at the end:
`{"issues":{"14":{"status":"in_progress|done|blocked|skipped","phase":"write|verify|review|pr|merge","branch":"feat/14-x","worktree":"../repo-ba/14","wave":2,"attempt":2,"pr":21,"reason":""}}}`
Write it before starting the step, so a context reset never loses more than the step in flight.
and append one line to `.ba/auto.md`.

# 2. Final report (only output of the whole run)
```
ba:auto — <done>/<total> done, <blocked> blocked, <skipped> skipped (par=<PAR>)
#14 | PR #21 | ✓ 1 att
#15 | PR #22 | ✓ 3 att
#16 | -      | blocked: <1-line reason> (.ba/runs/16.md)
Decisions: <n> logged in .ba/auto.md
```
Leftover worktrees of blocked issues: list their paths. If a stash was made, say so (`git stash pop` to restore).
Then delete `.ba/auto.lock` and `.ba/auto.count` — only after the report. On a fatal stop (auth missing, spec not approved) delete it too, after printing the error.
