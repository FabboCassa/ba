---
name: blender-proto
description: Blender step 2 - from an approved art/<slug>/BRIEF.md build a base in the live Blender (blockout, bone exoskeleton, modification pass, animation blocking or 2D rough), self-check it from fixed angles and against the references, version every iteration in Git, and iterate with the user until they approve it. Next is /ba:blender-build.
disable-model-invocation: true
argument-hint: <slug>
allowed-tools: Read Grep Glob Write Edit AskUserQuestion Bash(git *) Bash(ls *) Bash(mkdir *) Bash(bash *) Bash(python *) mcp__blender
---

Request: $ARGUMENTS

Kit: `K=<absolute path of ${CLAUDE_SKILL_DIR}/../../scripts/blender>` (bkit: shots, compare, silhouette, measure, checks, snapshot, save). Read `${CLAUDE_SKILL_DIR}/references/blender5.md` first and follow it.
Paths (absolute when passed to Blender): `A=art/<slug>`, master `$A/<slug>.blend`, scripts `$A/build/`, review images `$A/review/`.
Goal: a base the user recognises as "their" asset, approved before any detail work.

## 0. Load
- `$A/BRIEF.md` with `status: brief|proto`, else stop: no brief → "Prima `/ba:blender-brief`"; `proto-approved` or later → "Prototipo già approvato: `/ba:blender-build <slug>`" (unless the user says "riapri").
- Read the whole brief and every image in `$A/ref/`.
- Blender: `get_blendfile_summary_path_info`. Not connected → ask the user to start Blender with the MCP add-on, stop. Another file open with `is_dirty` → ask before switching (their unsaved work).

## 1. Master file
- Missing → `wm.read_homefile(use_empty=True)`, units/fps/frame range from the brief, collections `<slug>` (work), `ref` (reference images as Image Empties, ortho refs aligned front/right at real scale, hidden in render), `_original` (modify-existing: imported source, hidden + unselectable, never edited). `bkit.save(master)`.
- Exists → open it if not open. **Detect user edits**: `bkit.snapshot()` vs `git show HEAD:$A/<slug>.scene.json`; differences = the user worked in Blender: list them in ≤3 lines and keep them (never revert user edits).

## 2. Build v<N>
By kind (brief "Prototype scope" wins):
- model-3d: blockout from primitives + light modifiers (mirror, subsurf ≤1, bevel) at real scale; one object per part, named as in Parts; a distinct flat colour per part (`diffuse_color` + Base Color); sensible origins; no detail.
- modify-existing: non-destructive on a working copy (modifiers, shape keys, lattice); `_original` untouched.
- rig / exoskeleton: armature with bones per brief, `.L/.R` names, aligned to mesh/refs, `show_in_front`; 2-3 test poses on markers.
- animation: blocking only: key poses, `CONSTANT` interpolation, a marker per pose, clip ranges; proxy shapes if the model is not ready.
- 2d: Grease Pencil v3, one layer per part, rough strokes for the design / key poses.
- environment: layout blockout + camera(s) from the brief.
Every code that changes the scene is first appended to `$A/build/proto-v<N>.py` (readable, reproducible history), then executed.

## 3. Self-check before showing (≤2 fix rounds)
- `bkit.shots("$A/review/proto-v<N>")` (animation: `frames=` the key poses). Read every image; critique cold against brief + refs.
- Ortho references → `bkit.compare(ref, view, "$A/review/proto-v<N>/cmp")`: target IoU ≥0.85, |aspect_err| ≤0.05; name mismatches with numbers ("testa 12% troppo larga", worst band). `bkit.measure()` vs brief size ±2%.
- Fix the worst mismatch first, one area per round.

## 4. Save + show
- `bkit.save(master)` → `git add $A` → commit `art(<slug>): proto v<N> - <short label>`. Brief `status: proto`.
- `jump_to_view3d_object_by_name` on the main object. Tell the user (≤5 lines): what is built, numbers (size, IoU), what to look at, review images path; "Puoi anche modificare tu in Blender e salvare (Ctrl+S): rispetto le tue modifiche."
- End with: "Cosa cambio? ('ok' per approvare, 'torna a vN' per tornare indietro)".

## 5. Iterate
- Each message: run the step 1 user-edit check first. Split into atomic requests; clear → do; taste-ambiguous ("più cattivo", "più morbido", "non mi convince") → AskUserQuestion with 2-3 concrete variants, recommended first; for shape choices build them side by side as collections `var-A/B/C` offset on X and let the user pick in Blender. Never guess on taste.
- "torna a vN" → `git log --oneline -- $A` → `git checkout <sha> -- $A/<slug>.blend $A/<slug>.scene.json` → reopen in Blender → commit `art(<slug>): revert to proto vN`.
- Whole direction rejected → update the brief (section + Changelog) with the user, then the next version.
- Each version → steps 2-4 with N+1 (older versions stay in git history).

## 6. Approve ("ok", "va bene", "approvato", "perfetto")
- Lock silhouettes for drift checks: `bkit.silhouette("$A/review/proto-sil/<view>_sil.png", view)` for front, right, top.
- Brief: `status: proto-approved`, `proto_version: v<N>`, Changelog line with the final numbers. Commit `art(<slug>): proto approved (v<N>)`, `git tag <slug>-proto`; if `origin` exists: `git push origin HEAD <slug>-proto`.
- Tell the user: next `/ba:blender-build <slug>`.

Rules: never delete or rename user objects (hide or move to `_trash` and say so); never purge orphans; only the master file is written.
