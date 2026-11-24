"""Part 02, Seven Nights (2.1-2.9): at midnight he creeps down the corridor with a closed dark lantern while the
long-case clock nears twelve; the watch in his palm reaches it; his fingertips turn the latch; the door eased open a
sliver, the lantern in, then his head, an hour of it by the clock; his thumb cracks the shutter and a thread of light
falls on the closed eye. Six more nights, each one wearing him more; and each morning he throws open the shutters
and greets the old man warmly. (design: docs/superpowers/specs/2026-11-24-tell-tale-heart-whole-film-design.md)"""
import math

CO = 20.0                              # sets.SET_X["corridor"]
CARD_X = 170.0                         # the title stage's x: the night cards stand there, below the title
GAP = (-1.58, -2.53)                   # where he stands in the chamber doorway (as in the eighth night, v2/v3)
SHOTS = [("2.1", [("2.1_0_N", "N")], 10.0), ("2.2", [("2.2_0_N", "N")], 4.0), ("2.3", [("2.3_0_N", "N")], 5.0),
         ("2.4", [("2.4_0_N", "N")], 9.0), ("2.5", [("2.5_0_N", "N")], 11.0), ("2.6", [("2.6_0_N", "N")], 7.0),
         ("2.7", [("2.7_0_N", "N")], 6.0), ("2.8", [("2.8_0_N", "N")], 16.0),
         ("2.9", [("2.9_0_N", "N"), ("2.9_1_NS", "NS"), ("2.9_2_OM", "OM"), ("2.9_3_N", "N")], 16.0)]
ON_CAMERA = ("2.9_1_NS", "2.9_2_OM")
SETS = ["corridor", "chamber"]
CAST = ["Narrator", "OldMan"]
NIGHT_CAMS = [((1.6, -1.4, 1.35), (0.6, 1.6, 0.95), 50), ((-2.05, -1.45, 1.6), (-1.64, -2.3, 1.6), 85),
              ((1.9, -1.8, 2.2), (-0.5, 0.0, 1.0), 28), ((0.4, 0.6, 1.3), (0.94, 1.95, 0.88), 85),
              ((-2.0, -1.5, 1.62), (-1.62, -2.3, 1.6), 100), ((0.94, 1.2, 1.75), (0.94, 1.95, 0.88), 50)]
NIGHT_CAMS[3] = ((1.85, 1.3, 1.1), (0.9, 1.9, 0.66), 85)             # his sleeping face from the bed's side
CAMERAS = {
    "corridor": ((CO + 0.4, -3.7, 1.15), (CO, 3.7, 1.3), 24),
    "watch": ((CO, 0.0, 1.4), (CO, 0.5, 1.1), 100),                      # placed over the watch in act
    "latch": ((CO + 0.45, 0.42, 1.18), (CO + 0.85, 0.83, 1.0), 85),
    "door_from_room": ((0.25, 0.1, 1.25), (-1.45, -2.2, 1.25), 35),
    # his head and the lantern are only seen through the slot between the jamb and the door's edge (v2 measured
    # it: 123-151 degrees round from his head), so the gap's cameras stand in line with it
    "gap": ((-2.31, -1.79, 1.62), (-1.60, -2.36, 1.5), 50),
    "clock_gap": ((-2.4, -1.45, 1.35), (-1.75, -2.25, 1.62), 30),     # his head in the slot, the clock above it
    "lantern": ((-2.35, -1.40, 1.45), (-1.64, -2.20, 1.36), 26),
    "room": ((2.25, -1.95, 2.7), (-0.2, 0.4, 0.7), 22),
    "card": ((CARD_X, -3.0, -10.0), (CARD_X, 0.0, -10.0), 50),
    "window": ((0.4, -1.3, 1.55), (2.4, 0.15, 1.45), 28),
    "morning": ((0.15, -0.35, 1.6), (1.2, 0.9, 1.25), 35),          # both faces: his profile, the old man 3/4
    **{f"night{i}": c for i, c in enumerate(NIGHT_CAMS)},
}
CUTS = [("2.1", 0.0, "corridor"), ("2.2", 0.0, "watch"), ("2.3", 0.0, "latch"), ("2.4", 0.0, "door_from_room"),
        ("2.5", 0.0, "clock_gap"), ("2.6", 0.0, "lantern"), ("2.7", 0.0, "room"), ("2.8", 0.0, "card"),
        ("2.9", 0.0, "window")]
NIGHT = {"moon": 700, "fill": 30}
LIGHTS = {"2.1": {"co_moon": 250, "co_fill": 6}, "2.2": {"co_moon": 250, "co_fill": 6},
          "2.3": {"co_moon": 250, "co_fill": 6}, "2.4": NIGHT, "2.5": NIGHT, "2.6": NIGHT, "2.7": NIGHT,
          "2.8": NIGHT, "2.9": {"sun": 3.0, "fill": 30, "warm": 25}}
SNEAK = (("Neutral_FW", 240), ("Tiptoe_FW", 72))


def act(ctx):
    bpy, humans, cast3d, su, sets = ctx["bpy"], ctx["humans"], ctx["cast3d"], ctx["su"], ctx["sets"]
    import bmesh
    import preview_v3 as v3
    import preview_v4 as v4
    from mathutils import Matrix, Quaternion, Vector
    from material_library import material as M
    T, tl, cams, rigs, end = ctx["T"], ctx["tl"], ctx["cams"], ctx["rigs"], ctx["end"]
    scene = bpy.context.scene
    nar, om = rigs["Narrator"], rigs["OldMan"]
    room = ctx["set"]["chamber"]
    ease = v3.ease
    face = lambda rig, f, e: humans.face(rig, f, {**cast3d.NEUTRAL, **e})
    scene.eevee.volumetric_tile_size = "4"            # fine enough for a thread-thin beam (as v3)
    lantern, shutter, beam, glow = sets.dark_lantern(ctx["C"]["PROPS"])
    beam.location.y = -0.10
    beam.data.energy, glow.data.energy = 0.0, 6.0
    beam.data.spot_size, beam.data.use_shadow_jitter = math.radians(1.2), False

    def hold_hidden(objs, shown):                     # visible only in frames [a, b)
        for o in objs:
            o.hide_render = True
            o.keyframe_insert("hide_render", frame=1)
            for a_, b_ in shown:
                o.hide_render = False
                o.keyframe_insert("hide_render", frame=a_)
                o.hide_render = True
                o.keyframe_insert("hide_render", frame=b_)

    def spin(obj, pivot, axis, keys):                 # a part turning on its arbor/spindle: keys [(frame, degrees)]
        obj.rotation_mode = "XYZ"
        scene.frame_set(1)
        m0 = obj.matrix_world.copy()
        for f, deg in keys:
            obj.matrix_world = Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(deg), 4, axis) @ \
                Matrix.Translation(-pivot) @ m0
            obj.keyframe_insert("location", frame=f)
            obj.keyframe_insert("rotation_euler", frame=f)

    # ---- 2.1: down the corridor on tiptoe, the closed lantern hanging from his left hand; the long-case clock
    # ahead reads 11:56 and moves on to 11:58 by the latch
    a, b = T("2.1"), T("2.3") - 1
    stop = (CO + 0.05, 0.25)
    v4._walk(ctx, nar, [(a, (CO - 0.3, -2.0), 180), (T("2.2") - 18, stop, 180), (b, stop, 180)], a, b, clips=SNEAK)
    pivot = Vector((CO, 3.581, 1.735))                # the dial's arbor (the hands' bounds meet there)
    for part, at0, at1 in (("MinuteHand", 336, 348), ("HourHand", 358, 359)):
        hand = bpy.data.objects[f"CO_Long_Case_Clock_vintage_grandfather_clock_01_{part}"]
        far = max((hand.matrix_world @ v.co for v in hand.data.vertices), key=lambda p: (p - pivot).length)
        now = math.degrees(math.atan2(far.x - pivot.x, far.z - pivot.z)) % 360     # clockwise from 12, seen from -y
        span = T("2.4") - 1 - a
        spin(hand, pivot, "Y", [(f, at0 + (at1 - at0) * (f - a) / span - now) for f in range(a, T("2.4"), 6)])
    humans.eyes(nar, a, b, mode=lambda f: "listening", look=lambda f: (0.0, -6.0), seed=41)
    humans.breathe(nar, a, b, style="calm", seed=42)
    face(nar, a, cast3d.SLY)
    su.animate_camera(cams["corridor"], [(a, CAMERAS["corridor"][0], CAMERAS["corridor"][1]),
                                         (T("2.2") - 1, (CO + 0.3, -1.4, 1.2), (CO, 3.7, 1.35))])

    # ---- 2.2: his right palm, the watch in it; the minute hand reaches twelve (silver, white enamel, Roman
    # numerals, blued hands)
    def mat(name, color, metallic=0.0, rough=0.3):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bs = m.node_tree.nodes["Principled BSDF"]
        bs.inputs["Base Color"].default_value, bs.inputs["Metallic"].default_value = (*color, 1), metallic
        bs.inputs["Roughness"].default_value = rough
        return m
    coll = ctx["C"]["PROPS"]
    bm = bmesh.new()
    su.add_cylinder(bm, 0.025, 0.009, (0, 0, 0), segments=48)
    su.add_cylinder(bm, 0.0035, 0.006, (0, 0.028, 0), rotation=(90, 0, 0), segments=12)        # the crown
    su.add_torus(bm, 0.007, 0.0012, (0, 0.036, 0), rotation=(0, 90, 0), segments=16, ring=6)  # the bow
    watch = su.make_object("V5_Watch", coll, M("MAT_Steel"), bm, (0, 0, 0), bevel=0.0006)
    parts = [su.cylinder("V5_Watch_Dial", coll, mat("MAT_V5_Enamel", (0.92, 0.9, 0.84), rough=0.12), 0.0225,
                         0.001, (0, 0, 0.0047), segments=48)]
    black, blued = M("MAT_Plastic_Black"), mat("MAT_V5_Blued", (0.03, 0.05, 0.22), 1.0, 0.3)
    for i, numeral in enumerate(("XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI")):
        th = math.radians(30 * i)
        curve = bpy.data.curves.new(f"V5_Watch_{numeral}", "FONT")
        curve.body, curve.size, curve.align_x, curve.align_y = numeral, 0.0036, "CENTER", "CENTER"
        curve.materials.append(black)
        txt = bpy.data.objects.new(f"V5_Watch_{numeral}", curve)
        coll.objects.link(txt)
        txt.location, txt.rotation_euler.z = (0.0172 * math.sin(th), 0.0172 * math.cos(th), 0.0053), -th
        parts.append(txt)
    hands = {}
    for name, size, z in (("Minute", (0.0009, 0.0185, 0.0004), 0.0058), ("Hour", (0.0014, 0.011, 0.0004), 0.0055)):
        bm = bmesh.new()
        su.add_box(bm, size, (0, size[1] / 2 - 0.002, 0))
        hands[name] = su.make_object(f"V5_Watch_{name}", coll, blued, bm, (0, 0, z))
        parts.append(hands[name])
    for p in parts:
        p.parent = watch
    a, b = T("2.2"), T("2.3") - 1
    fwd = Vector((0, 1, 0))                           # he faces +y (heading 180): his right is +x
    palm = Vector((stop[0] + 0.12, stop[1] + 0.27, 1.08))
    v4._contact(ctx, nar, "Right", a - 30, b, lambda f: palm if f >= a - 18 else None,
                lambda f: humans.hand_frame((-0.3, 1.0, 0.0), (0.0, 0.0, 1.0)), blend=12)
    humans.grip(nar, "Right", a - 18, curl=0.25)      # cupped, holding it
    scene.frame_set(a)
    hb = nar.matrix_world @ nar.pose.bones["RightHand"].matrix
    along = (hb.to_3x3() @ Vector((0, 1, 0))).normalized()
    watch.matrix_world = Matrix.Translation(hb.translation + along * 0.075 + Vector((0, 0, 0.024))) @ \
        Matrix.Rotation(math.atan2(-fwd.x, fwd.y), 4, "Z")
    v4._carry(ctx, watch, nar, "RightHand", a, b)
    for name, (d0, d1) in (("Minute", (348, 360)), ("Hour", (359, 360))):
        h = hands[name]
        for f, d in ((1, d0), (a + 12, d0), (b - 10, d1)):
            h.rotation_euler.z = -math.radians(d)     # clockwise, seen from above the dial
            h.keyframe_insert("rotation_euler", frame=f)
    hold_hidden([watch] + parts, [(a, b + 1)])
    scene.frame_set(a + 12)
    w = watch.matrix_world.translation
    su.animate_camera(cams["watch"], [(a, tuple(w - fwd * 0.07 + Vector((0.02, 0, 0.27))), tuple(w))])
    cams["watch"].data.dof.use_dof, cams["watch"].data.dof.aperture_fstop = True, 5.6
    cams["watch"].data.dof.focus_object = watch
    glint = su.light("V5_Watch_Moon", ctx["C"]["SET"], "AREA", tuple(w + Vector((0.12, -0.2, 0.3))), 0,
                     (0.6, 0.72, 1.0), target=tuple(w), shape="DISK", size=0.15)
    for f, e in ((1, 0), (a - 1, 0), (a, 2.5), (b, 2.5), (b + 1, 0)):
        glint.data.energy = e
        glint.data.keyframe_insert("energy", frame=f)
    face(nar, a, cast3d.SLY)

    # ---- 2.3: at the old man's door his fingertips turn the knob, a little at a time (the latch moves only with
    # them); the lantern still hangs from his other hand
    a, b = T("2.3"), T("2.4") - 1
    spot = (CO + 0.55, 0.98)
    v4._walk(ctx, nar, [(a, spot, 90), (b, spot, 90)], a, b)
    knob = ctx["set"]["corridor"]["handle"]
    scene.frame_set(a)
    kp = knob.matrix_world.translation.copy()
    K0, K1 = T("2.3", 1.4), T("2.3", 4.2)
    turn = lambda f: 50 * ease(K0, K1, f)
    spin(knob, kp, "X", [(f, turn(f)) for f in range(K0 - 1, K1 + 2, 2)])
    humans._layer(nar, a, b, lambda f: {"LowerBack": (0, 6, 0), "Spine": (0, 4, 0), "Neck1": (0, 4, 0)})
    humans.eyes(nar, a, b, mode=lambda f: "listening", look=lambda f: (-10.0, -12.0), seed=43)
    humans.breathe(nar, a, b, style="calm", seed=44)
    grip_at = kp + Vector((-0.085, -0.02, -0.01))
    v4._contact(ctx, nar, "Right", a, b, lambda f: grip_at if f >= a + 10 else None,
                lambda f: humans.hand_frame((1.0, 0.0, -0.25),
                                            Matrix.Rotation(-math.radians(turn(f)), 3, "X") @ Vector((0, 1, 0))),
                blend=10)
    humans.grip(nar, "Right", a + 10, curl=0.8)
    dof = cams["latch"].data.dof
    dof.use_dof, dof.aperture_fstop = True, 2.8
    lens_at = Vector(CAMERAS["latch"][0])
    for f, p in ((a, grip_at + Vector((-0.03, 0, 0))), (K0, grip_at + Vector((-0.03, 0, 0))), (K0 + 20, kp)):
        dof.focus_distance = (p - lens_at).length    # a focus pull from the fingers to the latch
        dof.keyframe_insert("focus_distance", frame=f)
    ctx["marks"]["2.3/latch"] = K0 + 6
    # the lantern hangs from his left fingers by its ring all through 2.1-2.3 (after every layer on that arm)
    humans.grip(nar, "Left", T("2.1"), curl=1.6)
    humans.hang(lantern, nar, "Left", T("2.1"), b, ring=(0, 0, 0.32), length=0.22,
                yaw=lambda f: v4._at(nar, f).to_euler().z)

    # ---- 2.4-2.8: the chamber at midnight. The door eased open a sliver by his palm; the lantern in, then his
    # head (an hour of it by the clock behind him); his thumb cracks the shutter; a thread of light on the eye
    a, b = T("2.4"), T("2.9") - 1
    v4._walk(ctx, nar, [(a, GAP, 180), (b, GAP, 180)], a, b)
    door = room["door"]
    D0, D1 = T("2.4", 1.0), T("2.4", 7.0)
    for f, deg in ((1, 0), (D0, 0), (D1, -24), (T("2.9") - 1, -24), (T("2.9"), 0)):
        door.rotation_euler.z = math.radians(deg)
        door.keyframe_insert("rotation_euler", frame=f)
    for fc in v3._fcurves(door):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"

    def lean(f):                                      # as far as the opening lets him; then an hour, 1 cm a second
        x = ease(D0 + 30, D1, f) + 0.3 * ease(T("2.5"), T("2.6"), f)          # as the eighth night (v3)
        return {"Hips": (0, 9 * x, 0), "LeftUpLeg": (0, -9 * x, 0), "RightUpLeg": (0, -9 * x, 0),
                "LowerBack": (0, 3 + 4 * x, 0), "Spine": (0, 2 + 3 * x, 0), "Spine1": (0, 4 * x, 0),
                "Neck1": (0, -6 * x, 0), "Head": (0, -6 * x, 0)}
    humans._layer(nar, a, b, lean)
    humans.sway(nar, a, b, amount=0.35, seed=45)
    humans.breathe(nar, a, b, style="calm", seed=46)
    humans.eyes(nar, a, b, mode=lambda f: "listening", look=lambda f: (-18.0, -12.0), seed=47, head=False)
    face(nar, a, cast3d.TENSE)
    face(nar, T("2.5", 8.0), {**cast3d.SLY, "mouthSmileLeft": 0.25})     # "would a madman have been so wise?"
    face(nar, T("2.6"), cast3d.TENSE)
    om.location, om.rotation_euler = (0.9, 0.38, 0.56), (math.radians(-90), 0, 0)   # asleep on his back
    om.keyframe_insert("location", frame=1)
    om.keyframe_insert("rotation_euler", frame=1)
    humans.face(om, 1, {"eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0})
    humans.breathe(om, 1, T("2.9", 1.5), style="sleep", seed=48)
    # his left hand: the lantern low by his thigh behind the door, then up into the gap
    low, high = Vector((-1.86, -2.575, 1.02)), Vector((-1.70, -2.22, 1.31))
    R0, R1 = T("2.4", 7.5), T("2.4", 10.0)
    lift = lambda f: low.lerp(high, ease(R0, R1, f)) + Vector((0, 0, 0.05 * math.sin(math.pi * ease(R0, R1, f))))
    humans.reach(nar, "Left", a, b, lift, wrist=(15, (0, 0, -1)))
    scene.frame_set(T("2.6"))
    eye = lambda: om.matrix_world @ om.pose.bones["LeftEye"].head + Vector((0, -0.012, 0))
    humans.hang(lantern, nar, "Left", a, b, ring=(0, 0, 0.32), length=0.22, yaw=v3._yaw_to(high, eye()))
    # his right palm on the door's corridor face; once it is open enough, it comes to cradle the lantern's base
    def door_frame(f):
        scene.frame_set(min(f, D1))
        m = door.matrix_world
        out = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
        along = (m.to_3x3() @ Vector((1, 0, 0))).normalized()
        fingers = (Vector((0, 0, 1)) + 0.35 * along).normalized()
        return m, out, (fingers * math.cos(math.radians(12)) + out * math.sin(math.radians(12))).normalized()

    def on_door(f):
        m, out, fingers = door_frame(f)
        return m @ Vector((0.40, 0.02, 1.25)) - fingers * 0.05 + out * 0.048

    def at_lantern(f):
        scene.frame_set(f)
        return lantern.matrix_world @ Vector((0, 0, 0)) + Vector((0.085, -0.03, 0.09))   # its side, mid-height
    cup_from, cup_to = D1 + 6, T("2.5", 1.0)
    cup_turn = humans.hand_frame((0.0, 0.9, 0.4), (-1.0, 0.0, 0.0))     # palm on the tin, thumb to the shutter

    def right_hand(f):
        if f < D0 - 6:
            return None
        if f <= cup_from:
            return on_door(f)
        x = ease(cup_from, cup_to, f)
        side = at_lantern(f) + Vector((0.10, -0.06, 0.0))
        return on_door(f).lerp(side, x / 0.5) if x < 0.5 else side.lerp(at_lantern(f), (x - 0.5) / 0.5)

    def right_turn(f):
        on = humans.hand_frame(door_frame(f)[2], -door_frame(f)[1])
        return on.to_quaternion().slerp(cup_turn.to_quaternion(), ease(cup_from, cup_to, f)).to_matrix()
    humans.grip(nar, "Right", a, curl=-0.6)          # a flat hand on the door
    humans.grip(nar, "Right", cup_to, curl=1.0)
    v4._contact(ctx, nar, "Right", a, b, right_hand, right_turn, blend=10)
    ctx["held"].append(dict(prop=door.name, rig=nar.name, bone="RightHand", f0=D0, f1=D1, point=[0.40, 0.02, 1.25]))
    ctx["marks"]["2.4/door_creak_soft"] = D0 + 8
    # 2.6: a crevice: his right thumb eases the shutter; the beam held on the eye through the nights
    C1, C2 = T("2.6", 3.0), T("2.6", 7.5)
    thumb = nar.pose.bones[humans.THUMB["Right"]]
    scene.frame_set(C1 - 2)
    rest_thumb = thumb.rotation_quaternion.copy()
    for f, deg, sh in ((C1 - 2, 0, 0), (C2, 18, -9), (C2 + 8, 8, -9)):
        thumb.rotation_quaternion = rest_thumb @ Quaternion((1, 0, 0), math.radians(deg))
        thumb.keyframe_insert("rotation_quaternion", frame=f)
        shutter.rotation_euler.z = math.radians(sh)
        shutter.keyframe_insert("rotation_euler", frame=f)
    for f in range(C1, b + 1, 2):
        scene.frame_set(f)
        v3._aim_beam(beam, lantern, eye())
        beam.keyframe_insert("rotation_quaternion", frame=f)
    for f, e, g in ((1, 0, 2), (C1 + 10, 0, 2), (C2, 3500, 2), (b, 3500, 2), (b + 1, 0, 0)):
        beam.data.energy, glow.data.energy = e, g
        beam.data.keyframe_insert("energy", frame=f)
        glow.data.keyframe_insert("energy", frame=f)
    ctx["marks"]["2.6/hinge_tiny"] = C1 + 20
    hold_hidden([lantern, shutter], [(1, T("2.9"))])
    # the chamber's wall clock (behind him in 2.5) sweeps an hour: its hands made separate to turn on the arbor
    old = room["clock_hands"]
    bm = bmesh.new()
    bm.from_mesh(old.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in range(16)], context="VERTS")      # its two hand boxes
    bm.to_mesh(old.data)
    bm.free()
    scene.frame_set(1)
    m0, r = old.matrix_world.copy(), 0.15
    for name, size, center, d0 in (("Minute", (0.006, 0.002, r * 0.75), (0, 0, r * 0.33), 0),
                                   ("Hour", (r * 0.5, 0.002, 0.008), (r * 0.23, 0, 0), -90)):
        bm = bmesh.new()
        su.add_box(bm, size, center)
        h = su.make_object(f"V5_Wall_Clock_{name}", ctx["C"]["SET"], black, bm)
        h.rotation_mode = "XYZ"
        sweep = 360 if name == "Minute" else 30
        for f in [1] + list(range(T("2.5"), T("2.6") + 1, 2)):
            h.matrix_world = m0 @ Matrix.Rotation(math.radians(d0 + sweep * ease(T("2.5"), T("2.6"), f)), 4, "Y")
            h.keyframe_insert("location", frame=f)
            h.keyframe_insert("rotation_euler", frame=f)
    # cameras: the gap's slow push; the lantern macro; the room, dollying with the beam
    ctx.setdefault("extra_cuts", []).append(("2.4", 6.5, "gap"))      # the lantern, then his head, in the slot
    # the moon through the room onto the gap (as v2 and v3): his face and the lantern there are lit by it
    spill = su.light("V5_Moon_Spill", ctx["C"]["SET"], "AREA", (-2.30, -1.70, 1.90), 0, (0.55, 0.65, 1.0),
                     target=(-1.60, -2.38, 1.58), size=0.2)
    for f, e in ((1, 0), (T("2.4") - 1, 0), (T("2.4"), 9), (T("2.9") - 1, 9), (T("2.9"), 0)):
        spill.data.energy = e
        spill.data.keyframe_insert("energy", frame=f)
    cams["lantern"].data.dof.use_dof, cams["lantern"].data.dof.focus_object = True, lantern
    scene.frame_set(T("2.7"))                         # beside the thread of light, then along it to the eye (as v3)
    src, dst = lantern.matrix_world.translation.copy(), eye()
    ray = (dst - src).normalized()
    side = ray.cross(Vector((0, 0, 1))).normalized()
    su.animate_camera(cams["room"], [(T("2.7"), tuple(src + ray * 0.6 + side * 0.3 + Vector((0, 0, 0.1))),
                                      tuple(src + ray * 1.8)),
                                     (T("2.8") - 1, tuple(dst - ray * 1.1 + side * 0.25 + Vector((0, 0, 0.06))),
                                      tuple(dst))])
    cams["room"].data.lens = 40
    # 2.8: six more nights, each with its card; each night wears him more
    n0, seg = T("2.8"), (T("2.9") - T("2.8")) / 6 / 24
    cards = []
    for i, roman in enumerate(("II", "III", "IV", "V", "VI", "VII")):
        z = -10.0 - 3 * i
        cards.append(sets.text(f"V5_Card_{roman}", ctx["C"]["SET"], f"Night {roman}", (CARD_X, 0, z), 0.32))
        t0 = i * seg
        su.animate_camera(cams["card"], [(T("2.8", t0), (CARD_X, -3.0, z + 0.1), (CARD_X, 0, z + 0.1))])
        ctx.setdefault("extra_cuts", []).extend([("2.8", t0, "card"), ("2.8", t0 + 0.8, f"night{i}")])
        if i % 2 == 0:
            ctx["marks"]["2.8/clock_chime" + ("" if i == 0 else f"#{i // 2 + 1}")] = T("2.8", t0 + 0.3)
    v4._constant(cams["card"], ("location", "rotation_euler"))
    nights = [(T("2.8", i * seg), round(0.1 * (i + 1), 2)) for i in range(6)]

    # ---- 2.9: morning. He throws open the shutters (a hand on each leaf), the old man wakes and sits up; the
    # greeting, warm and hearty
    a, b = T("2.9"), end
    O0, O1 = T("2.9", 1.0), T("2.9", 2.0)
    ns = next(l for s in tl["shots"] for l in s["lines"] if l["line"] == "2.9_1_NS")
    NS = 1 + int(round(ns["start"] * 24))
    at_win, by_bed = (1.93, 0.0), (1.55, 0.45)
    v4._walk(ctx, nar, [(a, at_win, 90), (O1 + 12, at_win, 90), (NS - 8, by_bed, v4.heading_to(by_bed, (0.9, 1.5))),
                        (b, by_bed, v4.heading_to(by_bed, (0.9, 1.5)))], a, b)
    humans.eyes(nar, a, NS - 25, mode=lambda f: "thinking", look=lambda f: (0.0, 0.0) if f < O1 + 12 else (35.0, -8.0),
                seed=49)
    humans.breathe(nar, a, NS - 25, style="calm", seed=50)
    face(nar, a, cast3d.PLEASANT)
    face(nar, NS - 10, cast3d.CHARM)
    face(om, O1 + 20, cast3d.PLEASANT)
    humans.face(om, O0 + 2, {"eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0})          # the light wakes him
    humans.face(om, O1 + 4, {"eyeBlinkLeft": 0.0, "eyeBlinkRight": 0.0})
    rise = O1 + 8
    humans.rise_in_bed(om, rise, b, seconds=1.4, lead="Right")
    lines = [l for s in tl["shots"] for l in s["lines"] if l["line"] in ON_CAMERA]

    def idle(n, f):
        return ("OldMan" if n == "Narrator" else "Narrator"), "listening"
    v4._converse(ctx, lines, NS - 24, b, {"Narrator": 0.45, "OldMan": 0.15}, idle, seated=False,
                 no_fidget=("OldMan",), who={"NS": "Narrator", "OM": "OldMan"})
    for side, dx in (("Right", -0.24), ("Left", 0.24)):     # the old man's hands: on his belly asleep; they push on
        belly, push, lap = (Vector((0.9 + dx * 0.45, 1.32, 0.70)), Vector((0.9 + dx * 1.25, 1.40, 0.475)),   # the
                            Vector((0.9 + dx * 0.55, 1.18, 0.72)))                    # mattress as he sits; his lap

        def om_at(f, belly=belly, push=push, lap=lap):
            u, w = ease(rise, rise + 7, f), ease(rise + 38, rise + 53, f)
            return (belly.lerp(push, u) + Vector((0, 0, 0.05 * math.sin(math.pi * u)))).lerp(lap, w)
        humans.reach(om, side, 1, b, om_at, hand=humans.hand_frame((0.3 * (1 if dx > 0 else -1), -1, 0), (0, 0, -1)))
    # the shutters: each leaf turns on its outer hinge, pulled open by a hand, and swings on a little when let go
    scene.frame_set(1)
    for leaf in room["shutters"]:
        leaf.rotation_mode = "XYZ"
        vs = [leaf.matrix_world @ v.co for v in leaf.data.vertices]
        sy = 1 if sum(v.y for v in vs) > 0 else -1
        hinge = Vector((sum(v.x for v in vs) / len(vs), max(v.y * sy for v in vs) * sy, 1.575))
        m0 = leaf.matrix_world.copy()
        mid = sum(vs, Vector()) / len(vs)
        turn = 1 if (Matrix.Rotation(math.radians(90), 3, "Z") @ (mid - hinge)).x < 0 else -1
        angle = lambda f: 75 * ease(O0, O1, f) + 22 * ease(O1, O1 + 8, f)
        rot = lambda f: Matrix.Rotation(turn * math.radians(angle(f)), 3, "Z")
        for f in [1] + list(range(O0 - 1, O1 + 10)):
            leaf.matrix_world = Matrix.Translation(hinge) @ rot(f).to_4x4() @ Matrix.Translation(-hinge) @ m0
            leaf.keyframe_insert("location", frame=f)
            leaf.keyframe_insert("rotation_euler", frame=f)
        grab = Vector((hinge.x - 0.035, hinge.y - sy * 0.3, 1.45)) - hinge
        v4._contact(ctx, nar, "Left" if sy > 0 else "Right", O0 - 14, O1 + 14,
                    lambda f, grab=grab, hinge=hinge, rot=rot: (hinge + rot(f) @ grab) if O0 - 2 <= f <= O1 else None,
                    lambda f, rot=rot: humans.hand_frame((0, 0, 1), rot(f) @ Vector((1, 0, 0))), blend=10)
        ctx["held"].append(dict(prop=leaf.name, rig=nar.name, bone=("Left" if sy > 0 else "Right") + "Hand",
                                f0=O0, f1=O1, point=list(m0.inverted() @ (hinge + grab))))
    for name, lo in (("fill", 3), ("warm", 2)):       # the room fills with day as they open
        lt = ctx["lights"][name]
        for f, e in ((a, lo), (O0, lo), (O1 + 6, LIGHTS["2.9"][name])):
            lt.data.energy = e
            lt.data.keyframe_insert("energy", frame=f)
    sky = room["sky"]
    day = su.box("V5_Day_Sky", ctx["C"]["SET"], mat("MAT_V5_Day_Sky", (0.75, 0.85, 1.0), rough=1.0),
                 tuple(sky.dimensions), tuple(sky.matrix_world.translation), bevel=0)
    day.visible_shadow = False
    em = day.active_material.node_tree.nodes["Principled BSDF"]
    em.inputs["Emission Color"].default_value, em.inputs["Emission Strength"].default_value = (0.75, 0.85, 1.0, 1), 2.0
    hold_hidden([day], [(a, b + 1)])
    hold_hidden([sky], [(1, a)])
    ctx["extra_cuts"].append(("2.9", (NS - a) / 24 - 0.4, "morning"))
    su.animate_camera(cams["morning"], [(NS - 10, CAMERAS["morning"][0], CAMERAS["morning"][1]),
                                        (b, (1.85, -0.75, 1.57), (0.55, 1.15, 1.2))])
    humans.wear(nar, nights)                           # last: the lids are added to every blink keyed above
