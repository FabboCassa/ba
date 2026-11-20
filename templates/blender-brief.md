---
slug: <slug>
status: brief            # brief -> proto -> proto-approved -> building -> review -> done
kind: [model-3d]         # model-3d | modify-existing | 2d | animation | rig | environment (one or more)
blender: <version>
master: art/<slug>/<slug>.blend
source: null             # existing file being modified (path), else null
proto_version: null      # set at proto approval (git tag <slug>-proto)
---

# <Name>

## Intent
What it is, who/what it is for, the one thing it must get right.

## Style
Style family (e.g. stylized hand-painted, low-poly flat, toon + outline, realistic PBR, clay, voxel, 2D cel line art).
3 adjectives + 1 "never ...". Colour palette (hex) and material language.

## References
| file (ref/) | view | az/el/lens or ortho | take from it | ignore |
|---|---|---|---|---|

Conflicts between references and how they are resolved.

## Scale and proportions
Real-world size with source. 5-15 proportions to check (e.g. "head = 1/6 of height").

## Parts
Ordered list (big to small): name, shape idea, notes. Silhouette features that must read.

## Technical
Target (game engine / still render / animation / 3D print / web), poly budget, topology needs (quads, deformation loops),
UVs/textures (resolution, baked or procedural), rig type, export formats, naming conventions.

## Animation (if any)
| clip | frames @fps | loop | key poses | notes |
|---|---|---|---|---|

## Prototype scope
What the base is: blockout / exoskeleton (bones) / modification pass / animation blocking / 2D rough. What it does NOT include.

## Acceptance
Measurable checks for the final build (dimensions ±%, IoU vs ortho refs, poly budget, clips, export round-trip, mesh health).

## Inferred
Everything assumed without the user saying it (they confirm or correct).

## Changelog
- v1 brief: ...
