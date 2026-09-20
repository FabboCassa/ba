# AGENTS.md — BetterAI (ba) Multi-AI Standard Guide

Universal guidelines for AI coding assistants working in this repository (Gemini, Antigravity, DeepSeek, Qwen, OpenAI/ChatGPT/Codex, Cursor, Windsurf, Copilot, Claude Code, Cline, Roo Code, Aider).

---

## 1. Core Philosophy: Terse, Real Proofs, Zero Fluff
- **Token Efficiency**: No preambles ("Sure!", "I'd be happy to help"), no polite conversational filler, no unsolicited postambles or recap of code just modified.
- **Lead with Action or Result**: State directly what was done and the verification evidence (max 3-5 lines).
- **No Unverified Claims**: Never state "all tests pass" without running the verification commands in the current turn.
- **Comments**: Only comment the non-obvious *WHY* (workarounds, hardware/platform constraints, invariants). Never narrate *WHAT* the code does.

---

## 2. Role Separation: Writer vs Checker
When implementing features or bug fixes, keep the writer mindset distinct from the checker mindset:

1. **Writer (`implementer`)**:
   - Focus on implementing the specific task/issue.
   - For new behavior (`feature`) or security exploit fixes (`security`): write the test first (RED), then the minimal implementation (GREEN).
   - For `refactor`, `perf`, or `test-split`: maintain existing observable behavior and keep all tests passing without weakening assertions.
   - Run `bash scripts/gate.sh .` to confirm build, lint, and tests pass before declaring done.

2. **Checker (`verifier`)**:
   - Independent verification: assume the code might have hidden defects or fake tests until proven otherwise.
   - Run `bash scripts/prove-test.sh "<test-command>" <test-files...>`:
     - Temporarily reverts the implementation to ensure the new tests genuinely fail (RED ok).
     - Restores the implementation to ensure the tests pass (GREEN ok).
     - Detects tautological/fake tests (`FAKE TEST`).
   - Run `bash scripts/prove-refactor.sh <base-ref> <kind>` for refactoring/perf.
   - Run `bash scripts/gate.sh .` for full compilation, linting, and whole-suite test runs.

3. **Diff Reviewer (`reviewer`)**:
   - Inspects `git diff <base>...HEAD`.
   - Blocks on: security flaws (injections, exposed secrets), out-of-scope refactorings, unhandled error paths, dead/commented-out code.
   - Ignores purely subjective naming or stylistic preferences accepted by the project linter.

4. **Auditor (`auditor`)**:
   - Read-only analysis for performance, security, architecture drift, and test execution duration.
   - Evidence-first: every finding must cite `file:line`, benchmark numbers, or tool outputs.

---

## 3. Essential Deterministic Scripts (`scripts/`)
All AI agents can execute these bash scripts deterministically:

| Script | Purpose | Command |
|---|---|---|
| `detect.sh` | Detects project build, test, and lint commands | `bash scripts/detect.sh .` |
| `gate.sh` | Runs build + lint + test, printing compact logs (last 40 lines on error) | `bash scripts/gate.sh .` |
| `prove-test.sh` | Proves tests are real via RED->GREEN implementation rollback | `bash scripts/prove-test.sh "<test-cmd>" <test-files...>` |
| `prove-refactor.sh` | Proves refactoring/perf preserved all tests without regressions | `bash scripts/prove-refactor.sh origin/main refactor` |
| `sec-scan.sh` | Scans secrets (git tree + history), vulnerable code, and deps | `bash scripts/sec-scan.sh secrets` / `code` / `deps` |
| `secret-guard.sh` | Prevents accidental commits or publishes containing secret keys | `bash scripts/secret-guard.sh` |
| `test-times.sh` | Analyzes test suite runtimes and highlights slow bottlenecks | `bash scripts/test-times.sh --slow 60` |

---

## 4. Multi-AI Support Matrix
- **Gemini / Google Antigravity**: Read `AGENTS.md` and `GEMINI.md`. Use Antigravity skills or run scripts via terminal tool.
- **DeepSeek & Qwen**: Supported natively in Roo Code / Cline using `.clinerules` and `.roomodes`.
- **OpenAI / Cursor / Windsurf**: Adheres to `.cursorrules`, `.cursor/rules/*.mdc`, `.windsurfrules`.
- **Claude Code**: Uses `.claude-plugin/` and `skills/*/SKILL.md`.
