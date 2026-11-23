"""
Tell-Tale Heart v3 preview: "the attack" (film shots 3.11-3.21; the 3.19 street cutaway is left out).
It carries on from the v2 preview: the old man sitting up in bed, the narrator's head in the door. The
hardest part of the film is here: two people in contact (the narrator drags him from the bed to the floor)
and the heavy bed - in Poe's English the feather-bed - pulled off the frame and over him, so it drapes on
his body while the narrator kneels on it. Nothing moves unless a hand moves it: the door, the lantern
shutter, the old man and the feather-bed all follow hands; the lantern falls only when it is let go.

    blender -b --factory-startup --python stories/the_tell_tale_heart/preview_v3.py -- build
    blender -b blender/scenes/tell_tale_heart_v3_attack.blend --python stories/the_tell_tale_heart/preview_v3.py -- draft
        (480p draft: frames, soundtrack and MP4, all in Blender - no ffmpeg needed)
    blender -b blender/scenes/tell_tale_heart_v3_attack.blend --python stories/the_tell_tale_heart/preview_v3.py -- render A B
        (1080p frames, share A of B, like the v2 preview)

Voices: these shots only have the first (Piper) recordings, in audio/voiceovers/the_tell_tale_heart/.
preview_v3/lines.json lists the lines for scripts/chatterbox_lines.py to make v2-style (Chatterbox) voices
into audio/voiceovers/the_tell_tale_heart_v3/; once they exist the build uses them instead (then rebuild).
"""
import json
import math
import random
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
VO = ROOT / "audio" / "voiceovers" / "the_tell_tale_heart"
OUT = ROOT / "output" / "renders" / "the_tell_tale_heart_v3_attack"
BLEND = ROOT / "blender" / "scenes" / "tell_tale_heart_v3_attack.blend"
FPS, LEAD, GAP, TAIL = 24, 0.4, 0.35, 0.7

# shot id, lines (voice file prefix, who), minimum seconds - the film's own shot list
SHOTS = [
    ("3.11", [("3.11_0_N", "N"), ("3.11_1_OM", "OM")], 12.0),
    ("3.12", [("3.12_0_N", "N")], 7.0),
    ("3.13", [("3.13_0_N", "N")], 9.0),
    ("3.14", [("3.14_0_N", "N")], 4.0),
    ("3.15", [("3.15_0_N", "N")], 14.0),
    ("3.16", [("3.16_0_N", "N")], 12.0),
    ("3.17", [], 3.0),
    ("3.18", [("3.18_0_N", "N")], 11.0),
    ("3.20", [("3.20_0_N", "N")], 7.0),
    ("3.21", [("3.21_0_N", "N")], 9.0),
]
HEARTBEATS = [("3.15", 9.0, 62, 96, "3.17", 0.2, False),     # the film's heart: rising to the attack,
              ("3.18", 6.0, 90, 40, "3.20", 3.0, True)]      # then muffled under the feather-bed, to nothing


VO_V3 = ROOT / "audio" / "voiceovers" / "the_tell_tale_heart_v3"


def voice(prefix):
    """The Chatterbox take (preview_v3/lines.json) if it has been made, else the first Piper take."""
    shot, _, who = prefix.split("_")
    v3 = VO_V3 / f"{shot}_{who}.wav"
    return v3 if v3.exists() else next(VO.glob(f"{prefix}_*.wav"))


def seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def timeline(shots=None, voice_fn=None):
    t, out = 0.0, []
    for sid, lines, minimum in SHOTS if shots is None else shots:
        at, placed = LEAD, []
        for prefix, who in lines:
            path = (voice_fn or voice)(prefix)
            placed.append({"file": str(path.relative_to(ROOT)).replace("\\", "/"), "who": who, "line": prefix,
                           "start": round(t + at, 3), "seconds": round(seconds(path), 3)})
            at += placed[-1]["seconds"] + GAP
        length = max(minimum, at - GAP + TAIL)
        out.append({"id": sid, "start": round(t, 3), "seconds": round(length, 3), "lines": placed})
        t += length
    return {"fps": FPS, "seconds": round(t, 3), "frames": int(round(t * FPS)), "shots": out}


def ease(a, b, x):
    u = min(1.0, max(0.0, (x - a) / (b - a))) if b != a else float(x >= b)
    return u * u * (3 - 2 * u)


# ----------------------------------------------------------------------------------------------- build
def build():
    import bpy
    import numpy as np
    from mathutils import Euler, Matrix, Quaternion, Vector
    sys.path[:0] = [str(ROOT / "scripts"), str(HERE)]
    import humans
    import scene_utils as su
    import sets
    import cast3d
    from material_library import material as M

    tl = timeline()
    start = {s["id"]: 1 + int(round(s["start"] * FPS)) for s in tl["shots"]}
    end = tl["frames"]
    line_frame = {l["line"]: 1 + int(round(l["start"] * FPS)) for s in tl["shots"] for l in s["lines"]}

    def T(sid, sec=0.0):
        return start[sid] + int(round(sec * FPS))

    su.reset_scene()
    scene = bpy.context.scene
    su.configure_render(scene, width=1920, height=1080, fps=FPS, frame_end=end, samples=48)
    scene.eevee.volumetric_tile_size = "4"                   # fine enough to show a thread-thin beam
    scene.eevee.volumetric_samples = 48
    scene.eevee.volumetric_shadow_samples = 8
    root = su.collection("V3_ATTACK")
    C = {n: su.collection(n, root) for n in ("SET", "CAST", "PROPS", "CAMERAS")}
    lights = {}
    room = sets.chamber(C["SET"], lights)
    for name, energy in (("moon", 700), ("fill", 30), ("warm", 0), ("sun", 0), ("shadow", 0)):
        lights[name].data.energy = energy
    world = bpy.data.worlds.new("WORLD_Night")
    scene.world = world
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.002, 0.0025, 0.004, 1)
    lights["fill"].data.use_shadow = False
    room["blanket"].hide_render = room["blanket"].hide_viewport = True
    haze = room["haze"].active_material.node_tree.nodes.get("Principled Volume")
    if haze:
        haze.inputs["Density"].default_value = 0.03          # a little more than v2: the "thread" of light
    MATTRESS = 0.44

    # ---- the feather-bed: the bedding piece of the gothic bed becomes its own object; a straw tick and two
    # side boards are what is left on the frame under it, with the pillows
    featherbed, pillows = _split_featherbed(bpy, np, room)
    su.box("V3_Straw_Tick", C["SET"], M("MAT_Pillow"), (1.34, 1.76, 0.15), (0.935, 1.18, 0.265), bevel=0.03)
    for x in (0.215, 1.655):
        su.box(f"V3_Bed_Rail_{x:.2f}", C["SET"], M("MAT_Bed_Wood"), (0.05, 1.95, 0.2), (x, 1.23, 0.22), bevel=0.006)

    # ---- the cast, where the v2 preview left them
    om = humans.build(cast3d.OLD_MAN)
    om.location, om.rotation_euler = (0.9, 0.38, 0.56), Euler((math.radians(-90), 0, 0))
    nar = humans.build(cast3d.NARRATOR)
    nar.location, nar.rotation_euler = (-1.58, -2.53, 0.0), Euler((0, 0, math.radians(180)))
    for rig in (om, nar):
        humans.relax_arms(rig)
        for pb in rig.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=1)
    TRUNK = ("Hips", "LeftUpLeg", "RightUpLeg", "LeftLeg", "RightLeg", "LowerBack", "Spine", "Spine1", "Neck1", "Head")
    lying = {n: om.pose.bones[n].rotation_quaternion.copy() for n in TRUNK}

    # key moments (frames)
    R0, R1 = T("3.17", 0.30), T("3.17", 2.05)          # the leap: from the door to the bed
    GRAB, PUSH0 = T("3.18", 0.0), T("3.18", 0.30)       # hands on him; he is pushed down flat
    D0 = T("3.18", 0.75)                                # the drag off the bed
    D1 = D0 + 26
    W1 = T("3.18", 3.45)                                # at the foot of the bed
    G0 = T("3.18", 3.95)                                # the feather-bed pulled
    G1 = G0 + 28
    K0 = T("3.18", 6.30)                                # kneeling beside him
    K1 = K0 + 22
    DEAD = T("3.20", 3.0)                               # the heart stops
    UP = T("3.20", 4.6)                                 # he eases off

    # ---- the old man: sitting up (as at the end of v2), then pushed down flat
    humans.rise_in_bed(om, -40, PUSH0, seconds=1.1, lead="Right")
    for n in TRUNK:
        pb = om.pose.bones[n]
        pb.rotation_quaternion = lying[n]
        pb.keyframe_insert("rotation_quaternion", frame=PUSH0 + 9)
    # his body: on the mattress -> hauled to the edge -> over it -> onto the floor beside the bed
    drag = [(1, (0.9, 0.38, 0.56), 0), (D0, (0.9, 0.38, 0.56), 0), (D0 + 8, (0.45, 0.31, 0.60), 0),
            (D0 + 14, (0.02, 0.22, 0.58), -15), (D0 + 20, (-0.21, 0.13, 0.16), -25), (D0 + 26, (-0.25, 0.10, 0.12), 4),
            (D0 + 34, (-0.25, 0.10, 0.12), 0)]
    for f, loc, roll in drag:
        om.location = loc
        om.rotation_euler = Euler((math.radians(-90), math.radians(roll), 0))
        om.keyframe_insert("location", frame=f)
        om.keyframe_insert("rotation_euler", frame=f)
    for fc in _fcurves(om):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR" if D0 + 14 <= k.co.x < D0 + 20 else "BEZIER"   # he drops, he isn't eased down

    # ---- the narrator's body path: doorway -> leap to the bed -> drags him back -> foot of the bed ->
    # pulls the feather-bed -> round to his side -> kneels. (x, y), heading in degrees: 0 faces -y, 90 +x
    A0 = (-0.12, 1.15)
    path = [(1, (-1.58, -2.53), 180), (R0, (-1.58, -2.53), 180), (R0 + 6, (-1.52, -2.38), 160),
            (R1 - 12, (-0.45, 0.33), 158), (R1, A0, 95), (D0, A0, 92),
            (D1, (-0.80, 1.05), 90), (D1 + 8, (-0.80, 1.05), 20), (D1 + 26, (-0.86, 0.10), 0),
            (W1 - 6, (-0.35, -0.32), 70), (W1, (-0.12, -0.30), 128), (G0, (-0.12, -0.30), 125),
            (G1, (-0.80, -0.30), 112), (G1 + 8, (-0.80, -0.30), 170), (K0 - 6, (-0.80, 0.95), 180),
            (K0, (-0.74, 1.10), 92)]
    track = _sample_path(path, 1, end)
    kneel = {f: ease(K0, K1, f) for f in range(1, end + 1)}
    for f in range(1, end + 1):
        (x, y), h = track[f]
        nar.location = (x, y, -0.445 * kneel[f])
        nar.rotation_euler = Euler((0, 0, math.radians(h)))
        nar.keyframe_insert("location", frame=f)
        nar.keyframe_insert("rotation_euler", frame=f)

    # ---- the door: in 3.12 his right palm eases it from 30 to ~52 degrees; let go, it swings on, slowing,
    # to stand wide open (the lantern's thread of light and his leap need the doorway clear)
    door = room["door"]
    P0, P1 = T("3.12", 0.8), T("3.12", 4.0)
    for f, deg in ((1, -30), (P0 + 10, -30), (P0 + 46, -52), (P1 + 30, -104), (P1 + 40, -102)):
        door.rotation_euler.z = math.radians(deg)
        door.keyframe_insert("rotation_euler", frame=f)
    for fc in _fcurves(door):
        for k in fc.keyframe_points:
            if abs(k.co.x - (P0 + 46)) < 0.5:
                k.handle_left_type = k.handle_right_type = "AUTO"   # keeps its speed when the hand leaves

    # leaning in at the door: as at the end of v2, a little further once the door is wider
    def lean(f):
        x = 1.0 + 0.3 * ease(P0, P1, f)
        out = 1 - ease(R0 - 2, R0 + 4, f)
        x *= out
        return {"Hips": (0, 9 * x, 0), "LeftUpLeg": (0, -9 * x, 0), "RightUpLeg": (0, -9 * x, 0),
                "LowerBack": (0, (3 + 4 * x) * out, 0), "Spine": (0, (2 + 3 * x) * out, 0), "Spine1": (0, 4 * x, 0),
                "Neck1": (0, -6 * x, 0), "Head": (0, -6 * x, 0)}
    humans._layer(nar, 1, R0 + 6, lean)
    humans.sway(nar, 1, R0, amount=0.35, seed=11)
    humans.breathe(nar, 1, R0, style="anxious", seed=13)

    # ---- walking, hurrying and kneeling: steps from motion capture laid along his path (arms swing when
    # free, a lean that grows with speed), the planted feet locked to the floor
    hands_busy = (set(range(R0 - 6, T("3.17", 0.45) + 3))     # the shutter flung open, the lantern let go
                  | set(range(GRAB - 6, D1 + 6)) | set(range(W1 - 4, G1 + 6)) | set(range(K0 + 4, end + 1)))
    _mocap_gait(humans, nar, track, R0, K0, hands_busy)

    def kneel_layer(f):
        k = kneel[f]
        # leaning in from the hips (thighs held where they are): pressing the feather-bed down, until he eases
        # off; and again in 3.21, to the chest
        pressing = 1 - ease(UP, UP + 30, f)
        lean21 = ease(T("3.21") - 8, T("3.21") + 4, f)
        lean = max(pressing, lean21)
        press = (1.2 + 0.15 * lean21) * k * lean
        hinge = (24 + 6 * pressing + 10 * lean21) * k * lean
        return {"Hips": (0, hinge, 0), "LeftUpLeg": (0, -6 * k - hinge, 0), "RightUpLeg": (0, -6 * k - hinge, 0),
                "LeftLeg": (0, 96 * k, 0),
                "RightLeg": (0, 96 * k, 0), "LeftFoot": (0, -25 * k, 0), "RightFoot": (0, -25 * k, 0),
                "LowerBack": (0, 18 * press + 4 * k, 0), "Spine": (0, 12 * press, 0), "Spine1": (0, 8 * press, 0),
                "Neck1": (0, 10 * press, 0), "Head": (0, 8 * k, 0)}
    humans._layer(nar, K0 - 2, end, kneel_layer)

    # the grab and the haul: leaning over the bed with both hands in his nightshirt at the shoulders
    def bending(f):
        b = ease(GRAB - 8, GRAB + 4, f) * (1 - ease(D0 + 6, D1, f))
        g = ease(W1 - 6, W1 + 4, f) * (1 - ease(G1 - 6, G1 + 6, f))
        return {"LowerBack": (0, 22 * b + 30 * g, 0), "Spine": (0, 12 * b + 18 * g, 0), "Spine1": (0, 6 * b + 8 * g, 0),
                "LeftUpLeg": (0, -8 * g, 0), "RightUpLeg": (0, -14 * g, 0), "LeftLeg": (0, 14 * g, 0),
                "RightLeg": (0, 22 * g, 0)}
    humans._layer(nar, GRAB - 10, G1 + 8, bending)

    # ---- the lantern: held up in the gap; the shutter opened a crevice (3.13), thrown open (3.17), dropped
    lantern, shutter, beam, glow = sets.dark_lantern(C["PROPS"])
    beam.location.y = -0.10              # just in front of the lens: the shutter's swing (a crevice) covered it
    beam.data.energy, glow.data.energy = 0.0, 6.0
    beam.data.spot_size = math.radians(1.2)
    beam.data.use_shadow_jitter = False
    spill = su.light("V3_LIGHT_Moon_Spill", C["SET"], "AREA", (-2.30, -1.70, 1.90), 9, (0.55, 0.65, 1.0),
                     target=(-1.60, -2.38, 1.58), size=0.2)
    spill.data.use_shadow_jitter, spill.data.shadow_jitter_overblur = True, 0.0
    high = Vector((-1.70, -2.22, 1.31))
    RELEASE = T("3.17", 0.45)
    humans.grip(nar, "Left", frame=1, curl=1.6)
    humans.reach(nar, "Left", 1, RELEASE - 1, lambda f: high, wrist=(15, (0, 0, -1)))
    yaw = _yaw_to(high, Vector((0.895, 1.341, 1.26)))         # the lens toward his left eye
    humans.hang(lantern, nar, "Left", 1, RELEASE, ring=(0, 0, 0.32), length=0.22, yaw=yaw)
    _drop(lantern, RELEASE, FPS)                               # let go: it falls, rocks and stands on the floor
    # a crevice in 3.13: his right thumb eases the shutter; 3.17: thrown wide, the light floods the room
    C1, C2, FL = T("3.13", 1.0), T("3.13", 3.0), T("3.17", 0.05)
    # he keeps the thread of light on the eye (the small turns of his wrist are carried by the beam itself)
    for f in range(1, FL + 1, 2):
        scene.frame_set(f)
        _aim_beam(beam, lantern, om.matrix_world @ om.pose.bones["LeftEye"].head + Vector((0, -0.012, 0)))
        beam.keyframe_insert("rotation_quaternion", frame=f)
    thumb = nar.pose.bones[humans.THUMB["Right"]]
    scene.frame_set(C1 - 2)
    rest_thumb = thumb.rotation_quaternion.copy()
    for f, deg, sh in ((C1 - 2, 0, 0), (C2, 18, -9), (C2 + 8, 8, -9), (FL - 3, 8, -9), (FL, 40, -110), (FL + 6, 20, -110)):
        thumb.rotation_quaternion = rest_thumb @ Quaternion((1, 0, 0), math.radians(deg))
        thumb.keyframe_insert("rotation_quaternion", frame=f)
        shutter.rotation_euler.z = math.radians(sh)
        shutter.keyframe_insert("rotation_euler", frame=f)
    for f, e, size, g in ((1, 0, 1.8, 6), (C1 + 10, 0, 1.8, 6), (C2, 3500, 1.8, 6), (FL - 1, 3500, 1.8, 6),
                          (FL + 3, 650, 55, 40), (end, 650, 55, 40)):
        beam.data.energy, beam.data.spot_size, glow.data.energy = e, math.radians(size), g
        beam.data.keyframe_insert("energy", frame=f)
        beam.data.keyframe_insert("spot_size", frame=f)
        glow.data.keyframe_insert("energy", frame=f)

    # his right hand: cradles the lantern; in 3.12 it eases the door wider, then comes back to the lantern
    def door_frame(f):
        scene.frame_set(f)
        m = door.matrix_world
        out = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
        along = (m.to_3x3() @ Vector((1, 0, 0))).normalized()
        fingers = (Vector((0, 0, 1)) + 0.35 * along).normalized()
        fingers = (fingers * math.cos(math.radians(12)) + out * math.sin(math.radians(12))).normalized()
        return m, out, fingers

    def on_door(f):
        m, out, fingers = door_frame(f)
        return m @ Vector((0.40, 0.02, 1.25)) - fingers * 0.05 + out * 0.048

    def at_lantern(f):
        scene.frame_set(min(f, RELEASE))
        return lantern.matrix_world @ Vector((0, 0, 0)) + Vector((0.03, -0.085, -0.09))
    cup_turn = humans.hand_frame((-0.25, 0.95, 0.1), (0.0, 0.0, 1.0))
    to_door, off_door = P0, P0 + 46

    def right_hand(f):
        if f > FL + 2:
            return None                                     # 3.17: free (the thumb has flung the shutter)
        x = ease(to_door, to_door + 10, f) * (1 - ease(off_door, off_door + 14, f))
        if x <= 0:
            return at_lantern(f)
        return at_lantern(f).lerp(on_door(max(f, to_door + 10) if f < off_door else off_door), x)

    def right_turn(f):
        x = ease(to_door, to_door + 10, f) * (1 - ease(off_door, off_door + 14, f))
        on = humans.hand_frame(door_frame(min(max(f, to_door), off_door))[2], -door_frame(min(max(f, to_door), off_door))[1])
        return cup_turn.to_quaternion().slerp(on.to_quaternion(), x).to_matrix()
    humans.grip(nar, "Right", frame=1, curl=1.0)
    humans.reach(nar, "Right", 1, FL + 2, right_hand, hand=right_turn)

    # ---- the grab: his hands in the old man's nightshirt at the shoulders, through the push and the haul
    def shoulder(side, up=0.10, back=0.0):
        def at(f):
            scene.frame_set(f)
            pb = om.pose.bones[f"{side}Arm"]
            p = om.matrix_world @ pb.head
            chest = (om.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()      # his front
            return p + chest * up + Vector((back, 0, 0))
        return at
    humans.reach(nar, "Right", GRAB - 6, D1, lambda f: shoulder("Right")(f) if f >= GRAB else None,
                 hand=humans.hand_frame((1, 0, -0.4), (0.2, 0, -1)))
    humans.reach(nar, "Left", GRAB - 4, D1, lambda f: shoulder("Left")(f) if f >= GRAB + 2 else None,
                 hand=humans.hand_frame((1, 0.2, -0.4), (0.2, 0, -1)))
    humans.grip(nar, "Right", frame=GRAB + 2, curl=0.6)
    humans.grip(nar, "Left", frame=GRAB + 4, curl=-0.4)
    # his hands on the mattress beside his hips, as he sat up (v2) ...
    for side, dx in (("Right", -0.24), ("Left", 0.24)):
        push = Vector((0.9 + dx * 1.25, 1.40, MATTRESS + 0.035))
        humans.reach(om, side, 1, GRAB, lambda f, push=push: push if f < GRAB - 4 else None,
                     hand=humans.hand_frame((0.3 * (1 if dx > 0 else -1), -1, 0), (0, 0, -1)))
    # ... then he grabs back at the narrator's forearms while he is hauled
    for side, other in (("Right", "Left"), ("Left", "Right")):
        def wrist(f, other=other):
            if not (GRAB + 6 <= f <= D0 + 18):
                return None
            scene.frame_set(f)
            pb = nar.pose.bones[f"{other}ForeArm"]
            return nar.matrix_world @ pb.head.lerp(pb.tail, 0.7)
        humans.reach(om, side, GRAB - 4, D0 + 30, wrist)        # long enough for the 8-frame let-go to finish
                                                                 # (else the arms stay a third raised, for good)

    # ---- his blanket, shaped over his legs; it falls flat when his legs are hauled out from under it, and
    # later goes with the feather-bed it lies on (shape keys made below, with the feather-bed's)
    sheet, height = humans.bedsheet("V3_Blanket", C["SET"], room["blanket"].active_material, om,
                                    center=(0.9, 0.725), size=(1.35, 0.85), top=MATTRESS, frames=[1])

    # ---- on the floor: he fights (arms up at the narrator, legs kicking); under the feather-bed, only
    # twitches with the last beats; then nothing
    def struggle(f):
        rng = random.Random(f // 3)
        on = ease(D1 - 2, D1 + 6, f) * (1 - ease(G0 - 2, G0 + 9, f))       # arms down before the bed comes over
        twitch = ease(G1, G1 + 6, f) * (1 - ease(DEAD - 12, DEAD, f))
        t = f / FPS
        kick = math.sin(t * 7.1) * on
        arms = on * (70 + 25 * math.sin(t * 5.3))
        tw = twitch * (0.5 + 0.5 * math.sin(t * 9.0)) ** 6 * 12
        # under it the twitches stay small (it is a shape, not cloth: they must not come through it); his
        # bare feet, out from under it, show them
        return {"LeftArm": (0, -arms - 0.5 * tw, 0), "RightArm": (0, -arms * 0.8 - 0.35 * tw, 0),
                "LeftForeArm": (0, -35 * on, 0), "RightForeArm": (0, -45 * on, 0),
                "LeftUpLeg": (0, -25 * on * max(0, kick) - 0.4 * tw, 0), "RightUpLeg": (0, -25 * on * max(0, -kick) - 0.3 * tw, 0),
                "LeftLeg": (0, 50 * on * max(0, kick) + 0.6 * tw, 0), "RightLeg": (0, 50 * on * max(0, -kick) + 0.4 * tw, 0),
                "LeftFoot": (0, 1.6 * tw, 0), "RightFoot": (0, 1.2 * tw, 0),
                "Head": (8 * on * math.sin(t * 4.1) + rng.uniform(-1, 1) * on, 0, 0), "LowerBack": (0, 0, 6 * kick)}
    humans._layer(om, D1 - 4, end, struggle)

    # ---- the feather-bed: grabbed at its foot corner, pulled west off the frame, it drapes over him
    corner = _nearest_vertex(featherbed, Vector((0.24, 0.30, 0.42)))
    corner2 = _nearest_vertex(featherbed, Vector((0.24, 0.62, 0.42)))
    scene.frame_set(G1)
    bpy.context.view_layer.update()
    DX = -0.75
    heights = _height_field(bpy, np, [o for o in om.children if o.name.endswith((".body", ".nightshirt", ".hair"))] +
                            [bpy.data.objects[n] for n in bpy.data.objects.keys() if n.startswith(("V3_Straw", "V3_Bed_Rail"))],
                            (-1.4, 1.9), (-0.4, 2.5), 0.02)
    # where he will kneel on it: his knees, shins and feet press it flat to the floor
    scene.frame_set(K1 + 4)
    limbs = []
    for side in ("Left", "Right"):
        pts = [nar.matrix_world @ nar.pose.bones[f"{side}{b}"].head for b in ("Leg", "Foot", "ToeBase")
               if f"{side}{b}" in nar.pose.bones]
        limbs += list(zip(pts, pts[1:]))
    knees = _press_mask(np, limbs)
    quilt, quilt_pressed = _featherbed_shapes(np, featherbed, heights, DX, knees)
    _blanket_shapes(np, sheet, heights, DX, MATTRESS, quilt, quilt_pressed, knees)
    S21 = T("3.21")
    for f, dx, pulled, draped, pressed in ((1, 0, 0, 0, 0), (G0, 0, 0, 0, 0), (G0 + 10, -0.30, 1.0, 0.0, 0),
                                           (G0 + 18, -0.58, 0.55, 0.45, 0), (G1, DX, 0.0, 1.0, 0), (K0 + 6, DX, 0.0, 1.0, 0),
                                           (K1, DX, 0.0, 0.0, 1.0), (S21 - 1, DX, 0.0, 0.0, 1.0), (S21, 0, 0, 0, 0)):
        for obj in (featherbed, sheet):      # the blanket lies on the feather-bed and goes with it
            obj.location.x = dx
            obj.keyframe_insert("location", frame=f)
            keys = obj.data.shape_keys.key_blocks
            for name, v in (("pulled", pulled), ("draped", draped), ("pressed", pressed)):
                keys[name].value = v
                keys[name].keyframe_insert("value", frame=f)
    flat = sheet.data.shape_keys.key_blocks["flat"]                  # his legs leave from under it
    for f, v in ((1, 0.0), (D0 + 4, 0.0), (D0 + 14, 1.0)):
        flat.value = v
        flat.keyframe_insert("value", frame=f)
    # smoothed (subdivided) in the render from the cut to 3.18 on; the build reads its plain vertices (the
    # corner in his hands), so the viewport level stays 0
    sub = featherbed.modifiers.new("Subdivision", "SUBSURF")
    sub.levels = 0
    for f, lv in ((1, 0), (T("3.18") - 1, 0), (T("3.18"), 2)):
        sub.render_levels = lv
        featherbed.keyframe_insert('modifiers["Subdivision"].render_levels', frame=f)
    # the pillows stay on the frame: the feather-bed is pulled from under them and they settle onto what is
    # left under them (the straw tick, or the feather-bed's near edge)
    for p in pillows:
        scene.frame_set(1)
        deps = bpy.context.evaluated_depsgraph_get()
        pe = p.evaluated_get(deps)
        pts = [p.matrix_world @ v.co for v in pe.to_mesh().vertices]
        pe.to_mesh_clear()
        bottom = min(v.z for v in pts)
        under = [v for v in pts if v.z < bottom + 0.03]
        rest = max(max(heights.raw(v.x, v.y), quilt(v.x, v.y, 0.0)) for v in under[::max(1, len(under) // 80)])
        fall = max(0.0, bottom - rest - 0.003)
        for f, z in ((1, 0.0), (G0 + 6, 0.0), (G0 + 16, -fall), (S21 - 1, -fall), (S21, 0.0)):
            p.delta_location.z = z
            p.keyframe_insert("delta_location", index=2, frame=f)
        print(f"V3 pillow {p.name}: bottom {bottom:.3f}, rests on {rest:.3f} (drops {fall:.3f})")
    # 3.21: "I removed the bed and examined the corpse" - it is back on the frame, between the shots
    for obj in [featherbed, sheet] + pillows:
        for fc in list(_fcurves(obj)) + list(_shape_fcurves(obj)):
            for k in fc.keyframe_points:
                if k.co.x >= S21 - 1 or "render_levels" in fc.data_path:
                    k.interpolation = "CONSTANT"

    def at_corner(v, lift=0.0):
        def at(f):
            scene.frame_set(f)
            deps = bpy.context.evaluated_depsgraph_get()
            me = featherbed.evaluated_get(deps).data
            return featherbed.matrix_world @ me.vertices[v].co + Vector((0, -0.03, lift))
        return at
    humans.reach(nar, "Right", W1 - 4, G1 + 2, lambda f: at_corner(corner)(f) if f >= W1 else None,
                 hand=humans.hand_frame((0.6, 0.6, -0.5), (0, 0, -1)))
    humans.reach(nar, "Left", W1 - 2, G1 + 2, lambda f: at_corner(corner2)(f) if f >= W1 + 2 else None,
                 hand=humans.hand_frame((0.6, 0.6, -0.5), (0, 0, -1)))
    humans.grip(nar, "Right", frame=W1 + 2, curl=1.2)
    humans.grip(nar, "Left", frame=W1 + 4, curl=1.6)

    # ---- kneeling, both hands pressing the feather-bed down over his chest; then, the heart still, he eases off
    def press(dx, dy):
        def at(f):
            if f > UP + 10:
                return None
            x, y = -0.25 + dx, 1.20 + dy                 # wrist ~4 cm above the palm, sunk a little into it
            top = quilt_pressed(x, y, heights(x, y))
            return Vector((x, y, top + 0.035 - 0.015 * _beat(f, HEARTBEATS, tl, FPS)))
        return at
    humans.reach(nar, "Right", K0 + 4, UP + 22, press(0.06, -0.12), hand=humans.hand_frame((1, 0.3, 0), (0, 0, -1)))
    humans.reach(nar, "Left", K0 + 6, UP + 22, press(-0.02, 0.16), hand=humans.hand_frame((1, -0.2, 0), (0, 0, -1)))
    humans.grip(nar, "Right", frame=K0 + 10, curl=-0.3)
    humans.grip(nar, "Left", frame=K0 + 12, curl=-0.3)
    # 3.21: his right hand on the still chest
    def on_chest(f):
        if f < S21:
            return None
        scene.frame_set(f)
        pb = om.pose.bones["Spine"]
        p = om.matrix_world @ pb.head.lerp(pb.tail, 0.35)
        up = (om.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
        return p + up * 0.11 + Vector((-0.08, 0, 0))          # low on the near side of his chest
    humans.reach(nar, "Right", S21, end, on_chest, hand=humans.hand_frame((0.9, 0.4, 0), (0, 0, -1)))

    # ---- faces and eyes
    om_meshes = humans.face_meshes(om)
    humans.face(om, 1, {**cast3d.NEUTRAL, **cast3d.FEAR}, om_meshes)
    who = humans.lip_sync(om, voice("3.11_1_OM"), start_frame=line_frame["3.11_1_OM"])
    humans.eyes(om, 1, T("3.13"), mode="fear", look=(-30.0, -6.0), pauses=who["pauses"], seed=31)
    humans.breathe(om, 1, D0, style="panic", phrases=who["phrases"], seed=32)
    humans.tremble(om, T("3.12"), T("3.17"), strength=0.6)
    # the ray on his eye: it is open, wide open, toward the door
    humans.face(om, T("3.13", 6.0), {**cast3d.FEAR, "eyeWideLeft": 0.9, "eyeWideRight": 0.9}, om_meshes)
    humans._key_eyes(om, om_meshes, T("3.13", 6.0), (-32.0, -4.0))
    humans.startle(om, FL + 2, strength=1.0, until=FL + 40, legs=False)
    shriek = T("3.17", 0.6)
    humans.face(om, shriek - 1, {**cast3d.FEAR}, om_meshes)
    humans.face(om, shriek + 2, {**cast3d.FEAR, "jawOpen": 0.85, "mouthStretchLeft": 0.6, "mouthStretchRight": 0.6,
                                  "eyeWideLeft": 1.0, "eyeWideRight": 1.0, "browInnerUp": 1.0}, om_meshes)
    humans.face(om, D1, {**cast3d.FEAR, "jawOpen": 0.5, "eyeSquintLeft": 0.4, "eyeSquintRight": 0.4}, om_meshes)
    # dead: the eye open and still, the jaw slack
    humans.face(om, DEAD - 6, {**cast3d.FEAR, "jawOpen": 0.4}, om_meshes)
    humans.face(om, DEAD + 30, {**cast3d.NEUTRAL, "jawOpen": 0.18, "eyeWideLeft": 0.2, "eyeWideRight": 0.2,
                                "eyeBlinkLeft": 0.0, "eyeBlinkRight": 0.0}, om_meshes)
    humans._key_eyes(om, om_meshes, DEAD + 30, (-8.0, 12.0))

    nar_meshes = humans.face_meshes(nar)
    humans.face(nar, 1, cast3d.TENSE, nar_meshes)
    humans.eyes(nar, 1, T("3.15"), mode="listening", look=(-18.0, -12.0), seed=33, head=False)
    # 3.15: he hears it - head tilted, listening; 3.16: fury
    def listen(f):
        x = ease(T("3.15", 3.0), T("3.15", 5.0), f) * (1 - ease(R0 - 6, R0, f))
        return {"Head": (0, 0, 9 * x), "Neck1": (0, 0, 4 * x)}
    humans._layer(nar, T("3.15"), R0, listen)
    humans._key_eyes(nar, nar_meshes, T("3.15", 3.0), (-30.0, -14.0))
    humans.face(nar, T("3.16", 2.0), {**cast3d.TENSE, "browDownLeft": 0.9, "browDownRight": 0.9, "noseSneerLeft": 0.5,
                                       "noseSneerRight": 0.4, "mouthPressLeft": 0.6, "mouthPressRight": 0.6}, nar_meshes)
    yell = T("3.17", 0.1)
    humans.face(nar, yell + 2, {**cast3d.NEUTRAL, "jawOpen": 0.7, "browDownLeft": 1.0, "browDownRight": 1.0,
                                "mouthStretchLeft": 0.7, "mouthStretchRight": 0.7, "noseSneerLeft": 0.6}, nar_meshes)
    humans.face(nar, R1, {**cast3d.NEUTRAL, "browDownLeft": 0.8, "browDownRight": 0.8, "mouthPressLeft": 0.8,
                          "mouthPressRight": 0.8, "jawOpen": 0.0, "mouthStretchLeft": 0.0, "mouthStretchRight": 0.0}, nar_meshes)
    humans.face(nar, T("3.18", 9.0), {**cast3d.NEUTRAL, **cast3d.SLY}, nar_meshes)           # he straightens, smiling
    humans.face(nar, UP, {**cast3d.NEUTRAL, **cast3d.SLY}, nar_meshes)
    humans.blinks(nar, R0, end, seed=34)
    humans.breathe(nar, K1, end, style="panic", seed=35)

    # ---- small things the old man names: soot in the grate, a mouse crossing the floor
    soot, mouse = room["soot"], room["mouse"]
    s0 = line_frame["3.11_1_OM"] + int(1.2 * FPS)
    for f, z in ((1, 0.9), (s0, 0.9), (s0 + 30, 0.05)):
        soot.location.z = z
        soot.keyframe_insert("location", frame=f)
    m0 = line_frame["3.11_1_OM"] + int(3.3 * FPS)
    for f, (x, y) in ((1, (-1.8, -0.4)), (m0, (-1.8, -0.4)), (m0 + 40, (-1.05, -1.0))):
        mouse.location.x, mouse.location.y = x, y
        mouse.keyframe_insert("location", frame=f)
    mouse.rotation_euler.z = math.atan2(-0.6, 0.75) - math.pi / 2

    # ---- light: his shadow across the wall over the bed (3.12), from a low light behind him in the corridor
    # (far enough behind him that the doorway throws a lit frame on the far wall with his silhouette in it)
    shadow = su.light("V3_LIGHT_Shadow", C["SET"], "SPOT", (-1.45, -3.60, 0.55), 0, (1.0, 0.62, 0.32),
                      target=(0.4, 2.2, 1.8), spot_size=math.radians(70), spot_blend=0.3, shadow_soft_size=0.015)
    for f, e in ((1, 0), (T("3.12") - 1, 0), (T("3.12"), 6000), (T("3.13") - 1, 6000), (T("3.13"), 0)):
        shadow.data.energy = e
        shadow.data.keyframe_insert("energy", frame=f)
    # 3.20-3.21: the dropped lantern's light along the floor reaches the body (a low warm bounce)
    bounce = su.light("V3_LIGHT_Lantern_Bounce", C["SET"], "AREA", (-0.55, 0.05, 0.30), 0, (1.0, 0.66, 0.38),
                      target=(-0.25, 1.15, 0.2), size=0.6)
    for f, e in ((1, 0), (T("3.20") - 1, 0), (T("3.20"), 18), (end, 18)):
        bounce.data.energy = e
        bounce.data.keyframe_insert("energy", frame=f)

    # ---- cameras: (shot, seconds into it, camera) cuts
    scene.frame_set(T("3.14"))
    eye_now = om.matrix_world @ om.pose.bones["LeftEye"].head
    beam_dir = (eye_now - lantern.matrix_world.translation).normalized()
    side = beam_dir.cross(Vector((0, 0, 1))).normalized()
    scene.frame_set(T("3.13", 1.5))
    lens_at = lantern.matrix_world @ Vector((0, -0.07, 0.09))
    lens_dir = (lantern.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    lens_side = lens_dir.cross(Vector((0, 0, 1))).normalized()
    rigs = {
        "om_ms": dict(at=(2.0, -0.55, 1.30), look=(0.9, 1.30, 1.02), lens=42),
        "grate": dict(at=(-1.25, 0.05, 0.75), look=(-2.25, 0.5, 0.55), lens=35),
        "mouse": dict(at=(-0.85, 0.35, 0.22), look=(-1.45, -0.75, 0.03), lens=35),
        "wall": dict(at=(0.9, -1.55, 1.25), look=(0.9, 2.25, 2.1), lens=24),
        "crevice": dict(at=tuple(lens_at + lens_dir * 0.30 + lens_side * 0.11 + Vector((0, 0, 0.03))),
                        look=tuple(lens_at), lens=85),
        "ray": dict(at=tuple(lens_at + beam_dir * 0.6 + side * 0.25 + Vector((0, 0, 0.08))),
                    look=tuple(lens_at + beam_dir * 1.6), lens=40),
        "eye": dict(at=tuple(eye_now - beam_dir * 0.32 + side * 0.06 + Vector((0, 0, 0.01))), look=tuple(eye_now), lens=100),
        "nar_cu": dict(at=(-2.31, -1.79, 1.62), look=(-1.60, -2.36, 1.58), lens=75),
        "lantern_hand": dict(at=tuple(lens_at + lens_dir * 0.26 - lens_side * 0.30 + Vector((0, 0, 0.12))),
                             look=tuple(lens_at - lens_dir * 0.07 + Vector((0, 0, -0.05))), lens=50),
        "ws": dict(at=(-2.12, 0.95, 2.2), look=(-1.4, -2.2, 1.2), lens=24),
        "top": dict(at=(-0.20, 0.80, 2.88), look=(-0.20, 0.801, 0.0), lens=22),
        "floor": dict(at=(-0.30, -0.95, 0.17), look=(-0.30, 1.0, 0.12), lens=30),
    }
    scene.frame_set(T("3.21", 1.5))
    pb = om.pose.bones["Spine"]
    chest_at = om.matrix_world @ pb.head.lerp(pb.tail, 0.35) + Vector((-0.08, 0, 0.11))
    rigs["hand"] = dict(at=tuple(chest_at + Vector((0.42, -0.30, 0.32))), look=tuple(chest_at + Vector((-0.02, 0.0, 0.05))),
                        lens=70)
    cams = {}
    for name, c in rigs.items():
        cam = su.camera(f"CAM_{name}", C["CAMERAS"], c["at"], c["look"], lens=c["lens"])
        cam.data.dof.use_dof = name not in ("top", "ws")
        cam.data.dof.aperture_fstop = 2.8
        cam.data.dof.focus_distance = (Vector(c["look"]) - Vector(c["at"])).length
        cams[name] = cam
    # the top-down camera: north up in frame
    cams["top"].rotation_mode = "XYZ"
    cams["top"].rotation_euler = Euler((0, 0, 0))
    # moves: slow pushes / tilts, the ray track, the snap zoom, a creeping Dutch tilt, the whip pan
    su.animate_camera(cams["wall"], [(T("3.12"), rigs["wall"]["at"], (0.9, 2.25, 2.1)),
                                     (T("3.13"), rigs["wall"]["at"], (0.9, 2.2, 1.0))])
    su.animate_camera(cams["ray"], [(T("3.13", 3.6), rigs["ray"]["at"], rigs["ray"]["look"]),
                                    (T("3.14"), tuple(eye_now - beam_dir * 1.1 + side * 0.25 + Vector((0, 0, 0.06))),
                                     tuple(eye_now))])
    cams["eye"].data.lens = 60
    cams["eye"].data.keyframe_insert("lens", frame=T("3.14"))
    cams["eye"].data.lens = 100
    cams["eye"].data.keyframe_insert("lens", frame=T("3.14", 0.35))
    # the close-up of him follows his head as he leans and tilts (as an operator would), from the first
    # framing on; a Dutch tilt creeps in through 3.16 on it and on the inserts. Each key is the camera's aim
    # plus the roll at that frame (reading the keyed rotation back and rolling it again made the roll pile up)
    def tilt(f):
        return math.radians(14) * ease(T("3.16"), T("3.17"), f)
    h0 = T("3.14") - 12
    heads, eyes = {}, {}
    for g in range(h0, T("3.17") + 13, 4):
        scene.frame_set(min(max(g, 1), end))
        heads[g] = (nar.matrix_world @ nar.pose.bones["Head"].head).copy()
        eyes[g] = (om.matrix_world @ om.pose.bones["LeftEye"].head).copy()

    def smoothed(table, f):                                        # breath, sway and tremble stay in frame
        g0 = h0 + (f - h0) // 4 * 4
        pts = [table[g] for g in range(g0 - 12, g0 + 13, 4) if g in table]
        return sum(pts, Vector()) / len(pts)
    cu, at2 = cams["nar_cu"], Vector((-2.20, -1.90, 1.61))
    view = (Vector(rigs["nar_cu"]["look"]) - Vector(rigs["nar_cu"]["at"])).normalized()
    ahead = Vector((0, 0, 1)).cross(view).normalized()              # frame-left: where he looks (the bed)
    aim_off = Vector(rigs["nar_cu"]["look"]) - smoothed(heads, T("3.15")) + ahead * 0.16   # room in front of his face
    prev = None
    for f in list(range(T("3.15"), T("3.17"), 6)) + [T("3.17")]:
        at = Vector(rigs["nar_cu"]["at"]).lerp(at2, ease(T("3.15"), T("3.16"), f))
        q = (smoothed(heads, f) + aim_off - at).to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), tilt(f))
        cu.location = at
        cu.rotation_euler = prev = q.to_euler("XYZ", prev) if prev else q.to_euler("XYZ")
        cu.keyframe_insert("location", frame=f)
        cu.keyframe_insert("rotation_euler", frame=f)
        cu.data.dof.focus_distance = (smoothed(heads, f) - at).length - 0.06    # on his face, not his ear
        cu.data.dof.keyframe_insert("focus_distance", frame=f)
    eye_cam, prev = cams["eye"], None                               # the eye insert keeps the eye centred, in focus
    for f in list(range(T("3.14"), T("3.17"), 6)) + [T("3.17")]:
        e = smoothed(eyes, f)
        q = (e - eye_cam.location).to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), tilt(f))
        eye_cam.rotation_euler = prev = q.to_euler("XYZ", prev) if prev else q.to_euler("XYZ")
        eye_cam.keyframe_insert("rotation_euler", frame=f)
        eye_cam.data.dof.focus_distance = (e - eye_cam.location).length
        eye_cam.data.dof.keyframe_insert("focus_distance", frame=f)
    cam = cams["lantern_hand"]                                      # fixed: the same aim, rolling
    base, prev = cam.rotation_euler.to_quaternion(), cam.rotation_euler.copy()
    for f in range(T("3.16"), T("3.17") + 1, 6):
        cam.rotation_euler = prev = (base @ Quaternion((0, 0, 1), tilt(f))).to_euler("XYZ", prev)
        cam.keyframe_insert("rotation_euler", frame=f)
    whip = T("3.17", 1.0)
    su.animate_camera(cams["ws"], [(T("3.17"), rigs["ws"]["at"], (-1.4, -2.2, 1.2)),
                                   (whip, rigs["ws"]["at"], (-1.0, -1.2, 1.1)),
                                   (whip + 6, rigs["ws"]["at"], (0.4, 1.0, 0.85)),
                                   (T("3.18"), rigs["ws"]["at"], (0.45, 1.1, 0.8))])
    # the grate in 3.11: a little moonlight down the chimney, so the falling soot reads
    grate = su.light("V3_LIGHT_Chimney", C["SET"], "AREA", (-2.22, 0.5, 0.85), 0, (0.6, 0.7, 1.0),
                     target=(-2.22, 0.5, 0.0), size=0.3)
    for f, e in ((1, 0), (s0 - 4, 0), (s0, 120), (s0 + 40, 120), (s0 + 44, 0)):
        grate.data.energy = e
        grate.data.keyframe_insert("energy", frame=f)

    cuts = [("3.11", 0.0, "om_ms"),
            ("3.11", (m0 - start["3.11"]) / FPS, "mouse"),
            ("3.11", (m0 - start["3.11"]) / FPS + 1.8, "om_ms"),
            ("3.12", 0.0, "wall"), ("3.13", 0.0, "crevice"), ("3.13", 3.6, "ray"), ("3.14", 0.0, "eye"),
            ("3.15", 0.0, "nar_cu"), ("3.16", 0.0, "eye"), ("3.16", 1.6, "nar_cu"), ("3.16", 3.4, "lantern_hand"),
            ("3.16", 4.6, "eye"), ("3.16", 5.7, "nar_cu"), ("3.16", 7.0, "eye"), ("3.16", 7.8, "nar_cu"),
            ("3.16", 8.7, "eye"), ("3.16", 9.3, "nar_cu"), ("3.16", 10.0, "eye"), ("3.16", 10.5, "nar_cu"),
            ("3.17", 0.0, "ws"), ("3.18", 0.0, "top"), ("3.20", 0.0, "floor"), ("3.21", 0.0, "hand")]
    for sid, sec, cam in cuts:
        marker = scene.timeline_markers.new(f"SHOT_{sid}_{cam}_{sec:.1f}", frame=T(sid, sec))
        marker.camera = cams[cam]
    scene.camera = cams["om_ms"]

    OUT.mkdir(parents=True, exist_ok=True)
    marks = dict(release=RELEASE, flood=FL, grab=GRAB, drag=D0, pull=G0, kneel=K0, dead=DEAD, landed=D0 + 20)
    (OUT / "timeline.json").write_text(json.dumps(dict(tl, marks={k: (v - 1) / FPS for k, v in marks.items()}), indent=1))
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    su.save_blend(BLEND, compress=True)
    print(f"V3 built: {len(tl['shots'])} shots, {end} frames ({tl['seconds']:.1f} s) -> {BLEND.name}")


# ----------------------------------------------------------------------------------------------- helpers
def _fcurves(obj, data=None):
    """F-curves of an object's (or ID's) action (Blender 5 layered actions)."""
    ad = (data or obj).animation_data
    if ad is None or ad.action is None:
        return
    for layer in ad.action.layers:
        for strip in layer.strips:
            yield from strip.channelbag(ad.action_slot).fcurves


def _shape_fcurves(obj):
    return _fcurves(obj, obj.data.shape_keys)


def _sample_path(path, first, last):
    """Waypoints [(frame, (x, y), heading)] -> {frame: ((x, y), heading)}, eased between waypoints (a
    person speeds up and slows down) and holding before the first / after the last."""
    out = {}
    for f in range(first, last + 1):
        if f <= path[0][0]:
            out[f] = (path[0][1], path[0][2])
            continue
        if f >= path[-1][0]:
            out[f] = (path[-1][1], path[-1][2])
            continue
        i = max(k for k in range(len(path)) if path[k][0] <= f)
        (f0, p0, h0), (f1, p1, h1) = path[i], path[i + 1]
        u = (f - f0) / max(1, f1 - f0)
        # gentle ease only at the ends of a run of moving segments: constant speed in between
        prev_moving = i > 0 and path[i - 1][1] != p0
        next_moving = i + 2 < len(path) and path[i + 2][1] != p1
        if not prev_moving and not next_moving:
            u = u * u * (3 - 2 * u)
        elif not prev_moving:
            u = u * u * (2 - u) if u < 1 else 1.0
            u = min(1.0, u)
        elif not next_moving:
            u = 1 - (1 - u) * (1 - u)
        dh = (h1 - h0 + 180) % 360 - 180
        out[f] = ((p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u), h0 + dh * u)
    return out


# The narrator's steps are motion capture (100STYLE, CC BY 4.0): one stride of a plain walk and one of a
# hurried walk, blended by speed. (clip, frames searched for its straightest, fastest stretch)
GAIT_CLIPS = (("Neutral_FW", 240), ("Rushed_FW", 240))
LEGS = tuple(f"{s}{b}" for s in ("Left", "Right") for b in ("UpLeg", "Leg", "Foot", "ToeBase"))
SPINE = ("LowerBack", "Spine", "Spine1")
ARMS = tuple(f"{s}{b}" for s in ("Left", "Right") for b in ("Shoulder", "Arm", "ForeArm", "Hand"))


def _gait_cycle(humans, clip, frames, fps=FPS):
    """One stride of a mocap walk on the narrator's own skeleton, from a left-foot contact to the next:
    every bone's rotation per sample (the hips turned to walk straight ahead, -Y), the hips' bob and sway
    about a steady line (armature space), the mean pose (for layering swings on top of other motion), the
    stride length and the speed. The stride's two ends are made to meet, so it loops."""
    import bpy
    from mathutils import Matrix, Quaternion, Vector
    scene = bpy.context.scene
    bvh = ROOT / "assets" / "mocap" / "100style" / f"{clip}.bvh"
    skip = humans.straight_stretch(bvh, frames)
    kinds = ("objects", "meshes", "armatures", "actions", "shape_keys", "materials", "node_groups", "images")
    had = {k: set(getattr(bpy.data, k)) for k in kinds}
    tmp = humans.build({"name": "GaitTmp", "character": "Narrator"})
    humans.retarget(tmp, bvh, start_frame=1 - skip, max_frames=skip + frames)
    names = ("Hips",) + LEGS + SPINE + ARMS
    hips_rest = tmp.data.bones["Hips"].matrix_local.to_3x3().normalized()
    rec = []
    for f in range(1, frames + 1):
        scene.frame_set(f)
        hm = tmp.pose.bones["Hips"].matrix
        rec.append(dict(q={n: tmp.pose.bones[n].rotation_quaternion.copy() for n in names},
                        hip=hm.translation.copy(), hipm=hm.to_3x3().normalized(),
                        ball={s: tmp.pose.bones[f"{s}ToeBase"].matrix.translation.copy() for s in ("Left", "Right")},
                        ankle={s: tmp.pose.bones[f"{s}Foot"].matrix.translation.copy() for s in ("Left", "Right")}))
    leg = (tmp.data.bones["LeftUpLeg"].head_local - tmp.data.bones["LeftFoot"].head_local).length
    for o in list(tmp.children) + [tmp]:
        bpy.data.objects.remove(o)
    for _ in range(3):                    # the copy's meshes, materials, images ... nothing else uses them
        for k in kinds[1:]:
            for block in set(getattr(bpy.data, k)) - had[k]:
                if block.users == 0:
                    getattr(bpy.data, k).remove(block)
    # footfalls, by gait_stats.py's rule: the heel or ball low and the ball nearly still
    low = {s: min(min(r["ball"][s].z, r["ankle"][s].z) for r in rec) for s in ("Left", "Right")}
    down = {}
    for s in ("Left", "Right"):
        fl = [False] + [min(rec[i]["ball"][s].z, rec[i]["ankle"][s].z) - low[s] < 0.07 * leg and
                        (rec[i]["ball"][s].xy - rec[i - 1]["ball"][s].xy).length * fps < 0.35 * leg
                        for i in range(1, frames)]
        for i in range(1, frames - 1):                       # close 1-frame gaps, drop 1-frame blips
            fl[i] = (fl[i - 1] and fl[i + 1]) or (fl[i] and (fl[i - 1] or fl[i + 1]))
        down[s] = fl
    lands = {s: [i for i in range(1, frames) if down[s][i] and not down[s][i - 1]] for s in down}

    def drift(s, e):
        """How far the hips stray sideways from the straight line between the stride's ends (a stride on a
        curve, where the actor turns at the end of the capture area, would over-step and sway)."""
        a, b = rec[s]["hip"].xy, rec[e]["hip"].xy
        u = (b - a).normalized()
        return max(abs((rec[i]["hip"].xy - a).cross(u)) for i in range(s, e + 1))
    # a stride: left footfall to the next, the right one about halfway, straight, really walking
    strides = []
    for s, e in zip(lands["Left"], lands["Left"][1:]):
        mid = [r for r in lands["Right"] if s < r < e]
        if (len(mid) == 1 and 0.3 < (mid[0] - s) / (e - s) < 0.7 and 0.6 * fps <= e - s <= 1.6 * fps
                and (rec[e]["hip"] - rec[s]["hip"]).xy.length > 0.3 and drift(s, e) < 0.05):
            strides.append((s, e))
    if not strides:
        raise RuntimeError(f"{clip}: no clean stride found (left footfalls {lands['Left']})")
    typical = sorted(e - s for s, e in strides)[len(strides) // 2]

    def seam(s, e):
        return sum(rec[s]["q"][n].rotation_difference(rec[e]["q"][n]).angle for n in LEGS + ("Hips",))
    s, e = min(strides, key=lambda p: (abs(p[1] - p[0] - typical), seam(*p)))
    P = e - s
    travel = (rec[e]["hip"] - rec[s]["hip"]).xy
    turn = Matrix.Rotation(-math.pi / 2 - math.atan2(travel.y, travel.x), 3, "Z")     # stride -> straight ahead
    q, bob = [], []
    for i in range(P + 1):
        r = rec[s + i]
        line = rec[s]["hip"] + (rec[e]["hip"] - rec[s]["hip"]) * (i / P)
        bob.append(turn @ (r["hip"] - line))
        sample = dict(r["q"])
        sample["Hips"] = (hips_rest.inverted() @ (turn @ r["hipm"])).to_quaternion()
        q.append(sample)
    for n in q[0]:                                     # close the loop: spread the seam over the stride
        for i in range(1, P + 1):
            if q[i][n].dot(q[i - 1][n]) < 0:
                q[i][n].negate()
        fix = q[0][n] @ q[P][n].inverted()
        for i in range(P + 1):
            q[i][n] = Quaternion().slerp(fix, i / P) @ q[i][n]
    centre = sum(bob[:P], Vector()) / P                # bob and sway about the steady line, nothing more
    bob = [b - centre for b in bob]                    # (both walks start at a left footfall: in step)
    mean = {}
    for n in q[0]:
        acc = Quaternion((0, 0, 0, 0))
        for i in range(P):
            acc += q[i][n] if q[i][n].dot(q[0][n]) >= 0 else -q[i][n]
        mean[n] = acc.normalized()
    stride = travel.length
    stance = {side: [down[side][s + i] for i in range(P + 1)] for side in down}   # the mocap's own footfalls
    return dict(clip=clip, q=q, bob=bob, mean=mean, frames=P, stride=stride, speed=stride * fps / P,
                drift=drift(s, e), candidates=len(strides), stance=stance)


def _cycle_at(cyc, phase):
    """A cycle's pose and hips bob at a phase (strides; any real number, so it can run backward)."""
    x = (phase % 1.0) * cyc["frames"]
    i = min(int(x), cyc["frames"] - 1)
    t = x - i
    return ({n: cyc["q"][i][n].slerp(cyc["q"][i + 1][n], t) for n in cyc["q"][i]},
            cyc["bob"][i].lerp(cyc["bob"][i + 1], t))


def _mocap_gait(humans, rig, track, first, last, hands_busy, fps=FPS, clips=GAIT_CLIPS):
    """Steps for a body moved along `track` (its object carries it), from two mocap strides on its own
    skeleton (a plain and a hurried walk) blended by speed. The stride advances with the distance the body
    covers, so each step is as long as the ground it gains: walking backward plays it backward, and faster
    than the hurried walk raises the cadence. Layered on whatever the bones already do: the legs take the
    mocap, the hips, back and (free) arms its swing about their mean. Then each foot is locked to the floor
    for as long as the mocap has it down, and while he stands (a turn on the spot becomes two small steps):
    _plant_feet_world. Prints how much they slide."""
    import bpy
    from mathutils import Quaternion, Vector
    scene = bpy.context.scene
    slow, fast = (_gait_cycle(humans, c, n) for c, n in clips)
    for c in (slow, fast):
        print(f"V3 gait: {c['clip']} {c['speed']:.2f} m/s, stride {c['stride']:.2f} m in {c['frames']} frames, "
              f"hips stray {100 * c['drift']:.1f} cm (of {c['candidates']} strides)")
    frames = list(range(first, last + 1))
    step = {}
    for f in frames:
        (x0, y0), h0 = track[max(first, f - 1)]
        (x1, y1), h1 = track[f]
        hd = math.radians(h1)
        v = Vector((x1 - x0, y1 - y0))
        fwd = v.dot(Vector((math.sin(hd), -math.cos(hd))))
        lat = v.dot(Vector((math.cos(hd), math.sin(hd))))
        size = math.sqrt(fwd * fwd + lat * lat)
        step[f] = math.copysign(size, fwd) if abs(fwd) > 1e-5 else size
    speed = {f: fps * sum(abs(step.get(f + d, step[f])) for d in range(-3, 4)) / 7 for f in frames}
    phase, plan = 0.0, {}
    for f in frames:
        w = min(1.0, max(0.0, (speed[f] - slow["speed"]) / (fast["speed"] - slow["speed"])))
        phase += step[f] / (slow["stride"] + (fast["stride"] - slow["stride"]) * w)
        plan[f] = (phase, w)
    amt0 = {f: ease(0.02, 0.35, speed[f]) for f in frames}                # standing .. walking
    amt = {f: sum(amt0.get(f + d, amt0[f]) for d in range(-4, 5)) / 9 for f in frames}
    busy = sorted(hands_busy)
    free = {f: 0.0 if f in hands_busy else min(1.0, min((abs(f - b) for b in busy), default=99) / 6) for f in frames}

    for f in frames:                                   # nothing of the walk outside its frames
        amt[f] *= min(1.0, (f - first) / 4, (last - f) / 4)
    names = ("Hips",) + LEGS + SPINE + ARMS
    for n in names:
        rig.pose.bones[n].rotation_mode = "QUATERNION"
    hips_rest = rig.data.bones["Hips"].matrix_local.to_3x3().normalized()
    base = {}
    for f in [first - 1] + frames + [last + 1]:
        scene.frame_set(f)
        base[f] = ({n: rig.pose.bones[n].rotation_quaternion.copy() for n in names},
                   rig.pose.bones["Hips"].location.copy())
    for f in (first - 1, last + 1):                    # hold the motion around it as it was
        for n in names:
            rig.pose.bones[n].rotation_quaternion = base[f][0][n]
            rig.pose.bones[n].keyframe_insert("rotation_quaternion", frame=f)
        rig.pose.bones["Hips"].location = base[f][1]
        rig.pose.bones["Hips"].keyframe_insert("location", frame=f)
    ident = Quaternion()
    # the legs hang from the hips as the mocap has them (its pelvis tilt included, or every step would be
    # tipped: feet high at the front of a step and through the floor at the back); the lower back takes the
    # pelvis's mean tilt out again, so the trunk stands as it did
    rest3 = {n: rig.data.bones[n].matrix_local.to_3x3().normalized() for n in ("Hips", "LowerBack")}
    hips_to_back = rest3["Hips"].inverted() @ rest3["LowerBack"]
    for f in frames:
        ph, w = plan[f]
        a = amt[f]
        qs, bs = _cycle_at(slow, ph)
        qf, bf = _cycle_at(fast, ph)
        q0, loc0 = base[f]
        tilt = slow["mean"]["Hips"].slerp(fast["mean"]["Hips"], w)
        untilt = (hips_to_back.inverted() @ tilt.inverted().to_matrix() @ hips_to_back).to_quaternion()
        for n in names:
            walk = qs[n].slerp(qf[n], w)
            if n in LEGS or n == "Hips":
                q = q0[n] @ ident.slerp(walk, a)
            else:
                mean = slow["mean"][n].slerp(fast["mean"][n], w)
                swing = ident.slerp(mean.inverted() @ walk, a * (0.7 if n in SPINE else free[f] if n in ARMS else 1.0))
                q = q0[n] @ (ident.slerp(untilt, a) @ swing if n == "LowerBack" else swing)
            pb = rig.pose.bones[n]
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f)
        hb = rig.pose.bones["Hips"]
        hb.location = loc0 + hips_rest.inverted() @ (bs.lerp(bf, w) * a)
        hb.keyframe_insert("location", frame=f)

    def lean(f):                     # forward into a hurry; back a little hauling something backward
        return {"LowerBack": (0, amt[f] * (min(10.0, 1.5 + 3.5 * speed[f]) if step[f] >= 0 else -3.0), 0)}
    humans._layer(rig, first, last, lean)
    # which foot is down: the mocap's own footfalls while he walks, both while he stands
    stance = {s: {} for s in ("Left", "Right")}
    for f in frames:
        ph, w = plan[f]
        c = fast if w > 0.5 else slow
        i = int(round((ph % 1.0) * c["frames"])) % c["frames"]
        for s in stance:
            stance[s][f] = c["stance"][s][i] if amt[f] > 0.3 else None
    _plant_feet_world(humans, rig, first, last, amt, stance)


def _plant_feet_world(humans, rig, start, end, amount, stance, floor=0.0, blend=3):
    """humans.plant_feet for a body whose object is moved (that one locks feet in armature space, which here
    moves with him). stance[side][frame]: True/False while he walks (the mocap's own footfalls), None while
    he stands (both feet down). Each contact is locked to its average spot on the floor and the leg solved
    with the toolkit's two-bone IK. While standing, a turn of the body becomes small steps: each foot is
    picked up (a few cm) and set down again as the turn passes it, the left first. Before that the body is
    lowered or raised, footfall by footfall, so planted balls rest on the floor (only while walking, via the
    hips). He stands still at both ends of the range, so the locks meet the motion around it. Prints
    how much planted feet slide before and after."""
    import bpy
    from mathutils import Vector
    scene = bpy.context.scene
    fps = scene.render.fps
    sides = {"Left": ("LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase"),
             "Right": ("RightUpLeg", "RightLeg", "RightFoot", "RightToeBase")}
    names = ["Hips"] + [n for c in sides.values() for n in c]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    frames = list(range(start, end + 1))
    n = len(frames)
    hips_rest = rest["Hips"].to_3x3().normalized()

    def sample():
        pose, world = {}, {}
        for f in frames:
            scene.frame_set(f)
            pose[f] = {b: rig.pose.bones[b].matrix.copy() for b in names}
            world[f] = rig.matrix_world.copy()
        balls = {s: {f: world[f] @ pose[f][c[3]].translation for f in frames} for s, c in sides.items()}
        return pose, world, balls

    def runs(flags):
        out, i = [], 0
        while i < n:
            if flags[i]:
                j = i
                while j + 1 < n and flags[j + 1]:
                    j += 1
                if j - i >= 1:
                    out.append((i, j))
                i = j + 1
            else:
                i += 1
        return out

    walking = {s: [stance[s][f] is not None for f in frames] for s in sides}
    down = {s: [stance[s][f] is None or bool(stance[s][f]) for f in frames] for s in sides}

    def skate(balls, locked):
        """cm/s a locked foot still moves, and frames a free foot skims the floor (low and fast)."""
        held, low = [], 0
        for s in sides:
            for i in range(1, n):
                f, g = frames[i], frames[i - 1]
                v = (balls[s][f].xy - balls[s][g].xy).length * fps
                if f in locked[s] and g in locked[s]:
                    held.append(v)
                elif v > 0.4 and balls[s][f].z < floor + ball_rest + 0.01:
                    low += 1
        return 100 * sum(held) / max(1, len(held)), low

    toe, ankle = rest["LeftToeBase"].translation.z, rest["LeftFoot"].translation.z
    ball_rest = toe - min(toe, ankle) + 0.022                                   # ball joint height, foot flat
    pose, world, balls = sample()
    # the body's height, footfall by footfall: each walking stance should have its ball on the floor; how
    # far off it is, blended between footfalls and only while walking, moves the hips
    need = sorted(((i + j) / 2, (floor + ball_rest) - min(balls[s][frames[k]].z for k in range(i, j + 1)))
                  for s in sides for i, j in runs([d and w for d, w in zip(down[s], walking[s])]))
    lift = {}
    for k, f in enumerate(frames):
        if not need:
            lift[f] = 0.0
            continue
        after = next((x for x in need if x[0] >= k), need[-1])
        before_ = next((x for x in reversed(need) if x[0] <= k), need[0])
        t = 0.0 if after[0] == before_[0] else (k - before_[0]) / (after[0] - before_[0])
        lift[f] = max(-0.06, min(0.06, before_[1] + (after[1] - before_[1]) * t))
    smooth = {f: sum(lift[frames[min(n - 1, max(0, k + d))]] for d in range(-5, 6)) / 11 for k, f in enumerate(frames)}
    for f in frames:
        scene.frame_set(f)
        hb = rig.pose.bones["Hips"]
        hb.location = hb.location + hips_rest.inverted() @ Vector((0, 0, smooth[f] * amount.get(f, 0)))
        hb.keyframe_insert("location", frame=f)
    pose, world, balls = sample()
    heading = [world[f].to_euler().z for f in frames]
    plans, locked = {}, {}
    for side, (up, low, foot, _) in sides.items():
        # contacts; a standing contact during which the body turns is cut into steps, staggered by foot
        spans = []
        first_cut = math.radians(25 if side == "Left" else 50)
        for i, j in runs(down[side]):
            # a contact that goes from walking to standing (or back) is two: the foot is set down again.
            # Pieces under 3 frames join their neighbour (a speed hovering at the threshold, the first frames)
            parts, a = [], i
            for k in range(i + 1, j + 1):
                if walking[side][k] != walking[side][k - 1]:
                    parts.append([a, k - 1])
                    a = k
            parts.append([a, j])
            merged = []
            for p in parts:
                if merged and (p[1] - p[0] < 2 or merged[-1][1] - merged[-1][0] < 2):
                    merged[-1][1] = p[1]
                else:
                    merged.append(p)
            for p, (a, b) in enumerate(merged):
                a, b = a + (2 if p > 0 else 0), b - (1 if p < len(merged) - 1 else 0)
                if b - a < 1:
                    continue
                if any(walking[side][a:b + 1]):
                    spans.append((a, b, True))
                    continue
                cuts, turned, at, next_cut = [], 0.0, a, first_cut
                for k in range(a + 1, b + 1):
                    turned += abs((heading[k] - heading[k - 1] + math.pi) % (2 * math.pi) - math.pi)
                    if turned >= next_cut and k - at >= 3 and b - k >= 3:
                        cuts.append(k)
                        at, next_cut = k, next_cut + math.radians(60)
                edges = [a] + cuts + [b + 1]
                for c, d in zip(edges, edges[1:]):
                    spans.append((c + (2 if c != a else 0), d - 1 - (1 if d != b + 1 else 0), False))
        spans.sort()
        spots = [sum((balls[side][frames[k]] for k in range(i, j + 1)), Vector()) / (j - i + 1) for i, j, _ in spans]
        for m, (i, j, _) in enumerate(spans):      # at the ends of the range: where the foot really is
            if i == 0:
                spots[m] = balls[side][frames[0]].copy()
            elif j == n - 1:
                spots[m] = balls[side][frames[-1]].copy()
        weight, want = {}, {}                      # per frame: the lock's strength, where the ball goes

        def put(k, w, ball_to):
            f = frames[k]
            if w > weight.get(f, 0.0):
                weight[f] = w
                want[f] = balls[side][f].lerp(ball_to, w)
        for (i, j, _), spot in zip(spans, spots):
            for k in range(max(0, i - blend), min(n, j + blend + 1)):
                b = balls[side][frames[k]]
                put(k, 1.0 if i <= k <= j else 1 - min(abs(k - i), abs(k - j)) / (blend + 1), Vector((spot.x, spot.y, b.z)))
        for (i0, j0, w0), (i1, j1, w1), s0, s1 in zip(spans, spans[1:], spots, spots[1:]):
            # a step between contacts when he stands, or starts or stops walking: lifted across
            if 0 < i1 - j0 <= (8 if not (w0 and w1) else 0) and (s1 - s0).xy.length > 0.03:
                for k in range(j0 + 1, i1):
                    t = (k - j0) / (i1 - j0)
                    u = t * t * (3 - 2 * t)
                    p = s0.lerp(s1, u)
                    p.z = max(s0.z, s1.z) + 0.045 * math.sin(math.pi * t)
                    weight.pop(frames[k], None)
                    put(k, 1.0, p)
        # a foot moving fast doesn't skim the floor (the end of a swing as he slows, a low mocap swing, a lock
        # blending in or out): checked on where it finally goes
        clear = floor + ball_rest + 0.025
        prev = balls[side][frames[0]]
        for k in range(1, n):
            f = frames[k]
            p = want.get(f, balls[side][f]).copy()
            v = (p.xy - prev.xy).length * fps
            if v > 0.4 and p.z < clear:
                p.z += (clear - p.z) * min(1.0, (v - 0.4) / 0.4)
                want[f] = p
            prev = p
        target = {f: world[f].inverted() @ (world[f] @ pose[f][foot].translation + (p - balls[side][f]))
                  for f, p in want.items()}
        plans[side] = target
        locked[side] = {frames[k] for i, j, _ in spans for k in range(i, j + 1)}
    before = skate(balls, locked)
    for side, (up, low, foot, _) in sides.items():
        for f, t in plans[side].items():
            humans._two_bone(rig, rest, pose[f], f, up, low, foot, t)
    pose, world, balls = sample()
    after = skate(balls, locked)
    walk_lift = [smooth[f] for f in frames if amount.get(f, 0) > 0.5]
    print(f"V3 feet: body raised {100 * sum(walk_lift) / max(1, len(walk_lift)):.1f} cm on average while walking; "
          f"planted feet slide {before[0]:.1f} -> {after[0]:.1f} cm/s; free feet skimming the floor "
          f"{before[1]} -> {after[1]} frames")


def _yaw_to(src, dst):
    """hang(yaw=...) so a dark lantern's lens (local -Y) faces from src toward dst."""
    d = dst - src
    return math.atan2(d.x, -d.y)


def _aim_beam(beam, lantern, target):
    """Point the beam light (a child of the lantern) at a world point, fixed in the lantern's frame."""
    from mathutils import Vector
    local = lantern.matrix_world.inverted() @ target
    d = (local - beam.location).normalized()
    beam.rotation_mode = "QUATERNION"
    beam.rotation_quaternion = Vector((0, 0, -1)).rotation_difference(d)


def _drop(lantern, frame, fps):
    """Let go of the lantern: free fall to the floor, two damped rocks, then still (it lands upright)."""
    import bpy
    scene = bpy.context.scene
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    m = lantern.matrix_world.copy()
    loc, rot = m.translation.copy(), m.to_euler()
    fall = math.sqrt(2 * max(0.01, loc.z) / 9.81)
    n = max(2, math.ceil(fall * fps))                         # its last falling frame is on the floor
    for i in range(n + 1):
        t = i / fps
        lantern.location = (loc.x, loc.y, max(0.0, loc.z - 0.5 * 9.81 * t * t))
        lantern.rotation_euler = (0.0, 0.0, rot.z)
        lantern.keyframe_insert("location", frame=frame + i)
        lantern.keyframe_insert("rotation_euler", frame=frame + i)
    for j, deg in enumerate((9, -5, 2.5, 0)):
        lantern.rotation_euler = (math.radians(deg), 0.0, rot.z)
        lantern.keyframe_insert("rotation_euler", frame=frame + n + 3 * (j + 1))


def _nearest_vertex(obj, world):
    best, dist = 0, 1e9
    inv = obj.matrix_world.inverted()
    p = inv @ world
    for v in obj.data.vertices:
        d = (v.co - p).length
        if d < dist:
            best, dist = v.index, d
    return best


def _split_featherbed(bpy, np, room):
    """The gothic bed model is one mesh. Its bedding (the big draped piece) becomes V3_Featherbed and its
    two pillows V3_Bed_Pillow_0/1, in world coordinates. The pillows stay on the frame when the feather-bed
    is pulled from under them (they drop onto the straw tick). Returns (feather-bed, [pillows])."""
    import bmesh
    bed_obj = bpy.data.objects["CH_Bed_GothicBed_01"]
    bm = bmesh.new()
    bm.from_mesh(bed_obj.data)
    bm.verts.ensure_lookup_table()
    M = bed_obj.matrix_world
    seen, parts = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            comp.append(x.index)
            stack += [e.other_vert(x) for e in x.link_edges]
        pts = np.array([(M @ bm.verts[i].co)[:] for i in comp])
        parts.append((comp, pts))
    parts.sort(key=lambda p: -len(p[0]))
    pillows = [set(comp) for comp, pts in parts[1:]
               if 100 < len(comp) < 200 and pts.mean(0)[1] > 1.85 and 0.38 < pts.mean(0)[2] < 0.62]

    def piece(name, keep, smooth):
        """A world-space copy of the bed mesh with only `keep` (its material slots kept in order)."""
        b = bmesh.new()
        b.from_mesh(bed_obj.data)
        b.verts.ensure_lookup_table()
        bmesh.ops.delete(b, geom=[b.verts[i] for i in range(len(b.verts)) if i not in keep], context="VERTS")
        b.transform(M)
        me = bpy.data.meshes.new(name)
        b.to_mesh(me)
        b.free()
        for mat in bed_obj.data.materials:
            me.materials.append(mat)
        o = bpy.data.objects.new(name, me)
        bed_obj.users_collection[0].objects.link(o)
        if smooth:
            for p in me.polygons:
                p.use_smooth = True
        return o
    obj = piece("V3_Featherbed", set(parts[0][0]), True)
    pillow_objs = [piece(f"V3_Bed_Pillow_{i}", keep, True) for i, keep in enumerate(pillows)]
    taken = set(parts[0][0]).union(*pillows)
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in taken], context="VERTS")
    bm.to_mesh(bed_obj.data)
    bm.free()
    if room.get("pillow") is not None:
        for p in room["pillow"].data.polygons:
            p.use_smooth = True
        pillow_objs.append(room["pillow"])
    return obj, pillow_objs


def _height_field(bpy, np, objects, xs, ys, step):
    """Top surface height (z) over a grid of the given objects and the floor, cloth-like: spread so the
    feather-bed spans the gaps between a body and the bed instead of dropping into them. Returns h(x, y)."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    deps = bpy.context.evaluated_depsgraph_get()
    trees = [BVHTree.FromObject(o, deps) for o in objects if o.type == "MESH"]
    mats = [o.matrix_world for o in objects if o.type == "MESH"]
    gx = np.arange(xs[0], xs[1] + 1e-9, step)
    gy = np.arange(ys[0], ys[1] + 1e-9, step)
    H = np.zeros((len(gy), len(gx)))
    for (tree, m) in zip(trees, mats):
        inv = m.inverted()
        for j, y in enumerate(gy):
            for i, x in enumerate(gx):
                o = inv @ Vector((x, y, 3.0))
                d = (inv.to_3x3() @ Vector((0, 0, -1))).normalized()
                hit = tree.ray_cast(o, d, 6.0)
                if hit[0] is not None:
                    H[j, i] = max(H[j, i], (m @ hit[0]).z)
    # a heavy feather-bed bridges: dilate (max over ~4 cm), then blur (~5 cm), never below the surface
    def shift_max(a, r):
        out = a.copy()
        for dj in range(-r, r + 1):
            for di in range(-r, r + 1):
                if di * di + dj * dj <= r * r:
                    out = np.maximum(out, np.roll(np.roll(a, dj, 0), di, 1))
        return out

    def blur(a, sigma):
        k = np.exp(-0.5 * (np.arange(-3 * sigma, 3 * sigma + 1) / sigma) ** 2)
        k /= k.sum()
        a = np.apply_along_axis(lambda r: np.convolve(np.pad(r, 3 * sigma, mode="edge"), k, "valid"), 1, a)
        return np.apply_along_axis(lambda c: np.convolve(np.pad(c, 3 * sigma, mode="edge"), k, "valid"), 0, a)
    Hs = np.maximum(H, blur(shift_max(H, 2), 3))

    def sampler(A):
        def h(x, y):
            fx = min(max((x - xs[0]) / step, 0), len(gx) - 1.001)
            fy = min(max((y - ys[0]) / step, 0), len(gy) - 1.001)
            i, j = int(fx), int(fy)
            u, v = fx - i, fy - j
            return float((A[j, i] * (1 - u) + A[j, i + 1] * u) * (1 - v) + (A[j + 1, i] * (1 - u) + A[j + 1, i + 1] * u) * v)
        return h
    h = sampler(Hs)
    h.raw = sampler(H)                                   # the surfaces themselves
    h.soft = sampler(blur(shift_max(H, 4), 6))           # what a thick quilt feels through itself (~8 + 12 cm)
    return h


def _press_mask(np, segments, inner=0.06, outer=0.17):
    """0..1 weight of how hard a point (x, y) is pressed flat by limbs lying along `segments` (2D)."""
    segs = [(np.array(a[:2], float), np.array(b[:2], float)) for a, b in segments]

    def w(x, y):
        p, best = np.array((x, y)), 9.0
        for a, b in segs:
            ab = b - a
            t = min(max(float((p - a) @ ab) / max(float(ab @ ab), 1e-9), 0.0), 1.0)
            best = min(best, float(np.linalg.norm(p - (a + t * ab))))
        u = min(max((best - inner) / (outer - inner), 0.0), 1.0)
        return 1.0 - u * u * (3 - 2 * u)
    return w


def _surface(np, obj, arr, dx):
    """top(x, y, default): the height of shape `arr` (object coordinates, object moved `dx` in x) by a ray down."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    M = obj.matrix_world.copy()
    M.translation.x += dx - obj.location.x
    tree = BVHTree.FromPolygons([M @ Vector(v) for v in arr], [tuple(p.vertices) for p in obj.data.polygons])

    def top(x, y, default=None):
        hit = tree.ray_cast(Vector((x, y, 3.0)), Vector((0, 0, -1)), 6.0)[0]
        return hit.z if hit is not None else default
    return top


def _featherbed_shapes(np, obj, heights, dx, press):
    """Shape keys on the feather-bed: 'pulled' (its west side lifted and drawn toward him as he hauls the
    foot corner), 'draped' (lying on whatever is under it once moved `dx` west: the straw tick, his body, the
    floor) and 'pressed' (the same, flattened under the narrator's knees and shins: `press(x, y)` 0..1).
    The model is one draped sheet with hanging sides; draped, the sides fall open onto what is beside it,
    and the top lies a soft ~9 cm over what is under it (a thick quilt feels the body, not the nose),
    thinning to its edges, which lie on the floor. Returns (top of 'draped', top of 'pressed') as h(x, y)."""
    me = obj.data
    co = np.array([v.co[:] for v in me.vertices])
    west, east = co[:, 0].min(), co[:, 0].max()
    south, north = co[:, 1].min(), co[:, 1].max()
    cx, cy = (west + east) / 2, (south + north) / 2
    ups = [(p.center.z, p.area) for p in me.polygons if p.normal.z > 0.8]
    top = float(np.average([z for z, _ in ups], weights=[a for _, a in ups]))   # where it lay on the bed
    obj.shape_key_add(name="Basis", from_mix=False)
    pulled = co.copy()
    w = np.clip((west + 0.65 - co[:, 0]) / 0.65, 0, 1) ** 1.5
    w *= 0.55 + 0.45 * np.clip((south + 0.9 - co[:, 1]) / 0.9, 0, 1)
    pulled[:, 2] += 0.34 * w
    pulled[:, 0] -= 0.08 * w
    # unfold: a point a hanging side held `drop` below the top moves out by about that much
    drop = np.clip(top - 0.02 - co[:, 2], 0, None)
    flat = co[:, :2].copy()
    for i, (x, y, z) in enumerate(co):
        if drop[i] <= 0:
            continue
        ox, oy = x - cx, y - cy
        if abs(ox) / (east - cx) > abs(oy) / (north - cy):
            flat[i, 0] += math.copysign(drop[i], ox)                    # the long sides fall open
        else:                                                           # the foot end a little (his feet stay
            flat[i, 1] += math.copysign(drop[i] * (0.35 if oy < 0 else 0.10), oy)   # out); the head end barely
    X0, X1, Y0, Y1 = flat[:, 0].min(), flat[:, 0].max(), flat[:, 1].min(), flat[:, 1].max()
    inside = np.minimum.reduce([flat[:, 0] - X0, X1 - flat[:, 0], flat[:, 1] - Y0, Y1 - flat[:, 1]])
    s = np.clip(inside / 0.28, 0, 1)
    rise = 0.012 + 0.075 * s * s * (3 - 2 * s)
    # near its edges it lies on what is really there (his shins, the floor between them), not on the soft
    # bridge over it; at the foot end over a wider band, so it closes down over his legs
    hug = np.minimum(np.clip(inside / 0.15, 0, 1), np.clip((flat[:, 1] - Y0) / 0.25, 0, 1))
    hug = hug * hug * (3 - 2 * hug)
    relief = np.clip(co[:, 2] - top, 0, None) * 0.5                     # its own folds stay, a little
    draped, pressed = co.copy(), co.copy()
    for i in range(len(co)):
        wx, wy = flat[i, 0] + dx, flat[i, 1]
        floor = heights.raw(wx, wy)
        lying = floor + 0.016 + 0.012 * (0.5 + 0.5 * math.sin(wx * 23 + wy * 9))   # soft folds where it lies flat
        z = max(floor + 0.016, lying * (1 - hug[i]) + (heights.soft(wx, wy) + rise[i] + relief[i]) * hug[i])
        k = press(wx, wy)
        draped[i] = (flat[i, 0], flat[i, 1], z)
        pressed[i] = (flat[i, 0], flat[i, 1], z * (1 - k) + (floor + 0.012) * k)
    for name, arr in (("pulled", pulled), ("draped", draped), ("pressed", pressed)):
        kb = obj.shape_key_add(name=name, from_mix=False)
        kb.data.foreach_set("co", arr.astype(np.float64).ravel())
    print(f"V3 feather-bed: top {top:.3f}, draped footprint x {X0 + dx:.2f}..{X1 + dx:.2f}, y {Y0:.2f}..{Y1:.2f}")
    return _surface(np, obj, draped, dx), _surface(np, obj, pressed, dx)


def _blanket_shapes(np, sheet, heights, dx, mattress, quilt, quilt_pressed, press):
    """The blanket over his legs: 'flat' (his legs gone from under it, it lies on the feather-bed), and
    'pulled' / 'draped' / 'pressed' matching the feather-bed's, as deltas on top of 'flat' (shape keys add
    up). Draped, it lies on the feather-bed's top (`quilt(x, y)`), or on the floor past its edge."""
    me = sheet.data
    if me.shape_keys is None:
        sheet.shape_key_add(name="Basis", from_mix=False)
    n = len(me.vertices)
    basis = np.empty(n * 3)
    me.shape_keys.key_blocks[0].data.foreach_get("co", basis)
    basis = basis.reshape(-1, 3)
    M = np.array(sheet.matrix_world)
    world = basis @ M[:3, :3].T + M[:3, 3]
    inv = np.linalg.inv(M)
    top = mattress + 0.035
    flat = world.copy()
    up = flat[:, 2] > top
    flat[up, 2] = top
    west, south = flat[:, 0].min(), flat[:, 1].min()
    w = np.clip((west + 0.65 - flat[:, 0]) / 0.65, 0, 1) ** 1.5 * (0.55 + 0.45 * np.clip((south + 0.9 - flat[:, 1]) / 0.9, 0, 1))
    lift = np.zeros_like(flat)
    lift[:, 2] = 0.34 * w + 0.01
    lift[:, 0] = -0.08 * w
    draped = flat.copy()
    cx = (flat[:, 0].min() + flat[:, 0].max()) / 2
    for i, (x, y, z) in enumerate(flat):
        if z < top - 0.002:                               # its hanging sides fall open, part folded under
            x = x + math.copysign(0.6 * (top - z), x - cx)
        draped[i] = (x, y, 0.0)
    pressed = draped.copy()
    for arr, surf in ((draped, quilt), (pressed, quilt_pressed)):
        for i, (x, y, _) in enumerate(arr):
            under = surf(x + dx, y)
            floor = heights.raw(x + dx, y)
            fold = 0.010 * (0.5 + 0.5 * math.sin((x + dx) * 21 + y * 11)) * float(under is None or under < floor + 0.04)
            arr[i, 2] = (under if under is not None else floor) + 0.008 + fold
    for i, (x, y, z) in enumerate(pressed):
        k = press(x + dx, y)
        pressed[i, 2] = z * (1 - k) + (heights.raw(x + dx, y) + 0.02) * k
    local = lambda a: a @ inv[:3, :3].T + inv[:3, 3]
    for name, arr in (("flat", local(flat)), ("pulled", basis + local(flat + lift) - local(flat)),
                      ("draped", basis + local(draped) - local(flat)), ("pressed", basis + local(pressed) - local(flat))):
        kb = sheet.shape_key_add(name=name, from_mix=False)
        kb.data.foreach_set("co", arr.astype(np.float64).ravel())


def _beat(f, beats_spec, tl, fps):
    """0..1 pulse on the old man's heartbeats (the muffled run), for hands that feel it under them."""
    start = {s["id"]: s["start"] for s in tl["shots"]}
    t = (f - 1) / fps
    for sid, off, b0, b1, eid, eoff, muffled in beats_spec:
        if not muffled:
            continue
        t0, t1 = start[sid] + off, start[eid] + eoff
        if not (t0 <= t <= t1):
            continue
        tt, last = t0, t0
        while tt <= t:
            last = tt
            tt += 60.0 / (b0 + (b1 - b0) * (tt - t0) / max(t1 - t0, 1e-6))
        return math.exp(-((t - last) / 0.08) ** 2)
    return 0.0


# ----------------------------------------------------------------------------------------------- sound
def soundtrack(out_wav):
    """Voices, the film's sound effects and score (synthesised by scripts/sound_library.py, recorded Freesound
    takes where the film lists them), the heartbeat runs, and a few actions of this scene. Runs inside
    Blender: numpy for the mix, Blender's own decoder (aud) for the MP3s, so no ffmpeg is needed."""
    import aud
    import numpy as np
    sys.path[:0] = [str(ROOT / "scripts"), str(HERE)]
    import film
    from sound_library import LOOPS, RATE, heart, loop, music, sfx, thud, scrape, norm
    tl = json.loads((OUT / "timeline.json").read_text())
    shots = {s["id"]: s for s in tl["shots"]}
    marks = tl["marks"]
    total = tl["seconds"] + 1.5
    buf = np.zeros((int(total * RATE), 2), np.float32)

    def put(x, at, gain=1.0, pan=0.0):
        a = int(at * RATE)
        if a >= len(buf):
            return
        x = np.asarray(x, np.float32)[: len(buf) - a]
        buf[a:a + len(x), 0] += x * gain * (1 - max(0, pan))
        buf[a:a + len(x), 1] += x * gain * (1 + min(0, pan))

    def recording(name, longest=None):
        s = aud.Sound(str(ROOT / "audio" / "sfx" / "freesound" / name))
        try:
            s = s.resample(RATE, aud.RESAMPLE_QUALITY_MEDIUM)
        except (AttributeError, TypeError):
            s = s.resample(RATE, True)
        s = s.rechannel(1)
        x = np.asarray(s.data(), np.float32)[:, 0]
        if longest:
            x = x[: int(longest * RATE)]
            fade = min(len(x), int(0.05 * RATE))
            x[-fade:] *= np.linspace(1, 0, fade)
        return x
    film_shot = {s["id"]: s for s in film.SHOTS}
    for sid, s in shots.items():
        fs = film_shot[sid]
        t0, dur = s["start"], s["seconds"]
        cue = fs["music"] or "silence"
        seg = music(cue, t0, dur).copy()
        fade = min(len(seg) // 2, int(0.4 * RATE))
        if fade:
            seg[:fade] *= np.linspace(0, 1, fade)
            seg[-fade:] *= np.linspace(1, 0, fade)
        put(seg, t0, 0.4)
        for name, offset, gain in fs["sfx"]:
            if gain <= 0:
                continue
            at = offset if offset >= 0 else dur + offset
            if name in film.REAL_SFX:
                file, longest = film.REAL_SFX[name]
                x = recording(file, longest if name not in LOOPS else dur - at)
            elif name in LOOPS:
                x = loop(name, max(0.1, dur - at), t0 + at)
            else:
                x = sfx(name)
            put(x, t0 + at, gain * 0.8)
    # the scene's own actions
    put(recording("lantern_shutter_278204.mp3", 0.6), marks["flood"], 0.8)
    put(norm(thud(160, 0.25, 0.9)) * 0.5, marks["release"] + 0.47, 0.6)               # the lantern lands
    put(recording("bed_drag_735345.mp3", 1.6), marks["drag"], 0.6)
    put(norm(thud(55, 0.8, 0.7)), marks["landed"], 0.9)                               # he hits the floor
    put(recording("bed_drag_364988.mp3", 1.4), marks["pull"] + 0.1, 0.55)              # the feather-bed dragged
    put(recording("floorboard_creak_506662.mp3", 1.4), marks["kneel"], 0.5)
    # heartbeats
    for sid, off, b0, b1, eid, eoff, muffled in HEARTBEATS:
        t0, t1 = shots[sid]["start"] + off, shots[eid]["start"] + eoff
        beat = heart(muffled)
        t, beats = t0, []
        while t < t1:
            beats.append(t)
            t += 60.0 / (b0 + (b1 - b0) * (t - t0) / max(t1 - t0, 1e-6))
        for k, t in enumerate(beats):
            frac = k / max(len(beats) - 1, 1)
            put(beat, t, (0.35 + 0.75 * frac ** 1.5) if not muffled else (0.9 - 0.75 * frac))
    # voices, each at the same loudness
    for s in tl["shots"]:
        for line in s["lines"]:
            with wave.open(str(ROOT / line["file"])) as w:
                x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
                if w.getframerate() != RATE:
                    x = np.interp(np.arange(0, len(x), w.getframerate() / RATE), np.arange(len(x)), x)
            x *= 10 ** (-18 / 20) / (np.sqrt(np.mean(x ** 2)) + 1e-9)
            put(x, line["start"], 1.0 if line["who"] == "N" else 0.95, -0.12 if line["who"] == "OM" else 0.0)
    buf /= max(1e-6, np.abs(buf).max()) / 0.95
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    print(f"V3 soundtrack: {out_wav}")
    return out_wav


def render(part, parts, folder="frames", size=None, out=None):
    import bpy
    out = Path(out or OUT)
    scene = bpy.context.scene
    if size:
        scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = size[0], size[1], 100
    frames = list(range(scene.frame_start, scene.frame_end + 1))
    share = frames[int(part) - 1::int(parts)]
    (out / folder).mkdir(parents=True, exist_ok=True)
    for f in share:
        target = out / folder / f"{f:05d}.png"
        if target.exists():
            continue
        scene.frame_set(f)
        scene.render.filepath = str(target)
        scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=True)
    print(f"rendered part {part}/{parts}: {len(share)} frames -> {out / folder}")


def draft(out=None, mix=None, blend_name="V3"):
    """480p draft: frames, soundtrack and an H.264 MP4, encoded by Blender. `out`, `mix(out_wav)`: another
    scene's output folder and soundtrack (preview_v4 reuses this)."""
    import bpy
    out = Path(out or OUT)
    folder = "frames/480p"
    render(1, 1, folder, size=(854, 480), out=out)
    scene = bpy.context.scene
    first, last = scene.frame_start, scene.frame_end
    wav = (mix or soundtrack)(out / "soundtrack_draft.wav")
    ed = bpy.data.scenes.new("Draft480")
    ed.render.fps = FPS
    ed.render.resolution_x, ed.render.resolution_y, ed.render.resolution_percentage = 854, 480, 100
    ed.frame_start, ed.frame_end = first, last
    se = ed.sequence_editor_create()
    strips = se.strips if hasattr(se, "strips") else se.sequences
    img = strips.new_image("frames", str(out / folder / f"{first:05d}.png"), 1, first)
    for f in range(first + 1, last + 1):
        img.elements.append(f"{f:05d}.png")
    strips.new_sound("sound", str(wav), 2, first)
    r = ed.render
    if hasattr(r.image_settings, "media_type"):
        r.image_settings.media_type = "VIDEO"
    r.image_settings.file_format = "FFMPEG"
    r.ffmpeg.format, r.ffmpeg.codec, r.ffmpeg.constant_rate_factor = "MPEG4", "H264", "HIGH"
    r.ffmpeg.audio_codec, r.ffmpeg.audio_bitrate, r.ffmpeg.audio_channels = "AAC", 192, "STEREO"
    r.filepath = str(out / "draft_480p.mp4")
    r.use_sequencer = True
    bpy.ops.render.render(animation=True, scene=ed.name)
    print(f"{blend_name} draft: {out / 'draft_480p.mp4'}")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    {"build": build, "render": lambda: render(*args[1:3]), "draft": draft,
     "soundtrack": lambda: soundtrack(OUT / "soundtrack_draft.wav")}[args[0]]()
