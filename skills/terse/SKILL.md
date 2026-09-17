---
name: terse
description: Token-saving rules for replies and code comments. Use when writing code, reports, commit messages or PR text.
user-invocable: false
---

Follow `${CLAUDE_SKILL_DIR}/../../templates/terse-rules.md` (already injected at session start). Extra, for written artifacts:

- Commit: `type(scope): imperative subject` ≤72 chars. Body only for WHY.
- PR body: `Closes #n`, verification line, max 5 bullets of notable decisions.
- Issue comments: facts + next step. No apologies, no emojis.
- Code comment test: delete it — would a competent reader lose information? If no, it stays deleted.
