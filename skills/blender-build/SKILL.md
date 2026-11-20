---
name: blender-build
description: Blender step 3 - develop an approved prototype (art/<slug>/BRIEF.md status proto-approved) into the finished asset phase by phase (forms, detail, topology, UV, materials, rig, animation, presentation, export), each phase self-verified with renders, measurements and mesh checks and committed to Git; then hand the final review to the user and loop on their feedback until they accept it.
disable-model-invocation: true
argument-hint: <slug>
allowed-tools: Read Grep Glob Write Edit AskUserQuestion Bash(git *) Bash(ls *) Bash(mkdir *) Bash(bash *) Bash(python *) mcp__blender
---

Request: $ARGUMENTS

Kit and paths as in `${CLAUDE_SKILL_DIR}/../blender-proto/SKILL.md` (K, A, master, build/, review/). Read `${CLAUDE_SKILL_DIR}/../blender-proto/references/blender5.md` first.
Goal: the full asset, faithful to the approved prototype and brief, proven by numbers and renders, accepted by the user.

## 0. Load
- `$A/BRIEF.md` `status: proto-approved|building|review`, else stop ("Prima approva il prototipo con `/ba:blender-proto <slug>`").
- Read brief, references, `$A/review/proto-sil/`, latest review images. Open the master in Blender (dirty other file → ask). Run the user-edit check (proto step 1).
- `building` → resume at the first unticked phase of "Build plan"; `review` → step 3.

## 1. Plan
Pick phases from kind (drop what the brief excludes), write them as a checkbox list "Build plan" in the brief, `status: building`, print one line, proceed without asking:
- model-3d: forms → detail → topology + cleanup → UV → materials/textures → [rig + weights] → [animation] → presentation → export.
- modify-existing: apply the change fully → blend seams/cleanup → UV/material fixes → [re-rig/weights] → export.
- animation: breakdowns → spline (`BEZIER`) → polish (arcs, ease, overlap, follow-through) → loop check → bake/export.
- 2d: clean lines → fills/colour → shading/FX layers → timing → render/export.
- rig: deform bones → constraints/IK → weights (test poses) → controls/shape keys → test animation.
- environment: forms → detail/props → materials → lighting → cameras → export/render.

## 2. Each phase NN
- Build: code appended to `$A/build/NN-<phase>.py` first, then executed. Non-destructive until the export phase (keep modifiers live; apply only on export copies).
- Review: `bkit.shots("$A/review/NN-<phase>")` (`look="eevee"` from materials on; animation: `frames=` key poses + mid-breakdowns). Read every image, critique cold against brief, refs and approved proto.
- Gates (all must hold, numbers in the commit body):
  - drift: `bkit.compare("$A/review/proto-sil/<view>_sil.png", view, ...)` IoU ≥0.90 vs the approved proto (detail may add, not reshape); ortho refs IoU ≥0.90.
  - size: `bkit.measure()` within ±1% of the brief.
  - mesh: `bkit.checks()` - poly budget; no loose verts; non-manifold 0 for print/booleans; no ngons where it deforms; scale applied before rig/export; UVs before textures; no empty material slots.
  - animation: clip ranges as brief, loop clips first pose = last pose, no fcurve on unintended channels.
  - export: round-trip in a background Blender (`execute_blender_code_for_cli`): reimport, `measure()` within 1%, same object/bone/action counts.
- ≤3 fix rounds per phase; still failing → stop and ask the user, with numbers and the image paths.
- `bkit.save(master)` → commit `art(<slug>): build NN-<phase>` → tick the phase in the brief. Taste decisions that the brief does not settle → AskUserQuestion with concrete variants (recommended first), never guess.

## 3. Final review (`status: review`)
- Turntable: `bkit.shots("$A/review/final", views=[(a, 15) for a in range(0, 360, 45)], res=1024, look="eevee")`; animation: key frames of every clip; exports in `$A/export/`.
- Acceptance table from the brief: criterion | target | measured | ✔/✘. Focus Blender on the asset.
- Ask: "È ok? ('ok' per chiudere, oppure dimmi cosa cambiare)".

## 4. Feedback
- User-edit check first. Split into atomic requests; ambiguous → AskUserQuestion with variants.
- Map each request to the earliest affected phase, untick it and every later phase that depends on it, rerun from there (step 2), then step 3 again.
- "torna a <commit|fase>" → restore the master from git as in proto step 5.

## 5. Done ("ok", "va bene", "approvato")
- Brief `status: done`, Changelog line. Commit `art(<slug>): v<M> done`, `git tag <slug>-v<M>` (M = 1, then +1 for each later revision); if `origin` exists: `git push origin HEAD <slug>-v<M>`.
- Report ≤5 lines: master path, exports, tag, final images path.

Rules: never delete user objects or purge orphans; never lower a gate to pass; report a failing gate as failing.
