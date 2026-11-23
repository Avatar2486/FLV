"""
Tell-Tale Heart v4 preview: "the visitors" (film shots 5.1-5.15). Three officers of the police come at four in
the morning; the narrator lets them in, shows them the house, sets his chair on the planks over the body and
chats with them until the heartbeat he alone hears breaks him. Everyone on screen is alive: speakers gesture
with their speech (humans.gestures), listeners nod and look (humans.listen), everyone breathes and blinks.
Nothing moves unless a hand moves it. The officers are stand-ins (the narrator re-dressed) until the real ones
come from the character generator (docs/officers_cast_specs.md).

    blender -b --factory-startup --python stories/the_tell_tale_heart/preview_v4.py -- standins   (check)
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(HERE)]
import preview_v3 as v3  # noqa: E402  (the shared helpers: timeline, gait, feet, render, draft)

OUT = ROOT / "output" / "renders" / "the_tell_tale_heart_v4_visitors"
BLEND = ROOT / "blender" / "scenes" / "tell_tale_heart_v4_visitors.blend"
VO = ROOT / "audio" / "voiceovers" / "the_tell_tale_heart_v4"
FPS = v3.FPS
ON_SCREEN = ("NS", "O1", "O2", "O3")              # lines spoken on camera (N is the voice-over)

# (shot, [(line key, who)], minimum seconds); the line keys are files in VO (preview_v4/lines.json)
SHOTS = [
    ("5.1", [("5.1_0_N", "N")], 8.6),
    ("5.2", [("5.2_0_N", "N"), ("5.2_1_O1", "O1")], 13.2),
    ("5.3", [("5.3_0_NS", "NS")], 8.8),
    ("5.4", [("5.4_0_N", "N"), ("5.4_1_NS", "NS")], 8.0),
    ("5.5", [("5.5_0_N", "N")], 8.2),
    ("5.6", [("5.6_0_N", "N")], 16.2),
    ("5.7", [("5.7_0_N", "N"), ("5.7_1_O2", "O2"), ("5.7_2_O3", "O3"), ("5.7_3_N", "N")], 16.3),
    ("5.8", [("5.8_0_N", "N")], 10.0),
    ("5.9", [("5.9_0_N", "N")], 7.0),
    ("5.10", [("5.10_0_N", "N")], 13.0),
    ("5.11", [("5.11_0_N", "N")], 14.8),
    ("5.12", [("5.12_0_N", "N")], 13.5),
    ("5.13", [("5.13_0_N", "N")], 17.0),
    ("5.14", [("5.14_0_N", "N")], 8.1),
    ("5.15", [("5.15_0_NS", "NS")], 9.2),
]
# (shot, seconds into the shot, line key, who): the officers' small talk, and the narrator's, under the narration
# ("they chatted of familiar things"; in 5.11 he "argued about trifles, in a high key")
CHATTER = [
    ("5.7", 0.5, "5.7_c1_O1", "O1"), ("5.7", 3.1, "5.7_c2_NS", "NS"),
    ("5.7", 11.0, "5.7_c3_O2", "O2"), ("5.7", 13.4, "5.7_c4_NS", "NS"),
    ("5.8", 0.6, "5.8_c5_O3", "O3"), ("5.8", 3.7, "5.8_c6_O2", "O2"),
    ("5.9", 1.0, "5.9_c7_O1", "O1"),
    ("5.10", 0.8, "5.10_c8_O2", "O2"), ("5.10", 3.7, "5.10_c9_O3", "O3"),
    ("5.11", 1.0, "5.11_c10_NS", "NS"), ("5.11", 5.0, "5.11_c11_NS", "NS"),
    ("5.12", 6.0, "5.12_c12_O1", "O1"),
    ("5.13", 1.5, "5.13_c13_O2", "O2"), ("5.13", 4.2, "5.13_c14_O3", "O3"),
]


def voice(key):
    return VO / f"{key}.wav"


def timeline():
    """v3's timeline (shots laid end to end, each as long as its lines), plus the chatter at fixed offsets."""
    tl = v3.timeline(SHOTS, voice)
    start = {s["id"]: s["start"] for s in tl["shots"]}
    tl["chatter"] = [{"file": str(voice(key).relative_to(ROOT)), "who": who, "line": key,
                      "start": round(start[sid] + off, 3), "seconds": round(v3.seconds(voice(key)), 3)}
                     for sid, off, key, who in CHATTER]
    return tl


def check_timeline(tl=None):
    """Chatter never talks over an on-screen line or over other chatter, stays inside 5.7-5.13; >= 170 s."""
    tl = tl or timeline()
    spoken = [l for s in tl["shots"] for l in s["lines"] if l["who"] in ON_SCREEN]
    span = {s["id"]: (s["start"], s["start"] + s["seconds"]) for s in tl["shots"]}
    ids = [s["id"] for s in tl["shots"]]
    inside = ids[ids.index("5.7"): ids.index("5.13") + 1]
    lo, hi = span[inside[0]][0], span[inside[-1]][1]
    tol = 0.05

    def overlap(a, b):
        return a["start"] < b["start"] + b["seconds"] - tol and b["start"] < a["start"] + a["seconds"] - tol
    for i, c in enumerate(tl["chatter"]):
        assert lo <= c["start"] and c["start"] + c["seconds"] <= hi, f"chatter {c['line']} outside 5.7-5.13"
        for l in spoken:
            assert not overlap(c, l), f"chatter {c['line']} talks over {l['line']}"
        for d in tl["chatter"][i + 1:]:
            assert not overlap(c, d), f"chatter {c['line']} and {d['line']} at once"
    assert tl["seconds"] >= 170, f"only {tl['seconds']} s"
    print(f"V4 timeline OK: {tl['seconds']:.1f} s, {len(tl['chatter'])} chatter lines")
    return tl


# ----------------------------------------------------------------------------------------------- props
def _parent_to_bone(obj, rig, bone):
    """Parent obj to one of rig's bones, keeping where it is (it then moves with that bone)."""
    import bpy
    world = obj.matrix_world.copy()
    obj.parent, obj.parent_type, obj.parent_bone = rig, "BONE", bone
    bpy.context.view_layer.update()
    obj.matrix_world = world


def _material(name, rgb, roughness, metallic=0.0):
    import bpy
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def top_hat(coll, rig, crown=0.16, brim=0.065):
    """An 1840s top hat fitted to the character's hair: its band sits 7.5 cm below the top of the hair, the
    crown an ellipse 8 mm outside the hair at that height (so no hair pokes through), slightly flared, open
    underneath; a flat brim. Parented to the Head bone. Stores rx, ry (crown radii, m) and band (z, m)."""
    import bmesh
    import bpy
    from mathutils import Matrix, Vector
    hair = next(o for o in rig.children if o.name.endswith(".hair"))
    bpy.context.view_layer.update()
    up = (rig.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    pts = [hair.matrix_world @ v.co for v in hair.data.vertices]
    band = max(p.dot(up) for p in pts) - 0.075
    level = [p for p in pts if abs(p.dot(up) - band) < 0.01]
    rot = rig.matrix_world.to_3x3().normalized()
    local = [rot.inverted() @ p for p in level]               # the character's own axes
    xs, ys = [p.x for p in local], [p.y for p in local]
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    rx, ry = (max(xs) - min(xs)) / 2 + 0.008, (max(ys) - min(ys)) / 2 + 0.008
    bm = bmesh.new()
    n = 48

    def loop(ax, ay, z):
        return [bm.verts.new((ax * math.cos(2 * math.pi * i / n), ay * math.sin(2 * math.pi * i / n), z))
                for i in range(n)]
    low, high = loop(rx, ry, 0.0), loop(rx * 1.04, ry * 1.04, crown)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((low[i], low[j], high[j], high[i]))
    bm.faces.new(high)                                          # the crown's top; open underneath
    inner, outer = loop(rx, ry, 0.0), loop(rx + brim, ry + brim, 0.0)
    inner_t, outer_t = loop(rx, ry, 0.006), loop(rx + brim, ry + brim, 0.006)
    for i in range(n):
        j = (i + 1) % n
        for a, b in ((inner, outer), (inner_t, outer_t), (outer, outer_t)):
            bm.faces.new((a[i], a[j], b[j], b[i]))
    mesh = bpy.data.meshes.new(f"{rig.name}_Hat")
    bm.to_mesh(mesh)
    bm.free()
    hat = bpy.data.objects.new(f"V4_Hat_{rig.name}", mesh)
    coll.objects.link(hat)
    mesh.materials.append(_material("MAT_Felt_Black", (0.025, 0.022, 0.02), 0.85))
    for poly in mesh.polygons:
        poly.use_smooth = True
    centre = rot @ Vector((cx, cy, 0)) + up * band - up * up.dot(rot @ Vector((cx, cy, 0)))
    hat.matrix_world = Matrix.Translation(centre) @ rot.to_4x4()
    _parent_to_bone(hat, rig, "Head")
    hat["rx"], hat["ry"], hat["band"] = rx, ry, band
    return hat


def star_badge(coll, rig, size=0.04):
    """The copper eight-pointed star of an 1840s officer (New York's 1845 'star police'), on the left breast,
    2 mm off the coat, parented to the upper spine."""
    import bmesh
    import bpy
    from mathutils import Matrix, Vector
    shirt = next(o for o in rig.children if o.name.endswith(".shirt"))
    bpy.context.view_layer.update()
    m = rig.matrix_world
    k = m.to_scale().x
    rot = m.to_3x3().normalized()
    forward, left = rot @ Vector((0, -1, 0)), rot @ Vector((1, 0, 0))
    aim = m.translation + rot @ Vector((0.085 * k, 0, 1.31 * k))
    deps = bpy.context.evaluated_depsgraph_get()
    inv = shirt.matrix_world.inverted()
    hit, loc, normal, _ = shirt.evaluated_get(deps).ray_cast(inv @ (aim + forward * 0.5), inv.to_3x3() @ -forward)
    assert hit, f"{rig.name}: no shirt in front of the chest"
    where = shirt.matrix_world @ loc
    normal = (shirt.matrix_world.to_3x3().inverted().transposed() @ normal).normalized()
    bm = bmesh.new()
    rim = []
    for i in range(16):
        r = size / 2 if i % 2 == 0 else size * 0.22
        a = math.pi * i / 8 + math.pi / 2
        rim.append(bm.verts.new((r * math.cos(a), r * math.sin(a), 0)))
    top = bmesh.ops.extrude_face_region(bm, geom=[bm.faces.new(rim)])["geom"]
    bmesh.ops.translate(bm, verts=[v for v in top if isinstance(v, bmesh.types.BMVert)], vec=(0, 0, 0.002))
    mesh = bpy.data.meshes.new(f"{rig.name}_Badge")
    bm.to_mesh(mesh)
    bm.free()
    badge = bpy.data.objects.new(f"V4_Badge_{rig.name}", mesh)
    coll.objects.link(badge)
    mesh.materials.append(_material("MAT_Copper", (0.72, 0.42, 0.22), 0.35, metallic=1.0))
    z = normal
    x = left - z * left.dot(z)
    x.normalize()
    basis = Matrix((x, z.cross(x), z)).transposed()
    badge.matrix_world = Matrix.Translation(where + z * 0.002) @ basis.to_4x4()
    _parent_to_bone(badge, rig, "Spine1")
    return badge


# ----------------------------------------------------------------------------------------------- the scene
# Blocking, per shot: (x, y, heading). Heading 0 faces -y, 90 faces +x. The sets sit side by side
# (sets.SET_X): the entry hall at x 40 (street door south, stair up the west wall), the kitchen at x 60,
# the old man's chamber at x 0 (door south, bed north, loose planks at x -1.2..0, y -0.27..0.27).
SEATS = {"Narrator": (-0.6, 0.0), "Hale": (0.55, -0.35), "Brandt": (-0.05, 0.95), "Mercer": (0.0, -1.05)}
SEAT_FOCUS = {"Narrator": (0.25, -0.2), "Hale": (-0.3, -0.1), "Brandt": (-0.1, -0.3), "Mercer": (-0.2, 0.0)}
OUTSIDE = {"Hale": (40.0, -2.8, 180), "Brandt": (39.45, -3.1, 180), "Mercer": (40.6, -3.2, 180)}
PLACES = {
    "5.1": dict(Narrator=(38.55, -1.75, 0), **OUTSIDE),
    "5.2": dict(Narrator=(40.25, -1.45, 0), **OUTSIDE),
    "5.3": dict(Narrator=(40.25, -1.45, 0), **OUTSIDE),
    "5.4": dict(Narrator=(61.0, 0.2, 330), Hale=(60.1, 1.5, 10), Brandt=(59.5, 1.9, 350), Mercer=(60.5, 2.1, 0)),
    "5.5": dict(Narrator=(1.45, -1.3, 90), Hale=(1.05, -0.6, 135), Brandt=(1.65, -0.5, 170), Mercer=(0.8, -1.6, 70)),
}
CHAMBER_SHOTS = ("5.6", "5.7", "5.8", "5.9", "5.10", "5.11", "5.12", "5.13", "5.14", "5.15")
SEAT_HEIGHT = 0.46


def heading_to(p, q):
    """Heading (0 faces -y, 90 faces +x) that faces from p toward q."""
    return math.degrees(math.atan2(q[0] - p[0], -(q[1] - p[1])))


def places(sid):
    if sid in PLACES:
        return PLACES[sid]
    return {n: (*xy, heading_to(xy, SEAT_FOCUS[n])) for n, xy in SEATS.items()}


# Lights per shot (energy in W): 4 a.m.; the officers' lanterns make the chamber the brightest scene, warm and
# cosy in 5.7, draining from 5.8, cold from 5.12.
LIGHT_KEYS = {
    "5.1": dict(en_fill=4), "5.2": dict(V4_Gas_Lamp_light=300, en_fill=4), "5.3": dict(V4_Gas_Lamp_light=300, en_fill=4),
    "5.4": dict(ki_fill=4), "5.5": dict(warm=30, fill=6, moon=60), "5.6": dict(warm=45, fill=6, moon=60),
    "5.7": dict(warm=60, fill=6, moon=60), "5.8": dict(warm=40, fill=10, moon=70),
    "5.9": dict(warm=35, fill=10, moon=70), "5.10": dict(warm=25, fill=14, moon=80),
    "5.11": dict(warm=18, fill=18, moon=90), "5.12": dict(warm=8, fill=26, moon=110),
    "5.13": dict(warm=6, fill=28, moon=110), "5.14": dict(warm=5, fill=30, moon=120),
    "5.15": dict(warm=5, fill=30, moon=120)}
LANTERN_GLOW = {"5.5": 6, "5.6": 6, "5.7": 7, "5.8": 5, "5.9": 5, "5.10": 4, "5.11": 3, "5.12": 2, "5.13": 2,
                "5.14": 2, "5.15": 2}


def _cameras(T, su, C, Vector):
    """Every shot's camera: name -> (at, look, lens); moves are keyed by the acts (later) or here."""
    c4 = Vector((-0.05, -0.15, 0.95))
    rigs = {
        "stairs": ((38.95, -0.3, 2.0), (38.55, 0.9, 1.95), 35),
        "hall": ((41.3, 1.25, 1.6), (40.0, -2.8, 1.45), 30),
        "door_cu": ((39.75, -2.95, 1.62), (40.25, -1.45, 1.6), 50),
        "kitchen": ((62.4, -2.1, 2.1), (60.0, 1.8, 1.1), 24),
        "chest": ((0.75, -2.0, 1.45), (1.9, -1.3, 0.55), 35),
        "floor": ((0.45, -0.75, 0.16), (-0.6, 0.0, 0.12), 24),
        "four": (tuple(c4 + Vector((2.2 * math.cos(math.radians(-75)), 2.2 * math.sin(math.radians(-75)), 0.7))),
                 tuple(c4), 24),
        "nar_cu": ((0.35, -0.75, 1.3), (-0.6, 0.0, 1.2), 85),
        "macro": ((-0.38, -0.32, 0.05), (-0.6, -0.09, 0.0), 100),
        "nar_hh": ((0.15, -0.5, 1.28), (-0.6, 0.0, 1.2), 50),
        "orbit": ((-0.6, -1.8, 1.6), (-0.6, -0.3, 1.2), 35),
        "top": ((-0.2, -0.15, 2.85), (-0.2, -0.149, 0.0), 22),
        "officers": ((-0.4, -0.05, 1.25), (0.17, -0.15, 1.15), 35),
        "eye_n": ((-0.38, -0.12, 1.22), (-0.55, 0.0, 1.2), 100),
        "smile_h": ((0.15, -0.25, 1.2), (0.5, -0.33, 1.2), 85),
        "smile_b": ((-0.2, 0.55, 1.2), (-0.05, 0.9, 1.2), 85),
        "smile_m": ((-0.15, -0.65, 1.2), (0.0, -1.0, 1.2), 85),
        "ms15": ((0.6, -0.9, 1.4), (-0.6, 0.0, 1.1), 50),
    }
    cams = {}
    for name, (at, look, lens) in rigs.items():
        cam = su.camera(f"CAM_{name}", C["CAMERAS"], at, look, lens=lens)
        cam.data.dof.use_dof = name not in ("top", "four", "hall", "kitchen")
        cam.data.dof.aperture_fstop = 2.8
        cam.data.dof.focus_distance = (Vector(look) - Vector(at)).length
        cams[name] = cam
    cams["top"].rotation_mode = "XYZ"
    cams["top"].rotation_euler = (0, 0, 0)
    return cams, rigs


CUTS = [("5.1", 0.0, "stairs"), ("5.2", 0.0, "hall"), ("5.3", 0.0, "door_cu"), ("5.4", 0.0, "kitchen"),
        ("5.5", 0.0, "chest"), ("5.6", 0.0, "floor"), ("5.7", 0.0, "four"), ("5.8", 0.0, "nar_cu"),
        ("5.9", 0.0, "macro"), ("5.10", 0.0, "nar_hh"), ("5.11", 0.0, "orbit"), ("5.12", 0.0, "top"),
        ("5.13", 0.0, "officers"), ("5.14", 0.0, "eye_n"), ("5.15", 0.0, "ms15")]


def build(acts=True):
    """The whole scene: sets, cast, props, cameras, lights; then the acts (the animation of each part)."""
    import bpy
    from mathutils import Euler, Vector
    import humans
    import scene_utils as su
    import sets
    import cast3d
    if not ((ROOT / "voices" / "wav2arkit" / "config.json").exists() and (ROOT / ".venv").exists()):
        raise SystemExit("Wav2ARKit is not installed here: lips would fall back to loudness (see download_film_kit.sh)")
    tl = timeline()
    check_timeline(tl)
    start = {s["id"]: 1 + int(round(s["start"] * FPS)) for s in tl["shots"]}
    end = tl["frames"]

    def T(sid, sec=0.0):
        return start[sid] + int(round(sec * FPS))

    su.reset_scene()
    scene = bpy.context.scene
    su.configure_render(scene, width=1920, height=1080, fps=FPS, frame_end=end, samples=32)
    root = su.collection("V4_VISITORS")
    C = {n: su.collection(n, root) for n in ("SET", "CAST", "PROPS", "CAMERAS")}
    lights = {}
    room = sets.chamber(C["SET"], lights)
    entry = sets.entry(C["SET"], lights)
    sets.kitchen(C["SET"], lights)
    room["blanket"].hide_render = room["blanket"].hide_viewport = True          # the old man is under the floor
    _street_outside(bpy, su, sets, C["SET"], lights)
    world = bpy.data.worlds.new("WORLD_Night")
    scene.world = world
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.002, 0.0025, 0.004, 1)
    for light in lights.values():
        light.data.energy = 0

    # ---- the cast
    specs = {"Narrator": cast3d.NARRATOR, "Hale": cast3d.HALE, "Brandt": cast3d.BRANDT, "Mercer": cast3d.MERCER}
    layer = bpy.context.view_layer
    layer.active_layer_collection = layer.layer_collection.children["V4_VISITORS"].children["CAST"]
    rigs = {n: humans.build(s) for n, s in specs.items()}
    props = {}
    for n, rig in rigs.items():
        humans.relax_arms(rig)
        for pb in rig.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=1)
        if n != "Narrator":
            props[f"hat_{n}"] = top_hat(C["PROPS"], rig)
            props[f"badge_{n}"] = star_badge(C["PROPS"], rig)
    for s in tl["shots"]:
        for n, (x, y, h) in places(s["id"]).items():
            rig = rigs[n]
            rig.location, rig.rotation_euler = (x, y, 0), Euler((0, 0, math.radians(h)))
            rig.keyframe_insert("location", frame=T(s["id"]))
            rig.keyframe_insert("rotation_euler", frame=T(s["id"]))
    for rig in rigs.values():
        for fc in v3._fcurves(rig):
            if fc.data_path in ("location", "rotation_euler"):
                for k in fc.keyframe_points:
                    k.interpolation = "CONSTANT"          # cuts: each shot's blocking holds until an act moves it

    # ---- props: his candle, their lanterns, four chairs on and round the planks, Mercer's cup
    props["candle"] = sets.lib.candle(C["PROPS"], C["PROPS"], (38.75, -1.6, 1.0), prefix="V4_Candle")
    for n in ("Hale", "Brandt", "Mercer"):
        body, shutter, beam, glow = sets.dark_lantern(C["PROPS"], f"V4_Lantern_{n}")
        shutter.rotation_euler.z = math.radians(-100)                            # bull's-eye open
        glow.data.energy, beam.data.energy = 6, 40
        props[f"lantern_{n}"] = body
    for n, xy in SEATS.items():
        h = heading_to(xy, SEAT_FOCUS[n])
        props[f"chair_{n}"] = sets.ph("dining_chair_02", C["PROPS"], f"V4_Chair_{n}", (*xy, 0), rotation=h - 180)
    props["cup"] = sets.lib.mug(C["PROPS"], (0.15, -1.0, 0.48), prefix="V4_Cup")
    for i, (n, at) in enumerate((("Hale", (0.95, -0.85, 0)), ("Brandt", (0.45, 1.2, 0)), ("Mercer", (-0.55, -1.45, 0)))):
        lantern = props[f"lantern_{n}"]
        lantern.location = at
        lantern.rotation_euler.z = math.radians(heading_to(at[:2], (-0.1, -0.1)))
        lantern.keyframe_insert("location", frame=T("5.5"))
        lantern.keyframe_insert("rotation_euler", frame=T("5.5"))

    # ---- lights, keyed per shot
    for s in tl["shots"]:
        for name, light in lights.items():
            light.data.energy = LIGHT_KEYS.get(s["id"], {}).get(name, 0)
            light.data.keyframe_insert("energy", frame=T(s["id"]))
        for n in ("Hale", "Brandt", "Mercer"):
            glow = bpy.data.objects[f"LIGHT_V4_Lantern_{n}_Glow"]
            glow.data.energy = LANTERN_GLOW.get(s["id"], 6)
            glow.data.keyframe_insert("energy", frame=T(s["id"]))

    # ---- cameras and cuts
    cams, cam_rigs = _cameras(T, su, C, Vector)
    ctx = dict(bpy=bpy, humans=humans, su=su, sets=sets, cast3d=cast3d, tl=tl, T=T, start=start, end=end,
               rigs=rigs, props=props, cams=cams, cam_rigs=cam_rigs, lights=lights, room=room, entry=entry, C=C,
               marks={}, held=[])
    if acts:
        for act in ACTS:
            act(ctx)
    for sid, sec, cam in CUTS + ctx.get("extra_cuts", []):
        marker = scene.timeline_markers.new(f"SHOT_{sid}_{cam}_{sec:.1f}", frame=T(sid, sec))
        marker.camera = cams[cam]
    scene.camera = cams["stairs"]
    scene["v4_held"] = json.dumps(ctx["held"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "timeline.json").write_text(json.dumps(dict(tl, marks={k: (v - 1) / FPS for k, v in ctx["marks"].items()}),
                                                  indent=1))
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    su.save_blend(BLEND, compress=True)
    print(f"V4 built: {len(tl['shots'])} shots, {end} frames ({tl['seconds']:.1f} s) -> {BLEND.name}")


def _street_outside(bpy, su, sets, coll, lights):
    """What the open street door shows (5.2, 5.3): the brick sidewalk, a stone curb, wet cobbles, an 1840s gas
    lamp, and the red-brick row houses across the street with white marble steps, one window lit; low mist.
    Replaces the entry set's stub (a flat sky wall and a modern-looking lamp)."""
    x = sets.SET_X["entry"]
    for name in ("EN_Street", "EN_Street_Back"):
        bpy.data.objects.remove(bpy.data.objects[name])
    lamp = bpy.data.objects["EN_Street_Lamp"]
    for o in [lamp] + list(lamp.children_recursive):
        o.hide_render = o.hide_viewport = True
    cobble, pave, curb = sets.street_materials()
    su.box("V4_Sidewalk", coll, pave, (24, 3.0, 0.15), (x, -3.5, -0.075), bevel=0)
    su.box("V4_Curb", coll, curb, (24, 0.25, 0.2), (x, -5.1, -0.1), bevel=0.01)
    su.box("V4_Street", coll, cobble, (24, 8, 0.1), (x, -9.2, -0.2), bevel=0)
    su.box("V4_Sidewalk_Far", coll, pave, (24, 3.0, 0.15), (x, -14.5, -0.075), bevel=0)
    for i, dx in enumerate((-6, 0, 6)):
        sets.row_house(coll, f"V4_Opposite_{i}", x + dx, -16.0, -1, height=9.4 - (i % 2) * 0.5,
                       brick="MAT_Ex_Brick" if i % 2 else "MAT_Ex_Brick_B", lit={(1, -1.9)} if dx == 0 else ())
    sets.gas_lamp(coll, "V4_Gas_Lamp", (x + 1.7, -4.7, 0.0), lights, energy=0)
    sets.haze("V4_Street_Mist", coll, (x, -9.5, 1.2), (24, 14, 2.4), 0.03)


ACTS = []          # the animation, part by part (filled in below)


# ----------------------------------------------------------------------------------------------- checks
def check_standins():
    """The three stand-in officers and the narrator: heights, unique names, feet on the floor, hats over the
    hair (none of it poking through, the band close to the head), badges on the chest."""
    import bpy
    from mathutils import Vector
    import humans
    import cast3d
    import scene_utils as su
    su.reset_scene()
    bpy.context.scene.render.fps = 24
    coll = bpy.context.scene.collection
    want = {"Narrator": 1.76, "Hale": 1.72, "Brandt": 1.80, "Mercer": 1.78}
    specs = {"Narrator": cast3d.NARRATOR, "Hale": cast3d.HALE, "Brandt": cast3d.BRANDT, "Mercer": cast3d.MERCER}
    rigs = {n: humans.build(s, location=(1.2 * i, 0, 0)) for i, (n, s) in enumerate(specs.items())}
    names = [o.name for o in bpy.data.objects]
    assert len(names) == len(set(names)), "duplicate object names"
    bpy.context.view_layer.update()
    report = []
    for n, rig in rigs.items():
        parts = {o.name.split(".", 1)[1]: o for o in rig.children}
        top = max((rig.matrix_world @ v.co).z for v in parts["body"].data.vertices)
        sole = min((rig.matrix_world @ v.co).z for v in parts["shoes"].data.vertices)
        assert abs(top - want[n]) <= 0.01, f"{n}: height {top:.3f} m, want {want[n]}"
        assert abs(sole) <= 0.015, f"{n}: soles at {sole * 100:.1f} cm"
        report.append(f"{n} {top:.3f} m")
        if n == "Narrator":
            continue
        hat = top_hat(coll, rig)
        badge = star_badge(coll, rig)
        bpy.context.view_layer.update()
        inv = hat.matrix_world.inverted()
        rx, ry, band = hat["rx"], hat["ry"], hat["band"]
        for part in ("hair", "body"):              # nothing of the head pokes out through the crown
            for v in parts[part].data.vertices:
                p = inv @ (rig.matrix_world @ v.co)
                if p.z > 0.002:
                    assert (p.x / rx) ** 2 + (p.y / ry) ** 2 < 1.0, f"{n}: {part} pokes through the hat at {p}"
        ring = [inv @ (rig.matrix_world @ v.co) for v in parts["hair"].data.vertices]
        ring = [p for p in ring if abs(p.z) < 0.01]
        for d in (Vector((1, 0, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0)), Vector((0, -1, 0))):
            reach = max(p.dot(d) for p in ring)
            wall = abs(d.x) * rx + abs(d.y) * ry
            assert 0 <= wall - reach <= 0.02, f"{n}: hat band gap {wall - reach:.3f} m"
        origin = badge.matrix_world.translation
        normal = (badge.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
        deps = bpy.context.evaluated_depsgraph_get()
        shirt = parts["shirt"]
        local = shirt.matrix_world.inverted()
        hit, loc, _, _ = shirt.evaluated_get(deps).ray_cast(local @ (origin + normal * 0.05),
                                                           (local.to_3x3() @ -normal).normalized())
        assert hit, f"{n}: badge not over the shirt"
        gap = (shirt.matrix_world @ loc - origin).length
        assert gap <= 0.01, f"{n}: badge {gap * 100:.1f} cm off the chest"
    print("stand-ins OK: " + ", ".join(report))


CAST = ("Narrator", "Hale", "Brandt", "Mercer")
LIVING = ("LowerBack", "Spine", "Spine1", "Neck1", "Head") + tuple(
    f"{s}{b}" for s in ("Left", "Right") for b in ("Shoulder", "Arm", "ForeArm", "Hand"))


def _spans():
    tl = json.loads((OUT / "timeline.json").read_text())
    return {s["id"]: (1 + int(round(s["start"] * FPS)), int(round((s["start"] + s["seconds"]) * FPS)))
            for s in tl["shots"]}


def check(shots=None, step=4):
    """Measured checks on the built scene, printed with numbers; fails on any of:
    a hand more than 5 mm inside another person (body, shirt, trousers) or a chair (every `step` frames);
    a held prop drifting over 1 cm from its hand; planted feet sliding over 2 cm/s on average (not on the stair);
    an on-camera character moving less than 0.5 deg (summed over the spine, neck, head and arms) in any 1 s."""
    import bpy
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils.bvhtree import BVHTree
    scene = bpy.context.scene
    spans = _spans()
    rigs = {n: bpy.data.objects[n] for n in CAST}
    obstacles = {n: [bpy.data.objects[f"{n}.{p}"] for p in ("body", "shirt", "trousers")] for n in CAST}
    chairs = [o for o in bpy.data.objects if o.type == "MESH" and any(
        a.name.startswith("V4_Chair_") for a in [o] + list(_ancestors(o)))]
    hands = {}
    for n in CAST:
        body = obstacles[n][0]
        groups = {g.index for g in body.vertex_groups if g.name.startswith(("LeftHand", "RightHand"))}
        hands[n] = [v.index for v in body.data.vertices if any(g.group in groups and g.weight > 0.5 for g in v.groups)]
    held = json.loads(scene.get("v4_held", "[]"))
    animated = any(len(fc.keyframe_points) > 1 for r in rigs.values() for fc in v3._fcurves(r)
                   if fc.data_path.startswith("pose.bones"))
    deps = bpy.context.evaluated_depsgraph_get()
    fails, notes = [], []
    for sid in shots or list(spans):
        f0, f1 = spans[sid]
        worst = 0.0
        for f in range(f0, f1 + 1, step):                                   # 1. hands inside someone
            scene.frame_set(f)
            pts = {}
            for n in CAST:
                ev = obstacles[n][0].evaluated_get(deps)
                me = ev.to_mesh()
                pts[n] = [ev.matrix_world @ me.vertices[i].co for i in hands[n]]
                ev.to_mesh_clear()
            for n in CAST:
                others = [o for m in CAST if m != n and (rigs[m].matrix_world.translation -
                                                         rigs[n].matrix_world.translation).length < 2.0
                          for o in obstacles[m]] + chairs
                for o in others:
                    tree, inv = BVHTree.FromObject(o, deps), o.matrix_world.inverted()
                    for p in pts[n]:
                        loc, normal, _, dist = tree.find_nearest(inv @ p, 0.12)
                        if loc is not None:
                            depth = -((inv @ p) - loc).dot(normal)
                            if depth > 0.005:
                                worst = max(worst, depth)
                                fails.append(f"{sid} f{f}: {n}'s hand {depth * 100:.1f} cm inside {o.name}")
                                break
        notes.append(f"{sid}: hands inside others worst {worst * 100:.1f} cm")
        for h in held:                                                       # 2. held props stay in the hand
            a, b = max(h["f0"], f0), min(h["f1"], f1)
            if a > b:
                continue
            prop, rig = bpy.data.objects[h["prop"]], rigs[h["rig"]]
            drift, ref = 0.0, None
            for f in range(a, b + 1, 2):
                scene.frame_set(f)
                hand = rig.matrix_world @ rig.pose.bones[h["bone"]].matrix
                off = hand.inverted() @ (prop.matrix_world @ __import__("mathutils").Vector(h["point"]))
                ref = ref or off
                drift = max(drift, (off - ref).length)
            notes.append(f"{sid}: {h['prop']} in {h['rig']}'s hand, drift {drift * 100:.1f} cm")
            if drift > 0.01:
                fails.append(f"{sid}: {h['prop']} drifts {drift * 100:.1f} cm from {h['rig']}'s hand")
        if sid != "5.1":                                                     # 3. planted feet
            for n, rig in rigs.items():
                prev, slide, count = {}, 0.0, 0
                for f in range(f0, f1 + 1):
                    scene.frame_set(f)
                    for side in ("Left", "Right"):
                        p = rig.matrix_world @ rig.pose.bones[f"{side}ToeBase"].head
                        if side in prev and p.z < 0.05 and prev[side].z < 0.05:
                            slide += (p.xy - prev[side].xy).length * FPS
                            count += 1
                        prev[side] = p
                mean = slide / max(count, 1)
                if mean > 0.02:
                    fails.append(f"{sid}: {n}'s planted feet slide {mean * 100:.1f} cm/s")
        if animated:                                                         # 4. nobody frozen on camera
            for n, rig in rigs.items():
                for w0 in range(f0, f1 - FPS + 1, FPS // 2):
                    scene.frame_set(w0 + FPS // 2)
                    head = rig.matrix_world @ rig.pose.bones["Head"].head
                    v = world_to_camera_view(scene, scene.camera, head)
                    if not (0 < v.x < 1 and 0 < v.y < 1 and v.z > 0):
                        continue
                    base, most = None, 0.0
                    for f in range(w0, w0 + FPS, 2):
                        scene.frame_set(f)
                        q = [(rig.matrix_world @ rig.pose.bones[b].matrix).to_quaternion() for b in LIVING]
                        base = base or q
                        most = max(most, sum(math.degrees(a.rotation_difference(b).angle) for a, b in zip(base, q)))
                    if most < 0.5:
                        fails.append(f"{sid} f{w0}: {n} frozen on camera ({most:.2f} deg in 1 s)")
    for line in notes:
        print("V4 check:", line)
    if fails:
        print("V4 check FAILED:\n  " + "\n  ".join(fails[:40]) + (f"\n  ... {len(fails)} in all" if len(fails) > 40 else ""))
        raise SystemExit(1)
    print(f"V4 check OK ({'animated' if animated else 'no animation yet: stillness skipped'})")


def _ancestors(o):
    while o.parent:
        o = o.parent
        yield o


def stills(shots=None):
    """One 480p frame from the middle of each shot -> OUT/stills/<shot>.png (for looking at the framing)."""
    import bpy
    scene = bpy.context.scene
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = 854, 480, 100
    scene.eevee.taa_render_samples = 16
    (OUT / "stills").mkdir(parents=True, exist_ok=True)
    for sid, (f0, f1) in _spans().items():
        if shots and sid not in shots:
            continue
        scene.frame_set((f0 + f1) // 2)
        r.filepath = str(OUT / "stills" / f"{sid}.png")
        bpy.ops.render.render(write_still=True)
    print("V4 stills ->", OUT / "stills")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    shots = args[1].split(",") if len(args) > 1 and args[1] else None
    {"standins": check_standins, "build": build, "build_static": lambda: build(acts=False),
     "check": lambda: check(shots), "stills": lambda: stills(shots),
     "timeline": lambda: (OUT.mkdir(parents=True, exist_ok=True),
                          (OUT / "timeline.json").write_text(json.dumps(check_timeline(), indent=1)))}[args[0]]()
