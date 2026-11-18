"""
FLV asset library: procedural furniture, props, walls, doors and windows.

Every builder works the same way:
  * parts are modelled around a local origin on the floor, front facing -Y;
  * the first part is the root and the rest are parented to it, so selecting the
    root (e.g. BED_Frame) and moving it in Blender moves the whole piece;
  * `location` puts that origin in the room and `rotation` turns it (degrees).

Each part stays a separate object with its own material, so it can still be
selected and changed on its own. Future AI-generated models can replace any
builder: import the model, name it the same way, put it in the same collection.
"""
import math

import bmesh
from mathutils import Euler, Matrix, Vector

import scene_utils as su
from material_library import material as M


def assemble(parts, location, rotation=0.0):
    """Parent parts[1:] to parts[0], then place the group in the room."""
    root = parts[0]
    for part in parts[1:]:
        if part.parent is None:
            part.location = Vector(part.location) - Vector(root.location)
            part.parent = root
    turn = Matrix.Rotation(math.radians(rotation), 3, "Z")
    root.location = Vector(location) + turn @ Vector(root.location)
    root.rotation_euler.z += math.radians(rotation)
    return root


def corners(hx, hy):
    return [(-hx, -hy), (hx, -hy), (-hx, hy), (hx, hy)]


def legs(name, coll, material, positions, height, radius, taper=0.7):
    """Tapered legs (thinner at the floor), all in one object."""
    bm = bmesh.new()
    for x, y in positions:
        su.add_cylinder(bm, radius * taper, height, (x, y, height / 2), radius_top=radius, segments=12)
    return su.make_object(name, coll, material, bm)


def strips(name, coll, material, width, height, count, gap, location, depth=0.03, bevel=0.008):
    """Upright boards side by side (panelling, slats, tufted headboard).
    `location` is the bottom centre of their back face; local +Y is the wall."""
    w = (width - gap * (count - 1)) / count
    bm = bmesh.new()
    for i in range(count):
        su.add_box(bm, (w, depth, height), (-width / 2 + w / 2 + i * (w + gap), -depth / 2, height / 2))
    return su.make_object(name, coll, material, bm, location, bevel=bevel)


# ------------------------------------------------------------------ architecture

def wall(name, coll, material, length, height, thickness, location, rotation=0, opening=None):
    """Straight wall running along local +X from `location`; local +Y is outside.
    opening = (x_start, x_end, z_bottom, z_top) leaves a rectangular hole."""
    pieces = [(0, length, 0, height)]
    if opening:
        x0, x1, z0, z1 = opening
        pieces = [(0, x0, 0, height), (x1, length, 0, height), (x0, x1, 0, z0), (x0, x1, z1, height)]
    bm = bmesh.new()
    for a, b, lo, hi in pieces:
        if b - a > 1e-4 and hi - lo > 1e-4:
            su.add_box(bm, (b - a, thickness, hi - lo), ((a + b) / 2, thickness / 2, (lo + hi) / 2))
    return su.make_object(name, coll, material, bm, location, (0, 0, rotation))


def plank_floor(name, coll, materials, size_x, size_y, plank_width=0.18, plank_length=1.5,
                thickness=0.05):
    """Floor of staggered planks; top surface at z=0, centred on the origin."""
    rows = round(size_y / plank_width)
    pw = size_y / rows
    bm = bmesh.new()
    for r in range(rows):
        y = -size_y / 2 + pw * (r + 0.5)
        x = -size_x / 2 - (r * 0.37 % 1.0) * plank_length      # stagger the joints
        i = 0
        while x < size_x / 2:
            x0, x1 = max(x, -size_x / 2), min(x + plank_length, size_x / 2)
            if x1 - x0 > 0.05:
                su.add_box(bm, (x1 - x0 - 0.004, pw - 0.004, thickness),
                           ((x0 + x1) / 2, y, -thickness / 2), material_index=(r + i) % len(materials))
            x += plank_length
            i += 1
    return su.make_object(name, coll, materials, bm, bevel=0.004)


def door(coll, location, rotation=0, width=0.9, height=2.1, prefix="DOOR"):
    """Panel door on a wall. `location` = floor centre of the doorway on the room-side
    wall face; local +Y points into the wall. DOOR_Panel pivots on its hinge:
    rotate it around Z to open it onto a dark doorway."""
    hw = width / 2
    bm = bmesh.new()
    for size, center in (((0.08, 0.025, height + 0.08), (-hw - 0.04, -0.0125, (height + 0.08) / 2)),
                         ((0.08, 0.025, height + 0.08), (hw + 0.04, -0.0125, (height + 0.08) / 2)),
                         ((width + 0.16, 0.025, 0.08), (0, -0.0125, height + 0.04))):
        su.add_box(bm, size, center)
    frame = su.make_object(f"{prefix}_Frame", coll, M("MAT_Trim_White"), bm, bevel=0.005)
    doorway = su.box(f"{prefix}_Doorway_Shadow", coll, M("MAT_Base_Dark"), (width, 0.004, height),
                     (0, -0.002, height / 2), bevel=0)

    bm = bmesh.new()                       # slab + two raised panels, origin on the hinge
    su.add_box(bm, (width - 0.01, 0.04, height - 0.01), (hw, 0, height / 2))
    for z in (height * 0.28, height * 0.71):
        su.add_box(bm, (width - 0.24, 0.012, height * 0.36), (hw, -0.024, z))
    panel = su.make_object(f"{prefix}_Panel", coll, M("MAT_Furniture_Paint"), bm, (-hw, -0.025, 0),
                           bevel=0.006)

    bm = bmesh.new()
    su.add_cylinder(bm, 0.028, 0.012, rotation=(90, 0, 0))
    su.add_cylinder(bm, 0.01, 0.03, (0, -0.015, 0), rotation=(90, 0, 0), segments=12)
    su.add_box(bm, (0.13, 0.02, 0.02), (-0.05, -0.03, 0))
    handle = su.make_object(f"{prefix}_Handle", coll, M("MAT_Brass"), bm, (width - 0.08, -0.026, 1.0),
                            bevel=0.003)
    handle.parent = panel
    return assemble([frame, doorway, panel], location, rotation)


def window(coll, location, width, height, wall_thickness, rotation=0, prefix="WINDOW"):
    """Window for a wall opening. `location` = centre of the opening on the room-side
    wall face; local +Y points out of the room."""
    hw, hh, t, bar = width / 2, height / 2, wall_thickness, 0.07
    bm = bmesh.new()
    for size, center in (((width + 2 * bar, 0.03, bar), (0, -0.015, hh + bar / 2)),   # casing
                         ((bar, 0.03, height), (-hw - bar / 2, -0.015, 0)),
                         ((bar, 0.03, height), (hw + bar / 2, -0.015, 0)),
                         ((width, t, 0.03), (0, t / 2, hh - 0.015)),                   # jambs
                         ((width, t, 0.03), (0, t / 2, -hh + 0.015)),
                         ((0.03, t, height), (-hw + 0.015, t / 2, 0)),
                         ((0.03, t, height), (hw - 0.015, t / 2, 0))):
        su.add_box(bm, size, center)
    frame = su.make_object(f"{prefix}_Frame", coll, M("MAT_Trim_White"), bm, bevel=0.005)
    sill = su.box(f"{prefix}_Sill", coll, M("MAT_Trim_White"), (width + 2 * bar + 0.06, 0.16, 0.04),
                  (0, -0.05, -hh - 0.02), bevel=0.008)
    bm = bmesh.new()
    su.add_box(bm, (0.04, 0.045, height - 0.06), (0, t * 0.6, 0))
    su.add_box(bm, (width - 0.06, 0.045, 0.04), (0, t * 0.6, hh * 0.3))
    divider = su.make_object(f"{prefix}_Divider", coll, M("MAT_Trim_White"), bm, bevel=0.004)
    glass = su.box(f"{prefix}_Glass", coll, M("MAT_Window_Glass"), (width - 0.06, 0.008, height - 0.06),
                   (0, t * 0.6, 0), bevel=0)
    glass.visible_shadow = False           # let the moonlight through
    return assemble([frame, sill, divider, glass], location, rotation)


def curtains(coll, location, width, height, panel_width=0.42, rotation=0, prefix="WINDOW_Curtain"):
    """Rod with two pleated curtains. `location` = centre of the rod; local +Y = wall."""
    bm = bmesh.new()
    su.add_cylinder(bm, 0.012, width, rotation=(0, 90, 0), segments=16)
    for side in (-1, 1):
        su.add_sphere(bm, 0.03, (side * width / 2, 0, 0), segments=12)
    rod = su.make_object(f"{prefix}_Rod", coll, M("MAT_Metal"), bm)
    x = width / 2 - panel_width / 2 - 0.04
    left = su.curtain(f"{prefix}_Left", coll, M("MAT_Curtain"), panel_width, height, (-x, 0, -0.03))
    right = su.curtain(f"{prefix}_Right", coll, M("MAT_Curtain"), panel_width, height, (x, 0, -0.03))
    return assemble([rod, left, right], location, rotation)


def wall_art(coll, location, width=0.9, height=0.6, rotation=0, prefix="DECOR_Art"):
    """Framed moonlit-landscape painting. `location` = its centre on the wall face."""
    b, hw, hh = 0.045, width / 2, height / 2
    bm = bmesh.new()
    for size, center in (((width, 0.035, b), (0, -0.0175, hh - b / 2)),
                         ((width, 0.035, b), (0, -0.0175, -hh + b / 2)),
                         ((b, 0.035, height), (-hw + b / 2, -0.0175, 0)),
                         ((b, 0.035, height), (hw - b / 2, -0.0175, 0))):
        su.add_box(bm, size, center)
    frame = su.make_object(f"{prefix}_Frame", coll, M("MAT_Bed_Wood"), bm, bevel=0.006)
    iw, ih = width - 2 * b, height - 2 * b
    canvas = su.box(f"{prefix}_Canvas", coll, M("MAT_Art_Canvas"), (iw + 0.01, 0.01, ih + 0.01),
                    (0, -0.008, 0), bevel=0)
    moon = su.cylinder(f"{prefix}_Moon", coll, M("MAT_Art_Moon"), 0.055, 0.004,
                       (iw * 0.22, -0.015, ih * 0.18), rotation=(90, 0, 0))
    n = 24
    outline = [(-iw / 2, -ih / 2), (iw / 2, -ih / 2)] + [
        (iw / 2 - iw * i / n, -ih / 2 + ih * (0.3 + 0.1 * math.sin(i * 0.7) + 0.05 * math.sin(i * 2.1)))
        for i in range(n + 1)]
    bm = bmesh.new()
    bm.faces.new([bm.verts.new((x, 0, z)) for x, z in outline])
    hills = su.make_object(f"{prefix}_Hills", coll, M("MAT_Art_Hills"), bm, (0, -0.015, 0), flat=True)
    return assemble([frame, canvas, moon, hills], location, rotation)


# ---------------------------------------------------------------------- furniture

def bed(coll, location, rotation=0, width=1.8, length=2.2, prefix="BED"):
    """Double bed with tufted headboard; local +Y is the headboard end."""
    hw, hl, top = width / 2, length / 2, 0.62           # top = mattress surface
    frame = su.box(f"{prefix}_Frame", coll, M("MAT_Bed_Wood"), (width, length, 0.22), (0, 0, 0.27),
                   bevel=0.02)
    bed_legs = legs(f"{prefix}_Legs", coll, M("MAT_Bed_Wood"), corners(hw - 0.08, hl - 0.08), 0.16, 0.035)
    headboard = strips(f"{prefix}_Headboard", coll, M("MAT_Headboard_Fabric"), width + 0.16, 1.12, 7,
                       0.012, (0, hl + 0.13, 0.06), depth=0.12, bevel=0.035)
    mattress = su.box(f"{prefix}_Mattress", coll, M("MAT_Mattress"), (width - 0.12, length - 0.14, 0.24),
                      (0, -0.01, 0.50), bevel=0.06)
    sheet = su.drape(f"{prefix}_Sheet", coll, M("MAT_Bedsheet"), width - 0.06, length - 0.10, 0.2,
                     (0, -0.01, top + 0.012), sides=("left", "right", "front", "back"),
                     flare=0.01, wrinkles=0.004)
    cover = length * 0.68
    blanket_y = -hl - 0.04 + cover / 2
    blanket = su.drape(f"{prefix}_Blanket", coll, M("MAT_Blanket"), width + 0.14, cover, 0.42,
                       (0, blanket_y, top + 0.05), flare=0.07, wrinkles=0.03)
    fold = su.drape(f"{prefix}_Blanket_Fold", coll, M("MAT_Bedsheet"), width + 0.18, 0.3, 0.12,
                    (0, blanket_y + cover / 2 - 0.16, top + 0.085), sides=("left", "right"),
                    flare=0.02, wrinkles=0.006, thickness=0.03)
    throw = su.drape(f"{prefix}_Throw", coll, M("MAT_Fabric_Charcoal"), width + 0.22, 0.5, 0.4,
                     (0, -hl + 0.4, top + 0.09), sides=("left", "right"), flare=0.05, wrinkles=0.015)
    parts = [frame, bed_legs, headboard, mattress, sheet, blanket, fold, throw]
    for side, name in ((-1, "Left"), (1, "Right")):
        parts.append(su.pillow(f"{prefix}_Pillow_{name}", coll, M("MAT_Pillow"), (0.72, 0.5, 0.2),
                               (side * 0.42, hl - 0.19, top + 0.27), rotation=(62, 0, 0)))
        parts.append(su.pillow(f"{prefix}_Cushion_{name}", coll, M("MAT_Fabric_Mustard"),
                               (0.45, 0.42, 0.16), (side * 0.33, hl - 0.53, top + 0.23),
                               rotation=(68, 0, -side * 8)))
    return assemble(parts, location, rotation)


def nightstand(coll, location, rotation=0, prefix="TABLE_Bedside"):
    """Two-drawer bedside table; top surface at z = 0.62."""
    w, d = 0.5, 0.42
    body = su.box(prefix, coll, M("MAT_Furniture_Wood"), (w, d, 0.44), (0, 0, 0.36), bevel=0.012)
    top = su.box(f"{prefix}_Top", coll, M("MAT_Furniture_Wood"), (w + 0.04, d + 0.03, 0.04),
                 (0, 0, 0.60), bevel=0.012)
    stand_legs = legs(f"{prefix}_Legs", coll, M("MAT_Furniture_Wood"), corners(w / 2 - 0.05, d / 2 - 0.05),
                      0.14, 0.022)
    parts = [body, top, stand_legs]
    for label, z in (("Top", 0.47), ("Bottom", 0.25)):
        drawer = su.box(f"{prefix}_Drawer_{label}", coll, M("MAT_Furniture_Paint"), (w - 0.05, 0.02, 0.19),
                        (0, -d / 2 - 0.008, z), bevel=0.006)
        knob = su.sphere(f"{prefix}_Knob_{label}", coll, M("MAT_Brass"), 0.018, (0, -0.02, 0), segments=16)
        knob.parent = drawer               # pull a drawer out and its knob follows
        parts.append(drawer)
    return assemble(parts, location, rotation)


def table_lamp(coll, light_coll, location, rotation=0, prefix="LAMP", energy=40):
    """Ceramic table lamp: glowing shade with a warm point light inside."""
    base = su.cylinder(f"{prefix}_Base", coll, M("MAT_Brass"), 0.08, 0.025, (0, 0, 0.0125), bevel=0.005)
    body = su.sphere(f"{prefix}_Body", coll, M("MAT_Ceramic"), 0.1, (0, 0, 0.145), scale=(0.9, 0.9, 1.2))
    stem = su.cylinder(f"{prefix}_Stem", coll, M("MAT_Brass"), 0.01, 0.1, (0, 0, 0.3), segments=12)
    shade = su.cylinder(f"{prefix}_Shade", coll, M("MAT_Lamp_Shade"), 0.17, 0.2, (0, 0, 0.38),
                        radius_top=0.12, caps=False, segments=48)
    su.add_modifier(shade, "SOLIDIFY", "Shade Thickness", thickness=0.004)
    bulb = su.sphere(f"{prefix}_Bulb", coll, M("MAT_Bulb"), 0.03, (0, 0, 0.34), segments=16)
    bulb.visible_shadow = False
    glow = su.light(f"LIGHT_{prefix}_Bulb", light_coll, "POINT", (0, 0, 0.36), energy,
                    (1.0, 0.62, 0.32), shadow_soft_size=0.04)
    return assemble([base, body, stem, shade, bulb, glow], location, rotation)


def pendant_lamp(coll, light_coll, location, drop=1.1, prefix="PENDANT", energy=20):
    """Hanging lamp. `location` = the ceiling point it hangs from."""
    canopy = su.cylinder(f"{prefix}_Canopy", coll, M("MAT_Brass"), 0.06, 0.03, (0, 0, -0.015), bevel=0.004)
    cord = su.cylinder(f"{prefix}_Cord", coll, M("MAT_Metal"), 0.004, drop, (0, 0, -drop / 2), segments=8)
    shade = su.cylinder(f"{prefix}_Shade", coll, M("MAT_Brass"), 0.15, 0.2, (0, 0, -drop - 0.08),
                        radius_top=0.03, caps=False, segments=48)
    su.add_modifier(shade, "SOLIDIFY", "Shade Thickness", thickness=0.005)
    bulb = su.sphere(f"{prefix}_Bulb", coll, M("MAT_Bulb"), 0.035, (0, 0, -drop - 0.15), segments=16)
    bulb.visible_shadow = False
    glow = su.light(f"LIGHT_{prefix}_Bulb", light_coll, "POINT", (0, 0, -drop - 0.15), energy,
                    (1.0, 0.65, 0.35), shadow_soft_size=0.03)
    return assemble([canopy, cord, shade, bulb, glow], location)


def wardrobe(coll, location, rotation=0, width=1.95, depth=0.62, height=2.35, doors=3, prefix="WARDROBE"):
    """Sliding-door wardrobe; the middle door carries a full-length mirror."""
    body = su.box(f"{prefix}_Body", coll, M("MAT_Furniture_Wood"), (width, depth - 0.05, height - 0.08),
                  (0, 0.025, 0.08 + (height - 0.08) / 2), bevel=0.01)
    plinth = su.box(f"{prefix}_Plinth", coll, M("MAT_Base_Dark"), (width - 0.06, depth - 0.12, 0.08),
                    (0, 0.04, 0.04), bevel=0.004)
    cornice = su.box(f"{prefix}_Cornice", coll, M("MAT_Furniture_Wood"), (width + 0.04, depth + 0.02, 0.05),
                     (0, 0.01, height + 0.025), bevel=0.008)
    parts = [body, plinth, cornice]
    door_w, door_h = width / doors + 0.02, height - 0.16
    for i in range(doors):
        x = -width / 2 + width / doors * (i + 0.5)
        y = -depth / 2 + (0.0085 if i % 2 else 0.0355)     # doors alternate between two tracks
        panel = su.box(f"{prefix}_Door_{i + 1}", coll, M("MAT_Furniture_Paint"), (door_w, 0.025, door_h),
                       (x, y, 0.1 + door_h / 2), bevel=0.008)
        side = 1 if i < doors / 2 else -1
        handle = su.box(f"{prefix}_Handle_{i + 1}", coll, M("MAT_Brass"), (0.02, 0.02, 0.45),
                        (side * (door_w / 2 - 0.06), -0.022, 0), bevel=0.004)
        handle.parent = panel
        if i == doors // 2:
            mirror = su.box(f"{prefix}_Mirror", coll, M("MAT_Mirror"), (door_w - 0.2, 0.006, door_h - 0.3),
                            (0, -0.016, 0), bevel=0.002)
            mirror.parent = panel
        parts.append(panel)
    return assemble(parts, location, rotation)


def garment(name, coll, material, length, location):
    """Shirt or dress on a wooden hanger; `location` = where the hook meets the rail."""
    bm = bmesh.new()
    for v in su.add_box(bm, (0.05, 0.42, length), (0, 0, -0.04 - length / 2)):
        if v.co.z > -0.05:
            v.co.y *= 0.55                 # sloping shoulders
    su.add_cylinder(bm, 0.005, 0.05, (0, 0, -0.01), segments=8, material_index=1)
    su.add_cylinder(bm, 0.007, 0.34, (0, 0, -0.045), rotation=(90, 0, 0), segments=8, material_index=1)
    return su.make_object(name, coll, [material, M("MAT_Furniture_Wood")], bm, location, bevel=0.02)


def open_closet(coll, location, rotation=0, width=1.0, depth=0.5, height=2.2, prefix="CLOSET"):
    """Open wardrobe unit: clothes on a rail, shoes and a basket below, folded clothes on top."""
    t, hw = 0.025, width / 2
    bottom, shoe_shelf, top_shelf = 0.08, 0.36, 1.92
    bm = bmesh.new()
    for side in (-1, 1):
        su.add_box(bm, (t, depth, height), (side * (hw - t / 2), 0, height / 2))
    su.add_box(bm, (width, depth, t), (0, 0, height - t / 2))
    for z in (bottom, shoe_shelf, top_shelf):
        su.add_box(bm, (width - 2 * t, depth - 0.02, t), (0, 0.01, z))
    su.add_box(bm, (width - 2 * t, 0.012, height - t), (0, depth / 2 - 0.006, (height - t) / 2),
               material_index=1)
    frame = su.make_object(f"{prefix}_Frame", coll, [M("MAT_Furniture_Wood"), M("MAT_Furniture_Paint")],
                           bm, bevel=0.006)
    rail_z = 1.78
    rail = su.cylinder(f"{prefix}_Rail", coll, M("MAT_Brass"), 0.012, width - 2 * t, (0, 0, rail_z),
                       rotation=(0, 90, 0), segments=16)
    parts = [frame, rail]

    looks = (("MAT_Fabric_Sage", 0.78), ("MAT_Fabric_Rose", 0.95), ("MAT_Fabric_Navy", 0.66),
             ("MAT_Fabric_Cream", 0.9), ("MAT_Fabric_Mustard", 0.72), ("MAT_Fabric_Charcoal", 0.86))
    step = (width - 2 * t - 0.1) / (len(looks) - 1)
    for i, (mat, length) in enumerate(looks):
        parts.append(garment(f"{prefix}_Garment_{i + 1}", coll, M(mat), length,
                             (-hw + t + 0.05 + i * step, 0, rail_z)))

    for i, mat in enumerate(("MAT_Leather", "MAT_Fabric_Cream", "MAT_Fabric_Charcoal")):
        bm = bmesh.new()
        for dx in (-0.055, 0.055):
            su.add_box(bm, (0.09, 0.26, 0.08), (dx, 0, 0))
        parts.append(su.make_object(f"PROP_Shoes_{i + 1}", coll, M(mat), bm,
                                    (-hw + t + 0.16 + i * 0.29, -0.03, bottom + t / 2 + 0.04), bevel=0.03))
    parts.append(su.box(f"{prefix}_Basket", coll, M("MAT_Basket"), (0.42, 0.34, 0.22),
                        (0.18, -0.02, shoe_shelf + t / 2 + 0.11), bevel=0.02))

    for x, mats in ((-0.2, ("MAT_Fabric_Sage", "MAT_Fabric_Cream", "MAT_Fabric_Navy")),
                    (0.2, ("MAT_Fabric_Rose", "MAT_Fabric_Charcoal"))):
        bm = bmesh.new()
        for i in range(len(mats)):
            su.add_box(bm, (0.34, 0.3, 0.055), (0, 0, 0.0275 + i * 0.057), material_index=i)
        name = f"{prefix}_Folded_Clothes_{'Left' if x < 0 else 'Right'}"
        parts.append(su.make_object(name, coll, [M(m) for m in mats], bm,
                                    (x, -0.02, top_shelf + t / 2), bevel=0.02))
    return assemble(parts, location, rotation)


def desk(coll, location, rotation=0, width=0.9, depth=0.55, height=0.75, prefix="DESK"):
    top = su.box(f"{prefix}_Top", coll, M("MAT_Furniture_Wood"), (width, depth, 0.035),
                 (0, 0, height - 0.0175), bevel=0.008)
    drawer = su.box(f"{prefix}_Drawer", coll, M("MAT_Furniture_Paint"), (width - 0.14, depth - 0.1, 0.1),
                    (0, 0.02, height - 0.085), bevel=0.006)
    desk_legs = legs(f"{prefix}_Legs", coll, M("MAT_Furniture_Wood"), corners(width / 2 - 0.05, depth / 2 - 0.05),
                     height - 0.035, 0.024)
    return assemble([top, drawer, desk_legs], location, rotation)


def chair(coll, location, rotation=0, prefix="CHAIR"):
    """Small wooden chair with a seat cushion; a sitter faces local -Y."""
    seat = su.box(f"{prefix}_Seat", coll, M("MAT_Furniture_Wood"), (0.44, 0.42, 0.04), (0, 0, 0.45),
                  bevel=0.012)
    cushion = su.pillow(f"{prefix}_Cushion", coll, M("MAT_Fabric_Mustard"), (0.4, 0.38, 0.06),
                        (0, -0.01, 0.495), puff=0.35)
    chair_legs = legs(f"{prefix}_Legs", coll, M("MAT_Furniture_Wood"), corners(0.18, 0.17), 0.43, 0.022)
    bm = bmesh.new()
    for side in (-1, 1):
        su.add_cylinder(bm, 0.018, 0.42, (side * 0.18, 0.17, 0.66), segments=12)
    posts = su.make_object(f"{prefix}_Back_Posts", coll, M("MAT_Furniture_Wood"), bm)
    back = su.box(f"{prefix}_Backrest", coll, M("MAT_Furniture_Wood"), (0.42, 0.035, 0.16), (0, 0.18, 0.8),
                  rotation=(-6, 0, 0), bevel=0.012)
    return assemble([seat, cushion, chair_legs, posts, back], location, rotation)


def armchair(coll, location, rotation=0, prefix="ARMCHAIR"):
    """Upholstered reading chair; a sitter faces local -Y."""
    fabric = M("MAT_Fabric_Sage")
    base = su.box(f"{prefix}_Base", coll, fabric, (0.78, 0.74, 0.22), (0, 0, 0.26), bevel=0.05)
    seat = su.pillow(f"{prefix}_Seat_Cushion", coll, fabric, (0.6, 0.62, 0.12), (0, -0.04, 0.42), puff=0.25)
    back = su.box(f"{prefix}_Back", coll, fabric, (0.78, 0.16, 0.55), (0, 0.3, 0.62), rotation=(-10, 0, 0),
                  bevel=0.06)
    bm = bmesh.new()
    for side in (-1, 1):
        su.add_box(bm, (0.12, 0.7, 0.24), (side * 0.33, -0.02, 0.48))
    arms = su.make_object(f"{prefix}_Arms", coll, fabric, bm, bevel=0.05)
    chair_legs = legs(f"{prefix}_Legs", coll, M("MAT_Bed_Wood"), corners(0.32, 0.29), 0.15, 0.022)
    cushion = su.pillow(f"{prefix}_Cushion", coll, M("MAT_Fabric_Rose"), (0.38, 0.32, 0.12), (0, 0.11, 0.65),
                        rotation=(72, 0, 8), puff=0.5)
    return assemble([base, seat, back, arms, chair_legs, cushion], location, rotation)


def side_table(coll, location, prefix="SIDE_TABLE"):
    """Round pedestal table; top surface at z = 0.57."""
    top = su.cylinder(f"{prefix}_Top", coll, M("MAT_Furniture_Wood"), 0.22, 0.03, (0, 0, 0.555),
                      segments=48, bevel=0.008)
    stem = su.cylinder(f"{prefix}_Stem", coll, M("MAT_Brass"), 0.022, 0.52, (0, 0, 0.28), segments=16)
    foot = su.cylinder(f"{prefix}_Foot", coll, M("MAT_Brass"), 0.14, 0.025, (0, 0, 0.0125), segments=48,
                       bevel=0.006)
    return assemble([top, stem, foot], location)


def tv_stand(coll, location, rotation=0, width=1.4, prefix="TV"):
    """Low sideboard with a flat TV on top; both face local -Y."""
    body = su.box(f"{prefix}_Stand", coll, M("MAT_Furniture_Wood"), (width, 0.4, 0.38), (0, 0, 0.31),
                  bevel=0.012)
    stand_legs = legs(f"{prefix}_Stand_Legs", coll, M("MAT_Furniture_Wood"), corners(width / 2 - 0.06, 0.14),
                      0.12, 0.022)
    bm = bmesh.new()
    for side in (-1, 1):
        su.add_box(bm, (width / 2 - 0.04, 0.02, 0.32), (side * width / 4, -0.205, 0.31))
    doors = su.make_object(f"{prefix}_Stand_Doors", coll, M("MAT_Furniture_Paint"), bm, bevel=0.006)
    bm = bmesh.new()
    su.add_box(bm, (0.32, 0.2, 0.02), (0, 0.02, 0.51))
    su.add_box(bm, (0.06, 0.03, 0.12), (0, 0.04, 0.58))
    foot = su.make_object(f"{prefix}_Foot", coll, M("MAT_Plastic_Black"), bm, bevel=0.005)
    screen = su.box(f"{prefix}_Screen", coll, M("MAT_Plastic_Black"), (1.1, 0.04, 0.64), (0, 0.02, 0.92),
                    bevel=0.006)
    display = su.box(f"{prefix}_Display", coll, M("MAT_Screen_Off"), (1.06, 0.004, 0.6), (0, -0.021, 0),
                     bevel=0)
    display.parent = screen
    return assemble([body, stand_legs, doors, foot, screen], location, rotation)


def rug(coll, location, size, rotation=0, prefix="RUG"):
    sx, sy = size
    border = su.box(prefix, coll, M("MAT_Rug_Border"), (sx, sy, 0.012), (0, 0, 0.006), bevel=0.004)
    inner = su.box(f"{prefix}_Pattern", coll, M("MAT_Rug"), (sx - 0.24, sy - 0.24, 0.006), (0, 0, 0.014),
                   bevel=0.002)
    return assemble([border, inner], location, rotation)


def plant(coll, location, prefix="PLANT"):
    """Potted indoor tree with low-poly foliage."""
    pot = su.cylinder(f"{prefix}_Pot", coll, M("MAT_Terracotta"), 0.13, 0.32, (0, 0, 0.16), radius_top=0.17,
                      bevel=0.01)
    soil = su.cylinder(f"{prefix}_Soil", coll, M("MAT_Soil"), 0.155, 0.02, (0, 0, 0.31))
    trunk = su.cylinder(f"{prefix}_Trunk", coll, M("MAT_Bed_Wood"), 0.018, 0.9, (0, 0, 0.75),
                        radius_top=0.01, segments=8)
    bm = bmesh.new()
    for x, y, z, r in ((0, 0, 1.2, 0.22), (0.14, 0.05, 1.0, 0.18), (-0.13, 0.06, 0.95, 0.17),
                       (0.03, -0.12, 0.85, 0.15), (-0.02, 0.03, 1.4, 0.14)):
        verts = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)["verts"]
        bmesh.ops.translate(bm, vec=(x, y, z), verts=verts)
    leaves = su.make_object(f"{prefix}_Leaves", coll, M("MAT_Plant_Leaf"), bm, flat=True)
    return assemble([pot, soil, trunk, leaves], location)


# -------------------------------------------------------------------------- props

def book(name, coll, cover, size, location, rotation=(0, 0, 0)):
    """Hard-cover book lying flat; size = (width, depth, thickness), spine on local +Y."""
    w, d, t = size
    bm = bmesh.new()
    for z in (t / 2 - 0.002, -t / 2 + 0.002):
        su.add_box(bm, (w, d, 0.004), (0, 0, z))
    su.add_box(bm, (w, 0.004, t), (0, d / 2 - 0.002, 0))
    su.add_box(bm, (w - 0.01, d - 0.01, t - 0.008), (0, -0.003, 0), material_index=1)
    return su.make_object(name, coll, [cover, M("MAT_Paper")], bm, location, rotation, bevel=0.0015)


def book_stack(coll, location, books, rotation=0, prefix="PROP_Book"):
    """Pile of books, bottom first: books = [(cover material, (w, d, t)), ...].
    Returns (root, pile height) so something can be placed on top."""
    parts, z = [], 0.0
    for i, (mat, size) in enumerate(books):
        parts.append(book(f"{prefix}_{i + 1}", coll, M(mat), size, (0, 0, z + size[2] / 2),
                          (0, 0, (i * 37) % 17 - 8)))
        z += size[2]
    return assemble(parts, location, rotation), z


def alarm_clock(coll, location, rotation=0, prefix="PROP_Alarm_Clock"):
    """Twin-bell alarm clock. The hands show 3:00."""
    body = su.cylinder(prefix, coll, M("MAT_Clock_Body"), 0.055, 0.045, (0, 0, 0.07), rotation=(90, 0, 0),
                       bevel=0.006)
    face = su.cylinder(f"{prefix}_Face", coll, M("MAT_Clock_Face"), 0.045, 0.004, (0, -0.023, 0.07),
                       rotation=(90, 0, 0))
    bm = bmesh.new()
    su.add_box(bm, (0.003, 0.002, 0.034), (0, 0, 0.017))       # minute hand on 12
    su.add_box(bm, (0.024, 0.002, 0.004), (0.012, 0, 0))       # hour hand on 3
    hands = su.make_object(f"{prefix}_Hands", coll, M("MAT_Plastic_Black"), bm, (0, -0.026, 0.07))
    bm = bmesh.new()
    for side in (-1, 1):
        su.add_sphere(bm, 0.025, (side * 0.035, 0, 0.13), scale=(1, 1, 0.7), segments=16)
        su.add_cylinder(bm, 0.005, 0.03, (side * 0.03, 0, 0.015), segments=8)
    bells = su.make_object(f"{prefix}_Bells", coll, M("MAT_Brass"), bm)
    return assemble([body, face, hands, bells], location, rotation)


def water_glass(coll, location, prefix="PROP_Water_Glass"):
    bm = bmesh.new()
    su.add_cylinder(bm, 0.032, 0.11, (0, 0, 0.055), radius_top=0.036, caps=False, segments=32)
    su.add_cylinder(bm, 0.032, 0.006, (0, 0, 0.003), segments=32)
    glass = su.make_object(prefix, coll, M("MAT_Glass_Clear"), bm, smooth_angle=60)
    su.add_modifier(glass, "SOLIDIFY", "Glass Thickness", thickness=0.003)
    water = su.cylinder(f"{prefix}_Water", coll, M("MAT_Water"), 0.029, 0.07, (0, 0, 0.041),
                        radius_top=0.031, segments=32)
    return assemble([glass, water], location)


def picture_frame(coll, location, rotation=0, prefix="PROP_Picture_Frame"):
    frame = su.box(prefix, coll, M("MAT_Bed_Wood"), (0.16, 0.02, 0.21), (0, 0, 0.105), rotation=(-12, 0, 0),
                   bevel=0.004)
    photo = su.box(f"{prefix}_Photo", coll, M("MAT_Photo"), (0.12, 0.004, 0.16), (0, -0.01, 0), bevel=0)
    photo.parent = frame
    return assemble([frame], location, rotation)


def laptop(coll, location, rotation=0, prefix="PROP_Laptop"):
    """Open laptop with a glowing screen; the user sits on its local -Y side."""
    base = su.box(prefix, coll, M("MAT_Aluminium"), (0.34, 0.24, 0.016), (0, 0, 0.008), bevel=0.004)
    keys = su.box(f"{prefix}_Keyboard", coll, M("MAT_Plastic_Black"), (0.29, 0.1, 0.002), (0, 0.03, 0.017),
                  bevel=0)
    bm = bmesh.new()
    su.add_box(bm, (0.34, 0.008, 0.23), (0, 0, 0.115))          # lid, hinged at its bottom edge
    lid = su.make_object(f"{prefix}_Screen", coll, M("MAT_Aluminium"), bm, (0, 0.118, 0.016),
                         rotation=(-15, 0, 0), bevel=0.003)
    display = su.box(f"{prefix}_Display", coll, M("MAT_Screen_Glow"), (0.31, 0.002, 0.2), (0, -0.005, 0.118),
                     bevel=0)
    display.parent = lid
    return assemble([base, keys, lid], location, rotation)


def vase(coll, location, prefix="PROP_Vase"):
    """Ceramic vase with a few bare branches."""
    body = su.sphere(prefix, coll, M("MAT_Ceramic"), 0.07, (0, 0, 0.09), scale=(1, 1, 1.3))
    bm = bmesh.new()
    for tilt, turn, length in ((8, 0, 0.42), (18, 120, 0.36), (14, 240, 0.4), (26, 60, 0.3)):
        half = Vector((0, 0, length / 2))
        half.rotate(Euler((math.radians(tilt), 0, math.radians(turn))))
        su.add_cylinder(bm, 0.004, length, Vector((0, 0, 0.15)) + half, rotation=(tilt, 0, turn),
                        radius_top=0.0015, segments=6)
    branches = su.make_object(f"{prefix}_Branches", coll, M("MAT_Bed_Wood"), bm)
    return assemble([body, branches], location)
