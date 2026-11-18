"""
Check the bedroom project and its renders, and write output/validation_report.md.

    blender -b --factory-startup --python scripts/validate_scene.py

Run it after create_test_scene.py, render_preview.py and render_video.py.
Exits with code 1 if any check fails.
"""
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy
import numpy as np
from bpy_extras import anim_utils

import scene_utils as su

SCENE = su.SCENES_DIR / "test_bedroom.blend"
PREVIEW = su.PREVIEW_DIR / "bedroom_main_preview.png"
VIDEO = su.RENDER_DIR / "bedroom_main.mp4"
REPORT = su.PROJECT_ROOT / "output" / "validation_report.md"
COLLECTIONS = ("ROOM", "BED", "FURNITURE", "WINDOW", "PROPS", "LIGHTING", "CAMERAS")
KEY_OBJECTS = ("ROOM_Floor", "ROOM_BackWall", "ROOM_LeftWall", "BED_Frame", "BED_Mattress",
               "BED_Pillow_Left", "BED_Pillow_Right", "WINDOW_Glass", "WINDOW_Frame",
               "TABLE_Bedside_Left", "LAMP_Base", "LAMP_Shade", "CAMERA_Main", "CAMERA_Bed",
               "CAMERA_Window")
GENERIC_NAME = re.compile(r"^(Cube|Cylinder|Sphere|Icosphere|Plane|Cone|Torus|Mesh|Light|Camera|Empty)\b"
                          r"|\.\d{3}$")

results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok), detail))


def rel(path):
    return path.relative_to(su.PROJECT_ROOT).as_posix()


def write_report():
    lines = [f"# FLV bedroom validation report",
             "",
             f"{datetime.now():%Y-%m-%d %H:%M} | Blender {bpy.app.version_string}",
             "",
             "| Check | Result | Detail |",
             "|---|---|---|"]
    lines += [f"| {label} | {'PASS' if ok else 'FAIL'} | {detail} |" for label, ok, detail in results]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")
    for label, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    print(f"Report: {REPORT}")
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)


# 1. The project file -------------------------------------------------------------
check("Blend file exists", SCENE.is_file(), rel(SCENE))
if not SCENE.is_file():
    write_report()
bpy.ops.wm.open_mainfile(filepath=str(SCENE))
scene = bpy.context.scene
check("Blend file reopens", True, f"{len(scene.objects)} objects, {len(bpy.data.materials)} materials")

# 2. Organisation ---------------------------------------------------------------------
root = bpy.data.collections.get("FLV_BEDROOM")
children = {c.name for c in root.children} if root else set()
missing = [c for c in COLLECTIONS if c not in children]
check("Collections FLV_BEDROOM > ROOM, BED, FURNITURE, WINDOW, PROPS, LIGHTING, CAMERAS",
      root and not missing, f"missing: {missing}" if missing else "all present")
missing = [n for n in KEY_OBJECTS if n not in bpy.data.objects]
check("Key objects exist", not missing, f"missing: {missing}" if missing else f"{len(KEY_OBJECTS)} found")
generic = [o.name for o in scene.objects if GENERIC_NAME.search(o.name)]
check("No generic names (Cube.001 ...)", not generic, ", ".join(generic[:10]) or "none")
loose = [o.name for o in scene.objects if o.users_collection[0].name not in COLLECTIONS]
check("Every object sits in a scene collection", not loose, ", ".join(loose[:10]) or "none")

# 3. Materials --------------------------------------------------------------------------
meshes = [o for o in scene.objects if o.type == "MESH"]
bare = [o.name for o in meshes if not o.material_slots or any(s.material is None for s in o.material_slots)]
check("Every mesh has a material", not bare, ", ".join(bare[:10]) or f"{len(meshes)} meshes")
odd = [m.name for m in bpy.data.materials if m.users and not m.name.startswith("MAT_")]
check("Materials named MAT_*", not odd, ", ".join(odd) or f"{len(bpy.data.materials)} materials")

# 4. Cameras and animation ------------------------------------------------------------
check("CAMERA_Main is the active camera", scene.camera and scene.camera.name == "CAMERA_Main",
      scene.camera.name if scene.camera else "none")
timeline = (scene.frame_start, scene.frame_end, scene.render.fps / scene.render.fps_base)
check("Timeline 1-120 at 24 fps (5 s)", timeline == (1, 120, 24),
      f"frames {timeline[0]}-{timeline[1]} at {timeline[2]:g} fps")
for name in ("CAMERA_Main", "CAMERA_Bed", "CAMERA_Window"):
    cam = bpy.data.objects.get(name)
    anim = cam.animation_data if cam else None
    keys = []
    if anim and anim.action:
        bag = anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot)
        keys = [k for fc in bag.fcurves for k in fc.keyframe_points]
    frames = sorted({round(k.co.x) for k in keys})
    smooth = keys and all(k.interpolation == "BEZIER" for k in keys)
    check(f"{name} animated smoothly", frames == [1, 120] and smooth,
          f"keys at {frames}, {'Bezier ease' if smooth else 'not Bezier'}")

# 5. Render settings and portability ------------------------------------------------
render = scene.render
check("Eevee at 1080x1920 with AgX",
      render.engine == su.eevee_engine() and (render.resolution_x, render.resolution_y) == (1080, 1920)
      and scene.view_settings.view_transform == "AgX",
      f"{render.engine}, {render.resolution_x}x{render.resolution_y}, {scene.view_settings.view_transform}")
check("Saved output is H.264 MP4", render.image_settings.file_format == "FFMPEG"
      and render.ffmpeg.format == "MPEG4" and render.ffmpeg.codec == "H264", render.filepath)
check("Output path is relative to the .blend", render.filepath.startswith("//"), render.filepath)
absolute = [i.filepath for i in bpy.data.images if i.source == "FILE" and not i.filepath.startswith("//")]
check("No absolute file paths stored", not absolute, ", ".join(absolute) or "none")

# 6. Renders ------------------------------------------------------------------------------
if PREVIEW.is_file():
    image = bpy.data.images.load(str(PREVIEW))
    w, h = image.size
    pixels = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(pixels)
    contrast = float(np.ptp(pixels.reshape(-1, 4)[:, :3]))
    check("Preview PNG is 540x960 and has an image in it", (w, h) == (540, 960) and contrast > 0.2,
          f"{rel(PREVIEW)}: {w}x{h}, {PREVIEW.stat().st_size // 1024} KB, contrast {contrast:.2f}")
else:
    check("Preview PNG exists", False, f"{rel(PREVIEW)} missing - run render_preview.py")

if VIDEO.is_file():
    clip = bpy.data.movieclips.load(str(VIDEO))
    w, h = clip.size
    seconds = clip.frame_duration / clip.fps if clip.fps else 0
    check("Video MP4 is 1080x1920 and 5 s long", (w, h) == (1080, 1920) and abs(seconds - 5) < 0.05,
          f"{rel(VIDEO)}: {w}x{h}, {clip.frame_duration} frames at {clip.fps:g} fps = {seconds:.2f} s, "
          f"{VIDEO.stat().st_size / 1e6:.1f} MB")
else:
    check("Video MP4 exists", False, f"{rel(VIDEO)} missing - run render_video.py")

write_report()
