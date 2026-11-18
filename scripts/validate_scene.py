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
COLLECTIONS = ("ROOM", "BED", "FURNITURE", "WINDOW", "PROPS", "CHARACTERS", "LIGHTING", "CAMERAS")
KEY_OBJECTS = ("ROOM_Floor", "ROOM_BackWall", "ROOM_LeftWall", "BED_Frame", "BED_Mattress",
               "BED_Pillow_Left", "BED_Pillow_Right", "WINDOW_Glass", "WINDOW_Frame",
               "TABLE_Bedside_Left", "LAMP_Base", "LAMP_Shade", "CAMERA_Main", "CAMERA_Bed",
               "CAMERA_Window", "CHAR_Walker_Rig", "CHAR_Walker_Body", "CHAR_Sleeper_Head",
               "PROP_Notebook", "PROP_Pencil", "PROP_Pencil_In_Hand")
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
check(f"Collections FLV_BEDROOM > {', '.join(COLLECTIONS)}",
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
fps = scene.render.fps / scene.render.fps_base
story_seconds = (scene.frame_end - scene.frame_start + 1) / fps
check("Timeline starts at frame 1, 24 fps, whole seconds", scene.frame_start == 1 and fps == 24
      and story_seconds.is_integer(), f"frames {scene.frame_start}-{scene.frame_end} = {story_seconds:g} s")
for name in ("CAMERA_Main", "CAMERA_Bed", "CAMERA_Window"):
    cam = bpy.data.objects.get(name)
    anim = cam.animation_data if cam else None
    keys = []
    if anim and anim.action:
        bag = anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot)
        keys = [k for fc in bag.fcurves for k in fc.keyframe_points]
    frames = sorted({round(k.co.x) for k in keys})
    smooth = keys and all(k.interpolation == "BEZIER" for k in keys)
    check(f"{name} animated smoothly", frames == [scene.frame_start, scene.frame_end] and smooth,
          f"keys at {frames}, {'Bezier ease' if smooth else 'not Bezier'}")

rig = bpy.data.objects.get("CHAR_Walker_Rig")
anim = rig.animation_data if rig else None
walk_keys = []
if anim and anim.action:
    bag = anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot)
    walk_keys = sorted({round(k.co.x) for fc in bag.fcurves for k in fc.keyframe_points})
check("Walker animated (walk, pick up pencil, write)", len(walk_keys) > 100 and walk_keys[-1] > 0.75 * scene.frame_end,
      f"{len(walk_keys)} keyed frames, last at {walk_keys[-1] if walk_keys else '-'}")
covers = bpy.data.objects.get("CHAR_Sleeper_Under_Covers")
breathing = covers and covers.animation_data and any(
    m.type == "CYCLES" for fc in anim_utils.action_get_channelbag_for_slot(
        covers.animation_data.action, covers.animation_data.action_slot).fcurves for m in fc.modifiers)
check("Sleeper breathes (looping)", breathing, "covers rise and fall" if breathing else "no breathing loop")

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
    check(f"Video MP4 is 1080x1920 and {story_seconds:g} s long",
          (w, h) == (1080, 1920) and abs(seconds - story_seconds) < 0.05,
          f"{rel(VIDEO)}: {w}x{h}, {clip.frame_duration} frames at {clip.fps:g} fps = {seconds:.2f} s, "
          f"{VIDEO.stat().st_size / 1e6:.1f} MB")
else:
    check("Video MP4 exists", False, f"{rel(VIDEO)} missing - run render_video.py")

write_report()
