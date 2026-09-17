# ba rules (always on)

Output
- No preamble ("Sure", "Great question"), no closing recap, no restating the request.
- Lead with the answer or the action. Max 3 short sentences between tool calls, often zero.
- Final report: what changed + how verified, ≤5 lines. No per-file tour unless asked.
- Don't repeat code you just wrote. Show diffs/snippets only when asked.

Code
- Comments only for non-obvious WHY (constraint, workaround, invariant). Never narrate WHAT.
- No docblocks restating signatures. No "// added X", "// changed Y", no commented-out code.
- Smallest change that solves the task. No speculative abstractions, flags, or config.
- Match existing style; don't reformat untouched lines.

Tokens
- Read only what you need: Grep/Glob first, then Read with offset/limit.
- Pipe noisy commands: `| tail -n 60`, `--silent`, `-q`. Never dump full logs.
- Edit, don't rewrite whole files.
- Delegate wide searches to a subagent; keep only its conclusion.
- Never `sleep`/poll waiting for a subagent or a command you already launched synchronously.

Done means
- Built and tests run green in this session, with the command shown. Otherwise say "not verified" and why.
