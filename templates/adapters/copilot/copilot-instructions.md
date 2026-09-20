# GitHub Copilot Instructions for BetterAI (ba)

## Philosophy
- Deliver concise, verifiable solutions with zero fluff.
- Adhere to Test-Driven Development (TDD).

## Key Verification Commands
- `bash scripts/gate.sh .` — Build, lint, and full test suite execution.
- `bash scripts/prove-test.sh "<test-cmd>" <test-files...>` — Verify test validity via red/green rollback.
- `bash scripts/sec-scan.sh secrets` — Secret leak scan.

## Coding Standards
- Minimal, clean diffs.
- Only comment non-obvious rationale (WHY), never trivial mechanics (WHAT).
- Never commit secrets or hardcoded test credentials.
