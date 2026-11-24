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
SEATS = {"Narrator": (-0.6, 0.0), "Hale": (0.65, -0.3), "Brandt": (-0.05, 0.95), "Mercer": (-0.05, -1.15)}
SEAT_FOCUS = {"Narrator": (0.25, -0.2), "Hale": (-0.3, -0.1), "Brandt": (-0.1, -0.3), "Mercer": (-0.2, 0.0)}
OUTSIDE = {"Hale": (40.0, -2.8, 180), "Brandt": (39.35, -3.15, 180), "Mercer": (40.8, -3.25, 180)}
PLACES = {
    "5.1": dict(Narrator=(38.55, -1.75, 0), **OUTSIDE),
    "5.2": dict(Narrator=(40.25, -1.45, 0), **OUTSIDE),
    "5.3": dict(Narrator=(40.25, -1.45, 0), **OUTSIDE),
    "5.4": dict(Narrator=(61.0, 0.2, 330), Hale=(60.1, 1.5, 10), Brandt=(59.5, 1.9, 350), Mercer=(60.5, 2.1, 0)),
    "5.5": dict(Narrator=(1.30, -1.3, 90), Hale=(0.85, -0.95, 73), Brandt=(1.75, -0.55, 18), Mercer=(1.05, -1.95, 124)),
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
    "5.1": dict(en_fill=4), "5.2": dict(V4_Gas_Lamp_light=900, en_fill=25), "5.3": dict(V4_Gas_Lamp_light=900, en_fill=25),
    "5.4": dict(ki_fill=70), "5.5": dict(warm=70, fill=8, moon=60), "5.6": dict(warm=100, fill=8, moon=60),
    "5.7": dict(warm=130, fill=8, moon=60), "5.8": dict(warm=95, fill=14, moon=70),
    "5.9": dict(warm=85, fill=14, moon=70), "5.10": dict(warm=60, fill=20, moon=80),
    "5.11": dict(warm=25, fill=40, moon=110), "5.12": dict(warm=12, fill=50, moon=130),
    "5.13": dict(warm=10, fill=55, moon=130), "5.14": dict(warm=8, fill=55, moon=140),
    "5.15": dict(warm=8, fill=55, moon=140)}         # cold, but readable at 480p
LANTERN_GLOW = {"5.2": 10, "5.3": 10, "5.4": 16, "5.5": 14, "5.6": 14, "5.7": 16, "5.8": 12, "5.9": 12, "5.10": 10, "5.11": 8, "5.12": 5, "5.13": 5,
                "5.14": 5, "5.15": 5}


def _cameras(T, su, C, Vector):
    """Every shot's camera: name -> (at, look, lens); moves are keyed by the acts (later) or here."""
    c4 = Vector((-0.05, -0.15, 0.95))
    rigs = {
        "stairs": ((38.95, -0.3, 2.0), (38.55, 0.9, 1.95), 35),
        "hall": ((39.25, 0.9, 1.62), (40.05, -2.9, 1.5), 30),
        "door_cu": ((40.4, -3.15, 1.75), (39.47, -1.3, 1.6), 45),
        "kitchen": ((61.75, 1.55, 1.85), (60.0, -0.8, 1.1), 26),
        "chest": ((2.35, -2.15, 1.65), (1.25, -0.95, 1.2), 24),
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
    stand = {pb.name: pb.rotation_quaternion.copy() for pb in rigs["Narrator"].pose.bones}   # standing, arms down
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
        props[f"chair_{n}"] = sets.ph("dining_chair_02", C["PROPS"], f"V4_Chair_{n}", (*xy, 0), rotation=h)
    props["cup"] = sets.lib.mug(C["PROPS"], (0.15, -1.0, 0.48), prefix="V4_Cup")
    for i, (n, at) in enumerate((("Hale", (0.95, -0.85, 0)), ("Brandt", (0.45, 1.2, 0)), ("Mercer", (-0.55, -1.45, 0)))):
        lantern = props[f"lantern_{n}"]
        lantern.location = at
        lantern.rotation_euler.z = math.radians(heading_to(at[:2], (-0.1, -0.1)))
        lantern.keyframe_insert("location", frame=T("5.5"))
        lantern.keyframe_insert("rotation_euler", frame=T("5.5"))

    # ---- lights, keyed per shot
    ids = [s["id"] for s in tl["shots"]]
    for i, s in enumerate(tl["shots"]):
        last = T(ids[i + 1]) - 1 if i + 1 < len(ids) else end
        drain = i >= ids.index("5.7")                 # the chamber's light drains away across 5.7-5.15; elsewhere
        for name, light in lights.items():            # each shot's light holds and changes at the cut
            light.data.energy = LIGHT_KEYS.get(s["id"], {}).get(name, 0)
            light.data.keyframe_insert("energy", frame=T(s["id"]))
            if not (drain and name in ("warm", "fill", "moon")):
                light.data.keyframe_insert("energy", frame=last)
        for n in ("Hale", "Brandt", "Mercer"):
            glow = bpy.data.objects[f"LIGHT_V4_Lantern_{n}_Glow"]
            glow.data.energy = LANTERN_GLOW.get(s["id"], 6)
            glow.data.keyframe_insert("energy", frame=T(s["id"]))
            if not drain:
                glow.data.keyframe_insert("energy", frame=last)

    # ---- cameras and cuts
    cams, cam_rigs = _cameras(T, su, C, Vector)
    ctx = dict(bpy=bpy, humans=humans, su=su, sets=sets, cast3d=cast3d, tl=tl, T=T, start=start, end=end,
               rigs=rigs, props=props, cams=cams, cam_rigs=cam_rigs, lights=lights, room=room, entry=entry, C=C, stand=stand,
               marks={}, held=[], cache={})
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


# ----------------------------------------------------------------------------------------------- acting
WHO = {"NS": "Narrator", "O1": "Hale", "O2": "Brandt", "O3": "Mercer"}
OFFICERS = ("Hale", "Brandt", "Mercer")
import film  # noqa: E402  (the shot list; its HEARTBEATS drive the sound and these pictures alike)
HEARTBEATS = [h for h in film.HEARTBEATS if h[0].startswith("5.")]   # the heart under the floor, to the confession
WORRY = {"browInnerUp": 0.35, "mouthPressLeft": 0.25, "mouthPressRight": 0.25, "mouthSmileLeft": 0.1,
         "mouthSmileRight": 0.1}
WINCE = {"browDownLeft": 0.45, "browDownRight": 0.45, "browInnerUp": 0.3, "eyeSquintLeft": 0.5, "eyeSquintRight": 0.5,
         "mouthPressLeft": 0.3, "mouthPressRight": 0.3}
RAIL = (0.0, 0.30, 0.95)        # the chair's top rail, chair-local (its back is on +y; a sitter faces -y; the
                                # backrest leans back: its top, 0.974 high, runs from y 0.164 to 0.33)


def _frame(t):
    return 1 + int(round(t * FPS))


def _dir(h):
    """The (x, y) direction a heading faces (0 faces -y, 90 faces +x)."""
    return math.sin(math.radians(h)), -math.cos(math.radians(h))


def beat_times(tl):
    """Seconds of every heartbeat he hears (HEARTBEATS: from a shot + offset, bpm rising, to a shot + offset)."""
    start = {s["id"]: s["start"] for s in tl["shots"]}
    out = []
    for sid, off, b0, b1, eid, eoff, *_ in HEARTBEATS:
        t0, t1 = start[sid] + off, start[eid] + eoff
        t = t0
        while t < t1:
            out.append(t)
            t += 60.0 / (b0 + (b1 - b0) * (t - t0) / max(t1 - t0, 1e-6))
    return out


def _constant(obj, paths=("location", "rotation_euler", "hide_render", "hide_viewport")):
    for fc in v3._fcurves(obj):
        if fc.data_path in paths:
            for k in fc.keyframe_points:
                k.interpolation = "CONSTANT"


def _hold(bpy, rig, frame):
    """Key every bone as it is at `frame`, so the next pose keyed doesn't blend back over earlier shots."""
    bpy.context.scene.frame_set(frame)
    for pb in rig.pose.bones:
        pb.keyframe_insert("rotation_quaternion", frame=frame)
    rig.pose.bones["Hips"].keyframe_insert("location", frame=frame)


def _sit_pose(ctx):
    """The seated pose: CMU 113_15 (a man sitting down on a chair; at 3.0 s he is down, trunk 5 degrees back - by
    3.5 s he has slumped to 14, which read as drunk or asleep) on a scratch copy
    of the narrator's skeleton: (bone -> local rotation, hips location). Cached in ctx."""
    if "sit" in ctx:
        return ctx["sit"]
    bpy, humans = ctx["bpy"], ctx["humans"]
    scene = bpy.context.scene
    rig = ctx["rigs"]["Narrator"]
    tmp = rig.copy()
    tmp.data = rig.data.copy()
    tmp.animation_data_clear()
    tmp.location, tmp.rotation_euler, tmp.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
    scene.collection.objects.link(tmp)
    humans.retarget(tmp, humans.CMU_LIBRARY / "113_15.bvh", start_frame=1)
    scene.frame_set(_frame(3.0))
    pose = ({pb.name: pb.rotation_quaternion.copy() for pb in tmp.pose.bones}, tmp.pose.bones["Hips"].location.copy())
    # face the body along the skeleton's own forward (-Y): every layer (gaze, nods, breathing) works in that frame,
    # so a body turned on its skeleton would nod sideways and look past the person it should look at
    from mathutils import Matrix, Vector
    pb = tmp.pose.bones
    lat = pb["LeftUpLeg"].head - pb["RightUpLeg"].head
    fwd = lat.cross(Vector((0, 0, 1)))
    turn = Matrix.Rotation(-math.atan2(fwd.x, -fwd.y), 3, "Z")
    rest = tmp.data.bones["Hips"].matrix_local.to_3x3().normalized()
    rots, hips = pose
    rots["Hips"] = (rest.inverted() @ turn @ rest).to_quaternion() @ rots["Hips"]
    for name in ("Neck1", "Head"):                 # the actor's head was cocked 24 degrees as he sat: the gaze
        rots[name] = rots[name].copy()             # layers turn the head from here, so start it straight
        rots[name].identity()
    pose = (rots, rest.inverted() @ (turn @ (rest @ hips)))
    action, data = tmp.animation_data.action, tmp.data
    bpy.data.objects.remove(tmp)
    bpy.data.armatures.remove(data)
    bpy.data.actions.remove(action)
    ctx["sit"] = pose
    return pose


def _key_pose(rig, frame, pose):
    rots, hips = pose
    for name, q in rots.items():
        pb = rig.pose.bones[name]
        pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=frame)
    rig.pose.bones["Hips"].location = hips
    rig.pose.bones["Hips"].keyframe_insert("location", frame=frame)


def _seat_top(chair):
    """Height of the chair's seat: the highest point over the middle of the seat (chair-local)."""
    inv = chair.matrix_world.inverted()
    top = 0.0
    for o in [chair] + list(chair.children_recursive):
        if o.type != "MESH":
            continue
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            p = inv @ w
            if abs(p.x) < 0.15 and -0.2 < p.y < 0.08 and p.z < 0.6:
                top = max(top, w.z)
    return top


def _seat_on(ctx, rig, chair, frame):
    """Where the rig goes so that, in the pose keyed at `frame`, it sits on `chair`: facing the way the chair
    faces, the hips over the back half of the seat, the underside of the thighs on the seat. -> (location, rot z)."""
    bpy = ctx["bpy"]
    from mathutils import Matrix, Vector
    scene = bpy.context.scene
    scene.frame_set(frame)
    pb = rig.pose.bones
    lat = pb["LeftUpLeg"].head - pb["RightUpLeg"].head
    fwd = lat.cross(Vector((0, 0, 1)))
    facing = math.degrees(math.atan2(fwd.x, -fwd.y))
    rot = chair.matrix_world.to_euler().z - math.radians(facing)
    k = rig.scale.x
    hips = pb["Hips"].head
    deps = bpy.context.evaluated_depsgraph_get()
    low = 9.0
    for part in ("body", "trousers"):                  # the underside within 25 cm of the hips (armature space)
        o = bpy.data.objects[f"{rig.name}.{part}"]
        ev = o.evaluated_get(deps)
        me = ev.to_mesh()
        to_arm = rig.matrix_world.inverted() @ ev.matrix_world
        for v in me.vertices:
            p = to_arm @ v.co
            if (p.xy - hips.xy).length < 0.25 and p.z < hips.z:
                low = min(low, p.z)
        ev.to_mesh_clear()
    target = chair.matrix_world @ Vector((0, -0.03, 0))
    R = Matrix.Rotation(rot, 3, "Z")
    loc = Vector((target.x, target.y, _seat_top(chair))) - R @ Vector((hips.x * k, hips.y * k, low * k))
    toes = min((pb[f"{s}ToeBase"].head * k).z for s in ("Left", "Right")) + loc.z
    return loc, rot, toes


def _feet_down(ctx, rig, frame, drop):
    """Seated, the mocap's feet hang `drop` m above the floor: bring each ankle straight down with two-bone leg
    IK (knees bend a little more; the feet keep their angle), keyed at `frame`."""
    bpy, humans = ctx["bpy"], ctx["humans"]
    from mathutils import Vector
    bpy.context.scene.frame_set(frame)
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    for side in ("Left", "Right"):
        chain = (f"{side}UpLeg", f"{side}Leg", f"{side}Foot")
        pose = {n: rig.pose.bones[n].matrix.copy() for n in chain + ("Hips",)}
        target = pose[chain[2]].translation - Vector((0, 0, drop / rig.scale.x))
        humans._two_bone(rig, rest, pose, frame, *chain, target, pole=(0, -1, 0.3))
        bpy.context.view_layer.update()


# Seated hands at rest: (how far along the thigh from hip to knee, how far in from its middle in m) - a little
# different for each man. Wrists out near the knees locked every arm straight: shop-window dummies.
HAND_REST = {"Hale": (0.38, 0.03), "Brandt": (0.48, 0.0), "Mercer": (0.45, 0.01), "Narrator": (0.42, 0.015)}
# How far each leans in, degrees (engaged listeners lean toward the speaker: Mehrabian's immediacy cues).
LEAN = {"Hale": 8.0, "Brandt": 12.0, "Mercer": 10.0, "Narrator": 12.0}


def _sit_up(ctx, rig, frame):
    """Shoulders down and a slight lean in, keyed at `frame`. The mocap sitter's shoulders were shrugged (the
    collarbones 25-28 deg up, the shoulder joints 3 cm high): with the trunk upright that put the shoulders 52 cm
    above the lap - the arm's whole length - so every resting hand locked its arm straight. The collarbones go to
    rest; the trunk leans LEAN degrees forward from the lower back and spine, the neck taking most of it back so
    the face stays level (people keep their eyes level when they lean)."""
    from mathutils import Quaternion, Vector
    bpy = ctx["bpy"]
    bpy.context.scene.frame_set(frame)
    pb = rig.pose.bones
    lean = LEAN.get(rig.name, 10.0)
    for side in ("Left", "Right"):
        pb[f"{side}Shoulder"].rotation_quaternion = Quaternion()
        pb[f"{side}Shoulder"].keyframe_insert("rotation_quaternion", frame=frame)
    for name, deg in (("LowerBack", 0.6 * lean), ("Spine", 0.4 * lean), ("Neck1", -0.8 * lean)):
        bpy.context.view_layer.update()
        b = pb[name]
        axis = (b.matrix.to_3x3().normalized().inverted() @ Vector((1, 0, 0))).normalized()   # forward about the body's X
        b.rotation_quaternion = b.rotation_quaternion @ Quaternion(axis, math.radians(deg))
        b.keyframe_insert("rotation_quaternion", frame=frame)
    bpy.context.view_layer.update()


def _hands_on_thighs(ctx, rig, frame, skip=()):
    """Seated hands at rest: each wrist on the thigh about halfway to the knee (HAND_REST), the elbow bent and
    pointing back and a little out, the hand turned in, palm down, the fingers draped over the thigh in the resting
    cascade (arm IK, keyed at `frame`). The mocap's own seated arms were mid-gesture."""
    bpy, humans = ctx["bpy"], ctx["humans"]
    from mathutils import Vector
    bpy.context.scene.frame_set(frame)
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    pb = rig.pose.bones
    for side, out in (("Left", 1), ("Right", -1)):
        if side in skip:
            continue
        hip, knee = pb[f"{side}UpLeg"].head, pb[f"{side}Leg"].head
        along = (knee - hip).normalized()
        k, inward = HAND_REST.get(rig.name, (0.5, 0.01))
        target = hip.lerp(knee, k) + Vector((-inward * out, 0, 0.10))
        chain = (f"{side}Arm", f"{side}ForeArm", f"{side}Hand")
        pose = {n: pb[n].matrix.copy() for n in chain + (pb[chain[0]].parent.name,)}
        hand = humans.hand_frame(along + Vector((-0.45 * out, 0, -0.3)), Vector((0, 0, -1)))   # turned in ~25 deg
        humans._two_bone(rig, rest, pose, frame, *chain, target, pole=(0.35 * out, 0.7, -0.6), end_rot=hand,
                         force_pole=True)
        humans._finger_shape(rig, side, frame, "relaxed")          # draped in the resting cascade, not flat
        bpy.context.view_layer.update()


def _sit(ctx, rig, chair, frame, shots, skip_hands=()):
    """Seat `rig` on `chair` from `frame` (the pose keyed there), feet on the floor; key its place at each shot."""
    from mathutils import Euler
    T = ctx["T"]
    _key_pose(rig, frame, _sit_pose(ctx))
    _sit_up(ctx, rig, frame)
    loc, rz, toes = _seat_on(ctx, rig, chair, frame)
    for sid in shots:
        rig.location, rig.rotation_euler = loc, Euler((0, 0, rz))
        rig.keyframe_insert("location", frame=T(sid))
        rig.keyframe_insert("rotation_euler", frame=T(sid))
    _constant(rig)
    _feet_down(ctx, rig, frame, toes - 0.025)
    _hands_on_thighs(ctx, rig, frame, skip_hands)
    ctx["bpy"].context.scene.frame_set(frame)
    k = rig.scale.x
    now = min((rig.matrix_world @ rig.pose.bones[f"{s}ToeBase"].head).z for s in ("Left", "Right"))
    print(f"V4 seat: {rig.name} on {chair.name}: toes {toes * 100:+.1f} cm off the floor -> {now * 100:+.1f} cm; "
          f"body turned {math.degrees(rz) - math.degrees(chair.matrix_world.to_euler().z):+.1f} deg on its skeleton")


def _seed(name, k):
    """A seed from a name, the same on every run (a string's built-in hash changes from run to run)."""
    return sum(map(ord, name)) % k + 1


def _phrases(humans, wav, f0):
    """Voiced phrases of a line (gaps under 0.25 s merged), in scene frames from f0."""
    times, _, _, voiced = humans._voicing(wav)
    spans, on = [], None
    for t, v in zip(times, voiced):
        if v and on is None:
            on = t
        if not v and on is not None:
            if spans and on - spans[-1][1] < 0.25:
                spans[-1][1] = t
            else:
                spans.append([on, t])
            on = None
    if on is not None:
        spans.append([on, times[-1]])
    return [(f0 + a * FPS, f0 + b * FPS) for a, b in spans]


def _look_fn(ctx, n, frame_ref):
    """(yaw, pitch) from character n's head to another character's head (a name) or to a world point (x, y, z),
    in n's own frame. Someone walking (ctx["tracks"][name]: {frame: ((x, y), heading)}) is followed frame by
    frame; otherwise the frame_ref pose is used (seated: fixed). A (yaw, pitch) pair passes through."""
    bpy = ctx["bpy"]
    from mathutils import Matrix, Vector
    rigs = ctx.get("all_rigs", ctx["rigs"])
    bpy.context.scene.frame_set(frame_ref)
    heads = {m: r.matrix_world @ r.pose.bones["Head"].head for m, r in rigs.items()}
    inv = rigs[n].matrix_world.inverted().to_3x3()
    moving, tracks = ctx.get("moving_heads", {}), ctx.get("tracks", {})

    def head(m, f):
        if f is not None and m in tracks and f in tracks[m]:
            (x, y), _ = tracks[m][f]
            return Vector((x, y, heads[m].z))
        return moving[m].get(f, heads[m]) if m in moving and f is not None else heads[m]

    def toward(m, f=None):
        if not isinstance(m, str) and len(m) == 2:
            return m
        there = head(m, f) if isinstance(m, str) else Vector(m)
        turn = inv
        if f is not None and n in tracks and f in tracks[n]:
            turn = Matrix.Rotation(-math.radians(tracks[n][f][1]), 3, "Z")
        d = turn @ (there - head(n, f))
        return math.degrees(math.atan2(d.x, -d.y)), math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
    return toward


def _converse(ctx, lines, a, b, energy, idle, seated=True, no_fidget=(), who=None):
    """Everyone in a scene, frames a..b: speakers' lips (Wav2ARKit) and gestures; everyone's gaze (one eyes()
    call each: the speaker looks at whom he answers, listeners at the speaker, idle eyes per `idle`); listeners
    nod at phrase ends; breathing and sway. lines: timeline entries; energy: {name: 0..1}; idle(n, f) -> (target,
    mode), target a name or (yaw, pitch). Expressions must be keyed before (lips add on top of them)."""
    humans, rigs = ctx["humans"], ctx["rigs"]
    who = who or WHO
    events = sorted((_frame(l["start"]), _frame(l["start"] + l["seconds"]), who[l["who"]], ROOT / l["file"])
                    for l in lines)
    phrases = {e: _phrases(humans, e[3], e[0]) for e in events}
    spans = {n: [] for n in rigs}
    prev, addressee = None, {}
    present = list(ctx.get("all_rigs", rigs))
    for e in events:
        f0, f1, spk, _ = e
        others = [m for m in present if m != spk]                   # alone (the void): he speaks to us
        to = prev if prev and prev != spk else ("Narrator" if spk != "Narrator" and "Narrator" in present
                                                else (others[0] if others else None))
        addressee[e] = to
        for n in rigs:
            spans[n].append((f0, f1 + 12, to if n == spk else spk, "talking" if n == spk else "listening"))
        prev = spk
    for n, rig in rigs.items():
        toward = _look_fn(ctx, n, a + 2)

        def current(f, n=n):
            hit = [s for s in spans[n] if s[0] <= f <= s[1] and s[2] is not None]
            return (hit[-1][2], hit[-1][3]) if hit else idle(n, f)
        humans.eyes(rig, a, b, mode=lambda f: current(f)[1], look=lambda f, t=toward: t(current(f)[0], f),
                    pauses=[p[1] for e in events if e[2] == n for p in phrases[e][:-1]], seed=_seed(n, 97))
        others = [p[1] for e in events if e[2] != n for p in phrases[e]]
        humans.listen(rig, a, b, rig, phrase_ends=others, seed=_seed(n, 89), gaze=False,
                      shift="LowerBack" if seated else "Hips")
        humans.sway(rig, a, b, amount=0.7 if seated else 0.8, seed=_seed(n, 83))
    everyone = ctx.get("all_rigs", rigs)
    for e in events:                     # the speaker's hands, toward whom he speaks to; his lips, from his voice
        f0, f1, spk, wav = e
        busy = ctx.get("busy_hands", {}).get(spk, ())
        ctx["bpy"].context.scene.frame_set(f0)
        listener = everyone.get(addressee[e]) if addressee[e] else None
        humans.gestures(rigs[spk], wav, f0, energy=energy.get(spk, 0.4),
                        hands=tuple(s for s in ("Left", "Right") if s not in busy),
                        toward=listener.matrix_world @ listener.pose.bones["Head"].head if listener else None, seed=f0,
                        force=ctx.get("force_gestures", {}).get(Path(wav).stem, ()))
        humans.lip_sync(rigs[spk], wav, f0)
    for n, rig in rigs.items():          # and nobody's hands freeze between lines (a hand holding something excepted)
        if n in no_fidget:
            continue
        busy = ctx.get("busy_hands", {}).get(n, ())
        humans.fidget(rig, a, b, seed=_seed(n, 79), sides=tuple(s for s in ("Left", "Right") if s not in busy))
    return events, phrases


# ----------------------------------------------------------------------------------------------- the arrival
# The entry stair (sets.entry): 14 treads along the west wall rising toward +y; tread j (0 = the bottom) is
# centred at y -1.4 + 0.22 j, its top 0.214 (j + 1) high; the banister's rail runs 0.9 m above the nosings, from
# (39.03, -1.5, 1.133) up to (39.03, 1.6, 4.149), on his left as he comes down.
STAIR_X, RAIL_X = 38.75, 39.03
STEP_FRAMES = 10                 # 0.42 s a step: "almost lightly" (a brisk descent is about half a second a step)
POLITE = {"browInnerUp": 0.15, "mouthSmileLeft": 0.08, "mouthSmileRight": 0.08}   # officers at a door at 4 a.m.


def _tread(j):
    """(y of the middle of tread j, the height of its top); below the stair (j < 0) the hall floor at its foot (the
    street door's wall is only 60 cm beyond the bottom tread: the last step closes beside the other foot)."""
    if j < 0:
        return -1.62, 0.0
    return -1.4 + 0.22 * j, 0.214 * (j + 1)


def _rail_z(y):
    return 1.133 + (y + 1.5) * 3.016 / 3.1


def _at(obj, f):
    """obj's world matrix at frame f from its own location / rotation keys (no scene update; no parent)."""
    from mathutils import Euler, Matrix, Vector
    loc, rot = list(obj.location), list(obj.rotation_euler)
    for fc in v3._fcurves(obj):
        if fc.data_path == "location":
            loc[fc.array_index] = fc.evaluate(f)
        elif fc.data_path == "rotation_euler":
            rot[fc.array_index] = fc.evaluate(f)
    return Matrix.LocRotScale(Vector(loc), Euler(rot), obj.scale)


def _walk(ctx, rig, path, a, b, busy=None, z=None, clips=None):
    """Key rig's place every frame from a to b along path [(frame, (x, y), heading)] (z: frame -> height), and
    remember it in ctx["tracks"] (the gaze follows it); then mocap steps along it. busy: frames both hands are
    busy (no arm swing); None: all."""
    from mathutils import Euler
    track = v3._sample_path(path, a, b)
    for f in range(a, b + 1):
        (x, y), h = track[f]
        rig.location, rig.rotation_euler = (x, y, z(f) if z else 0.0), Euler((0, 0, math.radians(h)))
        rig.keyframe_insert("location", frame=f)
        rig.keyframe_insert("rotation_euler", frame=f)
    ctx.setdefault("tracks", {}).setdefault(rig.name, {}).update(track)
    if len({p for _, p, _ in path}) > 1 or len({h for _, _, h in path}) > 1:
        v3._mocap_gait(ctx["humans"], rig, track, a, b, set(range(a, b + 1)) if busy is None else busy,
                       **({"clips": clips} if clips else {}))
    return track


def _contact(ctx, rig, side, a, b, target, hand, blend=8, tol=0.02):
    """humans.reach, then measured: where target(f) is not None the wrist must be within tol of it (a hand on a
    door handle, a rail, a lid, a hat brim that misses reads as a ghost pushing things)."""
    humans, scene = ctx["humans"], ctx["bpy"].context.scene
    humans.reach(rig, side, a, b, target=target, hand=hand, blend=blend)
    worst, at = 0.0, None
    for f in range(a, b + 1, 2):
        t = target(f)
        if t is None:
            continue
        scene.frame_set(f)
        miss = ((rig.matrix_world @ rig.pose.bones[f"{side}Hand"].head) - t).length
        if miss > worst:
            worst, at = miss, f
    print(f"V4 contact: {rig.name}'s {side.lower()} hand misses its target by up to {worst * 100:.1f} cm (f{at})")
    if worst >= tol:                                  # all of them are reported, then the build stops
        ctx.setdefault("contact_misses", []).append(f"{rig.name}'s {side.lower()} hand {worst * 100:.1f} cm off at f{at}")
        scene.frame_set(at)
        pb, m = rig.pose.bones, rig.matrix_world
        sh, t = m @ pb[f"{side}Arm"].head, target(at)
        arm = (pb[f"{side}Arm"].length + pb[f"{side}ForeArm"].length) * m.to_scale().x
        d = m.inverted().to_3x3().normalized() @ (t - sh)
        print(f"V4 contact miss: shoulder {tuple(round(c, 3) for c in sh)} -> target {tuple(round(c, 3) for c in t)}: "
              f"{(t - sh).length:.3f} m for an arm of {arm:.3f} m (body frame: left {d.x:+.2f}, ahead {-d.y:+.2f}, up {d.z:+.2f})")


def _stairwell(ctx):
    """What the entry set lacks overhead (it ends at 3.5 m, the stair at 3 m): a ceiling over the hall with the
    stairwell left open, the stairwell's walls up to an upper ceiling, and the landing at the top of the stair."""
    su = ctx["su"]
    from material_library import material as M
    coll, plaster = ctx["C"]["SET"], M("MAT_Plaster_Old")
    su.box("V4_Hall_Ceiling", coll, plaster, (2.9, 4.1, 0.1), (40.55, 0.0, 3.55), bevel=0)
    su.box("V4_Hall_Ceiling_S", coll, plaster, (1.2, 1.75, 0.1), (38.5, -1.175, 3.55), bevel=0)
    for name, size, at in (("W", (0.15, 2.5, 2.8), (37.93, 0.85, 4.9)), ("E", (0.1, 2.5, 2.8), (39.15, 0.85, 4.9)),
                           ("S", (1.4, 0.1, 2.8), (38.5, -0.35, 4.9)), ("N", (1.4, 0.15, 2.8), (38.5, 2.07, 4.9))):
        su.box(f"V4_Stairwell_{name}", coll, plaster, size, at, bevel=0)
    su.box("V4_Stairwell_Ceiling", coll, plaster, (1.4, 2.6, 0.1), (38.5, 0.85, 6.35), bevel=0)
    su.box("V4_Landing", coll, M("MAT_Floor_Old"), (1.1, 0.42, 0.05), (38.55, 1.79, 2.975), bevel=0)


def _act_arrival(ctx):
    """5.1-5.5: the knock; down the stair with the candle; the street door; the officers on the step (Hale lifts
    his hat and speaks; the narrator charms them in); the kitchen searched by lantern; the strongbox opened."""
    _stairwell(ctx)
    _arrive_stairs(ctx)
    _arrive_door(ctx)
    _arrive_kitchen(ctx)
    _arrive_chest(ctx)
    _arrive_props(ctx)
    ctx["busy_hands"], ctx["force_gestures"] = {}, {}     # the chamber sets its own
    assert not ctx.get("contact_misses"), "hands that can't reach: " + "; ".join(ctx["contact_misses"])


def _arrive_stairs(ctx):
    """5.1: on the landing with his candle; the knock; a smile; down 'with a light heart', step over step (leg IK
    onto each tread), his left hand running down the banister; the camera backs down ahead of him."""
    bpy, humans, cast3d = ctx["bpy"], ctx["humans"], ctx["cast3d"]
    from mathutils import Euler, Vector
    T, nar, scene = ctx["T"], ctx["rigs"]["Narrator"], bpy.context.scene
    a, b = T("5.1"), T("5.2") - 1
    knock, go = T("5.1", 2.6), T("5.1", 3.2)
    ctx["marks"]["5.1/knock3"] = knock
    ctx["marks"]["5.1/steps_wood"] = go
    steps = 15                                    # tread 13 down to the hall floor, and a last step off the stair
    done = go + steps * STEP_FRAMES

    def phase(f):
        p = min(max(0.0, (f - go) / STEP_FRAMES), steps)
        k = min(int(p), steps - 1)
        return k, p - k
    for f in range(a, b + 1):
        k, u = phase(f)
        (y0, z0), (y1, z1) = _tread(13 - k), _tread(12 - k)
        e = u * u * (3 - 2 * u)                       # the body drops as the leading foot reaches down
        nar.location, nar.rotation_euler = (STAIR_X, y0 + 0.02 + (y1 - y0) * u, z0 + (z1 - z0) * e), Euler((0, 0, 0))
        nar.keyframe_insert("location", frame=f)
        nar.keyframe_insert("rotation_euler", frame=f)
    ctx.setdefault("tracks", {})["Narrator"] = {f: (tuple(_at(nar, f).translation.xy), 0.0) for f in range(a, b + 1)}
    rest = {bb.name: bb.matrix_local.copy() for bb in nar.data.bones}
    k_ = nar.scale.x
    ankle = {s: rest[f"{s}Foot"].translation * k_ for s in ("Left", "Right")}

    def spot(side, j):
        y, z = _tread(j)
        return Vector((STAIR_X + ankle[side].x, y + 0.03, z + ankle[side].z))
    for f in range(go, done):                         # step over step: one foot stays on its tread, the other
        k, u = phase(f)                               # swings past it to the tread below
        j = 13 - k
        swing = ("Left", "Right")[k % 2]
        stance = "Right" if swing == "Left" else "Left"
        s = u * u * (3 - 2 * u)
        targets = {stance: spot(stance, j),
                   swing: spot(swing, j + 1 if k else j).lerp(spot(swing, j - 1), s) + Vector((0, 0, 0.07 * math.sin(math.pi * u)))}
        scene.frame_set(f)
        inv = nar.matrix_world.inverted()
        for side, t in targets.items():
            chain = (f"{side}UpLeg", f"{side}Leg", f"{side}Foot")
            pose = {n: nar.pose.bones[n].matrix.copy() for n in chain + ("Hips",)}
            humans._two_bone(nar, rest, pose, f, *chain, inv @ t, pole=(0, -1, 0), force_pole=True)
            bpy.context.view_layer.update()
    face = lambda f, e: humans.face(nar, f, {**cast3d.NEUTRAL, **e})
    face(a, {"mouthSmileLeft": 0.12, "mouthSmileRight": 0.1})
    face(knock + 10, cast3d.SLY)                      # the knock: he knows who it is, and doesn't care
    face(go + 6, cast3d.CHARM)                        # "with a light heart"

    def look(f):
        if f < knock + 3:
            return 8.0, -12.0
        if f < go:
            return 20.0, -38.0                        # down the stair, toward the door
        if f >= done - 4:
            return 15.0, -6.0                         # the door
        return (12.0, -24.0) if (f - go) // 34 % 3 == 1 else (0.0, -30.0)   # his feet, a glance ahead
    humans.eyes(nar, a, b, mode=lambda f: "thinking" if f < knock else "talking", look=look, seed=21)
    humans.breathe(nar, a, b, style="calm", seed=22)
    humans.sway(nar, a, go, amount=0.4, seed=23)
    # the left hand runs down the rail, a little ahead of him; off it at the foot of the stair
    off = next(f for f in range(go, done) if _at(nar, f).translation.y - 0.06 < -1.42)   # the rail ends at y -1.5

    def on_rail(f):
        if f > off:
            return None
        y = _at(nar, f).translation.y - 0.06
        return Vector((RAIL_X - 0.025, y, _rail_z(y) + 0.05))
    humans.grip(nar, "Left", a + 1, curl=0.5)
    _contact(ctx, nar, "Left", a, off + 10, on_rail,
             hand=lambda f: humans.hand_frame((0.12, -1.0, -0.9), (0.35, 0.0, -1.0)), blend=8)
    humans._finger_shape(nar, "Left", off + 4, "relaxed")
    # the camera, low in the hall, looks up the stair at him on the landing and backs away toward the hall as he
    # comes down (it can't ride the stair ahead of him: the stairwell's walls and the hall ceiling are in the way);
    # it looks at a smoothed head, so his head bobs in the frame with each step
    cam = ctx["cams"]["stairs"]
    heads = {}
    for f in range(a, b + 1):
        scene.frame_set(f)
        heads[f] = nar.matrix_world @ nar.pose.bones["Head"].head
    smooth = {f: sum((heads[min(b, max(a, f + d))] for d in range(-STEP_FRAMES, STEP_FRAMES + 1)), Vector()) /
              (2 * STEP_FRAMES + 1) for f in heads}
    # off the last tread he turns toward the street door and steps that way (straight on would be the wall)
    _walk(ctx, nar, [(done, (STAIR_X, -1.60), 0.0), (b, (38.95, -1.66), 65.0)], done, b)
    for f in range(done, b + 1):
        scene.frame_set(f)
        heads[f] = nar.matrix_world @ nar.pose.bones["Head"].head
    smooth = {f: sum((heads[min(b, max(a, f + d))] for d in range(-STEP_FRAMES, STEP_FRAMES + 1)), Vector()) /
              (2 * STEP_FRAMES + 1) for f in heads}
    keys, start, finish = [], Vector((38.7, -1.25, 2.3)), Vector((40.05, -1.25, 1.55))
    for f in range(a, b + 1, 3):
        u = min(1.0, max(0.0, (f - go) / (done - go)))
        keys.append((f, tuple(start.lerp(finish, u * u * (3 - 2 * u))), smooth[f] + Vector((0, 0, -0.12))))
    ctx["su"].animate_camera(cam, keys)
    cam.data.lens = 40
    cam.data.dof.focus_object = nar
    if hasattr(cam.data.dof, "focus_subtarget"):
        cam.data.dof.focus_subtarget = "Head"


def _arrive_door(ctx):
    """5.2-5.3: his left hand pulls the street door open (it swings on when he lets go); the three officers on
    the step, two with lanterns, their breath fogging; Hale lifts his hat with a little bow and speaks; the
    narrator charms them - a wave-off on 'dream', an open arm on 'come in' - and steps aside."""
    bpy, humans, cast3d = ctx["bpy"], ctx["humans"], ctx["cast3d"]
    from mathutils import Matrix, Vector
    T, rigs, props, tl, scene = ctx["T"], ctx["rigs"], ctx["props"], ctx["tl"], bpy.context.scene
    nar, hale = rigs["Narrator"], rigs["Hale"]
    a, b = T("5.2"), T("5.4") - 1
    door, handle = ctx["entry"]["door"], bpy.data.objects["EN_DOOR_Handle"]
    GRAB, OPEN, LET = T("5.2", 0.9), T("5.2", 2.4), T("5.2", 3.4)
    ctx["marks"]["5.2/door_open"] = GRAB
    for f, deg in ((1, 0), (GRAB + 2, 0), (OPEN, -45), (LET, -84), (LET + 10, -82)):
        door.rotation_euler.z = math.radians(deg)
        door.keyframe_insert("rotation_euler", frame=f)
    for fc in v3._fcurves(door):
        for k in fc.keyframe_points:
            if abs(k.co.x - OPEN) < 0.5:
                k.handle_left_type = k.handle_right_type = "AUTO"       # it keeps its speed when the hand lets go
    path = [(a, (39.5, -1.62), 0), (GRAB + 6, (39.5, -1.62), 0), (OPEN + 4, (39.45, -1.25), 12),
            (T("5.3", 7.2), (39.45, -1.25), 12), (T("5.3", 8.4), (39.2, -0.9), 30), (b, (39.2, -0.9), 30)]
    _walk(ctx, nar, path, a, b)
    for n in OFFICERS:
        x, y, h = OUTSIDE[n]
        _walk(ctx, rigs[n], [(a, (x, y), h), (b, (x, y), h)], a, b)
    face = lambda rig, f, e: humans.face(rig, f, {**cast3d.NEUTRAL, **e})
    face(nar, a, cast3d.CHARM)
    for n in OFFICERS:
        face(rigs[n], a, POLITE)
        face(rigs[n], T("5.3", 6.0), cast3d.PLEASANT)                   # "Come in, come in!" - won over
    HAT0 = T("5.2", 4.4)

    def idle(n, f):
        if n == "Narrator":
            return ((0.0, -14.0), "thinking") if f < OPEN else ("Hale", "listening")
        if n == "Hale" or f < OPEN + 6:
            return "Narrator", "listening"
        k = (f + 17 * len(n)) // 40 % 4
        return ((40.0, 0.6, 1.7) if k == 2 else (38.7, 0.2, 2.6) if k == 3 else "Narrator"), "listening"   # past him
    ctx["busy_hands"] = {"Narrator": ("Right",), "Hale": ("Left",), "Brandt": ("Right",), "Mercer": ("Left",)}
    ctx["force_gestures"] = {"5.3_0_NS": [(2.75, "wave"), (5.54, "welcome")]}
    lines = [l for s in tl["shots"] if s["id"] in ("5.2", "5.3") for l in s["lines"] if l["who"] in ON_SCREEN]
    events, phrases = _converse(ctx, lines, a, b, {"Narrator": 0.5, "Hale": 0.4}, idle, seated=False)
    for n, rig in rigs.items():
        mine = [p for e in events if e[2] == n for p in phrases[e]]
        humans.breathe(rig, a, b, style="calm", phrases=mine, seed=_seed(n, 61))
    cam = ctx["cams"]["door_cu"]                      # the close-up keeps his face as he steps back to let them in
    keys = []
    for f in range(T("5.3"), b + 1, 8):
        scene.frame_set(f)
        keys.append((f, (40.4, -3.15, 1.75), nar.matrix_world @ nar.pose.bones["Head"].head + Vector((0, 0, -0.14))))
    ctx["su"].animate_camera(cam, keys)
    cam.data.dof.focus_object = nar
    if hasattr(cam.data.dof, "focus_subtarget"):
        cam.data.dof.focus_subtarget = "Head"
    # Hale's courtesy: a small bow as his hat comes off
    humans._layer(hale, HAT0 - 4, HAT0 + 40, lambda f: {
        "Spine": (0, 5 * v3.ease(HAT0, HAT0 + 10, f) * (1 - v3.ease(HAT0 + 22, HAT0 + 38, f)), 0),
        "Head": (0, 7 * v3.ease(HAT0 + 2, HAT0 + 12, f) * (1 - v3.ease(HAT0 + 20, HAT0 + 36, f)), 0)})

    # ---- contacts, after every layer that moves the body: his hand on the handle; Hale's on his hat brim
    def door_axes(f):
        scene.frame_set(f)
        m = door.matrix_world.to_3x3()
        return (m @ Vector((0, 1, 0))).normalized(), handle.matrix_world.translation.copy()

    def on_handle(f):
        if not GRAB <= f <= OPEN:
            return None
        out, at = door_axes(f)
        fingers = (Vector((0, 0, -1)) + 0.3 * out).normalized()
        return at - fingers * 0.07 - out * 0.03
    turn = lambda f: humans.hand_frame((Vector((0, 0, -1)) + 0.3 * door_axes(min(max(f, GRAB), OPEN))[0]),
                                       door_axes(min(max(f, GRAB), OPEN))[0])
    _contact(ctx, nar, "Left", GRAB - 10, OPEN + 10, on_handle, turn, blend=9)
    humans.grip(nar, "Left", GRAB, curl=0.8)
    humans._finger_shape(nar, "Left", OPEN + 3, "relaxed")
    hat = props["hat_Hale"]
    lift_at, held_at = HAT0 + 10, HAT0 + 26
    scene.frame_set(HAT0)
    hm = hat.matrix_world.copy()
    brim = hm @ Vector((0.05, -(hat["ry"] + 0.035), 0.0))
    fwd = (hm.to_3x3() @ Vector((0, -1, 0))).normalized()

    def on_hat(f):
        if f < HAT0:
            return None
        if f <= lift_at:
            return brim + (Vector((0, 0, 0.1)) + fwd * 0.05) * v3.ease(HAT0, lift_at, f)
        low = _at(hale, f) @ Vector((0.15, -0.24, 1.03))
        return (brim + Vector((0, 0, 0.1)) + fwd * 0.05).lerp(low, v3.ease(lift_at, held_at, f))
    brim_turn = humans.hand_frame(fwd + Vector((0, 0, -0.25)), (0, 0, -1))
    _contact(ctx, hale, "Left", HAT0 - 10, b, on_hat, lambda f: brim_turn, blend=10)
    humans.grip(hale, "Left", HAT0, curl=0.6)
    ctx["hat_lift"] = (HAT0, b)


def _arrive_kitchen(ctx):
    """5.4: the house searched by lantern. Brandt works along the dresser, Mercer at the hearth, their beams
    sweeping; Hale crosses to the window; the narrator stands by with his candle - 'Search well, gentlemen!',
    his arm sweeping out to the room."""
    bpy, humans, cast3d = ctx["bpy"], ctx["humans"], ctx["cast3d"]
    from mathutils import Vector
    T, rigs, tl = ctx["T"], ctx["rigs"], ctx["tl"]
    a, b = T("5.4"), T("5.5") - 1
    t = lambda sec: T("5.4", sec)
    ctx["marks"]["5.4/steps_group"] = a + 6
    paths = {
        "Narrator": [(a, (59.75, -1.45), 150), (b, (59.75, -1.45), 150)],
        "Brandt": [(a, (59.0, -1.3), 205), (t(3.4), (57.95, 0.35), 215), (t(4.2), (57.95, 0.35), 268),
                   (b, (57.95, 0.35), 270)],
        "Hale": [(a, (60.1, -2.05), 147), (t(1.9), (60.95, -0.95), 175), (t(3.3), (61.0, 0.7), 200),
                 (t(4.3), (60.35, 1.5), 225), (t(4.9), (60.35, 1.5), 200), (b, (60.35, 1.5), 200)],
        "Mercer": [(a, (60.95, -1.55), 146), (t(3.0), (62.0, 0.1), 146), (t(3.8), (62.0, 0.1), 105),
                   (b, (62.0, 0.1), 105)],
    }
    for n, path in paths.items():
        _walk(ctx, rigs[n], path, a, b, busy=None if n != "Hale" else set())
    face = lambda rig, f, e: humans.face(rig, f, {**cast3d.NEUTRAL, **e})
    face(rigs["Narrator"], a, cast3d.CHARM)
    for n in OFFICERS:
        face(rigs[n], a, {"browDownLeft": 0.12, "browDownRight": 0.12})           # searching, a little intent
        face(rigs[n], t(6.2), cast3d.PLEASANT)
    looks = {"Brandt": lambda f: (57.6, 0.3 + 0.5 * math.sin(f / 9.0), 1.1 + 0.3 * math.sin(f / 13.0)),
             "Mercer": lambda f: (62.6, 0.3, 0.45 + 0.25 * math.sin(f / 11.0)),
             "Hale": lambda f: (60.0, 2.4, 1.6)}

    def idle(n, f):
        if n == "Narrator":
            return ("Brandt" if (f // 50) % 2 else "Mercer"), "listening"
        return looks[n](f), "thinking"
    ctx["busy_hands"] = {"Narrator": ("Right",), "Brandt": ("Right",), "Mercer": ("Left",)}
    ctx["force_gestures"] = {"5.4_1_NS": [(0.74, "welcome")]}
    lines = [l for s in tl["shots"] if s["id"] == "5.4" for l in s["lines"] if l["who"] in ON_SCREEN]
    events, phrases = _converse(ctx, lines, a, b, {"Narrator": 0.55}, idle, seated=False)
    for n, rig in rigs.items():
        mine = [p for e in events if e[2] == n for p in phrases[e]]
        humans.breathe(rig, a, b, style="calm", phrases=mine, seed=_seed(n, 67))
    ctx["kitchen_looks"] = looks
    cam = ctx["cams"]["kitchen"]                      # pans with the searchers
    scene = bpy.context.scene
    keys = []
    for f in range(a, b + 1, 4):
        scene.frame_set(f)
        c = sum((rigs[n].matrix_world @ rigs[n].pose.bones["Spine1"].head for n in OFFICERS), Vector()) / 3
        keys.append((f, (61.75, 1.55, 1.85), c.lerp(Vector((60.0, -0.6, 1.1)), 0.5)))   # from the NE corner
    ctx["su"].animate_camera(cam, keys)


def _arrive_chest(ctx):
    """5.5: the old man's chamber. He stoops to the strongbox and lifts its lid by the front edge (it swings on
    open when he lets go), straightens and shows them, the candle held over it; the officers lean in, look, and
    nod."""
    bpy, humans, cast3d = ctx["bpy"], ctx["humans"], ctx["cast3d"]
    from mathutils import Matrix, Vector
    T, rigs, room, scene = ctx["T"], ctx["rigs"], ctx["room"], bpy.context.scene
    nar = rigs["Narrator"]
    a, b = T("5.5"), T("5.6") - 1
    t = lambda sec: T("5.5", sec)
    BEND0, GRAB, LET, UP = t(0.8), t(1.6), t(2.5), t(3.5)
    ctx["marks"]["5.5/coin"] = LET + 8
    lid = next(o for o in room["chest"].children if o.name.endswith("_lid"))
    lid.rotation_mode = "XYZ"                         # an imported asset, in quaternions: keyed Euler did nothing
    hinge = lid.matrix_world.translation.copy()
    lid0 = lid.matrix_world.copy()
    angle = {}
    for f in range(a, b + 1):
        angle[f] = (55 * v3.ease(GRAB + 1, LET, f) + 45 * v3.ease(LET, LET + 9, f) - 3 * v3.ease(LET + 9, LET + 15, f))
    def lid_m(f):
        R = Matrix.Rotation(math.radians(angle[f]), 4, "Y")
        return Matrix.Translation(hinge) @ R @ Matrix.Translation(-hinge) @ lid0
    for f in range(GRAB, LET + 16):
        lid.matrix_world = lid_m(f)
        lid.keyframe_insert("location", frame=f)
        lid.keyframe_insert("rotation_euler", frame=f)
    lid.matrix_world = lid0                           # shut before he lifts it, and again in the next shot
    for f in (GRAB - 1, b + 1):
        lid.keyframe_insert("location", frame=f)
        lid.keyframe_insert("rotation_euler", frame=f)
    _constant(lid, ("location", "rotation_euler"))
    x0, y0, h0 = PLACES["5.5"]["Narrator"]
    _walk(ctx, nar, [(a, (x0, y0), h0), (b, (x0, y0), h0)], a, b)
    for n in OFFICERS:
        x, y, h = PLACES["5.5"][n]
        _walk(ctx, rigs[n], [(a, (x, y), h), (b, (x, y), h)], a, b)
    # the stoop: hips back and down (knees bend, feet stay), the trunk hinged forward; up again once the lid goes
    bend = {f: v3.ease(BEND0, GRAB, f) * (1 - v3.ease(LET + 2, UP, f)) for f in range(a, b + 1)}
    humans._layer(nar, a, b, lambda f: {"LowerBack": (0, 36 * bend[f], 0), "Spine": (0, 26 * bend[f], 0),
                                        "Spine1": (0, 13 * bend[f], 0), "Neck1": (0, -22 * bend[f], 0)})
    rest = {bb.name: bb.matrix_local.copy() for bb in nar.data.bones}
    for f in range(BEND0 - 2, UP + 3):                # hips lowered; each foot kept where it stands
        nar.location.z = -0.34 * bend[f]                  # a half squat: the lid edge is 47 cm up
        nar.keyframe_insert("location", index=2, frame=f)
    scene.frame_set(a)
    feet = {s: nar.matrix_world @ nar.pose.bones[f"{s}Foot"].head for s in ("Left", "Right")}
    for f in range(BEND0 - 2, UP + 3):
        scene.frame_set(f)
        inv = nar.matrix_world.inverted()
        for s in ("Left", "Right"):
            chain = (f"{s}UpLeg", f"{s}Leg", f"{s}Foot")
            pose = {n: nar.pose.bones[n].matrix.copy() for n in chain + ("Hips",)}
            humans._two_bone(nar, rest, pose, f, *chain, inv @ feet[s], pole=(0, -1, 0), force_pole=True)
            bpy.context.view_layer.update()
    face = lambda rig, f, e: humans.face(rig, f, {**cast3d.NEUTRAL, **e})
    face(nar, a, cast3d.CHARM)
    face(nar, UP, cast3d.SLY)                         # "secure, undisturbed"
    for n in OFFICERS:
        face(rigs[n], a, cast3d.PLEASANT)
    inside = Vector((2.0, -1.3, 0.4))
    for n in OFFICERS:                                # they lean in to look, and nod
        rig = rigs[n]
        humans._layer(rig, a, b, lambda f: {"LowerBack": (0, 7 * v3.ease(LET - 4, LET + 14, f), 0),
                                            "Spine": (0, 6 * v3.ease(LET - 2, LET + 16, f), 0)})
    looks = {"Narrator": lambda f: inside if f < UP + 10 else "Hale"}

    def idle(n, f):
        if n == "Narrator":
            target = looks["Narrator"](f)
            return (tuple(target) if not isinstance(target, str) else target), "thinking"
        return (tuple(inside) if f > GRAB - 6 else "Narrator"), "listening"
    ctx["busy_hands"] = {"Narrator": ("Left", "Right")}
    events, phrases = _converse(ctx, [], a, b, {}, idle, seated=False)
    for n, rig in rigs.items():
        humans.breathe(rig, a, b, style="calm", seed=_seed(n, 73))
        if n != "Narrator":
            humans.listen(rig, a, b, nar, phrase_ends=[t(4.4 + (0.3 * len(n)) % 1), t(6.3)], seed=_seed(n, 77),
                          gaze=False, shift="LowerBack")
    # his left hand under the lid's front edge, lifting; let go at 55 degrees, it swings on open
    front = Vector((hinge.x - 0.405, hinge.y + 0.08, hinge.z + 0.135))

    def on_lid(f):
        if not GRAB <= f <= LET:
            return None
        p = lid_m(f) @ (lid0.inverted() @ front)
        along = (lid_m(f).to_3x3() @ (lid0.to_3x3().inverted() @ Vector((1, 0, 0)))).normalized()
        return p - along * 0.06 + Vector((0, 0, -0.02))
    lift = lambda f: humans.hand_frame((1.0, 0.0, 0.25), (0.0, 0.0, 1.0))
    _contact(ctx, nar, "Left", GRAB - 10, LET + 10, on_lid, lift, blend=10)
    humans.grip(nar, "Left", GRAB, curl=0.45)
    humans._finger_shape(nar, "Left", LET + 3, "open")
    # then shows them: the open left hand, palm up, toward the coins
    show = lambda f: (_at(nar, f) @ Vector((0.22, -0.36, 1.02))) if UP + 6 <= f <= t(6.8) else None
    humans.reach(nar, "Left", UP - 4, b, target=show,
                 hand=lambda f: humans.hand_frame(_at(nar, f).to_3x3() @ Vector((0.3, -1.0, -0.1)), (0, 0, 1)), blend=10)
    humans._finger_shape(nar, "Left", t(6.8) + 8, "relaxed")
    cam = ctx["cams"]["chest"]                        # a gentle push in
    ctx["su"].animate_camera(cam, [(a, (2.3, -2.1, 1.6), (1.6, -1.2, 0.72)), (GRAB, (2.28, -2.08, 1.58), (1.6, -1.2, 0.7)),
                                   (UP + 12, (2.25, -2.05, 1.72), (1.3, -0.95, 1.22)), (b, (2.15, -1.95, 1.7), (1.3, -0.95, 1.22))])
    ctx["chest_look"] = inside


def _arrive_props(ctx):
    """The props in hand, baked last (after every layer that moves an arm): his candle upright on its brass dish
    in his right hand, 5.1-5.5, then on the washstand; the officers' lanterns hanging from their hands, 5.2-5.4,
    beams on what they look at; Hale's hat in his hand once he lifts it; breath fog outside."""
    bpy, humans, su = ctx["bpy"], ctx["humans"], ctx["su"]
    from mathutils import Matrix, Vector
    from material_library import material as M
    T, rigs, props, scene = ctx["T"], ctx["rigs"], ctx["props"], bpy.context.scene
    nar = rigs["Narrator"]
    a, b = T("5.1"), T("5.6") - 1
    # ---- the candle: a chamberstick (the candle on a brass dish), carried upright on his palm
    candle = props["candle"]
    dish = su.cylinder("V4_Candle_Dish", ctx["C"]["PROPS"], M("MAT_Brass"), 0.055, 0.01, (0, 0, -0.005), segments=32)
    dish.parent = candle
    hold = lambda f: _at(nar, f) @ Vector((-0.13, -0.27 if f < T("5.2") else -0.34, 1.1 + 0.08 * (T("5.2") <= f < T("5.4"))))
    humans.reach(nar, "Right", a, b, target=hold,
                 hand=lambda f: humans.hand_frame(_at(nar, f).to_3x3() @ Vector((0.35, -1.0, 0.05)), (0, 0, 1)), blend=1)
    humans.grip(nar, "Right", a + 1, curl=0.35)
    scene.frame_set(a)
    hand = nar.matrix_world @ nar.pose.bones["RightHand"].matrix
    palm = hand.to_translation() + hand.to_3x3() @ Vector((0, 0.075, -0.035))      # on the palm (palm on -Z)
    candle.matrix_world = Matrix.Translation(palm + Vector((0, 0, 0.012)))
    _carry(ctx, candle, nar, "RightHand", a, b)
    candle.matrix_world = Matrix.Translation((2.05, 0.82, 0.8))                    # set down on the washstand
    candle.keyframe_insert("location", frame=b + 1)
    candle.keyframe_insert("rotation_euler", frame=b + 1)
    _constant(candle, ("location", "rotation_euler"))
    flame = bpy.data.objects["LIGHT_V4_Candle_Flame"]
    for f, e in ((1, 9.0), (T("5.6") - 1, 9.0), (T("5.6"), 1.5)):
        flame.data.energy = e
        flame.data.keyframe_insert("energy", frame=f)
    # ---- lanterns: hanging from Brandt's right hand and Mercer's left, out in front; beams on what they look at
    l0, l1 = T("5.2"), T("5.5") - 1
    for n, side, sx in (("Brandt", "Right", -1), ("Mercer", "Left", 1)):
        rig = rigs[n]
        humans.reach(rig, side, l0, l1, target=lambda f, rig=rig, sx=sx: _at(rig, f) @ Vector((0.17 * sx, -0.25, 0.84)),
                     hand=lambda f, rig=rig, sx=sx: humans.hand_frame(_at(rig, f).to_3x3() @ Vector((0, -0.5, -1)),
                                                                      _at(rig, f).to_3x3() @ Vector((-sx, 0, 0))), blend=1)
        humans.grip(rig, side, l0 + 1, curl=1.0)
        lantern = props[f"lantern_{n}"]
        scene.frame_set(T("5.5"))
        keep = lantern.matrix_world.copy()
        humans.hang(lantern, rig, side, l0, l1, yaw=lambda f, rig=rig: _at(rig, f).to_euler().z)   # lens ahead
        lantern.matrix_world = keep
        lantern.keyframe_insert("location", frame=T("5.5"))
        lantern.keyframe_insert("rotation_euler", frame=T("5.5"))
        ctx["held"].append(dict(prop=lantern.name, rig=rig.name, bone=f"{side}Hand", f0=l0, f1=l1, point=[0, 0, 0.255]))
        beam = bpy.data.objects[f"LIGHT_V4_Lantern_{n}_Beam"]
        beam.rotation_mode = "QUATERNION"
        aim0 = beam.matrix_basis.to_quaternion()
        looks = ctx.get("kitchen_looks", {})
        for f in range(l0, l1 + 1, 2):
            scene.frame_set(f)
            if f >= T("5.4"):
                aim = Vector(looks[n](f)) if n in looks else rig.matrix_world @ Vector((0, -2.0, 0.0))
            else:
                aim = nar.matrix_world @ Vector((0, 0, 0.9))           # on the man at the door
            v3._aim_beam(beam, lantern, aim)
            beam.keyframe_insert("rotation_quaternion", frame=f)
        beam.rotation_quaternion = aim0                # set down in the chamber: as it was
        beam.keyframe_insert("rotation_quaternion", frame=T("5.5"))
        for f, size, e in ((l0, 24, 160), (T("5.4") - 1, 24, 160), (T("5.4"), 24, 220), (T("5.5") - 1, 24, 220),
                           (T("5.5"), 2.2, 40)):
            beam.data.spot_size, beam.data.energy = math.radians(size), e
            beam.data.keyframe_insert("spot_size", frame=f)
            beam.data.keyframe_insert("energy", frame=f)
    # ---- Hale's hat follows his hand once he lifts it (it rode on his head until then)
    hat = props["hat_Hale"]
    h0, h1 = ctx["hat_lift"]
    scene.frame_set(h0 - 1)
    hat.keyframe_insert("location", frame=h0 - 1)
    hat.keyframe_insert("rotation_euler", frame=h0 - 1)
    scene.frame_set(h0)
    grab = (rigs["Hale"].matrix_world @ rigs["Hale"].pose.bones["LeftHand"].matrix).inverted() @ hat.matrix_world
    mats = {}
    for f in range(h0, h1 + 1):
        scene.frame_set(f)
        mats[f] = rigs["Hale"].matrix_world @ rigs["Hale"].pose.bones["LeftHand"].matrix @ grab
    for f, m in mats.items():
        scene.frame_set(f)
        hat.matrix_world = m
        hat.keyframe_insert("location", frame=f)
        hat.keyframe_insert("rotation_euler", frame=f)
    ctx["held"].append(dict(prop=hat.name, rig="Hale", bone="LeftHand", f0=h0, f1=h1, point=[0, 0, 0]))
    _breath_fog(ctx, T("5.2"), T("5.4") - 1)


def _breath_fog(ctx, a, b):
    """The officers' breath on the cold step: on each out-breath a little cloud leaves the mouth, drifts forward
    and up, swells and thins away (a small volume, its density from the object's colour, keyed)."""
    bpy, su = ctx["bpy"], ctx["su"]
    import random
    from mathutils import Vector
    mat = bpy.data.materials.new("MAT_V4_Breath")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out, vol, info, mul = (nt.nodes.new(t) for t in ("ShaderNodeOutputMaterial", "ShaderNodeVolumePrincipled",
                                                     "ShaderNodeObjectInfo", "ShaderNodeMath"))
    mul.operation, mul.inputs[1].default_value = "MULTIPLY", 2.5
    nt.links.new(info.outputs["Alpha"], mul.inputs[0])
    nt.links.new(mul.outputs[0], vol.inputs["Density"])
    vol.inputs["Color"].default_value = (0.85, 0.88, 0.95, 1)
    nt.links.new(vol.outputs[0], out.inputs["Volume"])
    scene = bpy.context.scene
    fps = scene.render.fps
    for n in OFFICERS:
        rig = ctx["rigs"][n]
        rng = random.Random(len(n) * 31)
        t = a + rng.uniform(0.5, 2.5) * fps
        i = 0
        while t < b - fps:
            puff = su.sphere(f"V4_Breath_{n}_{i}", ctx["C"]["PROPS"], mat, 0.05, segments=12)
            puff.color = (1, 1, 1, 0)
            f0, f1 = int(t), int(t + 1.4 * fps)
            scene.frame_set(f0)
            mouth = rig.matrix_world @ (rig.pose.bones["Head"].head + Vector((0, -0.11, -0.02)))
            fwd = (rig.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
            for f, k, alpha in ((f0 - 1, 0.2, 0.0), (f0, 0.3, 0.5), (f0 + 8, 1.0, 0.35), (f1, 2.2, 0.0)):
                u = max(0.0, (f - f0) / (f1 - f0))
                puff.location = mouth + fwd * 0.25 * u + Vector((0, 0, 0.08 * u))
                puff.scale = (k, k, k * 0.7)
                puff.color = (1, 1, 1, alpha)
                for path in ("location", "scale", "color"):
                    puff.keyframe_insert(path, frame=f)
            t += rng.uniform(3.2, 4.4) * fps
            i += 1


def _act_chamber(ctx):
    """5.6-5.10. Chairs are brought in; the officers rest; the narrator carries his own chair in by its back and
    sets its legs down on the loose planks ("placed my own seat upon the very spot"), and stands behind it, hands
    on the rail, smiling. Seated, all four chat (the officers' small talk, his cheery answers); then he hears the
    ringing, pales, a hand goes to his temple; the officers chat on; he forces a smile, sweating, breathing fast."""
    bpy, humans, cast3d = ctx["bpy"], ctx["humans"], ctx["cast3d"]
    from mathutils import Euler, Matrix, Vector
    rigs, props, T, tl = ctx["rigs"], ctx["props"], ctx["T"], ctx["tl"]
    scene = bpy.context.scene
    nar = rigs["Narrator"]
    A, N7, B = T("5.6"), T("5.7"), T("5.11") - 1
    hn = heading_to(SEATS["Narrator"], SEAT_FOCUS["Narrator"])
    face = lambda rig, f, e: humans.face(rig, f, {**cast3d.NEUTRAL, **e})

    # ---- between the shots: the chairs and Mercer's cup come in with 5.6; hats came off on entering (5.4)
    for n in OFFICERS:
        chair = props[f"chair_{n}"]
        keep = chair.location.copy()
        chair.location = (keep.x, keep.y, -5)
        chair.keyframe_insert("location", frame=1)
        chair.location = keep
        chair.keyframe_insert("location", frame=A)
        _constant(chair)
        hat = props[f"hat_{n}"]
        for f, hidden in ((1, False), (T("5.4"), True)):
            hat.hide_render = hat.hide_viewport = hidden
            hat.keyframe_insert("hide_render", frame=f)
            hat.keyframe_insert("hide_viewport", frame=f)
        _constant(hat)

    # ---- the officers sit (from 5.6)
    for n in OFFICERS:
        _hold(bpy, rigs[n], A - 1)
        _sit(ctx, rigs[n], props[f"chair_{n}"], A, CHAMBER_SHOTS)

    # ---- 5.6: the narrator carries his chair in, by its back, and sets it down on the planks
    C = Vector((*SEATS["Narrator"], 0))
    d = Vector((*_dir(hn), 0))
    Q = C - 0.6 * d                            # he stands here to set it down: the top rail 30 cm in front of him
    W0, W1 = T("5.6", 7.5), T("5.6", 11.3)
    D0, D1 = T("5.6", 11.5), T("5.6", 12.7)    # "placed my own seat upon the very spot"
    ctx["marks"]["5.6/chair_place"] = D1
    door = (-1.4, -1.85)
    path = [(A, door, 180), (W0, door, 180), (W0 + 38, (-1.45, -0.75), 170), (W1, (Q.x, Q.y), hn), (N7 - 1, (Q.x, Q.y), hn)]
    track = v3._sample_path(path, A, N7 - 1)
    for f in range(A, N7):
        (x, y), h = track[f]
        nar.location, nar.rotation_euler = (x, y, 0), Euler((0, 0, math.radians(h)))
        nar.keyframe_insert("location", frame=f)
        nar.keyframe_insert("rotation_euler", frame=f)
    v3._mocap_gait(humans, nar, track, A, N7 - 1, set(range(A, N7)))
    humans._layer(nar, D0 - 8, N7 - 1, lambda f: {"LowerBack": (0, 6 * v3.ease(D0 - 4, D1, f) *
                                                                (1 - 0.6 * v3.ease(D1 + 6, D1 + 30, f)), 0)})

    def chair_m(f):
        (x, y), h = track[min(max(f, A), N7 - 1)]
        lift = 0.12 * (1 - v3.ease(D0, D1, f))
        R = Matrix.Rotation(math.radians(h), 3, "Z")
        rail = Vector((x, y, 0)) + Vector((*_dir(h), 0)) * 0.30 + Vector((0, 0, RAIL[2] + lift))
        return Matrix.Translation(rail - R @ Vector(RAIL)) @ R.to_4x4()
    chair = props["chair_Narrator"]
    chair.location = (-1.4, -2.9, -5)
    chair.keyframe_insert("location", frame=1)
    chair.keyframe_insert("rotation_euler", frame=1)
    for f in range(A, D1 + 1):
        chair.matrix_world = chair_m(f)
        chair.keyframe_insert("location", frame=f)
        chair.keyframe_insert("rotation_euler", frame=f)
    _constant(chair)
    humans.breathe(nar, A, N7 - 1, style="calm", seed=5)
    humans.sway(nar, A, N7 - 1, amount=0.5, seed=6)
    humans.eyes(nar, A, N7 - 1, mode=lambda f: "thinking" if f < D1 + 10 else "talking",
                look=lambda f: (0.0, -22.0) if f < D1 + 10 else (-20.0, -5.0), seed=7)
    for side, x in (("Left", 0.14), ("Right", -0.14)):          # palms on the top rail, fingers over it
        humans.reach(nar, side, A, N7 - 1,
                     target=lambda f, x=x: chair_m(f) @ Vector((x, 0.37, 1.06)),
                     hand=lambda f: humans.hand_frame(chair_m(f).to_3x3() @ Vector((0, -1, -0.05)),
                                                      Vector((0, 0, -1))), blend=1)
        from mathutils import Quaternion
        fingers = [b for b in nar.pose.bones if b.name.startswith(f"{side}Hand") and b.name != f"{side}Hand"]
        scene.frame_set(A - 1)
        for pb in fingers:                                       # 5.5's hand held to the cut, then the grip
            pb.keyframe_insert("rotation_quaternion", frame=A - 1)
            pb.rotation_quaternion = Quaternion()
            pb.keyframe_insert("rotation_quaternion", frame=A)
        for finger, degs in humans.GRIP.items():                 # the fingers curl down over the front edge
            for j, deg in enumerate(degs, 1):
                pb = nar.pose.bones.get(f"{side}Hand{finger}{j}")
                if pb is not None:
                    pb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(deg * 0.55))
                    pb.keyframe_insert("rotation_quaternion", frame=A)
        ctx["held"].append(dict(prop=chair.name, rig=nar.name, bone=f"{side}Hand", f0=A, f1=D1, point=[x, RAIL[1], RAIL[2]]))
    face(nar, A, {})
    face(nar, D1, cast3d.SLY)                                  # "the wild audacity of my perfect triumph"

    # ---- the narrator seated (5.7 on)
    _hold(bpy, nar, N7 - 1)
    _sit(ctx, nar, chair, N7, CHAMBER_SHOTS[1:])

    # ---- faces: the officers easy and pleasant; the narrator charming, then the ringing
    for n in OFFICERS:
        face(rigs[n], A, cast3d.PLEASANT)
    face(nar, N7, cast3d.CHARM)
    face(nar, T("5.8", 1.0), cast3d.CHARM)
    face(nar, T("5.8", 3.5), WORRY)                           # "I felt myself getting pale"
    face(nar, T("5.8", 5.2), WINCE)                           # "my head ached"
    face(nar, T("5.9", 0.5), WORRY)
    face(nar, T("5.10", 0.5), {**cast3d.FORCED_SMILE, "eyeWideLeft": 0.35, "eyeWideRight": 0.35})

    # ---- the talk: the officers' small talk and his cheery answers (5.7), on under the narration (5.8-5.10)
    lines = [l for s in tl["shots"] if s["id"] in ("5.7", "5.8", "5.9", "5.10") for l in s["lines"]
             if l["who"] in ON_SCREEN]
    lines += [c for c in tl["chatter"] if N7 <= _frame(c["start"]) <= B]
    ctx.setdefault("busy_hands", {})["Mercer"] = ("Right",)   # his cup

    def idle(n, f):
        if n == "Narrator":
            return ((-20.0, -5.0), "listening") if f < T("5.8", 1.5) else \
                   (((0.0, -12.0), "thinking") if f < T("5.10") else ((0.0, -8.0), "fear"))
        return "Narrator", "listening"
    seated = {n: r for n, r in rigs.items()}
    scene.frame_set(A)
    walk_heads = {}
    for f in range(A, N7):
        scene.frame_set(f)
        walk_heads[f] = nar.matrix_world @ nar.pose.bones["Head"].head
    officers_only = dict(ctx, rigs={n: rigs[n] for n in OFFICERS}, all_rigs=rigs, moving_heads={"Narrator": walk_heads})
    _converse(officers_only, [l for l in lines if _frame(l["start"]) < N7], A, N7 - 1, {}, idle)
    events, phrases = _converse(dict(ctx, rigs=seated), [l for l in lines if _frame(l["start"]) >= N7], N7, B,
                                {"Narrator": 0.5, "Hale": 0.45, "Brandt": 0.5, "Mercer": 0.35}, idle)
    for n, rig in rigs.items():
        mine = [p for e in events if e[2] == n for p in phrases[e]]
        if n == "Narrator":
            humans.breathe(rig, N7, T("5.8") - 1, style="calm", phrases=mine, seed=11)
            humans.breathe(rig, T("5.8"), T("5.10") - 1, style="anxious", phrases=mine, seed=12)
            humans.breathe(rig, T("5.10"), B, style="panic", phrases=mine, seed=13)
        else:
            humans.breathe(rig, A, B, style="calm", phrases=mine, seed=_seed(n, 71))
    laugh = next(e for e in events if e[2] == "Brandt" and "c3" in str(e[3]))     # the stove went out at two
    humans.chuckle(rigs["Hale"], laugh[1] + 4, rest=cast3d.PLEASANT, seed=3)
    ctx["marks"]["5.7/laugh_group"] = laugh[1] + 4

    # ---- 5.8: "my head ached" - his left hand to his temple, and back
    H0, H1 = T("5.8", 5.0), T("5.8", 7.6)
    scene.frame_set(H0)
    temple = nar.matrix_world @ (nar.pose.bones["Head"].matrix @ Vector((0.075, 0.06, -0.02))) + Vector((0, 0, -0.13))
    humans.reach(nar, "Left", H0 - 10, H1 + 10, target=lambda f: temple if H0 <= f <= H1 else None,
                 hand=lambda f: humans.hand_frame(Vector((0, 0, 1)), nar.matrix_world.to_3x3() @ Vector((-1, 0, 0))),
                 blend=10)

    # ---- Mercer's cup, in his right hand on his thigh
    mer = rigs["Mercer"]
    knee = lambda f: mer.matrix_world @ mer.pose.bones["RightLeg"].head
    hip = lambda f: mer.matrix_world @ mer.pose.bones["RightUpLeg"].head
    humans.reach(mer, "Right", A, B, target=lambda f: hip(f).lerp(knee(f), 0.5) + Vector((0, 0, 0.11)),
                 hand=lambda f: humans.hand_frame(mer.matrix_world.to_3x3() @ Vector((0, -1, -0.2)),
                                                  mer.matrix_world.to_3x3() @ Vector((1, 0, 0))), blend=1,
                 pole=(-0.35, 0.7, -0.6))
    humans.grip(mer, "Right", A, curl=0.75)
    cup = props["cup"]
    scene.frame_set(A)
    pb = mer.pose.bones
    grip_at = mer.matrix_world @ pb["RightHandMiddle1"].head.lerp(pb["RightHandMiddle3"].tail, 0.3)
    cup.matrix_world = Matrix.Translation(grip_at + mer.matrix_world.to_3x3() @ Vector((0.045, 0, -0.05)))
    cup.keyframe_insert("location", frame=A)
    cup.keyframe_insert("rotation_euler", frame=A)
    _carry(ctx, cup, mer, "RightHand", A, B)

    # ---- 5.9: dust on the plank seam under his chair jumps on each heartbeat
    _dust(ctx, T("5.9"), T("5.10") - 1)

    # ---- cameras on the actual heads
    _frame_chamber_cams(ctx)


def _carry(ctx, prop, rig, bone, f0, f1):
    """Bake a prop onto a hand from f0 to f1: it keeps the pose it had relative to the hand at f0, so it moves
    only with the hand. Run after every layer that moves that arm; registered for check()."""
    bpy = ctx["bpy"]
    scene = bpy.context.scene
    scene.frame_set(f0)
    offset = (rig.matrix_world @ rig.pose.bones[bone].matrix).inverted() @ prop.matrix_world
    mats = {}
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        mats[f] = rig.matrix_world @ rig.pose.bones[bone].matrix @ offset
    for f, m in mats.items():
        prop.matrix_world = m
        prop.keyframe_insert("location", frame=f)
        prop.keyframe_insert("rotation_euler", frame=f)
    ctx["held"].append(dict(prop=prop.name, rig=rig.name, bone=bone, f0=f0, f1=f1, point=[0, 0, 0]))


def _dust(ctx, f0, f1):
    """Specks of dust along the seam between the loose planks, by his chair: each heartbeat makes them jump."""
    bpy, su = ctx["bpy"], ctx["su"]
    import bmesh
    from material_library import material as M
    beats = [_frame(t) for t in beat_times(ctx["tl"])]
    specks = []
    for i in range(14):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.0007 + 0.0005 * (i % 3))
        x, y = -0.98 + 0.05 * i + 0.012 * ((i * 7) % 5), -0.09 + 0.004 * ((i * 3) % 5 - 2)
        speck = su.make_object(f"V4_Dust_{i}", ctx["C"]["PROPS"], M("MAT_Plaster_Old"), bm, (x, y, 0.001))
        specks.append(speck)
    for i, s in enumerate(specks):
        base = s.location.z
        for f in range(f0, f1 + 1):
            hop = sum(0.004 * (0.6 + 0.4 * ((i * 5) % 3) / 2) * math.exp(-((f - b - (i % 3)) / 2.2) ** 2)
                      for b in beats if abs(f - b) < 12)
            s.location.z = base + hop
            s.keyframe_insert("location", index=2, frame=f)


def _frame_chamber_cams(ctx):
    """Aim the chamber's cameras at where the people really are, once they are seated."""
    bpy, su = ctx["bpy"], ctx["su"]
    from mathutils import Vector
    rigs, cams, T = ctx["rigs"], ctx["cams"], ctx["T"]
    scene = bpy.context.scene
    scene.frame_set(T("5.8", 1.0))
    head = {n: r.matrix_world @ r.pose.bones["Head"].head for n, r in rigs.items()}
    nar = rigs["Narrator"]
    fwd = (nar.matrix_world.to_3x3() @ Vector((0, -1, 0)))
    fwd.z = 0
    fwd.normalize()
    side = Vector((0, 0, 1)).cross(fwd)
    face_at = head["Narrator"] + Vector((0, 0, 0.06)) + fwd * 0.04
    group = sum((head[n] for n in rigs), Vector()) / 4
    behind = head["Narrator"] - fwd * 1.15 + side * 0.55 + Vector((0, 0, 0.45))

    def aim(name, f0, f1, at0, at1, look, lens=None):
        cam = cams[name]
        su.animate_camera(cam, [(f0, tuple(at0), tuple(look)), (f1, tuple(at1), tuple(look))])
        cam.data.dof.focus_distance = (Vector(look) - Vector(at0)).length
        if lens:
            cam.data.lens = lens
    toward_b = (head["Brandt"] - group) * 0.3
    aim("four", T("5.7"), T("5.8") - 1, behind, behind - side * 0.5 + fwd * 0.15,
        group - Vector((0, 0, 0.15)) + toward_b, 22)
    aim("nar_cu", T("5.8"), T("5.9") - 1, face_at + fwd * 1.35, face_at + fwd * 0.95, face_at, 85)
    hh = face_at + (fwd * 0.97 + side * 0.24).normalized() * 0.85
    aim("nar_hh", T("5.10"), T("5.11") - 1, hh, hh - (hh - face_at).normalized() * 0.2, face_at, 50)
    for fc in v3._fcurves(cams["nar_hh"]):                 # handheld: a slow, small drift
        if fc.data_path == "rotation_euler":
            mod = fc.modifiers.new("NOISE")
            mod.scale, mod.strength = 14.0, 0.012
    seam = Vector((-0.72, -0.09, 0.0))
    aim("macro", T("5.9"), T("5.10") - 1, seam + Vector((0.24, -0.26, 0.045)), seam + Vector((0.2, -0.22, 0.04)),
        seam, 100)
    cams["macro"].data.dof.aperture_fstop = 4.0
    aim("floor", T("5.6"), T("5.7") - 1, (-0.55, -1.05, 0.14), (-0.55, -1.0, 0.14), (-0.62, 0.05, 0.12), 24)


# ----------------------------------------------------------------------------------------------- the breakdown
# heavy strides (100STYLE): the angry walk is as fast as the hurried one (2.08 m/s), so it is blended with the plain
# walk by speed; its clip loops round the capture floor, so its straightest stretch is sought in 3 s, not 10
ANGRY = (("Neutral_FW", 240), ("Angry_FW", 72))
RAIL_GRIP = ((0.14, 0.37, 1.06), (-0.14, 0.37, 1.06))     # his palms on the chair's top rail, chair-local (as in 5.6)


def _stand_up(ctx, rig, r0, r1, stand, tuck=0.15):
    """Sit to stand, r0..r1: the feet slide back `tuck` m under the chair, the hips go forward over them and rise,
    the trunk leaning forward on the way up and the hands pushing on the thighs; the feet stay put through the rise
    (leg IK); he ends upright over them in `stand` (bone -> rotation). -> where he stands (world)."""
    bpy, humans = ctx["bpy"], ctx["humans"]
    from mathutils import Vector
    scene = bpy.context.scene
    _hold(bpy, rig, r0)
    scene.frame_set(r0)
    k, pb = rig.scale.x, rig.pose.bones
    seated_feet = {s: rig.matrix_world @ pb[f"{s}Foot"].head for s in ("Left", "Right")}
    back = rig.matrix_world.to_3x3().normalized() @ Vector((0, 1, 0))      # toward the chair
    back.z = 0
    feet = {s: p + back.normalized() * tuck for s, p in seated_feet.items()}
    tucked = r0 + int(0.3 * (r1 - r0))
    rest_mid = sum((rig.data.bones[f"{s}Foot"].head_local for s in ("Left", "Right")), Vector()) / 2
    seat = rig.location.copy()
    up = (feet["Left"] + feet["Right"]) / 2 - rig.matrix_world.to_3x3().normalized() @ (rest_mid * k)
    up.z = 0.0
    for name, q in stand.items():
        pb[name].rotation_quaternion = q
        pb[name].keyframe_insert("rotation_quaternion", frame=r1)
    pb["Hips"].location = (0, 0, 0)
    pb["Hips"].keyframe_insert("location", frame=r1)
    for f in range(r0, r1 + 1):
        u = (f - r0) / (r1 - r0)
        loc = seat.lerp(up, v3.ease(0.0, 0.55, u))
        loc.z = seat.z + (up.z - seat.z) * v3.ease(0.3, 1.0, u)
        rig.location = loc
        rig.keyframe_insert("location", frame=f)
    lean = lambda f: math.sin(math.pi * min(1.0, max(0.0, (f - r0) / (0.8 * (r1 - r0)))))
    humans._layer(rig, r0, r1, lambda f: {"LowerBack": (0, 26 * lean(f), 0), "Spine": (0, 12 * lean(f), 0),
                                          "Neck1": (0, -16 * lean(f), 0)})
    rest = {bb.name: bb.matrix_local.copy() for bb in rig.data.bones}
    for f in range(r0, r1 + 1):
        scene.frame_set(f)
        inv = rig.matrix_world.inverted()
        for s in ("Left", "Right"):
            chain = (f"{s}UpLeg", f"{s}Leg", f"{s}Foot")
            pose = {n: pb[n].matrix.copy() for n in chain + ("Hips",)}
            u = v3.ease(r0, tucked, f)
            humans._two_bone(rig, rest, pose, f, *chain, inv @ seated_feet[s].lerp(feet[s], u), pole=(0, -1, 0),
                             force_pole=True)
            bpy.context.view_layer.update()
    push = r0 + int(0.65 * (r1 - r0))                 # the hands push on the thighs, then let go
    for s in ("Left", "Right"):
        def on_thigh(f, s=s):
            if f > push:
                return None
            scene.frame_set(f)
            m = rig.matrix_world
            return m @ pb[f"{s}UpLeg"].head.lerp(pb[f"{s}Leg"].head, 0.45) + Vector((0, 0, 0.1))
        humans.reach(rig, s, r0, r1, target=on_thigh, blend=6,
                     hand=lambda f: humans.hand_frame(_at(rig, f).to_3x3() @ Vector((0, -1, -0.3)), (0, 0, -1)))
    return up


def _act_breakdown(ctx):
    """5.11-5.15. He rises and argues about trifles, in a high key, with violent gesticulations; paces with heavy
    strides; grips his chair, swings it and grinds it on the boards; the officers chat on, smiling (Mercer sips
    his tea); his horror; the cuts on the beat; the confession - stamping on the planks and pointing - and the
    officers start to their feet."""
    bpy, humans, cast3d = ctx["bpy"], ctx["humans"], ctx["cast3d"]
    from mathutils import Matrix, Vector
    T, rigs, props, tl, cams = ctx["T"], ctx["rigs"], ctx["props"], ctx["tl"], ctx["cams"]
    scene = bpy.context.scene
    nar, chair, mer = rigs["Narrator"], props["chair_Narrator"], rigs["Mercer"]
    a, end = T("5.11"), ctx["end"]
    t = lambda sid, sec: T(sid, sec)
    face = lambda rig, f, e: humans.face(rig, f, {**cast3d.NEUTRAL, **e})
    scene.frame_set(a)
    c0 = chair.matrix_world.copy()
    hn = math.degrees(c0.to_euler().z)
    back = (c0 @ Vector((0, 0.62, 0))).xy                # behind the backrest, where he grips it

    # ---- 5.11: up out of the chair, arguing; then pacing to and fro with heavy strides, back to the chair
    R0, R1 = t("5.11", 0.3), t("5.11", 1.5)
    S = _stand_up(ctx, nar, R0, R1, ctx["stand"]).xy
    hale_dir = heading_to(S, (0.65, -0.3))
    W, N, Sx = (-1.75, -0.6), (-1.75, 0.75), (-1.7, -0.45)
    path = [(R1, tuple(S), hn), (t("5.11", 4.6), tuple(S), hale_dir), (t("5.11", 5.6), (-0.3, -0.52), 230),
            (t("5.11", 7.2), (-1.0, -0.55), 270), (t("5.11", 9.0), (-1.0, -0.55), 80),
            (t("5.11", 9.6), W, heading_to((-1.0, -0.55), W)), (t("5.11", 9.9), W, 180),       # to and fro, twice
            (t("5.11", 10.95), N, 180), (t("5.11", 11.25), N, 0), (t("5.11", 12.2), Sx, heading_to(N, Sx)),
            (t("5.11", 12.5), Sx, 180), (t("5.11", 13.5), N, 180),
            (t("5.11", 13.8), N, heading_to(N, tuple(back))), (t("5.11", 14.6), tuple(back), heading_to(N, tuple(back))),
            (T("5.12") - 1, tuple(back), hn)]          # turned to the chair as he takes hold of it
    talk = {f for c in tl["chatter"] if c["line"] in ("5.11_c10_NS", "5.11_c11_NS")
            for f in range(_frame(c["start"]) - 8, _frame(c["start"] + c["seconds"]) + 8)}
    _walk(ctx, nar, path, R1 + 1, T("5.12") - 1, busy=talk, clips=ANGRY)
    ctx["marks"]["5.11/steps_heavy"] = t("5.11", 9.0)

    # ---- 5.12: both hands on the rail; the chair lifted, swung out and back, banged down, ground on the boards
    G, REL = t("5.12", 0.5), t("5.15", 0.3)

    def heading(f):
        return hn + 60 * v3.ease(t("5.12", 1.5), t("5.12", 2.8), f) * (1 - v3.ease(t("5.12", 2.8), t("5.12", 3.6), f))

    def lift(f):
        return 0.18 * v3.ease(t("5.12", 1.0), t("5.12", 1.5), f) * (1 - v3.ease(t("5.12", 2.8), t("5.12", 3.6), f))

    def grind(f):
        u = (f - t("5.12", 4.0)) / (t("5.12", 8.5) - t("5.12", 4.0))
        return 0.0 if not 0 < u < 1 else 0.16 * math.sin(2 * math.pi * 3 * u) * math.sin(math.pi * u)

    def chair_m2(f):
        h = heading(f)
        R = Matrix.Rotation(math.radians(h), 3, "Z")
        at = Vector((*back, 0)) + Vector((*_dir(h), 0)) * grind(f)
        return Matrix.Translation(at - R @ Vector((0, 0.62, 0)) + Vector((0, 0, lift(f)))) @ R.to_4x4()
    for f in range(G, t("5.12", 8.5) + 1):
        chair.matrix_world = chair_m2(f)
        chair.keyframe_insert("location", frame=f)
        chair.keyframe_insert("rotation_euler", frame=f)
    _constant(chair, ("location", "rotation_euler"))
    ctx["marks"]["5.12/chair_scrape"] = t("5.12", 4.0)
    body = [(f, tuple(Vector((*back, 0)).xy + Vector(_dir(heading(f))) * 0.7 * grind(f)), heading(f))
            for f in range(T("5.12"), REL + 1, 2)]
    _walk(ctx, nar, body, T("5.12"), REL)
    # ---- 5.15: he lets go and steps onto the planks
    _walk(ctx, nar, [(REL, body[-1][1], body[-1][2]), (t("5.15", 1.1), (-1.1, -0.2), 115), (end, (-1.1, -0.2), 115)],
          REL, end, busy=set())

    # ---- 5.15: the officers rise (the base pose: before any layer bakes the seated pose into every frame)
    for i, n in enumerate(OFFICERS):
        _stand_up(ctx, rigs[n], t("5.15", 1.2) + 2 * i, t("5.15", 2.6) + 2 * i, ctx["stand"])

    # ---- faces, breath, talk, gaze
    face(nar, a, cast3d.TENSE)
    face(nar, t("5.11", 5.0), cast3d.FURY)
    face(nar, t("5.13", 6.0), cast3d.HORROR)
    face(nar, T("5.15"), cast3d.FURY)
    smiling = {**cast3d.PLEASANT, "mouthSmileLeft": 0.65, "mouthSmileRight": 0.6, "cheekSquintLeft": 0.35,
               "cheekSquintRight": 0.3}                # "the men chatted pleasantly, and smiled"
    for n in OFFICERS:
        face(rigs[n], a, cast3d.PLEASANT)
        face(rigs[n], T("5.13"), smiling)
        face(rigs[n], t("5.15", 0.5), smiling)
        face(rigs[n], t("5.15", 1.0), {**cast3d.FEAR, "browInnerUp": 0.6})
    lines = [c for c in tl["chatter"] if _frame(c["start"]) >= a]
    lines += [l for s in tl["shots"] if s["id"] == "5.15" for l in s["lines"] if l["who"] in ON_SCREEN]
    ctx["busy_hands"] = {"Mercer": ("Right",)}
    ctx["force_gestures"] = {"5.15_0_NS": [(0.43, "chop"), (3.34, "fist"), (4.66, "point")]}
    officers = [n for n in OFFICERS]

    def idle(n, f):
        if n == "Narrator":
            k = int(f // 19) % 3                      # darting from one smiling face to the next
            return officers[k], ("fear" if f >= T("5.13") else "talking")
        return (officers[(officers.index(n) + 1) % 3] if int(f // 60) % 3 == 1 else "Narrator"), "listening"
    events, phrases = _converse(ctx, lines, a, end, {"Narrator": 0.9, "Hale": 0.4, "Brandt": 0.4, "Mercer": 0.35},
                                idle, seated=True, no_fidget=("Narrator",))
    ctx["busy_hands"], ctx["force_gestures"] = {}, {}
    mine = [p for e in events if e[2] == "Narrator" for p in phrases[e]]
    humans.breathe(nar, a, end, style="panic", phrases=mine, seed=91)
    for n in OFFICERS:
        humans.breathe(rigs[n], a, end, style="calm", seed=_seed(n, 93))
    humans.chuckle(rigs["Hale"], t("5.13", 2.0), rest=cast3d.PLEASANT, seed=7)
    ctx["marks"]["5.13/laugh_group"] = t("5.13", 2.0)
    humans.tremble(nar, T("5.13"), T("5.15") - 1, strength=0.8, seed=95)
    shake = lambda f, k: 0.8 * math.sin(2 * math.pi * 8.2 * f / FPS + k) * math.sin(2 * math.pi * 0.37 * f / FPS + 2 * k)
    humans._layer(nar, T("5.13"), T("5.15") - 1, lambda f: {"Spine1": (shake(f, 0), shake(f, 1), 0),
                                                           "Neck1": (shake(f, 2), shake(f, 3), 0),
                                                           "Head": (shake(f, 4), 0, shake(f, 5))})

    # ---- 5.15: stamping on the planks; the officers start up and rise
    for k, sec in enumerate((6.1, 6.6)):
        hit = t("5.15", sec)
        ctx["marks"]["5.15/stomp" + ("" if k == 0 else "#2")] = hit
        s = lambda f, hit=hit: v3.ease(hit - 5, hit - 1, f) * (1 - v3.ease(hit - 1, hit + 1, f))
        humans._layer(nar, hit - 8, hit + 6, lambda f, s=s: {"RightUpLeg": (0, -45 * s(f), 0),
                                                            "RightLeg": (0, 70 * s(f), 0), "RightFoot": (0, -15 * s(f), 0)})
    for i, n in enumerate(OFFICERS):                  # they start at "Villains!"
        humans.startle(rigs[n], t("5.15", 0.55) + i, strength=1.0, legs=False)

    # ---- hands that hold things, after every layer: his on the chair rail; Mercer's on his cup (and the sip)
    for x, side in zip((0.14, -0.14), ("Left", "Right")):
        from mathutils import Quaternion
        fingers = [b for b in nar.pose.bones if b.name.startswith(f"{side}Hand") and b.name != f"{side}Hand"]
        scene.frame_set(G - 1)
        for pb in fingers:
            pb.keyframe_insert("rotation_quaternion", frame=G - 1)
        for finger, degs in humans.GRIP.items():
            for j, deg in enumerate(degs, 1):
                pb = nar.pose.bones.get(f"{side}Hand{finger}{j}")
                if pb is not None:
                    pb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(deg * 0.55))
                    pb.keyframe_insert("rotation_quaternion", frame=G)
                    pb.keyframe_insert("rotation_quaternion", frame=REL)
        humans._finger_shape(nar, side, REL + 3, "relaxed")
        def on_rail(f, x=x):
            if f < G - 6 or f > REL + 6:
                return None
            up = 0.1 * max(0.0, (G - f) / 6, (f - REL) / 6)          # onto it from above, off it upward
            return chair_m2(min(max(f, G), t("5.12", 8.5))) @ Vector((x, 0.37, 1.06)) + Vector((0, 0, up))
        _contact(ctx, nar, side, G - 14, REL + 14, on_rail,
                 lambda f: humans.hand_frame(chair_m2(min(max(f, G), t("5.12", 8.5))).to_3x3() @ Vector((0, -1, -0.05)),
                                             Vector((0, 0, -1))), blend=10)
        ctx["held"].append(dict(prop=chair.name, rig=nar.name, bone=f"{side}Hand", f0=G, f1=REL,
                                point=[x, RAIL_GRIP[0][1], RAIL_GRIP[0][2]]))
    hip = lambda f: mer.matrix_world @ mer.pose.bones["RightUpLeg"].head
    knee = lambda f: mer.matrix_world @ mer.pose.bones["RightLeg"].head
    S0, S1, SIP0, SIP1 = t("5.15", 1.2) + 4, t("5.15", 2.6) + 4, t("5.13", 9.0), t("5.13", 12.5)

    def cup_at(f):
        scene.frame_set(f)
        on_thigh = hip(f).lerp(knee(f), 0.5) + Vector((0, 0, 0.11))
        head = mer.matrix_world @ mer.pose.bones["Head"].head
        fwd = (mer.matrix_world.to_3x3() @ Vector((0, -1, 0))).normalized()
        sip = v3.ease(SIP0, SIP0 + 20, f) * (1 - v3.ease(SIP1 - 20, SIP1, f))
        p = on_thigh.lerp(head + fwd * 0.1 - Vector((0, 0, 0.12)), sip)
        held = _at(mer, f) @ Vector((-0.2, -0.25, 0.98))
        return p.lerp(held, v3.ease(S0, S1, f))
    humans.reach(mer, "Right", a, end, target=cup_at,
                 hand=lambda f: humans.hand_frame(_at(mer, f).to_3x3() @ Vector((0, -1, -0.2)),
                                                  _at(mer, f).to_3x3() @ Vector((1, 0, 0))), blend=1, pole=(-0.35, 0.7, -0.6))
    _carry(ctx, props["cup"], mer, "RightHand", a, end)

    # ---- cameras: the orbit round him (5.11); the officers in a dolly zoom (5.13); cuts on the beat (5.14);
    # the push and the whip to the planks (5.15)
    heads = {}
    for f in range(a, T("5.12"), 6):
        scene.frame_set(f)
        heads[f] = nar.matrix_world @ nar.pose.bones["Head"].head
    keys = []
    for i, (f, h) in enumerate(sorted(heads.items())):
        ang = math.radians(-110 + 170 * i / max(1, len(heads) - 1))
        at = Vector((min(2.3, max(-2.3, h.x + 1.4 * math.cos(ang))), min(2.1, max(-2.1, h.y + 1.4 * math.sin(ang))), 1.6))
        keys.append((f, tuple(at), h - Vector((0, 0, 0.1))))
    ctx["su"].animate_camera(cams["orbit"], keys)
    oc = cams["officers"]
    ctx["su"].animate_camera(oc, [(T("5.13"), (-0.4, -0.05, 1.25), (0.17, -0.15, 1.15)),
                                  (T("5.14") - 1, (-0.75, 0.02, 1.25), (0.17, -0.15, 1.15))])
    for f, lens in ((T("5.13"), 35), (T("5.14") - 1, 52)):
        oc.data.lens = lens
        oc.data.keyframe_insert("lens", frame=f)
    scene.frame_set(T("5.14"))                        # the ECU of his eye, from the eye bone and its gaze
    eb = nar.matrix_world @ nar.pose.bones["LeftEye"].matrix
    eye, gaze = eb.translation, (eb.to_3x3() @ Vector((0, 1, 0))).normalized()
    ctx["su"].animate_camera(cams["eye_n"], [(T("5.14"), tuple(eye + gaze * 0.32), tuple(eye))])
    cams["eye_n"].data.lens = 85
    for name in ("eye_n", "smile_h", "smile_b", "smile_m"):        # cut fast: every frame must read sharp
        cams[name].data.dof.use_dof = False
    for name, n in (("smile_h", "Hale"), ("smile_b", "Brandt"), ("smile_m", "Mercer")):   # each smile, from the face
        r = rigs[n]
        eyes = [r.matrix_world @ r.pose.bones[f"{s}Eye"].matrix for s in ("Left", "Right")]
        mid = (eyes[0].translation + eyes[1].translation) / 2
        look = sum(((e.to_3x3() @ Vector((0, 1, 0))).normalized() for e in eyes), Vector()).normalized()
        nose = mid - Vector((0, 0, 0.05))
        ctx["su"].animate_camera(cams[name], [(T("5.14"), tuple(nose + look * 0.42 + Vector((0, 0, 0.02))), tuple(nose))])
        cams[name].data.lens = 50
    oc.data.dof.focus_object = rigs["Hale"]
    if hasattr(oc.data.dof, "focus_subtarget"):
        oc.data.dof.focus_subtarget = "Head"
    s14, s15 = T("5.14"), T("5.15")
    beats = [_frame(b) for b in beat_times(tl) if s14 <= _frame(b) < s15]
    cycle = ["smile_h", "macro", "smile_b", "eye_n", "smile_m", "macro"]
    for i, b in enumerate(beats[1::2]):
        ctx.setdefault("extra_cuts", []).append(("5.14", (b - s14) / FPS, cycle[i % len(cycle)]))
    for name in ("eye_n", "smile_h", "smile_b", "smile_m", "macro"):
        cam = cams[name]
        for k, b in enumerate(beats):
            for f, deg in ((b - 1, 0.0), (b, 1.2 * (1 if k % 2 else -1)), (b + 3, 0.0)):
                cam.delta_rotation_euler = (math.radians(deg), 0, math.radians(deg * 0.5))
                cam.keyframe_insert("delta_rotation_euler", frame=f)
    _dust(ctx, s14, s15 - 1)
    scene.frame_set(T("5.15"))
    face_at = nar.matrix_world @ nar.pose.bones["Head"].head
    planks = Vector((-0.85, -0.1, 0.0))
    # from the south-west, clear of where the officers stand once they are up
    # in front of him, in the gap between where Hale and Mercer stand once they are up, over the chair's back;
    # it follows his face as he steps onto the planks

    def face_now(f):
        scene.frame_set(f)
        return tuple(nar.matrix_world @ nar.pose.bones["Head"].head + Vector((0, 0, -0.04)))
    ctx["su"].animate_camera(cams["ms15"], [
        (T("5.15"), (0.05, -0.38, 1.6), face_now(T("5.15"))), (t("5.15", 1.4), (0.0, -0.37, 1.6), face_now(t("5.15", 1.4))),
        (t("5.15", 5.8), (-0.2, -0.35, 1.6), face_now(t("5.15", 5.8))),
        (t("5.15", 6.2), (-0.2, -0.35, 1.6), tuple(planks)), (t("5.15", 6.9), (-0.2, -0.35, 1.6), tuple(planks)),
        (t("5.15", 7.2), (-0.22, -0.34, 1.6), face_now(t("5.15", 7.2))), (end, (-0.3, -0.33, 1.6), face_now(end))])
    cams["ms15"].data.dof.focus_object = nar
    if hasattr(cams["ms15"].data.dof, "focus_subtarget"):
        cams["ms15"].data.dof.focus_subtarget = "Head"
    assert not ctx.get("contact_misses"), "hands that can't reach: " + "; ".join(ctx["contact_misses"])


ACTS = [_act_arrival, _act_chamber, _act_breakdown]          # the animation, part by part, in story order


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


def _check_scene(cast, chair_prefix):
    """What every check reads from the built scene: the rigs, their body/shirt/trousers meshes, the chairs, and
    each rig's hand vertices (weighted over 0.5 to a hand bone)."""
    import bpy
    rigs = {n: bpy.data.objects[n] for n in cast}
    obstacles = {n: [o for o in (bpy.data.objects.get(f"{n}.{p}") for p in ("body", "shirt", "trousers")) if o]
                 for n in cast}
    chairs = [o for o in bpy.data.objects if o.type == "MESH" and any(
        a.name.startswith(chair_prefix) for a in [o] + list(_ancestors(o)))]
    hands = {}
    for n in cast:
        body = obstacles[n][0]
        groups = {g.index for g in body.vertex_groups if g.name.startswith(("LeftHand", "RightHand"))}
        hands[n] = [v.index for v in body.data.vertices if any(g.group in groups and g.weight > 0.5 for g in v.groups)]
    return dict(scene=bpy.context.scene, deps=bpy.context.evaluated_depsgraph_get(), rigs=rigs, obstacles=obstacles,
                chairs=chairs, hands=hands)


def _check_inside(cx, sid, f0, f1, step):
    """A hand more than 5 mm inside another person (body, shirt, trousers) or a chair, every `step` frames."""
    from mathutils.bvhtree import BVHTree
    scene, deps, rigs, obstacles = cx["scene"], cx["deps"], cx["rigs"], cx["obstacles"]
    fails, worst = [], 0.0
    for f in range(f0, f1 + 1, step):
        scene.frame_set(f)
        pts = {}
        for n in rigs:
            ev = obstacles[n][0].evaluated_get(deps)
            me = ev.to_mesh()
            pts[n] = [ev.matrix_world @ me.vertices[i].co for i in cx["hands"][n]]
            ev.to_mesh_clear()
        for n in rigs:
            others = [o for m in rigs if m != n and (rigs[m].matrix_world.translation -
                                                     rigs[n].matrix_world.translation).length < 2.0
                      for o in obstacles[m]] + cx["chairs"]
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
    return fails, [f"{sid}: hands inside others worst {worst * 100:.1f} cm"]


def _check_held(cx, sid, f0, f1, held):
    """A held prop drifting over 1 cm from its hand."""
    import bpy
    from mathutils import Vector
    fails, notes = [], []
    for h in held:
        a, b = max(h["f0"], f0), min(h["f1"], f1)
        if a > b:
            continue
        prop, rig = bpy.data.objects[h["prop"]], cx["rigs"][h["rig"]]
        drift, ref = 0.0, None
        for f in range(a, b + 1, 2):
            cx["scene"].frame_set(f)
            hand = rig.matrix_world @ rig.pose.bones[h["bone"]].matrix
            off = hand.inverted() @ (prop.matrix_world @ Vector(h["point"]))
            ref = ref or off
            drift = max(drift, (off - ref).length)
        notes.append(f"{sid}: {h['prop']} in {h['rig']}'s hand, drift {drift * 100:.1f} cm")
        if drift > 0.01:
            fails.append(f"{sid}: {h['prop']} drifts {drift * 100:.1f} cm from {h['rig']}'s hand")
    return fails, notes


def _check_feet(cx, sid, f0, f1):
    """Planted feet (ball of the foot under 4 cm, moving under 25 cm/s, so a foot swinging low through a step
    doesn't count) sliding over 2 cm/s on average."""
    fails = []
    for n, rig in cx["rigs"].items():
        prev, slide, count = {}, 0.0, 0
        for f in range(f0, f1 + 1):
            cx["scene"].frame_set(f)
            for side in ("Left", "Right"):
                p = rig.matrix_world @ rig.pose.bones[f"{side}ToeBase"].head
                speed = (p.xy - prev[side].xy).length * FPS if side in prev else 9.0
                if side in prev and p.z < 0.04 and prev[side].z < 0.04 and speed < 0.25:   # down, still
                    slide += speed
                    count += 1
                prev[side] = p
        mean = slide / max(count, 1)
        if mean > 0.02:
            fails.append(f"{sid}: {n}'s planted feet slide {mean * 100:.1f} cm/s")
    return fails, []


def _check_locked(cx, sid, f0, f1, step):
    """A seated man's arm locked straight (elbow over 150 deg) with the hand on his lap."""
    fails = []
    for n, rig in cx["rigs"].items():
        for f in range(f0, f1 + 1, step * 3):
            cx["scene"].frame_set(f)
            m, pb = rig.matrix_world, rig.pose.bones
            for side in ("Left", "Right"):
                S, E, W = (m @ pb[f"{side}{b}"].head for b in ("Arm", "ForeArm", "Hand"))
                hip, knee = m @ pb[f"{side}UpLeg"].head, m @ pb[f"{side}Leg"].head
                t = max(0.0, min(1.0, (W - hip).dot(knee - hip) / (knee - hip).length_squared))
                on_lap = knee.z > hip.z - 0.15 and (W - hip.lerp(knee, t)).length < 0.2
                upright = S.z - hip.z > 0.3                   # seated (not lying, where straight arms are rest)
                elbow = math.degrees((S - E).angle(W - E))
                if on_lap and upright and elbow > 150:
                    fails.append(f"{sid} f{f}: {n}'s {side.lower()} arm locked straight on his lap ({elbow:.0f} deg)")
    return fails, []


def _check_lips(cx, sid, f0, f1, spoken, who):
    """A speaker's jaw opening less than 0.08 over a line he speaks on screen (lips must move while talking).
    spoken: timeline lines ({start, seconds, who, line}); who: voice code -> rig name."""
    import bpy
    fails, notes = [], []
    for l in spoken:
        l0, l1 = _frame(l["start"]), _frame(l["start"] + l["seconds"])
        if not (f0 <= l0 <= f1):
            continue
        keys = bpy.data.objects[f"{who[l['who']]}.body"].data.shape_keys.key_blocks
        jaw = []
        for f in range(l0, l1, 2):
            cx["scene"].frame_set(f)
            jaw.append(keys["jawOpen"].value)
        moved = max(jaw) - min(jaw)
        notes.append(f"{sid}: {l['line']} ({who[l['who']]}): jaw opens {moved:.2f}")
        if moved < 0.08:
            fails.append(f"{sid}: {who[l['who']]}'s lips still while he speaks {l['line']} (jaw range {moved:.2f})")
    return fails, notes


def _check_frozen(cx, sid, f0, f1):
    """An on-camera character moving less than 0.5 deg (summed over the spine, neck, head and arms) in any 1 s."""
    from bpy_extras.object_utils import world_to_camera_view
    scene, fails = cx["scene"], []
    for n, rig in cx["rigs"].items():
        for w0 in range(f0, f1 - FPS + 1, FPS // 2):
            if w0 + FPS > rig.get("dead_from", 10 ** 9):    # the dead are still
                continue
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
    return fails, []


def _check_continuity(cx, sid, f0, f1, step):
    """One film across the parts: the strongbox lid shut (except 1.5 and 5.5, where a hand opens it), the loose
    planks at rest (except 4.3-4.4, where his hands lift them) and the narrator's worn look never easing (it
    grows through Nights II-VII and stays)."""
    import bpy
    scene, fails = cx["scene"], []
    lid = bpy.data.objects.get("CH_Strongbox_treasure_chest_lid")
    planks = [o for o in bpy.data.objects if o.name.startswith("CH_Plank_Loose_")]
    nar = cx["rigs"].get("Narrator")
    if lid is not None and sid not in ("1.5", "5.5"):
        scene.frame_set(1)
        shut = lid.matrix_world.to_quaternion()
        for f in range(f0, f1 + 1, step * 3):
            scene.frame_set(f)
            if math.degrees(shut.rotation_difference(lid.matrix_world.to_quaternion()).angle) > 2.0:
                fails.append(f"{sid} f{f}: continuity: the strongbox lid is open with no hand on it")
                break
    if planks and sid not in ("4.3", "4.4"):
        for f in range(f0, f1 + 1, step * 3):
            scene.frame_set(f)
            off = max(abs(o.matrix_world.translation.z + 0.025) for o in planks)
            if off > 0.002:
                fails.append(f"{sid} f{f}: continuity: a loose plank is {off * 100:.1f} cm off its rest")
                break
    if nar is not None and "worn" in nar.keys():
        last = None
        for f in range(f0, f1 + 1, step * 3):
            scene.frame_set(f)
            if last is not None and nar["worn"] < last - 1e-4:
                fails.append(f"{sid} f{f}: continuity: the narrator's worn look eases ({last:.2f} -> {nar['worn']:.2f})")
                break
            last = nar["worn"]
    return fails, []


def run_checks(label, cast, chair_prefix, held, spans, shots, spoken, who, step=4, no_feet=(), animated=True):
    """Every measured check, shot by shot, printed with numbers (prefixed `label`); raises SystemExit on a fail."""
    cx = _check_scene(cast, chair_prefix)
    fails, notes = [], []
    for sid in shots or list(spans):
        f0, f1 = spans[sid]
        parts = [_check_inside(cx, sid, f0, f1, step), _check_held(cx, sid, f0, f1, held)]
        if sid not in no_feet:
            parts.append(_check_feet(cx, sid, f0, f1))
        parts += [_check_locked(cx, sid, f0, f1, step), _check_lips(cx, sid, f0, f1, spoken, who),
                  _check_continuity(cx, sid, f0, f1, step)]
        if animated:
            parts.append(_check_frozen(cx, sid, f0, f1))
        for fl, nt in parts:
            fails += fl
            notes += nt
    for line in notes:
        print(f"{label} check:", line)
    if fails:
        kinds = {}
        for line in fails:
            key = next((k for k in ("inside", "drifts", "slide", "frozen", "lips", "locked", "continuity")
                        if k in line), "other")
            who_ = line.split(": ", 1)[1].split("'")[0] if ": " in line else ""
            kinds[(key, who_)] = kinds.get((key, who_), 0) + 1
        print(f"{label} check failures by kind: " + ", ".join(f"{k} {w}: {n}" for (k, w), n in sorted(kinds.items())))
        print(f"{label} check FAILED ({len(fails)}):\n  " + "\n  ".join(fails))
        raise SystemExit(1)
    print(f"{label} check OK ({'animated' if animated else 'no animation yet: stillness skipped'})")


def check(shots=None, step=4):
    """The Visitors' measured checks (run_checks): hands inside people or chairs, held props drifting, planted
    feet sliding (not on the stair, 5.1), seated arms locked straight, lips still while speaking, continuity, and
    nobody frozen on camera."""
    import bpy
    rigs = {n: bpy.data.objects[n] for n in CAST}
    animated = any(len(fc.keyframe_points) > 1 for r in rigs.values() for fc in v3._fcurves(r)
                   if fc.data_path.startswith("pose.bones"))
    tl = json.loads((OUT / "timeline.json").read_text())
    spoken = [l for s_ in tl["shots"] for l in s_["lines"] if l["who"] in ON_SCREEN] + tl["chatter"]
    run_checks("V4", CAST, "V4_Chair_", json.loads(bpy.context.scene.get("v4_held", "[]")), _spans(), shots,
               spoken, WHO, step=step, no_feet=("5.1",), animated=animated)


def _voices(out_wav, t0, t1):
    """The voices alone, seconds t0..t1 (planned lines at -18 dB RMS, the chatter 12 dB under): for a test clip
    before the full soundtrack exists."""
    import wave
    import numpy as np
    tl = json.loads((OUT / "timeline.json").read_text())
    rate = 24000
    buf = np.zeros(int((t1 - t0) * rate) + 1, np.float32)
    lines = [(l, 1.0) for s in tl["shots"] for l in s["lines"]] + [(c, 0.25) for c in tl["chatter"]]
    for l, gain in lines:
        if l["start"] > t1 or l["start"] + l["seconds"] < t0:
            continue
        with wave.open(str(ROOT / l["file"])) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        x *= gain * 10 ** (-18 / 20) / (np.sqrt(np.mean(x ** 2)) + 1e-9)
        a = int((l["start"] - t0) * rate)
        if a < 0:
            x, a = x[-a:], 0
        x = x[: len(buf) - a]
        buf[a:a + len(x)] += x
    buf /= max(1e-6, np.abs(buf).max()) / 0.9
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    return out_wav


def test57(t0=0.3, t1=10.8):
    """10 s of 5.7 (the four of them chatting: the most gestures) at 480p with the voices -> OUT/test_5.7_480p.mp4."""
    import bpy
    import shutil
    scene = bpy.context.scene
    f0 = _spans()["5.7"][0]
    a, b = f0 + int(t0 * FPS), f0 + int(t1 * FPS)
    scene.frame_start, scene.frame_end = a, b
    scene.eevee.taa_render_samples = 24
    out = OUT / "test57"
    shutil.rmtree(out / "frames", ignore_errors=True)   # render() keeps frames it finds: a stale clip otherwise
    v3.draft(out=out, mix=lambda wav: _voices(wav, (a - 1) / FPS, b / FPS), blend_name="V4 test 5.7")
    shutil.copy(out / "draft_480p.mp4", OUT / "test_5.7_480p.mp4")
    print("V4 test:", OUT / "test_5.7_480p.mp4")


def testclip(first="5.1", last="5.5"):
    """Shots first..last at 480p with the voices -> OUT/test_<first>-<last>_480p.mp4 (to look at a part)."""
    import bpy
    import shutil
    scene = bpy.context.scene
    spans = _spans()
    a, b = spans[first][0], spans[last][1]
    scene.frame_start, scene.frame_end = a, b
    scene.eevee.taa_render_samples = 24
    out = OUT / f"test{first}-{last}"
    shutil.rmtree(out / "frames", ignore_errors=True)   # render() keeps frames it finds: a stale clip otherwise
    v3.draft(out=out, mix=lambda wav: _voices(wav, (a - 1) / FPS, b / FPS), blend_name=f"V4 test {first}-{last}")
    shutil.copy(out / "draft_480p.mp4", OUT / f"test_{first}-{last}_480p.mp4")
    print("V4 test:", OUT / f"test_{first}-{last}_480p.mp4")


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
    spans = _spans()
    for want in shots or list(spans):
        sid, _, sec = want.partition("@")
        f0, f1 = spans[sid]
        scene.frame_set(f0 + int(float(sec) * FPS) if sec else (f0 + f1) // 2)
        r.filepath = str(OUT / "stills" / f"{want}.png")
        bpy.ops.render.render(write_still=True)
    print("V4 stills ->", OUT / "stills")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    shots = args[1].split(",") if len(args) > 1 and args[1] else None
    {"standins": check_standins, "build": build, "build_static": lambda: build(acts=False),
     "check": lambda: check(shots), "stills": lambda: stills(shots), "test57": test57,
     "test": lambda: testclip(*(args[1].split("-") if len(args) > 1 else ("5.1", "5.5"))),
     "timeline": lambda: (OUT.mkdir(parents=True, exist_ok=True),
                          (OUT / "timeline.json").write_text(json.dumps(check_timeline(), indent=1)))}[args[0]]()
