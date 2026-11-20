"""
Sets for THE TELL-TALE HEART (1840s house). Each location is built as its own film set,
spread out along X so cameras never see one set from another:

    CHAMBER (0)  CORRIDOR (20)  ENTRY+STAIRS (40)  KITCHEN (60)  NARRATOR'S ROOM (80)
    VOID (100)   EXTERIOR (120) EYE macro (140)    WATCH (150)   BEETLE (160)  TITLE (170)

Every builder returns a dict of the objects the shots need to animate.
"""
import json
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import asset_library as lib
import scene_utils as su
from material_library import material as M

ASSETS = su.PROJECT_ROOT / "assets"
H = 3.0                                   # ceiling height
EYE_Z = 5.0                               # the eye macro set floats clear of the street
SET_X = {"chamber": 0, "corridor": 20, "entry": 40, "kitchen": 60, "narrator_room": 80, "void": 100,
         "exterior": 120, "eye": 140, "watch": 150, "beetle": 160, "title": 170}
_MANIFEST = json.loads((ASSETS / "polyhaven_manifest.json").read_text())


def ph(asset_id, coll, name, location=(0, 0, 0), rotation=0, scale=1.0):
    """Import a Poly Haven model (glTF) as one parented group; returns the root object."""
    gltf = next(f for f in _MANIFEST[asset_id]["files"] if f.endswith(".gltf"))
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ASSETS / gltf), import_pack_images=False)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    for obj in new:
        for c in obj.users_collection:
            c.objects.unlink(obj)
        coll.objects.link(obj)
        if obj.parent is None:
            obj.parent = root
        obj.name = f"{name}_{obj.name}"
    root.location, root.rotation_euler.z, root.scale = location, math.radians(rotation), (scale,) * 3
    return root


def walls(prefix, coll, mat, x0, x1, y0, y1, openings=None, height=H, wainscot=True):
    """Four walls around x0..x1, y0..y1 with their inside faces on those lines.
    openings = {"N"|"S": (x_from, x_to, z_from, z_to), "W"|"E": (y_from, y_to, z_from, z_to)} in room coordinates."""
    openings, t = openings or {}, 0.15
    w, d = x1 - x0, y1 - y0
    # side: (start point, rotation, length, function turning a room coordinate into distance along the wall)
    spec = {"N": ((x0 - t, y1), 0, w + 2 * t, lambda c: c - (x0 - t)),
            "S": ((x1 + t, y0), 180, w + 2 * t, lambda c: (x1 + t) - c),
            "W": ((x0, y0 - t), 90, d + 2 * t, lambda c: c - (y0 - t)),
            "E": ((x1, y1 + t), -90, d + 2 * t, lambda c: (y1 + t) - c)}
    out = {}
    for side, (start, rot, length, along) in spec.items():
        gap = openings.get(side)
        local = None
        if gap:
            a, b = sorted((along(gap[0]), along(gap[1])))
            local = (a, b, gap[2], gap[3])
        out[side] = lib.wall(f"{prefix}_Wall_{side}", coll, M(mat), length, height + 0.05, t,
                             (start[0], start[1], -0.05), rotation=rot, opening=local)
        if wainscot:
            segs = [(t, length - t)]
            if gap and gap[2] < 0.9:
                segs = [(t, local[0]), (local[1], length - t)]
            bm = bmesh.new()
            for s0, s1 in segs:
                if s1 - s0 > 0.05:
                    su.add_box(bm, (s1 - s0, 0.02, 0.95), ((s0 + s1) / 2, -0.01, 0.475))
            su.make_object(f"{prefix}_Wainscot_{side}", coll, M("MAT_Bed_Wood"), bm, (start[0], start[1], 0),
                           (0, 0, rot), bevel=0.004)
    return out


def room(prefix, coll, x0, x1, y0, y1, wall_mat="MAT_Plaster_Old", openings=None, ceiling=True, wainscot=True):
    """Plank floor + walls + ceiling."""
    floor = lib.plank_floor(f"{prefix}_Floor", coll, [M("MAT_Floor_Old"), M("MAT_Floor_Old_Alt")], x1 - x0, y1 - y0)
    floor.location = ((x0 + x1) / 2, (y0 + y1) / 2, 0)
    out = walls(prefix, coll, wall_mat, x0, x1, y0, y1, openings, wainscot=wainscot)
    out["floor"] = floor
    if ceiling:
        out["ceiling"] = su.box(f"{prefix}_Ceiling", coll, M(wall_mat), (x1 - x0 + 0.3, y1 - y0 + 0.3, 0.1),
                                ((x0 + x1) / 2, (y0 + y1) / 2, H + 0.05), bevel=0)
    return out


def shutters(prefix, coll, center, width, height, rotation=0):
    """Pair of board shutters (with hairline gaps the moon shines through). Returns the two leaves."""
    leaves = []
    for side in (-1, 1):
        bm = bmesh.new()
        boards = 5
        bw = width / 2 / boards
        for i in range(boards):
            su.add_box(bm, (bw - 0.008, 0.03, height), (side * (i + 0.5) * bw, 0, 0))
        su.add_box(bm, (width / 2, 0.035, 0.08), (side * width / 4, 0.015, height * 0.3))
        su.add_box(bm, (width / 2, 0.035, 0.08), (side * width / 4, 0.015, -height * 0.3))
        leaf = su.make_object(f"{prefix}_Shutter_{'L' if side < 0 else 'R'}", coll, M("MAT_Bed_Wood"), bm,
                              bevel=0.004)
        # hinge on the outer edge
        hinge = Vector((-side * width / 2, 0, 0))
        for v in leaf.data.vertices:
            v.co -= hinge
        hinge.rotate(Matrix.Rotation(math.radians(rotation), 3, "Z"))
        leaf.location = Vector(center) + hinge
        leaf.rotation_euler.z = math.radians(rotation)
        leaves.append(leaf)
    return leaves


def fireplace(prefix, coll, location, rotation=0):
    """Plain 1840s fireplace with mantel shelf; the opening is a black box."""
    x, y, z = location
    bm = bmesh.new()
    su.add_box(bm, (0.35, 0.4, 1.1), (-0.55, 0, 0.55))
    su.add_box(bm, (0.35, 0.4, 1.1), (0.55, 0, 0.55))
    su.add_box(bm, (1.45, 0.4, 0.35), (0, 0, 1.0))
    su.add_box(bm, (1.6, 0.5, 0.06), (0, -0.04, 1.2), material_index=1)
    surround = su.make_object(f"{prefix}_Fireplace", coll, [M("MAT_Plaster_Old"), M("MAT_Bed_Wood")], bm,
                              (x, y, z), (0, 0, rotation), bevel=0.01)
    inside = su.box(f"{prefix}_Fireplace_Opening", coll, M("MAT_Soot"), (0.76, 0.36, 0.84), (0, 0.04, 0.42),
                    bevel=0)
    inside.parent = surround
    hearth = su.box(f"{prefix}_Hearth", coll, M("MAT_Brick"), (1.6, 0.4, 0.04), (0, -0.4, 0.02), bevel=0.005)
    hearth.parent = surround
    return surround


def dark_lantern(coll, name="PROP_Dark_Lantern"):
    """Tin 'dark lantern' with a hinged shutter over its lens. Returns (body, shutter, beam, glow).
    The lens faces local -Y; open the shutter by rotating it around Z."""
    bm = bmesh.new()
    su.add_cylinder(bm, 0.055, 0.17, (0, 0, 0.085), segments=24)
    su.add_cylinder(bm, 0.055, 0.06, (0, 0, 0.2), radius_top=0.015, segments=24)
    su.add_torus(bm, 0.035, 0.005, (0, 0, 0.255), rotation=(90, 0, 0), segments=16)
    su.add_cylinder(bm, 0.03, 0.02, (0, -0.06, 0.09), rotation=(90, 0, 0), segments=20, material_index=1)
    body = su.make_object(name, coll, [M("MAT_Tin"), M("MAT_Bulb")], bm, bevel=0.002)
    bm = bmesh.new()
    su.add_cylinder(bm, 0.036, 0.004, (0.0, -0.073, 0.09), rotation=(90, 0, 0), segments=20)
    shutter = su.make_object(f"{name}_Shutter", coll, M("MAT_Tin"), bm)
    for v in shutter.data.vertices:                 # hinge on the shutter's left edge
        v.co.x += 0.036
    shutter.location = (-0.036, 0, 0)
    shutter.parent = body
    beam = su.light(f"LIGHT_{name}_Beam", coll, "SPOT", (0, -0.08, 0.09), 0, (1.0, 0.72, 0.42),
                    target=(0, -5, 0.09), spot_size=math.radians(2.2), spot_blend=0.15, shadow_soft_size=0.002)
    beam.parent = body
    glow = su.light(f"LIGHT_{name}_Glow", coll, "POINT", (0, -0.05, 0.11), 0, (1.0, 0.6, 0.3),
                    shadow_soft_size=0.02)
    glow.parent = body
    return body, shutter, beam, glow


def haze(name, coll, location, size, density):
    from material_library import haze_material
    bm = bmesh.new()
    su.add_box(bm, size, location)
    obj = su.make_object(name, coll, haze_material(f"MAT_{name}", density=density, color=(0.8, 0.85, 1.0)), bm)
    obj.display_type, obj.hide_select = "BOUNDS", True
    return obj


# --------------------------------------------------------------------- the sets

def chamber(coll, lights):
    """The old man's chamber, 5 x 4.5 m. Door (south), shuttered window (east), fireplace (west),
    the heavy bed (north). Three loose planks lie beside the bed."""
    out = {}
    door_x = -1.4
    # Floor: full-length planks except three short loose ones (where the narrator hides his secret).
    bm, loose = bmesh.new(), []
    pw, rows = 0.18, 25
    for r in range(rows):
        y = -2.25 + pw * (r + 0.5)
        segs = [(-2.5, 2.5)]
        if r in (11, 12, 13):
            segs = [(-2.5, -1.2), (0.0, 2.5)]
            loose.append(y)
        for a, b in segs:
            su.add_box(bm, (b - a - 0.004, pw - 0.004, 0.05), ((a + b) / 2, y, -0.025), material_index=r % 2)
    out["floor"] = su.make_object("CH_Floor", coll, [M("MAT_Floor_Old"), M("MAT_Floor_Old_Alt")], bm, bevel=0.004)
    out["planks"] = [su.box(f"CH_Plank_Loose_{i + 1}", coll, M("MAT_Floor_Old" if i % 2 else "MAT_Floor_Old_Alt"),
                            (1.196, pw - 0.004, 0.05), (-0.6, y, -0.025), bevel=0.004) for i, y in enumerate(loose)]
    void = su.box("CH_Under_Floor", coll, M("MAT_Soot"), (1.4, 0.7, 0.3), (-0.6, 0.0, -0.2), bevel=0)
    bm = bmesh.new()
    for x in (-1.1, -0.6, -0.1):
        su.add_box(bm, (0.06, 0.8, 0.18), (x, 0.0, -0.14))
    su.make_object("CH_Scantlings", coll, M("MAT_Bed_Wood"), bm)
    del void

    # Walls: a real doorway (south) and a window opening (east)
    t = 0.15
    walls("CH", coll, "MAT_Wallpaper_Dark", -2.5, 2.5, -2.25, 2.25,
          openings={"S": (door_x - 0.45, door_x + 0.45, 0.0, 2.15), "E": (-0.55, 0.55, 0.9, 2.25)})
    out["ceiling"] = su.box("CH_Ceiling", coll, M("MAT_Plaster_Old"), (5.4, 4.9, 0.1), (0, 0, H + 0.05), bevel=0)

    # Door (opens into the room) and a black stub of corridor behind it
    door = lib.door(coll, (door_x, -2.25, 0), rotation=180, prefix="CH_DOOR")
    bpy.data.objects.remove(bpy.data.objects["CH_DOOR_Doorway_Shadow"])
    out["door"] = bpy.data.objects["CH_DOOR_Panel"]
    su.box("CH_Corridor_Stub_Floor", coll, M("MAT_Floor_Old"), (2.0, 1.6, 0.05), (door_x, -3.1, -0.025), bevel=0)
    su.box("CH_Corridor_Stub_Back", coll, M("MAT_Black"), (2.4, 0.1, 3.0), (door_x, -3.95, 1.5), bevel=0)
    del door

    # Window with closed shutters (moon or sun shines through the gaps)
    lib.window(coll, (2.5, 0, 1.575), 1.1, 1.35, t, rotation=-90, prefix="CH_WINDOW")
    out["shutters"] = shutters("CH", coll, (2.43, 0, 1.575), 1.06, 1.3, rotation=90)
    out["sky"] = su.box("CH_Sky_Outside", coll, M("MAT_Night_Sky"), (0.02, 3.0, 2.5), (3.4, 0, 1.6), bevel=0)
    out["sky"].visible_shadow = False

    out["fireplace"] = fireplace("CH", coll, (-2.3, 0.5, 0), rotation=90)
    ph("mantel_clock_01", coll, "CH_Mantel_Clock", (-2.22, 0.5, 1.23), rotation=90)
    out["bed"] = ph("GothicBed_01", coll, "CH_Bed", (0.9, 1.2, 0), rotation=0)
    out["chest"] = ph("treasure_chest", coll, "CH_Strongbox", (2.0, -1.3, 0), rotation=-90, scale=0.8)
    ph("GothicCabinet_01", coll, "CH_Wardrobe", (-1.3, 1.85, 0), rotation=0, scale=0.85)
    ph("jug_01", coll, "CH_Jug", (2.15, 0.95, 0.8))
    lib.side_table(coll, (2.15, 0.95, 0), prefix="CH_Washstand")
    ph("fancy_picture_frame_01", coll, "CH_Portrait", (-0.2, 2.2, 1.9), rotation=180)

    # Bedclothes: blanket and pillow on the gothic bed (mattress top raycast at z 0.44; they floated ~0.2 m
    # above it before)
    out["blanket"] = su.drape("CH_Blanket", coll, M("MAT_Nightshirt"), 1.35, 1.45, 0.3, (0.9, 0.85, 0.46),
                              sides=("left", "right", "front"), flare=0.05, wrinkles=0.03)
    out["pillow"] = su.pillow("CH_Pillow", coll, M("MAT_Pillow"), (0.7, 0.42, 0.11), (0.9, 1.85, 0.50),
                              rotation=(10, 0, 0))
    out["wall_clock"] = lib.wall_clock(coll, (-2.05, -2.24, 2.05), rotation=180, radius=0.15,
                                       prefix="CH_Wall_Clock")
    out["clock_hands"] = bpy.data.objects["CH_Wall_Clock_Hands"]

    # Coins in the strongbox (shown when the lid opens)
    bm = bmesh.new()
    for i in range(14):
        a = i * 2.4
        su.add_cylinder(bm, 0.018, 0.004, (0.12 * math.cos(a) * (i % 3) / 2, 0.08 * math.sin(a), 0.42 + i * 0.002),
                        segments=16)
    coins = su.make_object("CH_Gold_Coins", coll, M("MAT_Gold"), bm)
    coins.parent = out["chest"]
    out["chest_lid"] = next((o for o in out["chest"].children if "lid" in o.name.lower()), None)

    # Mouse and soot for the old man's "it is only a mouse… the wind in the chimney"
    bm = bmesh.new()
    su.add_sphere(bm, 1.0, (0, 0, 0.022), scale=(0.022, 0.045, 0.02), segments=12)
    su.add_rod(bm, (0, 0.04, 0.012), (0.03, 0.11, 0.004), 0.002)
    out["mouse"] = su.make_object("CH_Mouse", coll, M("MAT_Fabric_Charcoal"), bm, (-1.8, -0.4, 0))
    bm = bmesh.new()
    for i in range(30):
        verts = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.006 + (i % 4) * 0.002)["verts"]
        bmesh.ops.translate(bm, vec=((i * 37 % 60) / 100 - 0.3, (i * 13 % 20) / 100 - 0.1, (i * 29 % 50) / 100),
                            verts=verts)
    out["soot"] = su.make_object("CH_Soot", coll, M("MAT_Soot"), bm, (-2.3, 0.5, 0.9), flat=True)

    # Lighting rig (energies are keyed per shot)
    # the moon is a small, sharp source; a 1.2 m area light's traced soft shadows speckled every lit surface
    # in Eevee (more samples did not help), and jitter alone on the big light gave blocky shadow tiles
    lights["moon"] = su.light("CH_LIGHT_Moon", coll, "AREA", (3.6, 0.3, 2.4), 0, (0.55, 0.68, 1.0),
                              target=(0.3, -0.2, 0.0), shape="RECTANGLE", size=0.15, size_y=0.18,
                              use_shadow_jitter=True, shadow_jitter_overblur=0.0)
    lights["sun"] = su.light("CH_LIGHT_Sun", coll, "SUN", (6, 0, 4), 0, (1.0, 0.9, 0.75), target=(0, 0.3, 0),
                             angle=math.radians(2))
    lights["fill"] = su.light("CH_LIGHT_Fill", coll, "AREA", (0.5, -1.5, 2.9), 0, (0.6, 0.7, 1.0),
                              target=(0.5, 0.5, 0.0), shape="DISK", size=3.0)
    lights["warm"] = su.light("CH_LIGHT_Warm_Fill", coll, "AREA", (-0.5, -1.0, 2.8), 0, (1.0, 0.7, 0.45),
                              target=(0, 0.5, 0.5), shape="DISK", size=3.0)
    lights["shadow"] = su.light("CH_LIGHT_Shadow_Caster", coll, "SPOT", (-1.4, -2.0, 0.45), 0, (1.0, 0.65, 0.35),
                                target=(0.9, 2.2, 2.2), spot_size=math.radians(80), spot_blend=0.6,
                                shadow_soft_size=0.01)
    out["haze"] = haze("CH_Haze", coll, (0, 0, 1.5), (5.0, 4.5, 3.0), 0.05)
    return out


def corridor(coll, lights):
    x = SET_X["corridor"]
    out = {}
    lib.plank_floor("CO_Floor", coll, [M("MAT_Floor_Old"), M("MAT_Floor_Old_Alt")], 1.8, 8.0).location = (x, 0, 0)
    t = 0.15
    walls("CO", coll, "MAT_Wallpaper_Dark", x - 0.9, x + 0.9, -4.0, 4.0,
          openings={"E": (0.75, 1.65, 0.0, 2.15), "S": (x - 0.4, x + 0.4, 1.0, 2.3)})
    out["ceiling"] = su.box("CO_Ceiling", coll, M("MAT_Plaster_Old"), (2.2, 8.4, 0.1), (x, 0, H + 0.05), bevel=0)
    lib.door(coll, (x + 0.9, 1.2, 0), rotation=-90, prefix="CO_DOOR")          # the old man's door
    out["door"] = bpy.data.objects["CO_DOOR_Panel"]
    out["handle"] = bpy.data.objects["CO_DOOR_Handle"]
    bpy.data.objects.remove(bpy.data.objects["CO_DOOR_Doorway_Shadow"])
    su.box("CO_Door_Dark", coll, M("MAT_Black"), (0.1, 1.2, 2.4), (x + 1.25, 1.2, 1.2), bevel=0)
    lib.door(coll, (x - 0.9, -2.2, 0), rotation=90, prefix="CO_DOOR_NARRATOR")
    out["clock"] = ph("vintage_grandfather_clock_01", coll, "CO_Long_Case_Clock", (x, 3.7, 0))     # faces -Y
    ph("fancy_picture_frame_01", coll, "CO_Portrait", (x - 0.88, 0.8, 1.8), rotation=-90)
    lib.window(coll, (x, -4.0, 1.65), 0.8, 1.3, t, rotation=180, prefix="CO_WINDOW")
    su.box("CO_Sky", coll, M("MAT_Night_Sky"), (3.0, 0.02, 3.0), (x, -4.9, 1.6), bevel=0).visible_shadow = False
    lights["co_moon"] = su.light("CO_LIGHT_Moon", coll, "AREA", (x, -4.6, 2.2), 0, (0.55, 0.68, 1.0),
                                 target=(x, 0, 0), shape="RECTANGLE", size=0.8, size_y=1.3)
    lights["co_fill"] = su.light("CO_LIGHT_Fill", coll, "AREA", (x, 0, 2.9), 0, (0.6, 0.7, 1.0),
                                 target=(x, 0, 0), shape="RECTANGLE", size=1.4, size_y=7)
    haze("CO_Haze", coll, (x, 0, 1.5), (1.8, 8, 3), 0.035)
    return out


def entry(coll, lights):
    """Entry hall with the street door, a straight stair and a stub of street outside."""
    x = SET_X["entry"]
    out = {}
    lib.plank_floor("EN_Floor", coll, [M("MAT_Floor_Old"), M("MAT_Floor_Old_Alt")], 4.0, 4.0).location = (x, 0, 0)
    walls("EN", coll, "MAT_Plaster_Old", x - 2.0, x + 2.0, -2.0, 2.0, openings={"S": (x - 0.5, x + 0.5, 0.0, 2.2)},
          height=3.5)
    lib.door(coll, (x, -2.0, 0), rotation=180, prefix="EN_DOOR")
    out["door"] = bpy.data.objects["EN_DOOR_Panel"]
    bpy.data.objects.remove(bpy.data.objects["EN_DOOR_Doorway_Shadow"])
    # Stairs along the west wall, rising toward +Y (14 steps up to 3 m)
    bm = bmesh.new()
    for i in range(14):
        su.add_box(bm, (1.0, 0.24, 0.214 * (i + 1)), (x - 1.45, -1.4 + i * 0.22, 0.107 * (i + 1)))
    out["stairs"] = su.make_object("EN_Stairs", coll, M("MAT_Floor_Old"), bm, bevel=0.005)
    bm = bmesh.new()
    for i in range(0, 14, 2):
        su.add_rod(bm, (x - 0.97, -1.4 + i * 0.22, 0.214 * (i + 1)), (x - 0.97, -1.4 + i * 0.22, 0.214 * (i + 1) + 0.9),
                   0.015)
    su.add_rod(bm, (x - 0.97, -1.5, 1.1), (x - 0.97, 1.6, 3.9), 0.03)
    su.make_object("EN_Banister", coll, M("MAT_Bed_Wood"), bm)
    lib.side_table(coll, (x + 1.5, 1.4, 0), prefix="EN_Hall_Table")
    ph("ornate_mirror_01", coll, "EN_Mirror", (x + 1.97, 0.6, 1.7), rotation=90)
    # Street stub outside the door
    su.box("EN_Street", coll, M("MAT_Cobble"), (8, 5, 0.1), (x, -4.6, -0.12), bevel=0)
    su.box("EN_Street_Back", coll, M("MAT_Night_Sky"), (10, 0.1, 6), (x, -7.0, 2.5), bevel=0)
    ph("street_lamp_01", coll, "EN_Street_Lamp", (x + 1.6, -3.4, -0.07))
    lights["en_lamp"] = su.light("EN_LIGHT_Street_Lamp", coll, "POINT", (x + 1.6, -3.4, 3.3), 0, (1.0, 0.7, 0.4),
                                 shadow_soft_size=0.15)
    lights["en_fill"] = su.light("EN_LIGHT_Fill", coll, "AREA", (x, 0.5, 3.4), 0, (0.65, 0.72, 1.0),
                                 target=(x, 0, 0), shape="DISK", size=3)
    lights["en_day"] = su.light("EN_LIGHT_Day", coll, "AREA", (x + 1.0, 1.0, 3.3), 0, (1.0, 0.92, 0.8),
                                target=(x - 1.2, 0.5, 1.5), shape="DISK", size=2.5)
    haze("EN_Haze", coll, (x, -3.0, 1.6), (8, 8, 3.4), 0.03)
    return out


def kitchen(coll, lights):
    x = SET_X["kitchen"]
    out = {}
    room("KI", coll, x - 3, x + 3, -2.5, 2.5, wall_mat="MAT_Plaster_Old",
         openings={"N": (x - 0.55, x + 0.55, 0.9, 2.2)}, wainscot=False)
    lib.window(coll, (x, 2.5, 1.55), 1.1, 1.3, 0.15, rotation=0, prefix="KI_WINDOW")
    su.box("KI_Sky", coll, M("MAT_Night_Sky"), (4, 0.02, 3), (x, 3.4, 1.6), bevel=0).visible_shadow = False
    ph("painted_wooden_table", coll, "KI_Table", (x, 0.2, 0), scale=0.75)
    for i, (dx, rot) in enumerate(((-0.6, 0), (0.6, 0))):
        ph("dining_chair_02", coll, f"KI_Chair_{i + 1}", (x + dx, -0.45, 0), rotation=rot)
    ph("painted_wooden_cabinet", coll, "KI_Cabinet", (x - 2.65, 0.3, 0), rotation=-90)
    fireplace("KI", coll, (x + 2.75, 0.3, 0), rotation=-90)
    ph("brass_pot_01", coll, "KI_Teapot", (x - 0.2, 0.25, 0.72))
    ph("jug_01", coll, "KI_Jug", (x + 0.5, 0.45, 0.72))
    out["tray"] = su.box("PROP_Tray", coll, M("MAT_Furniture_Wood"), (0.46, 0.32, 0.02), (x - 0.1, -0.05, 0.73),
                         bevel=0.006)
    cup = lib.mug(coll, (x - 0.2, -0.05, 0.74), prefix="PROP_Tray_Cup")
    cup.parent, cup.location = out["tray"], (-0.1, 0, 0.01)
    bread = su.sphere("PROP_Tray_Bread", coll, M("MAT_Basket"), 0.06, (0.1, 0, 0.04), scale=(1.3, 0.9, 0.6))
    bread.parent = out["tray"]
    lights["ki_sun"] = su.light("KI_LIGHT_Sun", coll, "AREA", (x, 3.2, 2.0), 0, (1.0, 0.9, 0.75),
                                target=(x, 0, 0.5), shape="RECTANGLE", size=1.2, size_y=1.4)
    lights["ki_fill"] = su.light("KI_LIGHT_Fill", coll, "AREA", (x, -1.0, 2.9), 0, (1.0, 0.92, 0.85),
                                 target=(x, 0.5, 0), shape="DISK", size=3.0)
    haze("KI_Haze", coll, (x, 0, 1.5), (6, 5, 3), 0.025)
    return out


def narrator_room(coll, lights):
    x = SET_X["narrator_room"]
    out = {}
    room("NR", coll, x - 2, x + 2, -2, 2, wall_mat="MAT_Plaster_Old",
         openings={"N": (x - 0.5, x + 0.5, 0.9, 2.2)}, wainscot=False)
    lib.window(coll, (x, 2.0, 1.55), 1.0, 1.3, 0.15, rotation=0, prefix="NR_WINDOW")
    out["sky"] = su.box("NR_Sky", coll, M("MAT_Night_Sky"), (4, 0.02, 3), (x, 2.8, 1.6), bevel=0)
    out["sky"].visible_shadow = False
    ph("old_bed_frame", coll, "NR_Bed", (x + 1.4, -0.6, 0), rotation=0)
    ph("dining_chair_02", coll, "NR_Chair", (x, 1.1, 0), rotation=180)
    lib.desk(coll, (x - 1.5, 1.6, 0), prefix="NR_Desk")
    out["candle"] = lib.candle(coll, coll, (x - 1.4, 1.55, 0.75), prefix="NR_Candle")
    lights["nr_candle"] = bpy.data.objects["LIGHT_NR_Candle_Flame"]
    lights["nr_sun"] = su.light("NR_LIGHT_Window", coll, "AREA", (x, 2.6, 2.0), 0, (1.0, 0.85, 0.65),
                                target=(x, 0, 0.5), shape="RECTANGLE", size=1.0, size_y=1.3)
    lights["nr_fill"] = su.light("NR_LIGHT_Fill", coll, "AREA", (x, -1.5, 2.9), 0, (0.7, 0.75, 1.0),
                                 target=(x, 0.5, 0), shape="DISK", size=2.5)
    return out


def void(coll, lights):
    x = SET_X["void"]
    ph("dining_chair_02", coll, "VO_Chair", (x, 0, 0), rotation=180)
    su.box("VO_Floor", coll, M("MAT_Black"), (12, 12, 0.02), (x, 0, -0.01), bevel=0)
    lights["vo_top"] = su.light("VO_LIGHT_Top", coll, "SPOT", (x, -0.35, 3.2), 0, (1.0, 0.92, 0.82),
                                target=(x, -0.05, 1.0), spot_size=math.radians(38), spot_blend=0.5,
                                shadow_soft_size=0.15)
    lights["vo_rim"] = su.light("VO_LIGHT_Rim", coll, "AREA", (x + 0.8, 1.2, 1.8), 0, (0.55, 0.68, 1.0),
                                target=(x, 0, 1.2), shape="DISK", size=0.6)
    return {}


def exterior(coll, lights):
    x = SET_X["exterior"]
    out = {}
    su.box("EX_Street", coll, M("MAT_Cobble"), (24, 30, 0.1), (x, -6, -0.05), bevel=0)
    for side, y, rot in (("House", 0.0, 0), ("Opposite", -12.0, 180)):
        bm = bmesh.new()
        su.add_box(bm, (8, 0.4, 8.5), (0, 0.2, 4.25))
        fac = su.make_object(f"EX_{side}_Facade", coll, M("MAT_Brick"), bm, (x, y, 0), (0, 0, rot), bevel=0.01)
        roof = su.box(f"EX_{side}_Roof", coll, M("MAT_Base_Dark"), (8.4, 3, 0.3), (0, 1.3, 8.9), (35, 0, 0), bevel=0)
        roof.parent = fac
        for wx, wz in ((-2.3, 2.0), (2.3, 2.0), (-2.3, 5.6), (2.3, 5.6), (0, 5.6)):
            w = su.box(f"EX_{side}_Window_{wx}_{wz}", coll, M("MAT_Night_Sky"), (1.0, 0.05, 1.5), (wx, -0.02, wz),
                       bevel=0)
            w.parent = fac
            frame = su.box(f"EX_{side}_Sill_{wx}_{wz}", coll, M("MAT_Trim_White"), (1.2, 0.12, 0.08),
                           (wx, -0.06, wz - 0.8), bevel=0.01)
            frame.parent = fac
        out[side] = fac
    lit = M("MAT_Lamp_Shade")
    bpy.data.objects["EX_House_Window_2.3_5.6"].data.materials[0] = lit             # the old man's lamp
    out["neighbour_window"] = bpy.data.objects["EX_Opposite_Window_2.3_2.0"]    # facade turned 180: world x - 2.3
    out["neighbour_window"].data.materials[0] = lit
    lib.door(coll, (x, 0.0, 0.15), rotation=0, prefix="EX_DOOR")
    bpy.data.objects.remove(bpy.data.objects["EX_DOOR_Doorway_Shadow"])
    su.box("EX_Steps", coll, M("MAT_Plaster_Old"), (1.8, 0.8, 0.15), (x, -0.45, 0.075), bevel=0.01)
    ph("street_lamp_01", coll, "EX_Street_Lamp", (x + 2.8, -2.2, 0))
    lights["ex_lamp"] = su.light("EX_LIGHT_Lamp", coll, "POINT", (x + 2.8, -2.2, 3.3), 0, (1.0, 0.7, 0.4),
                                 shadow_soft_size=0.2)
    lights["ex_moon"] = su.light("EX_LIGHT_Moon", coll, "SUN", (x, -10, 10), 0, (0.55, 0.68, 1.0),
                                 target=(x, 0, 0), angle=math.radians(3))
    lights["ex_window"] = su.light("EX_LIGHT_Neighbour", coll, "POINT", (x - 2.3, -11.5, 2.0), 0,
                                   (1.0, 0.65, 0.35), shadow_soft_size=0.3)
    haze("EX_Fog", coll, (x, -6, 3), (30, 20, 6), 0.012)
    return out


def gas_lamp(coll, name, location, lights, energy=450):
    """1840s cast-iron gas street lamp: fluted post, ladder bar, four-pane lantern, cap."""
    x, y, z = location
    iron = M("MAT_Metal")
    su.cylinder(f"{name}_Base", coll, iron, 0.15, 0.45, (x, y, z + 0.225), segments=12)
    su.cylinder(f"{name}_Post", coll, iron, 0.055, 2.7, (x, y, z + 1.8), segments=12)
    su.box(f"{name}_Ladder_Bar", coll, iron, (0.7, 0.04, 0.04), (x, y, z + 2.85), bevel=0.005)
    glass = bpy.data.materials.get("MAT_Gas_Glass") or bpy.data.materials.new("MAT_Gas_Glass")
    glass.use_nodes = True
    g = glass.node_tree.nodes["Principled BSDF"].inputs
    g["Base Color"].default_value = (1.0, 0.78, 0.5, 1)
    g["Emission Color"].default_value, g["Emission Strength"].default_value = (1.0, 0.6, 0.28, 1), 1.6
    g["Roughness"].default_value = 0.2
    lantern = su.box(f"{name}_Lantern", coll, glass, (0.32, 0.32, 0.46), (x, y, z + 3.4), bevel=0.01)
    lantern.visible_shadow = False        # the flame's light must get out through the glass
    for dx in (-0.17, 0.17):
        for dy in (-0.17, 0.17):
            su.box(f"{name}_Frame_{dx}_{dy}", coll, iron, (0.03, 0.03, 0.5), (x + dx, y + dy, z + 3.4), bevel=0)
    bm = bmesh.new()
    su.add_cylinder(bm, 0.3, 0.28, (0, 0, 0), radius_top=0.02, segments=4)
    su.make_object(f"{name}_Cap", coll, iron, bm, (x, y, z + 3.77), (0, 0, math.radians(45)), bevel=0)
    lights[f"{name}_light"] = su.light(f"{name}_LIGHT", coll, "POINT", (x, y, z + 3.4), energy, (1.0, 0.68, 0.38),
                                       shadow_soft_size=0.12)


def row_house(coll, name, x, y, facing, width=6.0, height=9.5, brick="MAT_Ex_Brick", door_x=1.6, lit=()):
    """Philadelphia-style brick row house: shuttered windows, white marble steps with iron rails,
    cornice, slate roof, chimney. facing=+1 if the front faces -Y (house side), -1 if it faces +Y."""
    s = facing          # front is at y; the house body extends away from the street
    su.box(f"{name}_Front", coll, bpy.data.materials[brick], (width, 0.5, height), (x, y + s * 0.25, height / 2), bevel=0)
    trim, shutter = M("MAT_Trim_White"), bpy.data.materials["MAT_Ex_Shutter"]
    glass = bpy.data.materials["MAT_Ex_Window"]
    for floor, wz in enumerate((1.9, 4.9, 7.6)):
        xs = (-1.6, 0.0) if floor == 0 else (-1.9, 0.0, 1.9)
        for wx in xs:
            wx = x + wx * s
            key = (floor, round(wx - x, 1))
            mat = bpy.data.materials["MAT_Ex_Window_Lit"] if key in lit else glass
            su.box(f"{name}_Win_{floor}_{wx:.1f}", coll, mat, (1.0, 0.06, 1.55 - 0.15 * floor), (wx, y - s * 0.01, wz), bevel=0)
            su.box(f"{name}_Sill_{floor}_{wx:.1f}", coll, trim, (1.2, 0.14, 0.08), (wx, y - s * 0.05, wz - 0.84 + 0.07 * floor), bevel=0.01)
            su.box(f"{name}_Lintel_{floor}_{wx:.1f}", coll, trim, (1.2, 0.1, 0.14), (wx, y - s * 0.03, wz + 0.85 - 0.07 * floor), bevel=0.01)
            h = 1.55 - 0.15 * floor
            for gx in (-0.17, 0.17):     # glazing bars: six-over-six sash windows
                su.box(f"{name}_Bar_{floor}_{wx:.1f}_{gx}", coll, trim, (0.035, 0.03, h), (wx + gx, y - s * 0.05, wz), bevel=0)
            for gz in (-h / 6, h / 6):
                su.box(f"{name}_Rail_{floor}_{wx:.1f}_{gz:.2f}", coll, trim, (1.0, 0.03, 0.035), (wx, y - s * 0.05, wz + gz), bevel=0)
            for sx in (-0.72, 0.72):     # shutters, folded open against the brick
                su.box(f"{name}_Shutter_{floor}_{wx:.1f}_{sx}", coll, shutter, (0.42, 0.05, h - 0.05),
                       (wx + sx, y - s * 0.04, wz), bevel=0.005)
    dx = x + door_x * s
    su.box(f"{name}_Door", coll, bpy.data.materials["MAT_Ex_Door"], (1.0, 0.08, 2.3), (dx, y - s * 0.02, 0.45 + 1.15), bevel=0.01)
    su.box(f"{name}_Door_Frame", coll, trim, (1.3, 0.1, 0.12), (dx, y - s * 0.05, 2.85), bevel=0.01)
    su.box(f"{name}_Fanlight", coll, bpy.data.materials["MAT_Ex_Window"], (0.9, 0.04, 0.35), (dx, y - s * 0.03, 3.05), bevel=0)
    marble = bpy.data.materials["MAT_Ex_Marble"]
    for i in range(3):              # the famous white marble steps
        depth = 0.32 * (3 - i)
        su.box(f"{name}_Step_{i}", coll, marble, (1.5, depth, 0.15), (dx, y - s * depth / 2, 0.15 + 0.15 * i + 0.075), bevel=0.01)
    for side in (-0.82, 0.82):      # iron railings beside the steps
        su.cylinder(f"{name}_Rail_Post_{side}", coll, M("MAT_Metal"), 0.018, 0.95, (dx + side, y - s * 0.95, 0.62), segments=8)
        su.box(f"{name}_Rail_{side}", coll, M("MAT_Metal"), (0.03, 1.0, 0.03), (dx + side, y - s * 0.48, 1.1), (s * 25, 0, 0), bevel=0)
    su.box(f"{name}_Cornice", coll, trim, (width + 0.1, 0.5, 0.35), (x, y - s * 0.05, height - 0.1), bevel=0.02)
    roof = su.box(f"{name}_Roof", coll, bpy.data.materials["MAT_Ex_Slate"], (width + 0.1, 3.6, 0.15),
                  (x, y + s * 1.6, height + 1.0), (-s * 32, 0, 0), bevel=0)
    su.box(f"{name}_Chimney", coll, bpy.data.materials[brick], (0.7, 0.6, 1.8), (x + 2.0 * s, y + s * 2.2, height + 1.9), bevel=0.01)
    su.box(f"{name}_Chimney_Cap", coll, trim, (0.85, 0.75, 0.1), (x + 2.0 * s, y + s * 2.2, height + 2.85), bevel=0.01)
    return dx


def street(coll, lights):
    """The 1843 street outside the house at 4 a.m.: wet cobbles, brick sidewalks with stone curbs,
    red-brick row houses with white marble steps, gas lamps, a bare tree, mist, moon and clouds."""
    from material_library import textured
    x0 = SET_X["exterior"]
    out = {}
    cobble = textured("MAT_Ex_Cobble", "cobblestone_floor_04", 0.5, (0.8, 0.8, 0.82), wet=0.8)
    pave = textured("MAT_Ex_Pavement", "brick_pavement", 0.55, (0.85, 0.75, 0.7), wet=0.4)
    curb = textured("MAT_Ex_Curb", "stone_floor", 0.6, (0.75, 0.75, 0.78), wet=0.3)
    textured("MAT_Ex_Brick", "red_brick", 0.45, (0.85, 0.7, 0.65))
    textured("MAT_Ex_Brick_B", "worn_brick_wall", 0.45, (0.78, 0.62, 0.56))
    textured("MAT_Ex_Slate", "roof_slates_02", 0.5, (0.6, 0.62, 0.68), wet=0.5)
    textured("MAT_Ex_Shutter", "wood_peeling_paint_weathered", 0.8, (0.16, 0.22, 0.18))
    textured("MAT_Ex_Door", "wood_peeling_paint_weathered", 0.8, (0.2, 0.12, 0.08))
    marble = bpy.data.materials.get("MAT_Ex_Marble") or bpy.data.materials.new("MAT_Ex_Marble")
    marble.use_nodes = True
    mb = marble.node_tree.nodes["Principled BSDF"].inputs
    mb["Base Color"].default_value, mb["Roughness"].default_value = (0.78, 0.77, 0.74, 1), 0.3
    for name, colour, emit in (("MAT_Ex_Window", (0.02, 0.025, 0.03), 0), ("MAT_Ex_Window_Lit", (1.0, 0.62, 0.3), 3.5)):
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        w = mat.node_tree.nodes["Principled BSDF"].inputs
        w["Base Color"].default_value, w["Roughness"].default_value = (*colour, 1), 0.05
        w["Emission Color"].default_value, w["Emission Strength"].default_value = (*colour, 1), emit

    su.box("EX_Street", coll, cobble, (60, 8, 0.1), (x0, -7, -0.05), bevel=0)
    for y in (-1.5, -12.5):
        su.box(f"EX_Sidewalk_{y}", coll, pave, (60, 3, 0.15), (x0, y, 0.075), bevel=0)
    for y in (-3.1, -10.9):
        su.box(f"EX_Curb_{y}", coll, curb, (60, 0.25, 0.2), (x0, y, 0.05), bevel=0.01)

    for i, dx in enumerate((-18, -12, -6, 0, 6, 12, 18)):
        brick = "MAT_Ex_Brick" if i % 2 else "MAT_Ex_Brick_B"
        door = row_house(coll, f"EX_House_{i}", x0 + dx, 0.0, 1, height=9.2 + (i % 3) * 0.6, brick=brick)
        if dx == 0:
            out["door"] = (door, -0.1)                          # the old man's door
        row_house(coll, f"EX_Opposite_{i}", x0 + dx, -14.0, -1, height=9.6 - (i % 2) * 0.5, brick=brick,
                  lit={(1, -1.9)} if dx == 0 else ())             # the neighbour who heard the shriek
    lights["ex_window"] = su.light("EX_LIGHT_Neighbour", coll, "POINT", (x0 + 1.9, -15.0, 4.9), 60, (1.0, 0.62, 0.3),
                                   shadow_soft_size=0.3)
    gas_lamp(coll, "EX_Gas_Lamp", (x0 + 4.2, -2.75, 0.15), lights)
    gas_lamp(coll, "EX_Gas_Lamp_Far", (x0 - 15.0, -2.75, 0.15), lights, energy=350)
    gas_lamp(coll, "EX_Gas_Lamp_Opp", (x0 - 6.0, -11.25, 0.15), lights, energy=300)
    su.cylinder("EX_Hitching_Post", coll, M("MAT_Metal"), 0.05, 1.0, (x0 - 2.2, -2.85, 0.65), segments=10)
    ph("Barrel_01", coll, "EX_Rain_Barrel", (x0 - 3.1, -0.45, 0.15), rotation=20)
    ph("shrub_02", coll, "EX_Shrub", (x0 + 3.0, -0.4, 0.15), scale=0.8)
    ph("dry_branches_medium_01", coll, "EX_Branches", (x0 - 7.5, -2.3, 0.15), rotation=40)
    # a bare winter tree on the near sidewalk (Sapling Tree Gen), framing the left of the street
    bpy.ops.curve.tree_add(seed=7, levels=3, bevel=True, showLeaves=False, scale=9.0, scaleV=1.0,
                           baseSize=0.35, ratio=0.018, prune=False)
    tree = bpy.context.active_object
    tree.name = "EX_Bare_Tree"
    tree.location = (x0 - 9.0, -2.4, 0.15)
    bpy.ops.object.convert(target="MESH")
    tree.data.materials.clear()
    tree.data.materials.append(textured("MAT_Ex_Bark", "brown_mud_leaves_01", 1.5, (0.18, 0.15, 0.13)))
    for c in tree.users_collection:
        c.objects.unlink(tree)
    coll.objects.link(tree)
    # a church steeple at the end of the street, half lost in the mist
    su.box("EX_Steeple_Tower", coll, bpy.data.materials["MAT_Ex_Brick"], (3, 3, 18), (x0 - 46, -7, 9), bevel=0)
    bm = bmesh.new()
    su.add_cylinder(bm, 2.2, 9, (0, 0, 0), radius_top=0.05, segments=4)
    su.make_object("EX_Steeple_Spire", coll, bpy.data.materials["MAT_Ex_Slate"], bm, (x0 - 46, -7, 22.5),
                   (0, 0, math.radians(45)), bevel=0)
    lights["ex_moon"] = su.light("EX_LIGHT_Moon", coll, "SUN", (x0, -10, 10), 0.35, (0.55, 0.68, 1.0),
                                 target=(x0 + 6, 4, 0), angle=math.radians(3))
    haze("EX_Mist_Low", coll, (x0, -7, 1.2), (70, 30, 2.4), 0.035)   # ground mist
    haze("EX_Mist_High", coll, (x0, -7, 9), (110, 60, 14), 0.006)    # distance haze, lamp halos
    return out


def eye_macro(coll, lights):
    """Close-up rig of the old man's 'vulture eye', built 10x real size (like a macro miniature):
    eyeball, milky pale-blue iris under a cataract film, lids with lashes, skin around it."""
    x, k, z = SET_X["eye"], 10.0, EYE_Z
    out = {}
    su.sphere("EYE_Face", coll, M("MAT_Skin_Pale"), 0.09 * k, (x, 0.07 * k, z), scale=(1.4, 1.0, 1.0), segments=64)
    su.sphere("EYE_Brow_Ridge", coll, M("MAT_Skin_Pale"), 0.03 * k, (x, -0.004 * k, z + 0.026 * k),
              scale=(1.6, 0.8, 0.55), segments=32)
    bm = bmesh.new()
    su.add_sphere(bm, 0.0125 * k, segments=48, material_index=0)
    su.add_sphere(bm, 1.0, (0, -0.0105 * k, 0), scale=(0.0065 * k, 0.0035 * k, 0.0065 * k), segments=32,
                  material_index=1)
    su.add_sphere(bm, 1.0, (0, -0.0118 * k, 0), scale=(0.0022 * k, 0.0015 * k, 0.0022 * k), segments=16,
                  material_index=2)
    out["eyeball"] = su.make_object("EYE_Ball", coll, [M("MAT_Eye_White"), M("MAT_Vulture_Eye"),
                                                       M("MAT_Plastic_Black")], bm, (x, -0.012 * k, z), smooth_angle=180)
    su.sphere("EYE_Film", coll, M("MAT_Eye_Film"), 0.0129 * k, (x, -0.012 * k, z), segments=48)
    lids = []
    for name, sign in (("Upper", 1), ("Lower", -1)):
        bm = bmesh.new()
        verts = su.add_sphere(bm, 0.0136 * k, segments=48)
        bmesh.ops.delete(bm, geom=[v for v in verts if v.co.z * sign < 0.0005 * k], context="VERTS")
        if sign > 0:
            for i in range(22):
                a = math.radians(-65 + i * 6.2)
                base = Vector((0.0136 * k * math.sin(a), -0.0136 * k * math.cos(a), 0.0008 * k))
                su.add_rod(bm, base, base + Vector((0.0, -0.0035 * k, 0.0035 * k)), 0.00016 * k, segments=5,
                           material_index=1)
        lid = su.make_object(f"EYE_Lid_{name}", coll, [M("MAT_Skin_Pale"), M("MAT_Hair_White")], bm,
                             (x, -0.012 * k, z), smooth_angle=180)
        su.add_modifier(lid, "SOLIDIFY", "Thickness", thickness=0.0015 * k)
        lids.append(lid)
    out["lid_upper"], out["lid_lower"] = lids
    out["lid_lower"].rotation_euler.x = math.radians(60)
    lights["eye_key"] = su.light("EYE_LIGHT_Key", coll, "AREA", (x + 0.8, -1.2, z + 0.6), 0, (0.85, 0.9, 1.0),
                                 target=(x, -0.12, z), shape="DISK", size=0.8)
    lights["eye_rim"] = su.light("EYE_LIGHT_Rim", coll, "AREA", (x - 0.6, 0.2, z + 0.5), 0, (1.0, 0.75, 0.45),
                                 target=(x, -0.12, z), shape="DISK", size=0.5)
    return out


def watch_macro(coll, lights):
    x = SET_X["watch"]
    out = {}
    hand = su.sphere("WA_Palm", coll, M("MAT_Skin"), 1.0, (x, 0, 0), scale=(0.05, 0.06, 0.018))
    for i, dx in enumerate((-0.03, -0.01, 0.01, 0.03)):
        bm = bmesh.new()
        su.add_rod(bm, (x + dx, 0.05, 0.0), (x + dx * 1.2, 0.11, 0.012), 0.0085, segments=10)
        su.add_sphere(bm, 0.0085, (x + dx * 1.2, 0.11, 0.012), segments=10)
        su.make_object(f"WA_Finger_{i}", coll, M("MAT_Skin"), bm, smooth_angle=180)
    bm = bmesh.new()
    su.add_cylinder(bm, 0.026, 0.009, (0, 0, 0), segments=48)
    su.add_cylinder(bm, 0.004, 0.006, (0, 0.029, 0), rotation=(90, 0, 0), segments=12)
    su.add_torus(bm, 0.006, 0.0012, (0, 0.036, 0), rotation=(0, 90, 0), segments=12, ring=6)
    case = su.make_object("WA_Case", coll, M("MAT_Gold"), bm, (x, 0.005, 0.022), bevel=0.001)
    face = su.cylinder("WA_Face", coll, M("MAT_Clock_Face"), 0.023, 0.001, (0, 0, 0.005))
    face.parent = case
    bm = bmesh.new()
    su.add_box(bm, (0.0012, 0.019, 0.0006), (0, 0.0085, 0))
    out["minute"] = su.make_object("WA_Minute_Hand", coll, M("MAT_Plastic_Black"), bm, (x, 0.005, 0.0282))
    bm = bmesh.new()
    su.add_box(bm, (0.0016, 0.012, 0.0006), (0, 0.0055, 0))
    out["hour"] = su.make_object("WA_Hour_Hand", coll, M("MAT_Plastic_Black"), bm, (x, 0.005, 0.0284))
    out["hour"].rotation_euler.z = math.radians(-2)
    lights["watch_moon"] = su.light("WA_LIGHT_Moon", coll, "AREA", (x + 0.15, -0.1, 0.25), 0, (0.6, 0.72, 1.0),
                                    target=(x, 0, 0), shape="DISK", size=0.15)
    return out


def beetle_macro(coll, lights):
    x = SET_X["beetle"]
    out = {}
    bm = bmesh.new()
    for i in range(6):
        su.add_box(bm, (0.6, 0.02, 0.11), (0, 0, -0.25 + i * 0.112))
    su.make_object("BE_Wall_Timber", coll, M("MAT_Floor_Old"), bm, (x, 0.02, 0), bevel=0.003)
    bm = bmesh.new()
    su.add_sphere(bm, 1.0, (0, 0, 0), scale=(0.0035, 0.0025, 0.0055), segments=16)
    for side in (-1, 1):
        for k in range(3):
            su.add_rod(bm, (side * 0.002, 0, 0.003 - k * 0.003), (side * 0.0055, -0.001, 0.004 - k * 0.0035),
                       0.00035, segments=4)
    body = su.make_object("BE_Beetle", coll, M("MAT_Beetle"), bm, (x, 0.008, 0.01), smooth_angle=180)
    out["head"] = su.sphere("BE_Beetle_Head", coll, M("MAT_Beetle"), 0.0022, (x, 0.007, 0.0165))
    del body
    lights["beetle_moon"] = su.light("BE_LIGHT_Moon", coll, "AREA", (x + 0.12, -0.12, 0.12), 0, (0.6, 0.72, 1.0),
                                     target=(x, 0, 0), shape="DISK", size=0.05)
    return out


def text(name, coll, body, location, size, align="CENTER"):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body, curve.size, curve.align_x, curve.extrude = body, size, align, 0.0
    obj = bpy.data.objects.new(name, curve)
    coll.objects.link(obj)
    obj.location = location
    obj.rotation_euler.x = math.radians(90)
    curve.materials.append(M("MAT_Title_Text"))
    return obj


def title_stage(coll, lights):
    x = SET_X["title"]
    out = {"title": text("TXT_Title", coll, "THE TELL-TALE HEART", (x, 0, 0.05), 0.3),
           "subtitle": text("TXT_Subtitle", coll, "after Edgar Allan Poe", (x, 0, -0.45), 0.18)}
    credits = ("THE TELL-TALE HEART\n\nBased on the story by Edgar Allan Poe (1843)\n\n"
               "An FLV — Future Life Videos production\n\n"
               "Voices: Piper TTS — john, joe, bryce, norman (public domain / CC0)\n"
               "LibriTTS voice (CC BY 4.0, Zen et al. 2019)\n"
               "Props: Poly Haven (CC0)    Made with Blender")
    out["credits"] = text("TXT_Credits", coll, credits, (x, 0, 1.1 - 20), 0.14)
    return out
