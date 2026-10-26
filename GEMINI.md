# GEMINI.md — BetterAI (ba) Guidelines for Gemini & Antigravity

This repository uses **ba (BetterAI)**: token-efficient, verified software development with strict verification gates and real proofs.

## 1. Model Tiering & Token Optimization (Gemini / Antigravity)
To maximize code quality while minimizing token consumption and cost, always route tasks and subagents by role:

| Role | Agent / Task | Antigravity (`agy` / IDE) Model | `invoke_subagent` Tier | Gemini CLI (`gemini`) Model | Why |
|---|---|---|---|---|---|
| **Orchestrator / Architect** | `/ba:architect`, `/ba:spec`, `/ba:issues`, `/ba:auto` | `gemini-4-argon-high` / `gemini-4-argon-medium` | `inherit` / `pro` | `gemini-3.1-pro-preview` (`pro`) | Deep reasoning, architecture, and wave coordination |
| **Writer (Codice & TDD)** | `ba:implementer` | `gemini-4-argon-high` / `gemini-4-argon-medium` | `pro` | `gemini-3.1-pro-preview` (`pro`) | Best coding quality for RED→GREEN tests and minimal diffs |
| **Checker (Prove & Gate)** | `ba:verifier` | `gemini-3.8-flash-medium` | `flash` | `gemini-3.8-flash` (`flash`) | Runs deterministic bash proof scripts (`prove-test.sh`, `gate.sh`) and checks assertions at low token cost |
| **Auditor (Optimize & Secure)** | `ba:auditor` | `gemini-3.8-flash-medium` | `flash` | `gemini-3.8-flash` (`flash`) | Fast read-only analysis of tool outputs, test durations, and call graphs |
| **Diff Reviewer** | `ba:reviewer` | `gemini-3.8-flash-low` | `flash_lite` | `gemini-3.5-flash-lite` (`flash-lite`) | Ultra-fast read-only `git diff` review for blocking bugs, security, and scope creep |

> **IMPORTANT for Antigravity (`invoke_subagent`)**: Never leave `Model` as `inherit` when invoking `ba:verifier`, `ba:auditor`, or `ba:reviewer` from a Pro/Argon session. Explicitly pass `Model: "pro"` for `implementer`, `Model: "flash"` for `verifier`/`auditor`, and `Model: "flash_lite"` for `reviewer`.

## 2. Core Rules for Gemini & Antigravity
1. **Terse Responses**: Follow `templates/terse-rules.md` (single source for output and comment rules).

2. **Writer vs Checker Separation**:
   - **Writer (`implementer` — tier `pro` / Gemini 4 Argon)**:
     - Writes the test first (RED), then the minimal implementation (GREEN).
     - For refactoring or performance, maintains all existing tests without weakening assertions.
     - Runs only `bash scripts/gate.sh . --only build` and filtered tests; never runs the full suite.
   - **Checker (`verifier` — tier `flash` / Gemini 3.8 Flash)**:
     - Never takes "tests pass" on faith.
     - Runs `bash scripts/prove-test.sh "<test-cmd>" <test-files...>` to confirm the tests fail with implementation reverted (RED) and pass with implementation applied (GREEN).
     - Runs `bash scripts/gate.sh . --tier fast` during loop and `bash scripts/gate.sh . --tier full` once to guarantee full build, lint, and test pass before shipping.
   - **Reviewer (`reviewer` — tier `flash_lite` / Gemini 3.8 Flash Low)**:
     - Read-only check on `git diff origin/<base>...HEAD` for blocking bugs, security issues, out-of-scope edits, or verbose comments.

3. **Deterministic Verification Commands** (`S` = `~/.gemini/config/plugins/ba/scripts` or `./scripts`):
   - Stack Detection: `bash $S/detect.sh .`
   - Fast Gate (Dev loop): `bash $S/gate.sh . --tier fast`
   - Full Gate (Pre-PR / Full suite): `bash $S/gate.sh . --tier full`
   - Real Test Proof: `bash $S/prove-test.sh "<test-cmd>" <test-files...>`
   - Refactor / Perf Proof: `bash $S/prove-refactor.sh origin/main <kind> [--tier fast|full]`
   - Security Audit: `bash $S/sec-scan.sh secrets` / `code` / `deps`
   - Secret Guard: `bash $S/secret-guard.sh`
   - Test Times & Bottlenecks: `bash $S/test-times.sh --slow 60 --timeout 600`

4. **Resuming Interrupted Runs (`.ba/auto.json`)**:
   - State is persisted on disk in `.ba/auto.json`, `.ba/auto.md`, `.ba/plan.json`, and `.ba/runs/<n>.md`, with isolated checkouts in `../<repo>-ba/<n>` git worktrees.
   - Any session (whether started in Claude Code, `agy`, or `gemini`) resumes directly from `.ba/auto.json`: skip `done`/`blocked`/`skipped` issues, and for `in_progress` issues run `verifier` (`flash`) + `reviewer` (`flash_lite`) on the existing worktree first.

5. **Safety & Zero Leaks**:
   - Never commit `.env`, keys, credentials, or secrets.
   - Never rewrite git history or force-push without explicit user request.
