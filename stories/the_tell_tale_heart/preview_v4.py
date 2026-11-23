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


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    {"standins": check_standins,
     "timeline": lambda: (OUT.mkdir(parents=True, exist_ok=True),
                          (OUT / "timeline.json").write_text(json.dumps(check_timeline(), indent=1)))}[args[0]]()
