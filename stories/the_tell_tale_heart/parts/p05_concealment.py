"""Part 05, Concealment (4.1-4.6): calm again in the void; in the chamber only his huge shadow works on the wall,
thrown by the lantern on the floor; his hands take up the three loose planks one by one and set them back so that
no eye could tell; he wipes his clean hands and laughs; the corridor clock strikes four, and then: a knock.
(design: docs/superpowers/specs/2026-11-24-tell-tale-heart-whole-film-design.md)"""
import math

VOID_X, CO = 100.0, 20.0               # sets.SET_X["void"], ["corridor"]
KNEEL = (-0.6, -0.73)                  # his knees' spot, south of the loose planks (x -1.2..0, y -0.27..0.27)
LANTERN = (1.4, -0.45)                 # on the floor east of him, 2 m off: his shadow up the bare west wall
STACK = (-0.6, -0.40)                  # where the planks are stacked (solid floor between the hole and his knees)
SHOTS = [("4.1", [("4.1_0_N", "N")], 8.0), ("4.2", [("4.2_0_N", "N")], 6.0), ("4.3", [("4.3_0_N", "N")], 8.0),
         ("4.4", [("4.4_0_N", "N")], 9.0), ("4.5", [("4.5_0_N", "N")], 9.0), ("4.6", [("4.6_0_N", "N")], 8.0)]
ON_CAMERA = ("4.1_0_N",)
SETS = ["void", "chamber", "corridor"]
CAST = ["Narrator"]
CAMERAS = {
    "void": ((VOID_X, 1.75, 1.24), (VOID_X, 0.0, 1.13), 50),
    "wall": ((-1.2, -2.1, 1.2), (-2.5, -0.95, 1.45), 28),             # the west wall only: he is behind the lens
    "floor": ((-0.45, 0.8, 0.75), (-0.6, -0.15, 0.0), 50),
    "top": ((-0.6, -0.42, 2.65), (-0.6, -0.41, 0.0), 35),
    "ms": ((-0.6, 1.05, 1.1), (-0.6, -0.6, 1.0), 50),
    "clock": ((CO, 2.92, 1.66), (CO, 3.58, 1.73), 50),
}
CUTS = [("4.1", 0.0, "void"), ("4.2", 0.0, "wall"), ("4.3", 0.0, "floor"), ("4.4", 0.0, "top"), ("4.5", 0.0, "ms"),
        ("4.6", 0.0, "clock")]
WORK = {"moon": 150, "fill": 4}
LIGHTS = {"4.1": {"vo_top": 450, "vo_rim": 45}, "4.2": WORK, "4.3": WORK, "4.4": WORK, "4.5": WORK,
          "4.6": {"co_moon": 250, "co_fill": 6}}


def act(ctx):
    bpy, humans, cast3d, su, sets = ctx["bpy"], ctx["humans"], ctx["cast3d"], ctx["su"], ctx["sets"]
    import preview_v3 as v3
    import preview_v4 as v4
    from mathutils import Euler, Matrix, Vector
    T, tl, cams, end = ctx["T"], ctx["tl"], ctx["cams"], ctx["end"]
    scene = bpy.context.scene
    nar = ctx["rigs"]["Narrator"]
    room = ctx["set"]["chamber"]
    ease = v3.ease
    face = lambda f, e: humans.face(nar, f, {**cast3d.NEUTRAL, **e})

    # ---- 4.1: the void, calm; to us
    a, b = T("4.1"), T("4.2") - 1
    v4._sit(ctx, nar, bpy.data.objects["VO_Chair"], a, ["4.1"])
    lens = Vector(CAMERAS["void"][0])
    lines = [l for s in tl["shots"] for l in s["lines"] if l["line"] in ON_CAMERA]
    events, phrases = v4._converse(ctx, lines, a, b, {"Narrator": 0.3}, lambda n, f: (tuple(lens), "talking"),
                                   seated=True, who={"N": "Narrator"})
    humans.breathe(nar, a, b, style="calm", phrases=[p for e in events for p in phrases[e]], seed=51)
    face(a, cast3d.SLY)
    su.animate_camera(cams["void"], [(a, CAMERAS["void"][0], CAMERAS["void"][1]),
                                     (b, (VOID_X, 1.35, 1.22), CAMERAS["void"][1])])

    # ---- 4.2-4.5: kneeling at the loose planks (as v3 kneels), bent deep over the work while his hands are on it
    a, b = T("4.2"), T("4.6") - 1
    scene.frame_set(a - 1)                            # seated to the cut (no drift from the chair across 4.1)
    for pb in nar.pose.bones:
        pb.keyframe_insert("rotation_quaternion", frame=a - 1)
        pb.keyframe_insert("location", frame=a - 1)
    nar.keyframe_insert("location", frame=a - 1)
    nar.keyframe_insert("rotation_euler", frame=a - 1)
    v4._key_pose(nar, a, (ctx["stand"], (0.0, 0.0, 0.0)))      # standing bones again (rotations, hips)
    for f in (a, b):
        nar.location, nar.rotation_euler = (KNEEL[0], KNEEL[1], -0.445), Euler((0, 0, math.radians(180)))
        nar.keyframe_insert("location", frame=f)
        nar.keyframe_insert("rotation_euler", frame=f)
    planks = room["planks"]
    scene.frame_set(1)
    home = [p.matrix_world.copy() for p in planks]
    stack = [Matrix.Translation((STACK[0], STACK[1], 0.025 + 0.05 * i)) @ home[i].to_3x3().to_4x4() for i in range(3)]
    moves = []
    for i, (s0, s1) in enumerate(((0.4, 2.2), (2.6, 4.4), (4.8, 6.6))):   # taken up, nearest first, and stacked
        moves.append((i, T("4.3", s0), T("4.3", s1), home[i], stack[i]))
    for i, (s0, s1) in zip((2, 1, 0), ((0.6, 2.4), (2.8, 4.6), (5.0, 6.8))):   # set back, the top one first
        moves.append((i, T("4.4", s0), T("4.4", s1), stack[i], home[i]))

    def lift(src, dst, u):
        arc = 0.0 if (dst.translation - src.translation).length < 0.05 else 0.12 * math.sin(math.pi * u)
        return Matrix.Translation(src.translation.lerp(dst.translation, u) + Vector((0, 0, arc))) @ src.to_3x3().to_4x4()

    def plank_at(i, f):
        m = home[i]
        for j, f0, f1, src, dst in moves:
            if j == i and f >= f0:
                m = lift(src, dst, ease(f0, f1, f)) if f <= f1 else dst
        return m
    for i, p in enumerate(planks):
        p.rotation_mode = "XYZ"
        for f in [1] + [f for j, f0, f1, *_ in moves if j == i for f in range(f0 - 1, f1 + 2)]:
            p.matrix_world = plank_at(i, f)
            p.keyframe_insert("location", frame=f)
            p.keyframe_insert("rotation_euler", frame=f)
    GRIP = {"Left": Vector((-0.22, -0.06, 0.025)), "Right": Vector((0.22, -0.06, 0.025))}   # on the near edge
    WRIST = Vector((0, -0.07, 0.06))                  # the wrist behind and above the fingers on the edge

    def hand_on(side, f):
        """Where his hand is in 4.2-4.4: on the plank it moves; between moves, carried over to the next one."""
        spans = [(f0, f1, i) for i, f0, f1, *_ in moves]
        for k, (f0, f1, i) in enumerate(spans):
            if f0 - 4 <= f <= f1 + 4:
                return plank_at(i, f) @ GRIP[side] + WRIST
            if k + 1 < len(spans) and f1 + 4 < f < spans[k + 1][0] - 4:
                g0, g1, j = spans[k + 1]
                p0, p1 = plank_at(i, f1) @ GRIP[side] + WRIST, plank_at(j, g0) @ GRIP[side] + WRIST
                u = ease(f1 + 4, g0 - 4, f)
                return p0.lerp(p1, u) + Vector((0, 0, 0.08 * math.sin(math.pi * u)))
        return None
    work0, work1 = moves[0][1] - 14, moves[-1][2] + 10
    W2 = T("4.3") - 1                                 # 4.2: kneeling up, leaning a little, his arms working low in
    bend = lambda f: max(0.4 * ease(a, a + 12, f) * (1 - ease(W2 - 10, W2, f)),      # front of him (only his
                         ease(work0 - 12, work0 + 6, f) * (1 - ease(work1, work1 + 18, f)))   # shadow is seen)

    def kneel(f):
        k, hinge = 1.0, 30 + 34 * bend(f)
        return {"Hips": (0, hinge, 0), "LeftUpLeg": (0, -6 * k - hinge, 0), "RightUpLeg": (0, -6 * k - hinge, 0),
                "LeftLeg": (0, 96 * k, 0), "RightLeg": (0, 96 * k, 0), "LeftFoot": (0, -25 * k, 0),
                "RightFoot": (0, -25 * k, 0), "LowerBack": (0, 4 + 22 * bend(f), 0), "Spine": (0, 2 + 14 * bend(f), 0),
                "Spine1": (0, 8 * bend(f), 0), "Neck1": (0, -12 * bend(f), 0), "Head": (0, -10 * bend(f), 0)}
    humans._layer(nar, a, b, kneel)
    humans.breathe(nar, a, b, style="anxious", seed=52)
    humans.eyes(nar, a, T("4.5") - 1, mode=lambda f: "thinking", look=lambda f: (0.0, -40.0), seed=53, head=False)
    face(a, cast3d.TENSE)
    for side in ("Left", "Right"):
        v4._contact(ctx, nar, side, work0 - 12, work1 + 16, lambda f, side=side: hand_on(side, f),
                    lambda f: humans.hand_frame((0, 1, -1), (0, 0, -1)), blend=10)
        humans.grip(nar, side, work0, curl=0.6)
        for i, f0, f1, *_ in moves:
            ctx["held"].append(dict(prop=planks[i].name, rig=nar.name, bone=f"{side}Hand", f0=f0, f1=f1,
                                    point=list(GRIP[side])))
    for k, (i, f0, *_rest) in enumerate(moves[0:3]):
        ctx["marks"]["4.3/nail_squeal" + ("" if k == 0 else f"#{k + 1}")] = f0 + 4
    ctx["marks"]["4.4/hammer_muffled"], ctx["marks"]["4.4/hammer_muffled#2"] = moves[4][2], moves[5][2]
    for side, sx in (("Left", -1), ("Right", 1)):     # 4.2's work: a hasty rhythm of both arms, low over the floor
        base = Vector((KNEEL[0] + 0.13 * sx, KNEEL[1] + 0.42, 0.42))
        humans.reach(nar, side, a + 4, W2, lambda f, base=base, sx=sx: base + Vector((
            0.02 * sx * math.sin(f * 0.27), 0.09 * math.sin(f * 0.29 + (0 if sx < 0 else 1.4)),
            0.04 * math.sin(f * 0.58))), hand=humans.hand_frame((0, 1, -0.6), (0, 0, -1)), blend=10)
    # the lantern stands open on the floor, its light low across the boards toward him
    lantern, shutter, beam, glow = sets.dark_lantern(ctx["C"]["PROPS"])
    lantern.location = (LANTERN[0], LANTERN[1], 0.0)
    lantern.rotation_euler.z = v3._yaw_to(Vector((*LANTERN, 0)), Vector((KNEEL[0], KNEEL[1] + 0.4, 0.3)))
    shutter.rotation_euler.z = math.radians(-110)
    beam.data.energy, beam.data.spot_size, glow.data.energy = 900, math.radians(75), 40
    # 4.5: kneeling up, he wipes his clean hands (palm on palm) and laughs
    a5, b5 = T("4.5"), T("4.6") - 1
    face(a5, cast3d.SLY)
    c = Vector((KNEEL[0], KNEEL[1] + 0.36, 0.74))
    rub = lambda f: Vector((0, 0.022 * math.cos(f * 0.9), 0.018 * math.sin(f * 0.9)))
    W0, W1 = T("4.5", 0.6), T("4.5", 4.2)
    for side, sx in (("Left", -1), ("Right", 1)):
        v4._contact(ctx, nar, side, W0 - 12, W1 + 12,
                    lambda f, sx=sx: (c + Vector((0.055 * sx, 0, 0)) + rub(f) * sx) if W0 <= f <= W1 else None,
                    lambda f, sx=sx: humans.hand_frame((0, 1, 0.5), (-sx, 0, 0)), blend=10)
        humans.grip(nar, side, W0, curl=0.2)
    line = next(l for s_ in tl["shots"] for l in s_["lines"] if l["line"] == "4.5_0_N")
    ha = 1 + int(round((line["start"] + line["seconds"] - 1.3) * 24))
    humans.chuckle(nar, ha, rest=cast3d.SLY)
    ctx["marks"]["4.5/laugh_group"] = ha
    # ---- 4.6: the corridor's long-case clock at four; four strikes, then the knock
    pivot = Vector((CO, 3.581, 1.735))
    for part, want in (("MinuteHand", 0), ("HourHand", 120)):
        hand = bpy.data.objects[f"CO_Long_Case_Clock_vintage_grandfather_clock_01_{part}"]
        hand.rotation_mode = "XYZ"
        far = max((hand.matrix_world @ v.co for v in hand.data.vertices), key=lambda p: (p - pivot).length)
        now = math.degrees(math.atan2(far.x - pivot.x, far.z - pivot.z)) % 360
        hand.matrix_world = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(want - now), 4, "Y") @ \
            Matrix.Translation(-pivot) @ hand.matrix_world
        hand.keyframe_insert("location", frame=1)
        hand.keyframe_insert("rotation_euler", frame=1)
    face_light = su.light("V5_Clock_Moon", ctx["C"]["SET"], "AREA", (CO - 0.45, 3.15, 2.35), 0, (0.6, 0.72, 1.0),
                          target=(CO, 3.58, 1.73), shape="DISK", size=0.3)    # on the dial, its glint off the lens
    for f, e in ((1, 0), (T("4.6") - 1, 0), (T("4.6"), 40)):
        face_light.data.energy = e
        face_light.data.keyframe_insert("energy", frame=f)
    for k, sec in enumerate((0.4, 1.9, 3.4, 4.9)):
        ctx["marks"]["4.6/clock_strike" + ("" if k == 0 else f"#{k + 1}")] = T("4.6", sec)
    ctx["marks"]["4.6/knock3"] = end - 38
