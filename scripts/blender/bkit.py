"""BetterAI Blender kit. Runs inside Blender (bpy), live via MCP or `blender --background`.

Load in MCP execute_blender_code:
    import sys, importlib; sys.path.insert(0, r"<abs path to scripts/blender>")
    import bkit; importlib.reload(bkit)
    result = bkit.shots(r"<abs out dir>")
All paths must be absolute: Blender's cwd is not the project.
"""
import json
import math
import os

import bpy
import numpy as np
from mathutils import Vector

GEOM = {"MESH", "CURVE", "SURFACE", "META", "FONT", "CURVES", "GREASEPENCIL", "POINTCLOUD", "VOLUME"}
# (azimuth, elevation) in degrees; az 0 = Blender Front view (camera on -Y looking +Y), az 90 = Right (+X).
VIEWS = {
    "front": (0, 0), "right": (90, 0), "back": (180, 0), "left": (270, 0), "top": (0, 90),
    "persp": (35, 22), "back34": (215, 22),
}
DEFAULT_VIEWS = ("front", "right", "persp", "back34", "top")
_SHADING = ("light", "color_type", "single_color", "show_object_outline", "show_cavity", "studio_light")


def _r(v, n=4):
    return [round(float(x), n) for x in v]


def _abs(path):
    if not os.path.isabs(path):
        raise ValueError(f"absolute path required, got {path!r}")
    return path


def _targets(names=None):
    if names:
        return [bpy.data.objects[n] for n in names]
    return [o for o in bpy.context.scene.objects if o.type in GEOM and not o.hide_render and o.visible_get()]


def bounds(names=None):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in _targets(names):
        oe = o.evaluated_get(dg)
        pts += [oe.matrix_world @ Vector(c) for c in oe.bound_box]
    if not pts:
        raise ValueError("no visible renderable geometry")
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return lo, hi


def measure(names=None):
    """World-space size of the given objects (default: all visible geometry), in scene units."""
    lo, hi = bounds(names)
    us = bpy.context.scene.unit_settings
    return {"min": _r(lo), "max": _r(hi), "size": _r(hi - lo), "unit": us.system, "scale_length": us.scale_length}


class _Stage:
    """Temporary camera + render settings; everything is restored on exit."""

    def __init__(self, names, res, ortho, look, transparent=False):
        self.names, self.res, self.ortho, self.look, self.transparent = names, res, ortho, look, transparent

    def __enter__(self):
        sc = bpy.context.scene
        r, sh = sc.render, sc.display.shading
        self.saved = {
            "camera": sc.camera, "frame": sc.frame_current, "engine": r.engine, "rx": r.resolution_x,
            "ry": r.resolution_y, "pct": r.resolution_percentage, "fp": r.filepath, "transp": r.film_transparent,
            "fmt": r.image_settings.file_format, "cm": r.image_settings.color_mode,
            # single_color is a live bpy array: copy it or the restore writes back the modified value
            "shading": {k: tuple(getattr(sh, k)) if k == "single_color" else getattr(sh, k) for k in _SHADING},
        }
        self.lo, self.hi = bounds(self.names)
        self.hidden = []
        if self.names:
            keep = set(self.names)
            for o in sc.objects:
                if o.type in GEOM and o.name not in keep and not o.hide_render:
                    o.hide_render = True
                    self.hidden.append(o)
        cam_data = bpy.data.cameras.new("_ba_cam")
        self.cam = bpy.data.objects.new("_ba_cam", cam_data)
        sc.collection.objects.link(self.cam)
        sc.camera = self.cam
        r.resolution_x = r.resolution_y = self.res
        r.resolution_percentage = 100
        r.image_settings.file_format = "PNG"
        r.image_settings.color_mode = "RGBA"
        r.film_transparent = self.transparent
        if self.look == "eevee":
            r.engine = "BLENDER_EEVEE"
        else:
            r.engine = "BLENDER_WORKBENCH"
            sh.light, sh.color_type = "STUDIO", "MATERIAL"
            sh.show_object_outline, sh.show_cavity = True, True
        return self

    def aim(self, view):
        az, el = VIEWS[view] if isinstance(view, str) else view
        az, el = math.radians(az), math.radians(min(el, 89.9))
        center = (self.lo + self.hi) / 2
        radius = max((self.hi - self.lo).length / 2, 1e-3)
        cam = self.cam.data
        if self.ortho:
            cam.type, cam.ortho_scale = "ORTHO", radius * 2.1
            dist = radius * 3
        else:
            cam.type, cam.lens, cam.sensor_width = "PERSP", 50, 36
            dist = radius / math.sin(math.atan(18 / 50)) * 1.08
        d = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
        self.cam.location = center + d * dist
        self.cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        cam.clip_start, cam.clip_end = dist / 1000, dist + radius * 4

    def render(self, path):
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        return path

    def __exit__(self, *exc):
        sc = bpy.context.scene
        r, sh, s = sc.render, sc.display.shading, self.saved
        cam_data = self.cam.data
        bpy.data.objects.remove(self.cam)
        bpy.data.cameras.remove(cam_data)
        for o in self.hidden:
            o.hide_render = False
        sc.camera = s["camera"]
        sc.frame_set(s["frame"])
        r.engine, r.resolution_x, r.resolution_y = s["engine"], s["rx"], s["ry"]
        r.resolution_percentage, r.filepath, r.film_transparent = s["pct"], s["fp"], s["transp"]
        r.image_settings.file_format, r.image_settings.color_mode = s["fmt"], s["cm"]
        for k, v in s["shading"].items():
            setattr(sh, k, v)
        return False


def shots(out_dir, views=DEFAULT_VIEWS, res=768, names=None, frames=None, ortho=False, look="solid"):
    """Render review images from a fixed set of angles. look: "solid" (workbench) | "eevee".
    frames: list of frame numbers for animation review (one image per view per frame)."""
    os.makedirs(_abs(out_dir), exist_ok=True)
    out = []
    with _Stage(names, res, ortho, look) as st:
        for f in frames or [None]:
            if f is not None:
                bpy.context.scene.frame_set(f)
            for v in views:
                st.aim(v)
                tag = v if isinstance(v, str) else f"az{v[0]}_el{v[1]}"
                name = f"{tag}.png" if f is None else f"f{f:04d}_{tag}.png"
                out.append(st.render(os.path.join(out_dir, name)))
    return out


def silhouette(path, view="front", res=512, names=None):
    """Orthographic black-on-transparent silhouette, for comparing against a reference."""
    with _Stage(names, res, True, "solid", transparent=True) as st:
        sh = bpy.context.scene.display.shading
        sh.light, sh.color_type, sh.single_color = "FLAT", "SINGLE", (0, 0, 0)
        sh.show_object_outline, sh.show_cavity = False, False
        st.aim(view)
        return st.render(_abs(path))


def _pixels(path):
    img = bpy.data.images.load(_abs(path), check_existing=False)
    try:
        w, h = img.size
        a = np.empty(w * h * img.channels, np.float32)
        img.pixels.foreach_get(a)
        a = a.reshape(h, w, img.channels)
    finally:
        bpy.data.images.remove(img)
    if a.shape[2] == 3:
        a = np.concatenate([a, np.ones((h, w, 1), np.float32)], axis=2)
    return a[::-1]  # Blender stores bottom row first; row 0 = top from here on


def mask(px, tol=0.15):
    """Foreground mask: alpha if the image has transparency, else distance from the corner background."""
    if px[..., 3].min() < 0.5:
        return px[..., 3] > 0.5
    lum = px[..., :3].mean(-1)
    k = max(2, min(lum.shape) // 64)
    corners = np.concatenate([lum[:k, :k].ravel(), lum[:k, -k:].ravel(), lum[-k:, :k].ravel(), lum[-k:, -k:].ravel()])
    return np.abs(lum - np.median(corners)) > tol


def _normalize(m, n=128):
    ys, xs = np.nonzero(m)
    if not len(ys):
        raise ValueError("empty silhouette")
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    crop = m[y0:y1, x0:x1]
    ri = (np.arange(n) * crop.shape[0] / n).astype(int)
    ci = (np.arange(n) * crop.shape[1] / n).astype(int)
    return crop[ri][:, ci], (y1 - y0) / (x1 - x0)


def metrics(ref_mask, model_mask, bands=10):
    """Bbox-normalised IoU + aspect + per-band width. Bbox alignment hides absolute scale/offset:
    check real size with measure()."""
    a, ar = _normalize(ref_mask)
    b, br = _normalize(model_mask)
    iou = float((a & b).sum() / max((a | b).sum(), 1))
    rows = np.array_split(np.arange(a.shape[0]), bands)
    wa = [round(float(a[r].mean()), 3) for r in rows]
    wb = [round(float(b[r].mean()), 3) for r in rows]
    err = [round(y - x, 3) for x, y in zip(wa, wb)]
    worst = int(np.argmax(np.abs(err)))
    return {
        "iou": round(iou, 3), "aspect_ref": round(float(ar), 3), "aspect_model": round(float(br), 3),
        "aspect_err": round(float(br / ar - 1), 3), "band_width_ref": wa, "band_width_model": wb,
        "band_err": err, "worst_band": worst, "worst_band_err": err[worst],
    }


def _save_overlay(ref_m, mod_m, path):
    a, _ = _normalize(ref_m, 256)
    b, _ = _normalize(mod_m, 256)
    rgba = np.ones((256, 256, 4), np.float32)
    rgba[a & ~b, :3] = (0.9, 0.2, 0.2)
    rgba[b & ~a, :3] = (0.2, 0.3, 0.9)
    rgba[a & b, :3] = (0.35, 0.35, 0.35)
    img = bpy.data.images.new("_ba_overlay", 256, 256, alpha=True)
    try:
        img.pixels.foreach_set(rgba[::-1].ravel())
        img.filepath_raw, img.file_format = path, "PNG"
        img.save()
    finally:
        bpy.data.images.remove(img)
    return path


def compare(ref_path, view, out_dir, names=None, res=512):
    """Render the model silhouette from `view` and measure it against a reference image
    (orthographic sheet or clean-background photo). Writes <view>_sil.png and <view>_overlay.png
    (grey = match, red = only in reference, blue = only in model). band 0 = top."""
    os.makedirs(_abs(out_dir), exist_ok=True)
    tag = view if isinstance(view, str) else f"az{view[0]}_el{view[1]}"
    sil = silhouette(os.path.join(out_dir, f"{tag}_sil.png"), view, res, names)
    ref_m, mod_m = mask(_pixels(ref_path)), mask(_pixels(sil))
    m = metrics(ref_m, mod_m)
    m["overlay"] = _save_overlay(ref_m, mod_m, os.path.join(out_dir, f"{tag}_overlay.png"))
    m["view"] = tag
    return m


def checks(names=None):
    """Mesh health per object: tris, ngons, non-manifold edges, loose verts, unapplied scale, UVs, empty slots."""
    import bmesh
    out = {}
    for o in [o for o in _targets(names) if o.type == "MESH"]:
        bm = bmesh.new()
        try:
            bm.from_mesh(o.data)
            out[o.name] = {
                "tris": sum(len(f.verts) - 2 for f in bm.faces),
                "ngons": sum(1 for f in bm.faces if len(f.verts) > 4),
                "non_manifold_edges": sum(1 for e in bm.edges if not e.is_manifold),
                "loose_verts": sum(1 for v in bm.verts if not v.link_edges),
                "unapplied_scale": any(abs(s - 1) > 1e-4 for s in o.scale),
                "uv_layers": [u.name for u in o.data.uv_layers],
                "empty_material_slots": sum(1 for s in o.material_slots if s.material is None),
                "modifiers": [m.type for m in o.modifiers],
            }
        finally:
            bm.free()
    return out


def _fcurve_count(action):
    n = 0
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for cb in getattr(strip, "channelbags", []):
                n += len(cb.fcurves)
    return n


def snapshot(path=None):
    """Deterministic, text-diffable summary of the open file (committed next to the .blend)."""
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    objects = {}
    for o in sorted(sc.objects, key=lambda o: o.name):
        rot = o.rotation_quaternion if o.rotation_mode == "QUATERNION" else o.rotation_euler
        d = {
            "type": o.type, "parent": o.parent.name if o.parent else None,
            "collections": sorted(c.name for c in o.users_collection),
            "loc": _r(o.location), "rot": _r(rot), "rot_mode": o.rotation_mode, "scale": _r(o.scale),
            "dims": _r(o.dimensions), "hide_viewport": o.hide_viewport, "hide_render": o.hide_render,
            "modifiers": [f"{m.type}:{m.name}" for m in o.modifiers],
            "constraints": [f"{c.type}:{c.name}" for c in o.constraints],
            "materials": [s.material.name if s.material else None for s in o.material_slots],
        }
        if o.type == "MESH":
            me, ev = o.data, o.evaluated_get(dg).data
            d["mesh"] = {
                "verts": len(me.vertices), "faces": len(me.polygons),
                "eval_tris": sum(len(p.vertices) - 2 for p in ev.polygons),
                "uv_layers": [u.name for u in me.uv_layers],
                "shape_keys": [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],
                "vertex_groups": len(o.vertex_groups),
            }
        elif o.type == "ARMATURE":
            d["bones"] = sorted(b.name for b in o.data.bones)
        elif o.type == "GREASEPENCIL":
            d["layers"] = {l.name: len(l.frames) for l in o.data.layers}
        if o.animation_data and o.animation_data.action:
            d["action"] = o.animation_data.action.name
        objects[o.name] = d
    data = {
        "file": os.path.basename(bpy.data.filepath),
        "blender": bpy.app.version_string,
        "scene": {
            "name": sc.name, "unit": sc.unit_settings.system, "scale_length": sc.unit_settings.scale_length,
            "fps": sc.render.fps, "frames": [sc.frame_start, sc.frame_end], "engine": sc.render.engine,
            "camera": sc.camera.name if sc.camera else None,
        },
        "collections": {c.name: sorted(ch.name for ch in c.children) for c in bpy.data.collections},
        "objects": objects,
        "materials": {
            m.name: {"users": m.users, "nodes": sorted(n.bl_idname for n in m.node_tree.nodes) if m.node_tree else []}
            for m in bpy.data.materials if m.users
        },
        "actions": {
            a.name: {"range": _r(a.frame_range, 2), "slots": [s.identifier for s in a.slots], "fcurves": _fcurve_count(a)}
            for a in bpy.data.actions
        },
        "images": {i.name: {"size": list(i.size), "file": i.filepath} for i in bpy.data.images if i.users},
    }
    if path:
        with open(_abs(path), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, indent=1, sort_keys=True)
            fh.write("\n")
    return data


def save(blend_path):
    """Save the open file as `blend_path` (compressed: best size with Git LFS) + `<name>.scene.json` beside it."""
    os.makedirs(os.path.dirname(_abs(blend_path)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True, relative_remap=True)
    snap = os.path.splitext(blend_path)[0] + ".scene.json"
    snapshot(snap)
    return {"blend": blend_path, "snapshot": snap, "bytes": os.path.getsize(blend_path)}
