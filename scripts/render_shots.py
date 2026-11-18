"""
Render a film shot by shot into separate MP4 files (so one shot can be redone alone).

    blender -b blender/scenes/tell_tale_heart.blend --python scripts/render_shots.py -- \\
        --timeline stories/the_tell_tale_heart/timeline.json --out output/renders/tell_tale_heart/shots \\
        [--only 2.5,3.1] [--worker 0 --workers 2]

Shots whose file already exists are skipped unless named in --only. Camera cuts inside a
shot come from the .blend's timeline markers.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy

import scene_utils as su

parser = argparse.ArgumentParser()
parser.add_argument("--timeline", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--only", default="")
parser.add_argument("--worker", type=int, default=0)
parser.add_argument("--workers", type=int, default=1)
args = parser.parse_args(su.script_args())

shots = json.loads((su.PROJECT_ROOT / args.timeline).read_text())["shots"]
only = set(filter(None, args.only.split(",")))
out = su.PROJECT_ROOT / args.out
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
for i, shot in enumerate(shots):
    target = out / f"{i:03d}_{shot['id']}.mp4"
    if only and shot["id"] not in only:
        continue
    if not only and (i % args.workers != args.worker or (target.exists() and target.stat().st_size > 0)):
        continue
    scene.frame_start, scene.frame_end = shot["start"], shot["start"] + shot["frames"] - 1
    su.set_mp4_output(scene, target)
    bpy.ops.render.render(animation=True)
    print(f"RENDERED {shot['id']} -> {target.name}", flush=True)
