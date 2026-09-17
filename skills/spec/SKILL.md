---
name: spec
description: Interview the user until a feature/project is fully specified, then write docs/specs/<slug>.md. Start of the ba flow.
disable-model-invocation: true
argument-hint: <what you want to build>
allowed-tools: Read Grep Glob Write Edit AskUserQuestion Bash(git *) Bash(gh repo view *) Bash(ls *) Bash(bash *)
---

Request: $ARGUMENTS

Goal: a spec with zero open questions, saved from `${CLAUDE_SKILL_DIR}/../../templates/spec.md` layout to `docs/specs/<slug>.md`.

1. Context (silent, cheap): `git remote -v`, `gh repo view --json nameWithOwner,defaultBranchRef`, top-level `ls`, README head, `bash ${CLAUDE_SKILL_DIR}/../../scripts/detect.sh`. Don't ask what you can read.
2. Interview with AskUserQuestion, max 4 questions per round:
   - Every question has a **recommended option first, labelled "(Consigliato)"**, grounded in the repo/context.
   - Order: goal & users → scope in/out → flows → data/integrations → edge cases & errors → non-functional (perf, security, i18n) → build/test commands → acceptance criteria.
   - Skip anything already answered. No filler questions.
3. After each round, keep a private list of gaps. Continue rounds until every Requirement has an observable, testable acceptance criterion and no "TBD" remains.
4. Write the spec. Show the user only: path + 5-line summary + "Approvi? (sì / modifiche)".
5. On approval set `Status: approved` and tell them: next `/ba:issues docs/specs/<slug>.md`.

Rules: user's language for questions, English for the spec file. Don't write code here.
