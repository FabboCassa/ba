---
name: design-apply
description: Apply an approved docs/design/<slug>/DESIGN.md to the codebase - "auto" everywhere, or only the given paths/globs/screens, or "issues" to route it through the ba flow. Token layer first, behavior preserved, gate + design-lint per batch.
disable-model-invocation: true
argument-hint: <slug|DESIGN.md> [auto | <path|glob|screen>... | issues]
allowed-tools: Read Grep Glob Write Edit AskUserQuestion Agent Bash(git *) Bash(gh *) Bash(ls *) Bash(python *) Bash(python3 *) Bash(bash *) Bash(npm *) Bash(npx *) Bash(pnpm *) Bash(yarn *) Bash(dotnet *)
---

Request: $ARGUMENTS

Scripts: `S=${CLAUDE_SKILL_DIR}/../../scripts`.

## 0. Load
- Resolve `docs/design/<slug>/DESIGN.md` (or the given path). `status` must be `approved`, else stop: "Prima approva il design con `/ba:design <slug>`".
- Mode = 2nd arg: `auto` | paths/globs/screen names | `issues`. Missing → AskUserQuestion: "auto (Consigliato)", "solo alcune parti", "come issue".
- Read DESIGN.md fully and the final prototype (`prototype:`): the prototype's component sheet is the visual reference.

## 1. Context (silent)
`bash $S/detect.sh .`; find the styling system and its single entry point:
Tailwind (`tailwind.config.*` or CSS `@theme`), shadcn/`globals.css` vars, plain CSS/SCSS vars, CSS-in-JS theme (styled-components/emotion/MUI/Chakra/Mantine), Bootstrap vars, Angular Material, Razor/Blazor (`wwwroot/css`), XAML/MAUI ResourceDictionary, Flutter ThemeData, Compose/SwiftUI theme.
Branch: on the default branch → `git switch -c design/<slug>`.
Baseline: count hard-coded style literals in UI files (hex/rgb/hsl, Tailwind palette classes like `bg-blue-500`, font-family, px radius/shadow) → `before=N`. If a dev server can run and a browser tool is available, screenshot the main screens at 390/1440 into `.ba/design/<slug>/before/`.

## 2. Token layer (always, first commit)
Map every DESIGN.md token into the entry point found in step 1 (CSS custom properties + framework config pointing to them; never two sources of truth). Load fonts the project's way (`next/font`, `<link>`, `@font-face` self-hosted). Dark mode if defined. Global `prefers-reduced-motion` rule + motion tokens. Focus-visible style.
No component edits in this commit. `bash $S/gate.sh . --tier fast` → commit `style(design): <slug> tokens`.

## 3. Scope
- `auto`: inventory every UI surface (Glob components/pages/templates/views; Grep the literals from step 1, animation libs, icon sets). Order: primitives (button, input, select, link, badge, card/list item, modal, toast, table) → shell (header, nav/sidebar, footer) → screens by importance. Write the checklist `.ba/design/<slug>-apply.md` (file → change), print one summary line, proceed without asking.
- Paths/globs/screens: only those (a screen name → resolve its route to files with Grep). Shared primitives they use are restyled only if the user listed them; otherwise style locally via tokens.
- `issues`: write `docs/specs/design-<slug>.md` (`Status: approved`, one requirement per batch from the inventory, acceptance = lint 0 errors + gate green + matches prototype sheet), then stop: "next `/ba:issues docs/specs/design-<slug>.md`" (or `/ba:auto`).

## 4. Apply, batch by batch (≤ ~8 files per batch)
- Replace literals with tokens; adopt the type scale, radius-by-hierarchy, surfaces, component rules, Voice verbs for labels only where DESIGN.md says so.
- Motion only as DESIGN.md "Motion" defines: the focal moment on its own screen, feedback on controls, continuity where listed. Nothing else animates.
- Preserve behavior: no changes to logic, handlers, props/API, routes, data, a11y attributes, test ids, user-facing text (unless DESIGN.md Voice explicitly renames an action and the user approved it).
- No new runtime dependency without asking (font packages excepted).
- Large `auto` runs: optionally delegate a batch to the `implementer` agent with the checklist slice; you stay the checker.

Per batch verify, then commit `style(design): apply <slug> to <batch>`:
1. `bash $S/gate.sh . --tier fast` green. Snapshot/visual tests failing only on visuals → update snapshots and say so; behavior tests failing → fix the code, never the test.
2. `python $S/design-lint.py <changed files>` → 0 errors (waivers only if listed in DESIGN.md "Deliberate exceptions").
3. Literal count of the batch files does not increase.

## 5. Finish
- `bash $S/gate.sh . --tier full`. `ba:reviewer` on `git diff <base>...HEAD` (blocking: behavior changes, scope creep).
- If screenshots were taken: retake into `.ba/design/<slug>/after/` and compare with prototype; fix gaps that are clearly off-spec.
- Report (≤6 lines): mode, files changed, literals before→after (+ leftovers with reason), lint result, gate result with command, branch. Ask before pushing / opening a PR.
