# GEMINI.md — BetterAI (ba) Guidelines for Gemini & Antigravity

This repository uses **ba (BetterAI)**: token-efficient, verified software development with strict verification gates and real proofs.

## Core Rules for Gemini & Antigravity
1. **Terse Responses**: Follow `templates/terse-rules.md` (single source for output and comment rules).

2. **Writer vs Checker Separation**:
   - **Writer (`implementer`)**:
     - Writes the test first (RED), then the minimal implementation (GREEN).
     - For refactoring or performance, maintains all existing tests without weakening assertions.
   - **Checker (`verifier`)**:
     - Never takes "tests pass" on faith.
     - Runs `bash scripts/prove-test.sh "<test-cmd>" <test-files...>` to confirm the tests fail with implementation reverted (RED) and pass with implementation applied (GREEN).
     - Runs `bash scripts/gate.sh .` to guarantee full build, lint, and test pass.

3. **Deterministic Verification Commands**:
   - Stack Detection: `bash scripts/detect.sh .`
   - Full Gate (Build + Lint + Test): `bash scripts/gate.sh .`
   - Real Test Proof: `bash scripts/prove-test.sh "<test-cmd>" <test-files...>`
   - Refactor / Perf Proof: `bash scripts/prove-refactor.sh origin/main <kind>`
   - Security Audit: `bash scripts/sec-scan.sh secrets` / `code` / `deps`
   - Secret Guard: `bash scripts/secret-guard.sh`
   - Test Times: `bash scripts/test-times.sh --slow 60`

4. **Safety & Zero Leaks**:
   - Never commit `.env`, keys, credentials, or secrets.
   - Never rewrite git history or force-push without explicit user request.
