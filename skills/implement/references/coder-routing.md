# Coder routing (PM + optional external Pure Coder)

You (main AI) stay PM / tech lead and final checker. Code may be written by an external coder:
`colibri` (local OpenAI-compatible endpoint, `COLIBRI_API_BASE`, default `http://127.0.0.1:8000/v1`)
or `deepseek` (API, `DEEPSEEK_API_KEY`). `native` = agent `ba:implementer`, exactly as without this feature.
Never assume a coder is up: always detect.

## 1. Choose (once per run)
`coder=` in args wins. Else `bash $S/delegate-coder.sh --detect` (<1s):
```
colibri=UP|DOWN  deepseek=READY|MISSING_KEY  native=READY
pref=<saved> (ok|unavailable|none)  recommend=<x>  chain=<order>
```
- `pref` ok → use it, don't ask.
- `pref` unavailable → say which coder is down/missing, then ask (below).
- Interactive skills (`implement` run by the user, `ship`): ask ONE question, recommended first, only real options:
  - colibri UP + deepseek READY: `Auto (Colibri → DeepSeek) (Consigliato)` / `Solo Colibri` / `Solo DeepSeek` / `Nativo`
  - one up: `<that one> (Consigliato)` / `Nativo` / `Attiva/configura <the other> ora`
  - none: `Nativo (Consigliato)` / `Avvio Colibri ora e riprova` / `Configura DeepSeek API`
  Then ask: save for this repo (`python $S/coder.py save <x>` → `.ba/config.json`) or session only.
  "Avvio Colibri": user starts it, re-run detect. "Configura DeepSeek": user puts `DEEPSEEK_API_KEY=...`
  in `~/.ba/credentials.env` (or env var / repo `.env`), never in chat, never in `.ba/`; re-run detect.
- `auto` skill: never ask. Use `chain` from detect (arg > ok pref > recommend). Log choice + any warning in `.ba/auto.md`.
Final chain = `bash $S/delegate-coder.sh --detect --warm --coder <choice>` → `chain=`. Always ends in `native`.
`--warm` (chain starts with colibri) loads the local model + caches the system prompt in background while you write the brief.

## 2. Delegated attempt (chain head ≠ native)
1. Write `.ba/runs/<n>-brief.md`, ≤40 lines. The coder sees ONLY the brief + target files, so include:
   `Kind`, target impl files + test files, exact signatures/types it must create or call (paste the
   few lines of existing interfaces it depends on), acceptance checks → each one a test assertion,
   test framework/style to copy, traps (edge cases, things not to touch), `Test cmd` (filtered).
   Attempt k>1: append the `Why/Next` of the previous failure.
2. `bash $S/delegate-coder.sh --issue <n> --coder <head> --brief .ba/runs/<n>-brief.md --files "<impl,...>" --tests "<tests,...>" --test-cmd "<filtered cmd>"`
   (non-test kinds: omit `--tests/--test-cmd`; the verifier still runs the KIND proof). Run in the issue's worktree.
   The script retries ≤2 times internally with the error tail — no PM tokens spent.
3. Result (last line):
   - `PASS` → verifier + reviewer as usual, given only issue text, KIND, file lists, branch. Writer claims ignored.
   - `FAIL` → tree rolled back; counts as attempt k: write `Why/Evidence/Next` to `.ba/runs/<n>.md`,
     next attempt uses the next coder in chain (`colibri → deepseek → native`).
   - `CODER_UNAVAILABLE` → drop it from chain, log `coder switch: <from> → <to> (<reason>)` in
     `.ba/runs/<n>.md` (and `.ba/auto.md` in auto), retry the SAME attempt with the next coder. Never block on it.
4. Verifier/reviewer FAIL after a delegated PASS → same as FAIL (escalate).

## 3. Native attempt (chain head = native)
Agent `ba:implementer`, unchanged TDD flow.
