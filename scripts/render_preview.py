"""
Render a 540x960 PNG preview (frame 1) of the bedroom into output/previews/.

    blender -b --factory-startup --python scripts/render_preview.py
    blender -b --factory-startup --python scripts/render_preview.py -- --camera CAMERA_Bed
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy

import scene_utils as su

parser = argparse.ArgumentParser(description="Render a PNG preview")
parser.add_argument("--camera", default="CAMERA_Main", help="camera object to render through")
parser.add_argument("--scene", default=str(su.SCENES_DIR / "test_bedroom.blend"))
args = parser.parse_args(su.script_args())

su.open_blend(args.scene)
scene = bpy.context.scene
scene.camera = bpy.data.objects[args.camera]
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
scene.render.resolution_percentage = 50          # 540 x 960, same 9:16 framing as the video
scene.frame_set(1)

shot = args.camera.removeprefix("CAMERA_").lower()
output = su.PREVIEW_DIR / f"bedroom_{shot}_preview.png"
su.set_png_output(scene, output)
bpy.ops.render.render(write_still=True)
print(f"Preview saved: {output}")
