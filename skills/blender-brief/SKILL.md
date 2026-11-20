---
name: blender-brief
description: Blender step 1 - interview the user about the asset they want (3D model, change to an existing model, 2D Grease Pencil, animation, rig, environment), analyse their reference images, set up Git + LFS versioning, and lock art/<slug>/BRIEF.md. Next is /ba:blender-proto.
disable-model-invocation: true
argument-hint: <what you want | slug to resume>
allowed-tools: Read Grep Glob Write Edit AskUserQuestion WebSearch WebFetch Bash(git *) Bash(gh *) Bash(ls *) Bash(cp *) Bash(mkdir *) Bash(bash *) Bash(python *) mcp__blender
---

Request: $ARGUMENTS

Scripts: `S=${CLAUDE_SKILL_DIR}/../../scripts`. Template: `${CLAUDE_SKILL_DIR}/../../templates/blender-brief.md`. Read `${CLAUDE_SKILL_DIR}/../blender-proto/references/blender5.md` once.
Output: `art/<slug>/BRIEF.md`, references in `art/<slug>/ref/`. Brief in English, conversation in the user's language.
Goal: a brief so precise that the prototype matches what the user pictures on the first try. Never start building here.

## 0. Resume or start
- `$ARGUMENTS` is an existing slug, or empty and one `art/*/BRIEF.md` has `status: brief` → resume: show the open/INFERRED points and continue at step 2.
- Context (silent): `bash $S/blender-vc.sh status .`; `mcp__blender__get_blendfile_summary_path_info` (fails → tell the user to open Blender with the MCP add-on connected, then continue: the interview does not need it). Blender version → `bpy.app.version_string`.
- Slug: short kebab-case from the subject; confirm it in the first question round.

## 1. Inputs
- **Reference images**: local paths → copy to `art/<slug>/ref/NN-<name>.<ext>`. URLs → look with WebFetch; download into `ref/` only after asking (filename + source). Images pasted in chat are not on disk → ask the user to save them into `art/<slug>/ref/` (give the absolute path).
- **Existing model to modify** (.blend/.fbx/.glb/.obj): inspect, don't ask: `get_blendfile_summary_datablocks_for_cli`, or `execute_blender_code_for_cli` importing it into an empty scene and returning `bkit.snapshot()` + `bkit.measure()` (kit load line in blender5.md). Record objects, dimensions, rig, actions, materials.
- **Analyse every reference** (Read the image): view (front/side/3-4/top), orthographic sheet or perspective (estimate lens: phone photo 24-35 mm), what it defines (silhouette, proportions, colour, detail, pose, timing), what to ignore, conflicts between references. Fill the References table.

## 2. Interview (AskUserQuestion, ≤4 questions/round)
Every question: recommended option first with "(Consigliato)", grounded in context and references; options concrete (a named style with a well-known example, real numbers, real engines), never abstract adjectives. Rounds in order, skipping what is already known:
1. **Kind + purpose**: model-3d / modify-existing / 2d / animation / rig / environment (multi-select); target: game engine (which), still render, animation film, 3D print, web (GLB), concept only.
2. **Style**: family (stylized hand-painted, low-poly flat, toon + outline, realistic PBR, clay, voxel, 2D cel line art...), 3 adjectives + 1 "never ...", palette/material language. Propose what the references suggest.
3. **Form**: real-world size (look it up with WebSearch, cite it; never guess), proportions to respect, parts list big → small, silhouette features that must read, symmetry, hard-surface vs organic.
4. **Kind-specific**:
   - modify-existing: what changes, what must stay identical, may we be destructive (default no: modifiers, shape keys, working copy).
   - 2d: pure 2D or 2.5D, line weight and taper, fills, frame aspect, on 1s or 2s.
   - animation: clip list (name, frames @fps, loop, key poses), root motion, timing feel with a known reference ("snappy like ...", "floaty like ..."), rig exists or must be made.
   - rig: deformation needs, controls (simple FK/IK vs Rigify), face (shape keys/bones).
5. **Technical**: poly budget, topology needs, UVs/textures (resolution, procedural vs painted), export formats, naming.
6. **Prototype scope**: propose what the base will be (blockout / exoskeleton of bones / modification pass / animation blocking / 2D rough) and what it excludes.
Loop until every template section is filled: no "TBD". Anything assumed → **Inferred** section; show it and let the user confirm or correct.
For each reference, state in one line what you take and what you ignore ("Da 02 prendo silhouette e proporzioni, ignoro i colori") inside the confirmation round.

## 3. Version control
- Not a git repo → AskUserQuestion: "git + repo GitHub privato (Consigliato)", "solo git locale", "nessun versioning". Then `git init`; GitHub → `gh repo create <folder-name> --private --source . --remote origin` (name confirmed in the same question).
- Git repo → `bash $S/blender-vc.sh init .` (LFS for .blend, exports, textures and `art/**` images; `.blend1` backups ignored). Exit 3 → give the git-lfs install link and stop until installed. Warnings about .blend committed outside LFS → show them, never rewrite history without an explicit yes.

## 4. Lock
- Write `art/<slug>/BRIEF.md` from the template, `status: brief`, every section filled, Changelog `v1 brief`.
- Show ≤8 lines (kind, style, size, parts, prototype scope, acceptance) + "Confermi il brief? (o dimmi cosa cambiare)".
- On yes: `git add art/<slug> .gitattributes .gitignore` → commit `art(<slug>): brief`. Tell the user: next `/ba:blender-proto <slug>`.

Rules: no Blender scene changes in this skill (inspection only, background for external files). Never invent facts about references; ask.
