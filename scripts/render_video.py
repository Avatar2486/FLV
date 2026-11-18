"""
Render the bedroom animation as a 1080x1920 (9:16) H.264 MP4 into output/renders/.

    blender -b --factory-startup --python scripts/render_video.py
    blender -b --factory-startup --python scripts/render_video.py -- --camera CAMERA_Bed

Frame range and frame rate come from the .blend file (1-120 at 24 fps = 5 s), so
a change made on the Blender timeline carries through to the render.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy

import scene_utils as su

parser = argparse.ArgumentParser(description="Render the MP4 video")
parser.add_argument("--camera", default="CAMERA_Main", help="camera object to render through")
parser.add_argument("--scene", default=str(su.SCENES_DIR / "test_bedroom.blend"))
args = parser.parse_args(su.script_args())

su.open_blend(args.scene)
scene = bpy.context.scene
scene.camera = bpy.data.objects[args.camera]
scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
scene.render.resolution_percentage = 100

shot = args.camera.removeprefix("CAMERA_").lower()
output = su.RENDER_DIR / f"bedroom_{shot}.mp4"
output.parent.mkdir(parents=True, exist_ok=True)
su.set_mp4_output(scene, output)
seconds = (scene.frame_end - scene.frame_start + 1) / scene.render.fps
print(f"Rendering frames {scene.frame_start}-{scene.frame_end} ({seconds:.1f} s) through {args.camera}")
bpy.ops.render.render(animation=True)
print(f"Video saved: {output}")
