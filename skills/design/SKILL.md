---
name: design
description: Interview the user until a visual direction is clear, deal 3 distinct non-generic directions, build an HTML prototype, iterate on feedback until approved, then lock docs/design/<slug>/DESIGN.md. Apply it later with /ba:design-apply.
disable-model-invocation: true
argument-hint: <what to design> | <slug to resume>
allowed-tools: Read Grep Glob Write Edit AskUserQuestion WebSearch WebFetch Bash(git *) Bash(ls *) Bash(python *) Bash(python3 *) Bash(bash *)
---

Request: $ARGUMENTS

Scripts: `S=${CLAUDE_SKILL_DIR}/../../scripts`. Read `${CLAUDE_SKILL_DIR}/references/anti-slop.md` before step 3.
Output: `docs/design/<slug>/` = `brief.md`, `proto-v<N>.html` (all kept), `DESIGN.md` (from `${CLAUDE_SKILL_DIR}/../../templates/design.md`).
Goal: a design that could not be mistaken for any other project and does not read as AI-made, approved by the user.

## 0. Resume or start
- `$ARGUMENTS` is an existing slug, or empty and a `docs/design/*/DESIGN.md` has `status: exploring` → resume at step 5 from the latest proto.
- Context (silent, cheap): top-level `ls`, README head, `bash $S/detect.sh .`, existing styling (tailwind config, CSS vars, theme files, fonts, logo, `DESIGN.md`), `.ba/design/history.json`. Don't ask what you can read.

## 1. Interview (AskUserQuestion, ≤4 questions/round, user's language)
Every question: recommended option first labelled "(Consigliato)", grounded in context; options concrete (named palettes, real fonts, real sites) not abstract adjectives. Order:
1. Subject & job: what it is, who uses it, the ONE thing a visitor/user must do. New design or redesign of existing UI.
2. Personality: 3 adjectives + 1 anti-adjective ("never ..."); sites/apps they love and hate (ask for links; WebFetch them if given and note what to take, not copy).
3. Constraints: fixed brand colours/logo/fonts, light/dark/both, accessibility level, target stack, real content and images available.
4. Appetite: how bold (quiet → loud), motion budget (none / feedback only / one signature moment / expressive), density.
5. Prototype scope: which screen first (recommend the most characteristic one).
Loop until every field of `brief.md` is filled; no "TBD". Write `brief.md` (English, 15-30 lines) with mood tags from the catalog vocabulary (`python $S/design-deal.py list`).

## 2. Deal 3 directions
`python $S/design-deal.py deal --n 3 --mood <tags>` → 3 combos that share no palette/type/layout/motion/surface item and skip the last projects' choices; the 3rd is a wildcard outside the mood.
For each, adapt (never copy blindly) to the subject and write: name, one-line thesis tied to the subject, 6 hex tokens (respect brand constraints; check AA contrast ink/bg, accent/bg), type pair + one treatment, ASCII wireframe of the key screen, motion thesis (focal moment + feedback), the ONE bold thing.
Self-check each against anti-slop.md ("would I produce this for any similar brief?") and revise what repeats.
Present with AskUserQuestion, one option per direction, `preview` = ASCII wireframe + palette + fonts. Allow "mix" (Other) and "redeal" (rerun with a new `--seed`).

## 3. Prototype v1
One self-contained `proto-v1.html`: CSS custom properties = the tokens, Google Fonts link ok, vanilla JS only, real content from the brief (no lorem, no invented facts/metrics/logos).
Contains: the key screen + a **component sheet** section (buttons all states, inputs + error, list/card, nav, empty state, toast) + light/dark if requested.
Floor: AA contrast, visible focus, `prefers-reduced-motion`, works at 390/768/1440, line length < 80ch.
Build the one signature element first, then the rest quiet.

## 4. Verify before showing
- `python $S/design-lint.py docs/design/<slug>/proto-v<N>.html` → 0 errors; each warning removed or justified in DESIGN.md "Deliberate exceptions".
- If a browser tool is available (built-in browser `preview_start` with the file URL, or Chrome): screenshot at 390 and 1440, critique cold (hierarchy, the one bold thing visible, nothing generic), fix, then remove one accessory.
- Show the user: path, 4 lines (direction, bold thing, motion, what to look at), then "Cosa cambio? (o 'va bene' per approvare)". Open it in the browser pane if available.

## 5. Iterate
On each feedback message:
- Split into atomic requests. Clear ones → do. Ambiguous ones ("più moderno", "più vivace", "non mi convince") → AskUserQuestion with 2-3 concrete variants (preview: hex/fonts/ASCII), recommended first. Never guess on taste.
- Write `proto-v<N+1>.html` (never overwrite older versions), append to DESIGN.md Changelog, rerun step 4.
- If feedback rejects the whole direction → back to step 2 with a new seed, excluding the rejected ids.
- Keep DESIGN.md (`status: exploring`) in sync with the latest proto at each version.

## 6. Lock (user says "va bene" / "ok" / "approvato" / "perfetto")
- Finalize DESIGN.md: tokens = exactly what the last proto uses; every section filled; `status: approved`; `prototype:` → final version.
- `python $S/design-deal.py record <slug> --palette .. --type .. --layout .. --motion .. --surface ..` (ids of the base combo) so future projects avoid it.
- Tell the user: path + next step `/ba:design-apply <slug> auto` (everywhere) or `/ba:design-apply <slug> <path|glob|screen>` (only there).

Rules: don't touch app source code here (prototype files only). Brief/DESIGN.md in English, conversation in the user's language. Tokens are the single source of truth: no hex/font in the prototype outside `:root` vars.
