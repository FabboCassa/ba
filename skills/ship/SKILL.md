---
name: ship
description: Run /ba:implement for every open ba issue in dependency order, stacking or merging as configured.
disable-model-invocation: true
argument-hint: "[issue numbers...] [merge]"
allowed-tools: Read Write Skill Bash(gh *) Bash(git *) Bash(jq *)
---

Targets: $ARGUMENTS (empty → all open issues in `.ba/plan.json`, else `gh issue list --label ba --state open`).

1. Topologically sort by deps. Show order in one line. No confirmation needed unless >10 issues.
2. For each issue:
   - If a dep has an unmerged PR: base the new branch on that dep's branch (stacked PR, `--base feat/<dep>…`) and note it in the PR body.
   - Invoke skill `ba:implement <n>`. Keep only its 3-line result in context.
   - `blocked` → skip issues depending on it; continue with independent ones.
3. Final table: `#n | PR | status (✓ / blocked: reason)`. Nothing else.

Merging is the user's call: never merge PRs unless they said so in $ARGUMENTS ("merge").
