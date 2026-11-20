"""Tests for scripts/blender/bkit.py, run inside a headless Blender. Skipped when Blender is absent.
Blender is found via $BLENDER, PATH, or the default Windows install dir.
"""
import glob
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "scripts" / "blender"


def find_blender():
    cands = [os.environ.get("BLENDER"), shutil.which("blender")]
    cands += sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe"), reverse=True)
    return next((c for c in cands if c and os.path.isfile(c)), None)


BLENDER = find_blender()


def run_in_blender(body, tmp):
    script = Path(tmp) / "case.py"
    out = Path(tmp) / "out.json"
    script.write_text(textwrap.dedent(f"""
        import sys, json
        sys.path.insert(0, {str(KIT)!r})
        import bpy, bkit
        TMP = {str(tmp)!r}
        result = None
    """) + textwrap.dedent(body) + f"\njson.dump(result, open({str(out)!r}, 'w'))\n", encoding="utf-8")
    r = subprocess.run([BLENDER, "--background", "--factory-startup", "--python-exit-code", "1",
                        "--python", str(script)], capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return json.loads(out.read_text())


@unittest.skipUnless(BLENDER, "Blender not installed")
class BlenderKit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_shots_render_every_view_and_restore_scene(self):
        res = run_in_blender("""
            sc = bpy.context.scene
            before = [sc.camera.name, sc.render.engine, sc.render.resolution_x, len(bpy.data.objects)]
            paths = bkit.shots(TMP + "/shots", res=64, frames=[1, 2])
            after = [sc.camera.name, sc.render.engine, sc.render.resolution_x, len(bpy.data.objects)]
            result = {"paths": paths, "before": before, "after": after}
        """, self.tmp)
        self.assertEqual(len(res["paths"]), 10)
        self.assertTrue(all(os.path.getsize(p) > 0 for p in res["paths"]))
        self.assertEqual(res["before"], res["after"])

    def test_compare_separates_matching_and_different_shapes(self):
        res = run_in_blender("""
            cube = bpy.data.objects["Cube"]
            cube.scale = (1, 1, 2)  # tall box: front view is a 1:2 rectangle
            bpy.ops.mesh.primitive_uv_sphere_add(location=(5, 0, 0))
            sphere = bpy.context.active_object.name
            ref = bkit.silhouette(TMP + "/ref.png", "front", 256, names=["Cube"])
            same = bkit.compare(ref, "front", TMP + "/a", names=["Cube"], res=256)
            other = bkit.compare(ref, "front", TMP + "/b", names=[sphere], res=256)
            result = {"same": same, "other": other}
        """, self.tmp)
        self.assertGreaterEqual(res["same"]["iou"], 0.98)
        self.assertLess(abs(res["same"]["aspect_err"]), 0.03)
        self.assertLess(res["other"]["iou"], 0.9)
        self.assertGreater(abs(res["other"]["aspect_err"]), 0.3)
        self.assertTrue(os.path.isfile(res["same"]["overlay"]))

    def test_mask_reads_opaque_reference_against_plain_background(self):
        res = run_in_blender("""
            import numpy as np
            px = np.ones((100, 100, 4), np.float32)
            px[20:80, 40:60, :3] = 0.1
            result = {"fg": int(bkit.mask(px).sum())}
        """, self.tmp)
        self.assertEqual(res["fg"], 60 * 20)

    def test_checks_flags_open_mesh_and_unapplied_scale(self):
        res = run_in_blender("""
            bpy.ops.mesh.primitive_plane_add(location=(4, 0, 0))
            bpy.context.active_object.scale = (2, 2, 2)
            result = bkit.checks()
        """, self.tmp)
        self.assertEqual(res["Cube"]["non_manifold_edges"], 0)
        self.assertEqual(res["Plane"]["non_manifold_edges"], 4)
        self.assertTrue(res["Plane"]["unapplied_scale"])
        self.assertFalse(res["Cube"]["unapplied_scale"])

    def test_save_writes_blend_and_deterministic_snapshot(self):
        res = run_in_blender("""
            info = bkit.save(TMP + "/art/box/box.blend")
            first = open(info["snapshot"]).read()
            bkit.snapshot(info["snapshot"])
            result = {"info": info, "stable": first == open(info["snapshot"]).read(), "snap": json.loads(first)}
        """, self.tmp)
        self.assertTrue(os.path.isfile(res["info"]["blend"]))
        self.assertTrue(res["stable"])
        self.assertEqual(res["snap"]["file"], "box.blend")
        self.assertEqual(res["snap"]["objects"]["Cube"]["mesh"]["faces"], 6)

    def test_relative_paths_are_rejected(self):
        res = run_in_blender("""
            try:
                bkit.shots("relative/dir")
                result = "accepted"
            except ValueError as e:
                result = str(e)
        """, self.tmp)
        self.assertIn("absolute path required", res)


if __name__ == "__main__":
    unittest.main()
