"""
Measure how people actually move in motion-capture clips: speed, cadence, step length, crouch, knee bend,
heel lift (tiptoe), trunk lean, arm spread, head bob and pauses. Lengths are in leg lengths, so CMU and
100STYLE clips compare directly.

    blender -b --factory-startup --python scripts/gait_stats.py -- out.json clip.bvh [clip.bvh ...]
"""
import json
import math
import sys

import bpy
from mathutils import Vector

NAMES = {   # role -> (CMU name, 100STYLE name)
    "hips": ("Hips", "Hips"), "neck": ("Neck", "Neck"), "head": ("Head", "Head"),
    "l_hip": ("LeftUpLeg", "LeftHip"), "l_knee": ("LeftLeg", "LeftKnee"), "l_ankle": ("LeftFoot", "LeftAnkle"),
    "l_toe": ("LeftToeBase", "LeftToe"), "r_hip": ("RightUpLeg", "RightHip"), "r_knee": ("RightLeg", "RightKnee"),
    "r_ankle": ("RightFoot", "RightAnkle"), "r_toe": ("RightToeBase", "RightToe"),
    "l_hand": ("LeftHand", "LeftWrist"), "r_hand": ("RightHand", "RightWrist"),
}


def measure(path, fps=30):
    scene = bpy.context.scene
    scene.render.fps = fps
    before = set(bpy.data.objects)
    bpy.ops.import_anim.bvh(filepath=path, use_fps_scale=True, update_scene_fps=False, update_scene_duration=False)
    arm = (set(bpy.data.objects) - before).pop()
    a, b = (int(x) for x in arm.animation_data.action.frame_range)
    result = measure_armature(arm, a, b, fps)
    bpy.data.objects.remove(arm)
    result["clip"] = path.rsplit("/", 1)[-1]
    return result


def measure_armature(arm, a, b, fps=24, floor=None):
    """Gait numbers for an animated armature (CMU-named rigs such as MPFB's cmu_mb, or 100STYLE).
    floor: the ground height if known (retargeted characters stand on z=0), else the lowest foot point."""
    scene = bpy.context.scene
    style = 1 if "LeftHip" in arm.pose.bones else 0
    bone = {role: arm.pose.bones[names[style]] for role, names in NAMES.items()}
    head = lambda r: arm.matrix_world @ bone[r].head
    rest = lambda r: arm.matrix_world @ arm.data.bones[bone[r].name].head_local
    leg = (rest("l_hip") - rest("l_knee")).length + (rest("l_knee") - rest("l_ankle")).length
    frames = []
    for f in range(a, b + 1):
        scene.frame_set(f)
        frames.append({r: head(r).copy() for r in NAMES})
    lowest = min(min(p["l_toe"].z, p["r_toe"].z, p["l_ankle"].z, p["r_ankle"].z) for p in frames)
    floor = lowest if floor is None else floor
    n = len(frames)
    dt = 1 / fps

    def contact(side, i):
        if i == 0:
            return False
        toe, prev = frames[i][f"{side}_toe"], frames[i - 1][f"{side}_toe"]
        low = min(toe.z, frames[i][f"{side}_ankle"].z) - floor < 0.07 * leg
        still = (toe.xy - prev.xy).length / dt < 0.35 * leg
        return low and still

    contacts = {s: [contact(s, i) for i in range(n)] for s in ("l", "r")}
    steps = sum(1 for s in "lr" for i in range(1, n) if contacts[s][i] and not contacts[s][i - 1])
    speeds = [(frames[i]["hips"].xy - frames[i - 1]["hips"].xy).length / dt for i in range(1, n)]
    distance = sum(speeds) * dt
    stance = [(s, i) for s in "lr" for i in range(n) if contacts[s][i]]

    def angle(u, v):
        return math.degrees(u.angle(v)) if u.length and v.length else 0.0

    knee = [180 - angle(frames[i][f"{s}_hip"] - frames[i][f"{s}_knee"], frames[i][f"{s}_ankle"] - frames[i][f"{s}_knee"])
            for s, i in stance]
    heel = [math.degrees(math.atan2(frames[i][f"{s}_ankle"].z - frames[i][f"{s}_toe"].z,
                                    (frames[i][f"{s}_ankle"].xy - frames[i][f"{s}_toe"].xy).length)) for s, i in stance]
    lean = [angle(p["neck"] - p["hips"], Vector((0, 0, 1))) for p in frames]
    stand = rest("hips").z - min(rest("l_toe").z, rest("l_ankle").z)
    hips = [(p["hips"].z - floor) / stand for p in frames]
    arms = [((p["l_hand"] - p["r_hand"]).xy.length) / leg for p in frames]
    bob = [p["head"].z for p in frames]
    paused = sum(1 for v in speeds if v < 0.08 * leg) / max(1, len(speeds))
    duration = n * dt
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    skate = [(frames[i][f"{s}_toe"].xy - frames[i - 1][f"{s}_toe"].xy).length / dt for s, i in stance if i]
    return {
        "clip": arm.name, "seconds": round(duration, 1),
        "foot_skate_cm_per_s": round(mean(skate) * 100, 1),         # planted foot sliding: ~0 is right
        "foot_skate_legs_per_s": round(mean(skate) / leg, 3),
        "lowest_foot_vs_floor_cm": round((lowest - floor) * 100, 1),  # below 0 = foot through the floor
        "speed_legs_per_s": round(distance / duration / leg, 2),
        "cadence_steps_per_min": round(steps / duration * 60, 1),
        "step_length_legs": round(distance / max(1, steps) / leg, 2),
        "hips_height_vs_standing": round(mean(hips), 2),
        "knee_bend_in_stance_deg": round(mean(knee), 1),
        "foot_pitch_in_stance_deg": round(mean(heel), 1),        # heel above toe: tiptoe if large
        "trunk_lean_deg": round(mean(lean), 1),
        "hand_spread_legs": round(mean(arms), 2),
        "head_bob_legs": round((max(bob) - min(bob)) / leg, 3),
        "time_paused": round(paused, 2),
        "time_both_feet_down": round(sum(1 for i in range(n) if contacts["l"][i] and contacts["r"][i]) / n, 2),
    }


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:]
    results = [measure(p) for p in args[1:]]
    with open(args[0], "w") as fh:
        json.dump(results, fh, indent=1)
    for r in results:
        print("GAIT", json.dumps(r))
