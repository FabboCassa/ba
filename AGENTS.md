# AGENTS.md — BetterAI (ba) Multi-AI Standard Guide

Universal guidelines for AI coding assistants working in this repository (Gemini, Antigravity, DeepSeek, Qwen, OpenAI/ChatGPT/Codex, Cursor, Windsurf, Copilot, Claude Code, Cline, Roo Code, Aider).

---

## 1. Core Philosophy: Terse, Real Proofs, Zero Fluff
Follow `templates/terse-rules.md` (token efficiency, comment rules, output format). Never state "all tests pass" without running the verification commands in the current turn.

---

## 2. Role Separation: Writer vs Checker
When implementing features or bug fixes, keep the writer mindset distinct from the checker mindset:

1. **Writer (`implementer`)**:
   - Focus on implementing the specific task/issue.
   - For new behavior (`feature`) or security exploit fixes (`security`): write the test first (RED), then the minimal implementation (GREEN).
   - For `refactor`, `perf`, or `test-split`: maintain existing observable behavior and keep all tests passing without weakening assertions.
   - Run `bash scripts/gate.sh . --tier fast` to confirm build, lint, and fast tests pass before declaring done.

2. **Checker (`verifier`)**:
   - Independent verification: assume the code might have hidden defects or fake tests until proven otherwise.
   - Run `bash scripts/prove-test.sh "<test-command>" <test-files...>`:
     - Temporarily reverts the implementation to ensure the new tests genuinely fail (RED ok).
     - Restores the implementation to ensure the tests pass (GREEN ok).
     - Detects tautological/fake tests (`FAKE TEST`).
   - Run `bash scripts/prove-refactor.sh <base-ref> <kind> [--tier fast|full]` for refactoring/perf.
   - Run `bash scripts/gate.sh . --tier fast` during iterations, and `bash scripts/gate.sh . --tier full` for final whole-suite pass before ship.

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
| `detect.sh` | Detects project build, test, and fast/full tier commands | `bash scripts/detect.sh .` |
| `gate.sh` | Runs build + lint + test (supports `--tier fast\|full` and `--timeout <sec>`) | `bash scripts/gate.sh . --tier fast` |
| `prove-test.sh` | Proves tests are real via RED->GREEN implementation rollback | `bash scripts/prove-test.sh "<test-cmd>" <test-files...>` |
| `prove-refactor.sh` | Proves refactoring/perf preserved all tests without regressions | `bash scripts/prove-refactor.sh origin/main refactor` |
| `sec-scan.sh` | Scans secrets (git tree + history), vulnerable code, and deps | `bash scripts/sec-scan.sh secrets` / `code` / `deps` |
| `secret-guard.sh` | Prevents accidental commits or publishes containing secret keys | `bash scripts/secret-guard.sh` |
| `test-times.sh` | Analyzes test suite runtimes, bottlenecks, with timeout killing | `bash scripts/test-times.sh --slow 60 --timeout 600` |
| `delegate-coder.sh` | Detects external coders; delegates code writing + proof with zero-PM retries | `bash scripts/delegate-coder.sh --detect` / `ba delegate-code ...` |
| `model-resolver.py` | Dynamic multi-model discovery and cross-family tier resolver | `python scripts/model-resolver.py [--flagship ds\|claude\|gemini]` |
| `deepseek-bridge.py`| Lightweight native bridge for DeepSeek API discovery & chat | `python scripts/deepseek-bridge.py best-model` |
| `blender-vc.sh` | Git + Git LFS setup for Blender assets (idempotent) | `bash scripts/blender-vc.sh init .` |
| `blender/bkit.py` | In-Blender kit: multi-angle renders, silhouette IoU vs references, snapshot JSON, mesh checks | loaded via MCP `execute_blender_code` |

---

## 4. Multi-AI Support Matrix
- **Gemini / Google Antigravity**: Read `AGENTS.md` and `GEMINI.md`. Use Antigravity skills or run scripts via terminal tool.
- **DeepSeek & Qwen**: Supported natively in Roo Code / Cline using `.clinerules` and `.roomodes`, and via `scripts/deepseek-bridge.py` across all terminal orchestrators.
- **OpenAI / Cursor / Windsurf**: Adheres to `.cursorrules`, `.cursor/rules/*.mdc`, `.windsurfrules`.
- **Claude Code**: Uses `.claude-plugin/` and `skills/*/SKILL.md`.

---

## 5. Dynamic Model Routing & Cross-Family Asymmetric Verification
To prevent correlated hallucinations and blind spots, BetterAI enforces asymmetric model verification:
1. **Flagship Choice**: User selects or specifies the flagship family (`deepseek`, `claude`, `gemini`), or is prompted at skill launch.
2. **Dynamic Discovery**: Resolves the highest version available via live API discovery (e.g. DeepSeek v4 > v3 > reasoner).
3. **Asymmetric Rule**:
   - Flagship **DeepSeek** (Writer) -> Verifier routes to **Claude Sonnet** or **Gemini Flash**.
   - Flagship **Claude** (Writer) -> Verifier routes to **DeepSeek** or **Gemini Flash**.
   - Flagship **Gemini** (Writer) -> Verifier routes to **DeepSeek** or **Claude Sonnet**.
4. **Resolution Cache**: Persisted in `.ba/models.json` via `ba models --save`.

---

## 6. Optional External Pure Coder (Colibri / DeepSeek)
The main AI stays PM (spec, issues, brief) and final checker. Code writing may be delegated:
1. **Detect, never assume**: `bash scripts/delegate-coder.sh --detect` → `colibri=UP|DOWN` (local OpenAI-compatible endpoint, `COLIBRI_API_BASE`), `deepseek=READY|MISSING_KEY` (`DEEPSEEK_API_KEY` from env, `~/.ba/credentials.env` or repo `.env`; never `.ba/`), `native=READY`, plus `pref`, `recommend`, `chain`.
2. **Choose**: `coder=` arg > saved `.ba/config.json` pref (if available) > ask ONE question listing only available options (recommended first). Autonomous runs never ask: they use `chain`.
3. **Delegate**: PM writes `.ba/runs/<n>-brief.md` (≤40 lines) → `bash scripts/delegate-coder.sh --issue <n> --coder <c> --brief ... --files ... --tests ... --test-cmd ...` → coder writes, script runs `prove-test.sh` + `gate.sh --tier fast`, retries ≤2 with the error tail. Last line: `RESULT: PASS | FAIL | CODER_UNAVAILABLE`.
4. **Escalate**: `FAIL` → next attempt with the next coder (`colibri → deepseek → native`); `CODER_UNAVAILABLE` → next coder, same attempt. `PASS` → `verifier` + `reviewer` still decide.
5. Nothing active → `native` (the `implementer` agent), identical to the pre-delegation flow.
Rules: `skills/implement/references/coder-routing.md`.
