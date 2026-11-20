# Blender 5.x via MCP — working rules and pitfalls

Verified on Blender 5.3 + Blender Lab MCP (`mcp__blender__*`). Check `bpy.app.version_string` first; on older versions verify with `get_python_api_docs` before trusting this file.

## Session
- Load the kit at the top of every `execute_blender_code` call that uses it:
  `import sys, importlib; K=r"<abs scripts/blender>"; sys.path.insert(0, K) if K not in sys.path else None; import bkit; importlib.reload(bkit)`
- Assign a JSON-serialisable dict to `result`; never rely on `print`.
- Absolute paths only (Blender's cwd is not the project). bkit raises on relative paths.
- `wm.open_mainfile` / `wm.read_homefile` keep the MCP connection alive: reverting a version = open the restored file.
- Before opening another file: `get_blendfile_summary_path_info`; if `is_dirty` and it is not our master, ask the user (unsaved work).
- Prefer specific MCP tools (`get_objects_summary`, `get_object_detail_summary`, `jump_to_view3d_object_by_name`) over code for reading.

## Context and modes
- Operators depend on mode, active object and selection: set all three explicitly before each operator; operators change them as a side effect.
- Viewport operators (`view3d.*`) need a VIEW_3D area: `with bpy.context.temp_override(area=a, region=r): ...` where `a` comes from `bpy.context.screen.areas`.
- Edit mode geometry: use `bmesh.from_edit_mesh` + `bmesh.update_edit_mesh`; otherwise `bm.from_mesh` / `bm.to_mesh` + `mesh.update()`.
- Read computed values (world matrix, modifier result) only after `bpy.context.view_layer.update()` or via `evaluated_depsgraph_get()`.

## Data
- Shared data: check `ob.data.users > 1` before editing a mesh; `ob.data = ob.data.copy()` to make single-user.
- Never `bpy.ops.outliner.orphans_purge()` without asking: it deletes unassigned materials/actions the user may want.
- Never delete user objects; hide or move to a `_trash` collection and tell the user.
- Units: default metric, 1 unit = 1 m. Model at real scale; look up real dimensions, don't guess.
- Apply rotation/scale (`object.transform_apply`) before rigging, booleans driven by scale, and export.

## Animation (5.x layered actions)
- `Action.fcurves` no longer exists. Use `from bpy_extras import anim_utils; cb = anim_utils.action_get_channelbag_for_slot(ob.animation_data.action, ob.animation_data.action_slot)` → `cb.fcurves`.
- `ob.keyframe_insert("location", frame=N)` still works and creates the layered action + slot.
- Blocking: set keyframe interpolation `CONSTANT` (stepped); splining: `BEZIER`. Name clips `<slug>_<clip>` and mark key poses with `scene.timeline_markers.new(name, frame=N)`.
- One action per clip; keep clips in NLA tracks or as fake-user actions (`action.use_fake_user = True`) so they survive save.

## Grease Pencil (2D) — v3 API
- Object type `GREASEPENCIL`, data `bpy.data.grease_pencils.new(name)` (not the legacy `gpencil` API).
- Stroke: `layer = gp.layers.new("Lines"); dr = layer.frames.new(frame).drawing; dr.add_strokes([n_points]); dr.strokes[i].points[j].position = (x, y, z)`.
- Draw on the XZ plane (front view) unless the brief says otherwise; one layer per part (lines, fill, shading, FX).

## Rendering and review
- Engines: `BLENDER_WORKBENCH`, `BLENDER_EEVEE`, `CYCLES` (`BLENDER_EEVEE_NEXT` is gone).
- `bkit.shots` uses workbench + material viewport colour: set `mat.diffuse_color` as well as the Principled Base Color so blockout colours show.
- The viewport is not evidence: judge from `bkit.shots` / `bkit.compare` output read back with the Read tool.
- Elongated objects: add a view along the long axis; thin objects can vanish in an edge-on view.
- Cannot render without a camera: bkit adds a temporary one; final turntables need a real camera in the file.

## Export
- glTF/GLB: `bpy.ops.export_scene.gltf(filepath=..., export_format='GLB', use_selection=True)`; Y-up conversion is on by default.
- FBX (Unity/Unreal): `bpy.ops.export_scene.fbx(filepath=..., use_selection=True, apply_scale_options='FBX_SCALE_ALL', bake_anim=True)`.
- Round-trip every export: import into a fresh scene (`wm.read_homefile(use_empty=True)` in a background run via `execute_blender_code_for_cli`) and compare `bkit.measure()` within 1%.
