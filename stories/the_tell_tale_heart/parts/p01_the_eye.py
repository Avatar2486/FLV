"""Part 01, The Eye (1.1-1.9): the house at dusk; the narrator's morning kindness - a breakfast tray prepared with
care and carried up to the old man, who sits up and smiles; the gold he doesn't look at; the old man's eye; the
narrator's cup trembling on its saucer; his decision, made sitting still while day becomes night.
(production_plan.md, design: docs/superpowers/specs/2026-11-24-tell-tale-heart-whole-film-design.md)"""
import math

HOUSE = (121.6, 0.0)                   # the old man's door in the street set (sets.street: house 3, door_x 1.6)
KITCHEN_X, NR_X = 60.0, 80.0           # sets.SET_X
SHOTS = [("1.1", [], 5.0), ("1.2", [("1.2_0_N", "N")], 8.8), ("1.3", [("1.3_0_N", "N")], 5.0),
         ("1.4", [("1.4_0_N", "N")], 7.0), ("1.5", [("1.5_0_N", "N")], 4.0), ("1.6", [("1.6_0_N", "N")], 5.0),
         ("1.7", [("1.7_0_N", "N")], 7.0), ("1.8", [("1.8_0_N", "N")], 4.5), ("1.9", [("1.9_0_N", "N")], 10.5)]
SETS = ["street", "kitchen", "entry", "chamber", "narrator_room"]
CAST = ["Narrator", "OldMan"]
CAMERAS = {
    "street": ((HOUSE[0] - 3.0, -13.0, 7.5), (HOUSE[0] - 1.0, 0.0, 9.8), 35),     # roofline, lit window, dusk
    "kitchen": ((61.4, 1.3, 1.55), (59.95, -0.2, 0.95), 28),                     # three-quarter front: his hands
    "stairs": ((38.7, -2.0, 1.6), (38.75, 0.0, 2.2), 35),
    "two": ((-0.9, -0.6, 1.5), (0.6, 0.9, 0.9), 35),
    "chest": ((1.55, -1.75, 0.75), (2.0, -1.3, 0.36), 85),
    "ots": ((-0.25, 0.25, 1.62), (0.75, 1.55, 0.95), 85),
    "eye": ((0.9, 1.0, 1.0), (0.9, 1.5, 0.9), 100),
    "cup": ((-0.2, 0.35, 1.45), (0.2, 0.6, 1.4), 85),
    "room": ((NR_X + 1.6, -1.4, 1.7), (NR_X, 1.3, 1.0), 24),
}
CUTS = [("1.1", 0.0, "street"), ("1.2", 0.0, "kitchen"), ("1.3", 0.0, "stairs"), ("1.4", 0.0, "two"),
        ("1.5", 0.0, "chest"), ("1.6", 0.0, "ots"), ("1.7", 0.0, "eye"), ("1.8", 0.0, "cup"), ("1.9", 0.0, "room")]
DAY = {"sun": 3.0, "fill": 30, "warm": 25}
LIGHTS = {"1.1": {"ex_moon": 1.2, "EX_Gas_Lamp_light": 450, "EX_Gas_Lamp_Far_light": 250},
          "1.2": {"ki_sun": 320, "ki_fill": 70}, "1.3": {"en_day": 260, "en_fill": 45},
          "1.4": DAY, "1.5": DAY, "1.6": DAY, "1.7": DAY, "1.8": DAY, "1.9": {"nr_sun": 420, "nr_fill": 40}}


def act(ctx):
    bpy, humans, cast3d, su = ctx["bpy"], ctx["humans"], ctx["cast3d"], ctx["su"]
    import preview_v3 as v3
    import preview_v4 as v4
    from mathutils import Euler, Matrix, Vector
    from material_library import material as M
    T, tl, cams, rigs = ctx["T"], ctx["tl"], ctx["cams"], ctx["rigs"]
    scene = bpy.context.scene
    nar, om = rigs["Narrator"], rigs["OldMan"]
    face = lambda rig, f, e: humans.face(rig, f, {**cast3d.NEUTRAL, **e})
    end = ctx["end"]
    v4._stairwell(ctx)                                # the entry set's ceiling and stairwell (as in the Visitors)

    def stoop(k):                                     # bending to a table: from the hips (legs kept), then the back
        return {"Hips": (0, 16 * k, 0), "LeftUpLeg": (0, -16 * k, 0), "RightUpLeg": (0, -16 * k, 0),
                "LowerBack": (0, 16 * k, 0), "Spine": (0, 12 * k, 0), "Spine1": (0, 7 * k, 0), "Neck1": (0, -14 * k, 0)}

    # ---- 1.1: the house at dusk; the lamp flickers; one window lit upstairs; the camera cranes down to the door
    world = scene.world.node_tree.nodes["Background"].inputs[0]
    for f, col in ((1, (0.03, 0.045, 0.09, 1)), (T("1.2") - 1, (0.03, 0.045, 0.09, 1)), (T("1.2"), (0.002, 0.0025, 0.004, 1))):
        world.default_value = col
        world.keyframe_insert("default_value", frame=f)
    lamp = bpy.data.objects["LIGHT_EX_Gas_Lamp"] if "LIGHT_EX_Gas_Lamp" in bpy.data.objects else \
        next(o for o in bpy.data.objects if o.type == "LIGHT" and o.name.startswith("EX_Gas_Lamp") and "Far" not in o.name
             and "Opp" not in o.name)
    for f in range(T("1.1"), T("1.2"), 2):            # a gas flame's flicker, on the lamp's own light
        lamp.data.energy = 450 * (0.88 + 0.12 * math.sin(f * 1.7) * math.sin(f * 0.43 + 1.0))
        lamp.data.keyframe_insert("energy", frame=f)
    lamp.data.energy = 0
    lamp.data.keyframe_insert("energy", frame=T("1.2"))
    upstairs = su.light("V5_Lit_Window", ctx["C"]["SET"], "POINT", (HOUSE[0] - 1.6, 0.6, 4.9), 0, (1.0, 0.62, 0.3),
                        shadow_soft_size=0.3)
    for f, e in ((1, 80), (T("1.2") - 1, 80), (T("1.2"), 0)):
        upstairs.data.energy = e
        upstairs.data.keyframe_insert("energy", frame=f)
    win = min((o for o in bpy.data.objects if o.name.startswith("EX_House_3") and o.type == "MESH"
               and o.active_material and o.active_material.name == "MAT_Ex_Window"),
              key=lambda o: (o.matrix_world.translation - Vector((HOUSE[0] - 1.6, 0.0, 4.9))).length, default=None)
    if win is not None:
        win.active_material = bpy.data.materials["MAT_Ex_Window_Lit"]
    su.animate_camera(cams["street"], [(T("1.1"), CAMERAS["street"][0], CAMERAS["street"][1]),
                                       (T("1.2") - 1, (HOUSE[0], -6.5, 1.75), (HOUSE[0], 0.0, 1.4))])

    # ---- 1.2: the kitchen, morning. At the table's edge, bending to it: his right hand sets the teapot on the tray,
    # his left eases the cup into place (the table top is 0.72 m: a standing man bends to reach it)
    a, b = T("1.2"), T("1.3") - 1
    v4._walk(ctx, nar, [(a, (59.95, -0.38), 180), (b, (59.95, -0.38), 180)], a, b)
    pot, tray, cup = bpy.data.objects["KI_Teapot"], bpy.data.objects["PROP_Tray"], bpy.data.objects["PROP_Tray_Cup"]
    pot.rotation_mode = "XYZ"
    for obj, at in ((tray, (59.80, -0.02, 0.73)), (pot, (60.12, 0.0, 0.72))):   # laid out as the shot opens:
        obj.location = at                                                   # the pot by his right hand
        obj.keyframe_insert("location", frame=1)
    scene.frame_set(1)
    keep = cup.matrix_world.copy()                    # off the tray's parenting, staying where it is
    cup.parent = None
    cup.matrix_world = keep
    cup.keyframe_insert("location", frame=1)
    cup.keyframe_insert("rotation_euler", frame=1)
    scene.frame_set(a)
    p0, on_tray = pot.matrix_world.copy(), tray.matrix_world @ Vector((0.1, 0.02, 0.01))
    G0, G1, R0 = T("1.2", 0.9), T("1.2", 2.4), T("1.2", 2.6)          # grip, set down, let go
    C0, C1 = T("1.2", 3.4), T("1.2", 4.6)
    bend = lambda f: max(v3.ease(G0 - 10, G0, f) * (1 - v3.ease(R0, R0 + 10, f)),
                         v3.ease(C0 - 10, C0, f) * (1 - v3.ease(C1, C1 + 10, f)))
    humans._layer(nar, a, b, lambda f: stoop(bend(f)))
    face(nar, a, cast3d.PLEASANT)
    face(nar, T("1.2", 6.0), cast3d.CHARM)            # pleased with it
    humans.eyes(nar, a, b, mode=lambda f: "thinking", look=lambda f: (0.0, -35.0), seed=11)
    humans.breathe(nar, a, b, style="calm", seed=12)
    humans.sway(nar, a, b, amount=0.6, seed=13)
    lift = lambda f: 0.1 * math.sin(math.pi * v3.ease(G0, G1, f))
    pot_at = lambda f: p0.translation.lerp(on_tray, v3.ease(G0, G1, f)) + Vector((0, 0, lift(f)))
    for f in range(G0 - 1, R0 + 1):
        pot.matrix_world = Matrix.Translation(pot_at(f)) @ p0.to_3x3().to_4x4()
        pot.keyframe_insert("location", frame=f)
        pot.keyframe_insert("rotation_euler", frame=f)
    v4._constant(pot, ("location", "rotation_euler"))
    handle = Vector((0.0, -0.08, 0.10))               # the side of the pot toward him: his hand round it
    v4._contact(ctx, nar, "Right", G0 - 10, R0 + 10,
                lambda f: (pot_at(f) + handle) if G0 <= f <= R0 else None,
                lambda f: humans.hand_frame((0.0, 1.0, -0.6), (1.0, 0.3, 0.0)), blend=10)
    humans.grip(nar, "Right", G0, curl=0.7)
    humans._finger_shape(nar, "Right", R0 + 3, "relaxed")
    ctx["held"].append(dict(prop=pot.name, rig=nar.name, bone="RightHand", f0=G0, f1=R0, point=list(handle)))
    scene.frame_set(C0)
    cw = cup.matrix_world.copy()
    nudge = lambda f: Vector((0.03, 0.02, 0.0)) * v3.ease(C0 + 4, C1 - 4, f)
    for f in range(C0 - 1, C1 + 1):
        cup.matrix_world = Matrix.Translation(cw.translation + nudge(f)) @ cw.to_3x3().to_4x4()
        cup.keyframe_insert("location", frame=f)
        cup.keyframe_insert("rotation_euler", frame=f)
    v4._constant(cup, ("location", "rotation_euler"))
    v4._contact(ctx, nar, "Left", C0 - 10, C1 + 10,
                lambda f: (cw.translation + nudge(f) + Vector((0.0, -0.06, 0.07))) if C0 <= f <= C1 else None,
                lambda f: humans.hand_frame((0.0, 1.0, -0.5), (0.0, 0.0, -1.0)), blend=10)
    su.animate_camera(cams["kitchen"], [(a, CAMERAS["kitchen"][0], CAMERAS["kitchen"][1]),
                                        (b, (61.1, 1.0, 1.5), (59.95, -0.15, 0.95))])

    def follow(obj, leader, f0, f1):                  # rides on the tray: moved only by the hands that carry it
        scene.frame_set(f0)
        off = leader.matrix_world.inverted() @ obj.matrix_world
        mats = {}
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            mats[f] = leader.matrix_world @ off
        for f, m in mats.items():
            obj.matrix_world = m
            obj.keyframe_insert("location", frame=f)
            obj.keyframe_insert("rotation_euler", frame=f)

    # ---- 1.3: up the stair with the tray in both hands, step over step; the camera follows behind
    a, b = T("1.3"), T("1.4") - 1
    up_frames = 12
    steps = max(1, (b - a - 6) // up_frames)
    track = {}
    for f in range(a, b + 1):
        p = min(max(0.0, (f - a) / up_frames), steps)
        k = min(int(p), steps - 1)
        u = p - k
        (y0, z0), (y1, z1) = v4._tread(k - 1), v4._tread(k)
        e = u * u * (3 - 2 * u)
        track[f] = Vector((v4.STAIR_X, y0 + 0.02 + (y1 - y0) * u, z0 + (z1 - z0) * e))
        nar.location, nar.rotation_euler = track[f], Euler((0, 0, math.radians(180)))
        nar.keyframe_insert("location", frame=f)
        nar.keyframe_insert("rotation_euler", frame=f)
    v4._constant(nar, ("location", "rotation_euler"))
    rest = {bb.name: bb.matrix_local.copy() for bb in nar.data.bones}
    ankle = {s: rest[f"{s}Foot"].translation * nar.scale.x for s in ("Left", "Right")}

    def spot(side, j):
        y, z = v4._tread(j)
        return Vector((v4.STAIR_X - ankle[side].x, y - 0.03, z + ankle[side].z))     # facing +y: his left is -x
    for f in range(a, a + steps * up_frames + 1):
        p = min((f - a) / up_frames, steps)
        k = min(int(p), steps - 1)
        u = p - k
        swing = ("Left", "Right")[k % 2]
        stance = "Right" if swing == "Left" else "Left"
        s_ = u * u * (3 - 2 * u)
        targets = {stance: spot(stance, k - 1 if k else -1),
                   swing: spot(swing, k - 2 if k > 1 else -1).lerp(spot(swing, k), s_) + Vector((0, 0, 0.08 * math.sin(math.pi * u)))}
        scene.frame_set(f)
        inv = nar.matrix_world.inverted()
        for side, t in targets.items():
            chain = (f"{side}UpLeg", f"{side}Leg", f"{side}Foot")
            pose = {n: nar.pose.bones[n].matrix.copy() for n in chain + ("Hips",)}
            humans._two_bone(nar, rest, pose, f, *chain, inv @ t, pole=(0, -1, 0), force_pole=True)
            bpy.context.view_layer.update()
    humans.eyes(nar, a, b, mode=lambda f: "thinking", look=lambda f: (0.0, -10.0), seed=14)
    humans.breathe(nar, a, b, style="calm", seed=15)
    tray_pose = lambda f: v4._at(nar, f) @ Matrix.Translation((0.0, -0.30, 1.08))
    for f in range(a, b + 1):
        tray.matrix_world = tray_pose(f)
        tray.keyframe_insert("location", frame=f)
        tray.keyframe_insert("rotation_euler", frame=f)
    for side, x in (("Left", 0.2), ("Right", -0.2)):
        v4._contact(ctx, nar, side, a, b, lambda f, x=x: tray_pose(f) @ Vector((x, 0.0, 0.0)),
                    lambda f: humans.hand_frame(v4._at(nar, f).to_3x3() @ Vector((0, -1, 0)), (0.0, 0.0, 1.0)), blend=1)
        humans.grip(nar, side, a + 1, curl=0.5)
    heads = {f: track[f] + Vector((0, 0, 1.55)) for f in track}
    su.animate_camera(cams["stairs"], [(f, (40.2, -1.7, 1.2 + 0.5 * (f - a) / (b - a)),     # in the hall beside the
                                        heads[f] + Vector((0, 0, -0.1))) for f in range(a, b + 1, 4)])   # stair

    # ---- 1.4-1.8: the chamber by day. The tray set down on the washstand by the bed; the old man sits up and smiles;
    # the gold; his eye; the narrator's cup trembling on its saucer
    a, b = T("1.4"), T("1.9") - 1
    om.location, om.rotation_euler = (0.9, 0.38, 0.56), Euler((math.radians(-90), 0, 0))
    om.keyframe_insert("location", frame=1)
    om.keyframe_insert("rotation_euler", frame=1)
    humans.rise_in_bed(om, a + 6, b, seconds=1.4, lead="Right")
    S0, S1 = T("1.4", 1.0), T("1.4", 2.6)              # the tray goes down on the washstand
    at_stand = v4.heading_to((1.98, 0.6), (2.15, 0.95))
    at_bed = v4.heading_to((1.98, 0.6), (0.9, 0.7))
    v4._walk(ctx, nar, [(a, (1.98, 0.6), at_stand), (S1 + 10, (1.98, 0.6), at_stand), (S1 + 30, (1.98, 0.6), at_bed),
                        (b, (1.98, 0.6), at_bed)], a, b)
    setdown = lambda f: v3.ease(S0 - 10, S0 + 4, f) * (1 - v3.ease(S1, S1 + 12, f))
    humans._layer(nar, a, b, lambda f: stoop(setdown(f)))
    scene.frame_set(a)
    held_tray = v4._at(nar, a) @ Matrix.Translation((0.0, -0.30, 1.08))
    stand_top = Matrix.Translation((2.12, 0.9, 0.82)) @ held_tray.to_3x3().to_4x4()
    tray_at = lambda f: Matrix.Translation(held_tray.translation.lerp(stand_top.translation, v3.ease(S0, S1, f))) @ \
        held_tray.to_3x3().to_4x4()
    for f in range(a, S1 + 1):
        tray.matrix_world = tray_at(f)
        tray.keyframe_insert("location", frame=f)
        tray.keyframe_insert("rotation_euler", frame=f)
    v4._constant(tray, ("location", "rotation_euler"))
    face(om, a, cast3d.NEUTRAL)
    face(om, T("1.4", 3.0), cast3d.PLEASANT)           # he smiles as the tray is set down
    face(nar, a, cast3d.PLEASANT)
    face(nar, T("1.6"), {"browDownLeft": 0.15, "browDownRight": 0.15})
    face(nar, T("1.8"), {"browInnerUp": 0.35, "mouthPressLeft": 0.25, "mouthPressRight": 0.25})   # blood running cold
    lid = next(o for o in ctx["set"]["chamber"]["chest"].children if o.name.endswith("_lid"))
    lid.rotation_mode = "XYZ"
    scene.frame_set(1)
    lid0 = lid.matrix_world.copy()
    hinge = lid0.translation.copy()
    for f, deg in ((T("1.5") - 1, 0), (T("1.5"), 100), (T("1.6") - 1, 100), (T("1.6"), 0)):   # open in 1.5 only
        lid.matrix_world = Matrix.Translation(hinge) @ Matrix.Rotation(math.radians(deg), 4, "Y") @ \
            Matrix.Translation(-hinge) @ lid0
        lid.keyframe_insert("location", frame=f)
        lid.keyframe_insert("rotation_euler", frame=f)
    v4._constant(lid, ("location", "rotation_euler"))
    turn = T("1.6", 1.6)                              # the old man turns his head toward him

    def om_look(f):
        return ((-40.0, 5.0) if f >= turn else (0.0, 10.0)), "listening"
    humans.eyes(om, a, b, mode=lambda f: om_look(f)[1], look=lambda f: om_look(f)[0], seed=21)
    humans.eyes(nar, a, b, mode=lambda f: "listening", look=lambda f: (0.0, -20.0) if f < T("1.6") else (12.0, -15.0), seed=22)
    for rig, s in ((om, 23), (nar, 24)):
        humans.breathe(rig, a, b, style="calm", seed=s)
        humans.sway(rig, a, b, amount=0.6, seed=s + 10)
    R = a + 6                                         # the old man's hands: folded on his belly as he lies; they
    for side, dx in (("Right", -0.24), ("Left", 0.24)):   # push on the mattress as he sits up, then rest on his lap
        belly, push, lap = (Vector((0.9 + dx * 0.45, 1.32, 0.70)), Vector((0.9 + dx * 1.25, 1.40, 0.475)),
                            Vector((0.9 + dx * 0.55, 1.18, 0.72)))

        def at(f, belly=belly, push=push, lap=lap):
            u, w = v3.ease(R, R + 7, f), v3.ease(R + 38, R + 53, f)
            return (belly.lerp(push, u) + Vector((0, 0, 0.05 * math.sin(math.pi * u)))).lerp(lap, w)
        humans.reach(om, side, 1, b, at, hand=humans.hand_frame((0.3 * (1 if dx > 0 else -1), -1, 0), (0, 0, -1)))
    carry = lambda f: humans.hand_frame(v4._at(nar, f).to_3x3() @ Vector((0, -1, 0)), (0.0, 0.0, 1.0))
    for side, x in (("Left", 0.2), ("Right", -0.2)):  # both hands set the tray down, then let go
        v4._contact(ctx, nar, side, a, S1 + 12, lambda f, x=x: (tray_at(f) @ Vector((x, 0.0, 0.0))) if f <= S1 else None,
                    carry, blend=10)
        humans._finger_shape(nar, side, S1 + 3, "relaxed")
    ctx["held"].append(dict(prop=tray.name, rig=nar.name, bone="RightHand", f0=T("1.3"), f1=S0, point=[-0.2, 0, 0]))
    follow(pot, tray, T("1.3"), S1)
    follow(cup, tray, T("1.3"), S1)
    E0 = T("1.7", 2.8)                                # the slow blink of the vulture eye
    for f, w in ((E0 - 1, 0.0), (E0 + 8, 1.0), (E0 + 14, 1.0), (E0 + 26, 0.0)):
        humans.face(om, f, {"eyeBlinkLeft": w, "eyeBlinkRight": w})
    scene.frame_set(T("1.7"))
    eye = om.matrix_world @ om.pose.bones["LeftEye"].matrix
    gaze = (eye.to_3x3() @ Vector((0, 1, 0))).normalized()
    su.animate_camera(cams["eye"], [(T("1.7"), tuple(eye.translation + gaze * 0.16), tuple(eye.translation)),
                                    (T("1.8") - 1, tuple(eye.translation + gaze * 0.12), tuple(eye.translation))])
    cams["eye"].data.dof.use_dof = False
    # 1.8: a cup on a saucer in his left hand; his hand trembles, so the cup rattles on it
    saucer = su.cylinder("V5_Saucer", ctx["C"]["PROPS"], M("MAT_Ceramic"), 0.075, 0.012, (0, 0, 0), segments=32)
    mug = ctx["sets"].lib.mug(ctx["C"]["PROPS"], (0, 0, 0), prefix="V5_Cup")
    mug.parent = saucer
    mug.location = (0, 0, 0.006)
    a8, b8 = T("1.8"), T("1.9") - 1
    hold = lambda f: v4._at(nar, f) @ Vector((0.05, -0.3, 1.18))
    v4._contact(ctx, nar, "Left", a8, b8, hold, lambda f: humans.hand_frame(v4._at(nar, f).to_3x3() @ Vector((-0.3, -1, 0)),
                                                                          (0, 0, 1)), blend=1)
    humans.grip(nar, "Left", a8 + 1, curl=0.4)
    shake = lambda f: 0.9 * math.sin(2 * math.pi * 7.1 * f / 24) * math.sin(2 * math.pi * 0.6 * f / 24 + 1.0)
    humans._layer(nar, a8, b8, lambda f: {"LeftHand": (0, shake(f), shake(f + 3) * 0.6)})
    scene.frame_set(a8)
    hand = nar.matrix_world @ nar.pose.bones["LeftHand"].matrix
    saucer.matrix_world = Matrix.Translation(hand.to_translation() + hand.to_3x3() @ Vector((0, 0.07, -0.03)))
    v4._carry(ctx, saucer, nar, "LeftHand", a8, b8)
    for f in range(a8, b8 + 1, 2):                    # rattling on the saucer as the hand shakes
        mug.location = (0.002 * math.sin(f * 2.3), 0.002 * math.cos(f * 1.9), 0.006 + 0.0015 * abs(math.sin(f * 3.1)))
        mug.keyframe_insert("location", frame=f)
    for o in (saucer, mug):
        for f in (1, a8 - 1):
            o.hide_render = o.hide_viewport = True
            o.keyframe_insert("hide_render", frame=f)
        o.hide_render = o.hide_viewport = False
        o.keyframe_insert("hide_render", frame=a8)
        o.hide_render = True
        o.keyframe_insert("hide_render", frame=b8 + 1)
    scene.frame_set(a8)
    head = nar.matrix_world @ nar.pose.bones["Head"].head
    fwd = (nar.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
    mid = head.lerp(hold(a8), 0.38)
    left = fwd.cross(Vector((0, 0, 1))).normalized()
    su.animate_camera(cams["cup"], [(a8, tuple(mid + fwd * 1.35 + left * 0.35 + Vector((0, 0, 0.05))), tuple(mid))])
    cams["cup"].data.lens = 50
    su.animate_camera(cams["two"], [(T("1.4"), CAMERAS["two"][0], CAMERAS["two"][1]),
                                    (T("1.5") - 1, (-0.7, -0.4, 1.45), CAMERAS["two"][1])])
    chest_cam = cams["chest"]
    chest_cam.data.dof.use_dof = True
    for f, d in ((T("1.5"), 0.7), (T("1.5", 2.4), 0.7), (T("1.5", 3.6), 2.3)):           # rack focus: box -> him
        chest_cam.data.dof.focus_distance = d
        chest_cam.data.dof.keyframe_insert("focus_distance", frame=f)
    ctx["marks"]["1.5/coin"] = T("1.5", 0.5)
    patch = su.light("V5_Chest_Sun", ctx["C"]["SET"], "AREA", (2.45, -0.85, 0.95), 0, (1.0, 0.9, 0.75),
                     target=(2.0, -1.3, 0.35), shape="DISK", size=1.2)        # where the gold mirrors it to the lens
    for f, e in ((1, 0), (T("1.5") - 1, 0), (T("1.5"), 60), (T("1.6") - 1, 60), (T("1.6"), 0)):
        patch.data.energy = e
        patch.data.keyframe_insert("energy", frame=f)
    scene.frame_set(T("1.6", 1.0))
    head_n = nar.matrix_world @ nar.pose.bones["Head"].head
    head_o = om.matrix_world @ om.pose.bones["Head"].head
    d = (head_o - head_n).normalized()
    side = d.cross(Vector((0, 0, 1))).normalized()
    su.animate_camera(cams["ots"], [(T("1.6"), tuple(head_n - d * 0.55 - side * 0.22 + Vector((0, 0, 0.06))),
                                     tuple(head_o + Vector((0, 0, -0.05))))])
    cams["ots"].data.lens = 50
    cams["ots"].data.dof.use_dof, cams["ots"].data.dof.focus_distance = True, (head_o - head_n).length + 0.55

    # ---- 1.9: his room, day into night, as he sits perfectly still - only breathing, blinking
    a, b = T("1.9"), end
    v4._sit(ctx, nar, bpy.data.objects["NR_Chair"], a, ["1.9"])
    humans.eyes(nar, a, b, mode=lambda f: "thinking", look=lambda f: (0.0, 2.0), seed=31)
    humans.breathe(nar, a, b, style="calm", seed=32)
    sun, fill = ctx["lights"]["nr_sun"], ctx["lights"]["nr_fill"]
    moon = su.light("V5_NR_Moon", ctx["C"]["SET"], "AREA", (NR_X, 2.6, 2.0), 0, (0.55, 0.68, 1.0),
                    target=(NR_X, 0, 0.5), shape="RECTANGLE", size=1.0, size_y=1.3)
    for f, s_, fl, mn in ((a, 420, 40, 0), (a + int(0.45 * (b - a)), 160, 25, 0), (a + int(0.75 * (b - a)), 12, 8, 60),
                          (b, 0, 4, 90)):
        sun.data.energy, fill.data.energy, moon.data.energy = s_, fl, mn
        for lt in (sun, fill, moon):
            lt.data.keyframe_insert("energy", frame=f)
