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
import random

import bmesh
from mathutils import Euler, Matrix, Vector

import scene_utils as su
from material_library import material as M


def assemble(parts, location, rotation=0.0):
    """Parent parts[1:] to parts[0], then place the group in the room."""
    root = parts[0]
    built = root.matrix_basis.copy()
    for part in parts[1:]:
        if part.parent is None:
            part.parent = root
            part.matrix_parent_inverse = built.inverted()      # keep it where it was built (like Ctrl+P)
    turn = Matrix.Rotation(math.radians(rotation), 4, "Z")
    root.matrix_basis = Matrix.Translation(Vector(location)) @ turn @ built
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

def bed(coll, location, rotation=0, width=1.8, length=2.2, cover=0.68, prefix="BED"):
    """Double bed with tufted headboard; local +Y is the headboard end.
    `cover` = how much of the bed the blanket covers (0.8 reaches a sleeper's shoulders)."""
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
    cover = length * cover
    blanket_y = -hl - 0.04 + cover / 2
    blanket = su.drape(f"{prefix}_Blanket", coll, M("MAT_Blanket"), width + 0.14, cover, 0.42,
                       (0, blanket_y, top + 0.05), flare=0.07, wrinkles=0.03)
    fold = su.drape(f"{prefix}_Blanket_Fold", coll, M("MAT_Bedsheet"), width + 0.18, 0.3, 0.12,
                    (0, blanket_y + cover / 2 - 0.16, top + 0.085), sides=("left", "right"),
                    flare=0.02, wrinkles=0.006, thickness=0.03)
    throw = su.drape(f"{prefix}_Throw", coll, M("MAT_Fabric_Charcoal"), width + 0.22, 0.5, 0.4,
                     (0, -hl + 0.4, top + 0.09), sides=("left", "right"), flare=0.05, wrinkles=0.015)
    parts = [frame, bed_legs, headboard, mattress, sheet, blanket, fold, throw]
    pillow_sides = ((0, "Center"),) if width < 1.4 else ((-1, "Left"), (1, "Right"))   # single or double
    for side, name in pillow_sides:
        parts.append(su.pillow(f"{prefix}_Pillow_{name}", coll, M("MAT_Pillow"), (0.72, 0.5, 0.2),
                               (side * width * 0.233, hl - 0.19, top + 0.27), rotation=(62, 0, 0)))
        parts.append(su.pillow(f"{prefix}_Cushion_{name}", coll, M("MAT_Fabric_Mustard"),
                               (0.45, 0.42, 0.16), (side * width * 0.183, hl - 0.53, top + 0.23),
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


def desk(coll, location, rotation=0, width=0.9, depth=0.55, height=0.75, drawer=True, prefix="DESK"):
    """Desk with a slim drawer; drawer=False makes a plain (dining) table."""
    top = su.box(f"{prefix}_Top", coll, M("MAT_Furniture_Wood"), (width, depth, 0.035),
                 (0, 0, height - 0.0175), bevel=0.008)
    parts = [top, legs(f"{prefix}_Legs", coll, M("MAT_Furniture_Wood"),
                       corners(width / 2 - 0.05, depth / 2 - 0.05), height - 0.035, 0.024)]
    if drawer:
        parts.append(su.box(f"{prefix}_Drawer", coll, M("MAT_Furniture_Paint"), (width - 0.14, depth - 0.1, 0.1),
                            (0, 0.02, height - 0.085), bevel=0.006))
    return assemble(parts, location, rotation)


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


def armchair(coll, location, rotation=0, width=0.78, fabric="MAT_Fabric_Sage", prefix="ARMCHAIR"):
    """Upholstered chair; a sitter faces local -Y. Make it wider and it is a sofa."""
    fabric, hw = M(fabric), width / 2
    base = su.box(f"{prefix}_Base", coll, fabric, (width, 0.74, 0.22), (0, 0, 0.26), bevel=0.05)
    seat = su.pillow(f"{prefix}_Seat_Cushion", coll, fabric, (width - 0.18, 0.62, 0.12), (0, -0.04, 0.42),
                     puff=0.25)
    back = su.box(f"{prefix}_Back", coll, fabric, (width, 0.16, 0.55), (0, 0.3, 0.62), rotation=(-10, 0, 0),
                  bevel=0.06)
    bm = bmesh.new()
    for side in (-1, 1):
        su.add_box(bm, (0.12, 0.7, 0.24), (side * (hw - 0.06), -0.02, 0.48))
    arms = su.make_object(f"{prefix}_Arms", coll, fabric, bm, bevel=0.05)
    chair_legs = legs(f"{prefix}_Legs", coll, M("MAT_Bed_Wood"), corners(hw - 0.07, 0.29), 0.15, 0.022)
    cushion = su.pillow(f"{prefix}_Cushion", coll, M("MAT_Fabric_Rose"), (0.38, 0.32, 0.12),
                        (hw - 0.3, 0.11, 0.65), rotation=(72, 0, 8), puff=0.5)
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


# -------------------------------------------------------- more furniture & lighting

def sofa(coll, location, rotation=0, prefix="SOFA"):
    """Three-seat sofa (a wide armchair)."""
    return armchair(coll, location, rotation, width=1.9, fabric="MAT_Fabric_Cream", prefix=prefix)


def bookshelf(coll, location, rotation=0, width=0.9, depth=0.32, height=1.8, shelves=5, prefix="BOOKSHELF"):
    """Open bookcase filled with books; its back is local +Y."""
    t, hw = 0.025, width / 2
    gap = (height - t) / shelves
    bm = bmesh.new()
    for side in (-1, 1):
        su.add_box(bm, (t, depth, height), (side * (hw - t / 2), 0, height / 2))
    for i in range(shelves + 1):
        su.add_box(bm, (width - 2 * t, depth, t), (0, 0, t / 2 + i * gap))
    su.add_box(bm, (width - 2 * t, 0.01, height), (0, depth / 2 - 0.005, height / 2), material_index=1)
    parts = [su.make_object(prefix, coll, [M("MAT_Furniture_Wood"), M("MAT_Furniture_Paint")], bm, bevel=0.005)]
    covers = [M(m) for m in ("MAT_Book_Red", "MAT_Book_Green", "MAT_Book_Blue", "MAT_Book_Tan", "MAT_Fabric_Cream")]
    rng = random.Random(prefix)                      # same books every time the asset is built
    for i in range(shelves):
        bm = bmesh.new()
        x, end = -hw + t + 0.01, hw - t - rng.uniform(0.05, 0.25)     # leave a gap on each shelf
        while x < end:
            w, h = rng.uniform(0.02, 0.045), min(gap - t - 0.02, rng.uniform(0.17, 0.26))
            su.add_box(bm, (w, depth * 0.75, h), (x + w / 2, 0, h / 2), material_index=rng.randrange(len(covers)))
            x += w + 0.002
        parts.append(su.make_object(f"{prefix}_Books_{i + 1}", coll, covers, bm, (0, -0.01, t + i * gap),
                                    bevel=0.002))
    return assemble(parts, location, rotation)


def floor_lamp(coll, light_coll, location, prefix="FLOOR_LAMP", energy=50):
    base = su.cylinder(f"{prefix}_Base", coll, M("MAT_Metal"), 0.15, 0.03, (0, 0, 0.015), bevel=0.006)
    pole = su.cylinder(f"{prefix}_Pole", coll, M("MAT_Brass"), 0.012, 1.45, (0, 0, 0.75), segments=12)
    shade = su.cylinder(f"{prefix}_Shade", coll, M("MAT_Lamp_Shade"), 0.22, 0.3, (0, 0, 1.55), radius_top=0.16,
                        caps=False, segments=48)
    su.add_modifier(shade, "SOLIDIFY", "Shade Thickness", thickness=0.004)
    bulb = su.sphere(f"{prefix}_Bulb", coll, M("MAT_Bulb"), 0.04, (0, 0, 1.5), segments=16)
    bulb.visible_shadow = False
    glow = su.light(f"LIGHT_{prefix}_Bulb", light_coll, "POINT", (0, 0, 1.52), energy, (1.0, 0.62, 0.32),
                    shadow_soft_size=0.05)
    return assemble([base, pole, shade, bulb, glow], location)


def desk_lamp(coll, light_coll, location, rotation=0, prefix="DESK_LAMP", energy=15):
    """Angled reading lamp; it shines down toward local +X."""
    base = su.cylinder(f"{prefix}_Base", coll, M("MAT_Metal"), 0.07, 0.02, (0, 0, 0.01), bevel=0.004)
    elbow, head = Vector((0.1, 0, 0.32)), Vector((0.3, 0, 0.36))
    beam = Vector((0.5, 0, -0.866))                    # 30 degrees off straight down
    bm = bmesh.new()
    su.add_rod(bm, (0, 0, 0.02), elbow, 0.008)
    su.add_rod(bm, elbow, head, 0.008)
    su.add_sphere(bm, 0.014, elbow, segments=12)
    arm = su.make_object(f"{prefix}_Arm", coll, M("MAT_Metal"), bm)
    shade = su.cylinder(f"{prefix}_Shade", coll, M("MAT_Metal"), 0.025, 0.12, head + beam * 0.06,
                        rotation=(0, 150, 0), radius_top=0.07, caps=False)
    su.add_modifier(shade, "SOLIDIFY", "Shade Thickness", thickness=0.003)
    bulb = su.sphere(f"{prefix}_Bulb", coll, M("MAT_Bulb"), 0.02, head + beam * 0.07, segments=12)
    bulb.visible_shadow = False
    glow = su.light(f"LIGHT_{prefix}_Bulb", light_coll, "SPOT", head + beam * 0.06, energy, (1.0, 0.7, 0.4),
                    target=head + beam, spot_size=math.radians(80), spot_blend=0.5, shadow_soft_size=0.02)
    return assemble([base, arm, shade, bulb, glow], location, rotation)


def ceiling_light(coll, light_coll, location, prefix="CEILING_LIGHT", energy=60):
    """Flush dome light. `location` = the point on the ceiling."""
    base = su.cylinder(f"{prefix}_Base", coll, M("MAT_Trim_White"), 0.12, 0.02, (0, 0, -0.01), bevel=0.004)
    dome = su.sphere(f"{prefix}_Dome", coll, M("MAT_Lamp_Shade"), 0.16, (0, 0, -0.02), scale=(1, 1, 0.4))
    dome.visible_shadow = False
    glow = su.light(f"LIGHT_{prefix}", light_coll, "POINT", (0, 0, -0.09), energy, (1.0, 0.8, 0.6),
                    shadow_soft_size=0.12)
    return assemble([base, dome, glow], location)


def candle(coll, light_coll, location, height=0.12, radius=0.025, prefix="CANDLE", energy=3):
    """Pillar candle with a glowing flame and a small flickery-warm light."""
    body = su.cylinder(prefix, coll, M("MAT_Wax"), radius, height, (0, 0, height / 2), segments=24, bevel=0.004)
    wick = su.cylinder(f"{prefix}_Wick", coll, M("MAT_Plastic_Black"), 0.0015, 0.015, (0, 0, height + 0.0075),
                       segments=6)
    flame = su.sphere(f"{prefix}_Flame", coll, M("MAT_Flame"), 0.007, (0, 0, height + 0.024), scale=(1, 1, 2.2),
                      segments=12)
    flame.visible_shadow = False
    glow = su.light(f"LIGHT_{prefix}_Flame", light_coll, "POINT", (0, 0, height + 0.03), energy, (1.0, 0.55, 0.2),
                    shadow_soft_size=0.01)
    return assemble([body, wick, flame, glow], location)


def coat_rack(coll, location, prefix="COAT_RACK"):
    """Standing coat rack with a long coat on one hook."""
    pole = su.cylinder(prefix, coll, M("MAT_Bed_Wood"), 0.02, 1.75, (0, 0, 0.875), segments=16, bevel=0.004)
    bm = bmesh.new()
    for i in range(4):
        a = math.radians(45 + 90 * i)
        out = Vector((math.cos(a), math.sin(a), 0))
        su.add_rod(bm, (0, 0, 0.15), out * 0.28 + Vector((0, 0, 0.01)), 0.015)       # feet
        su.add_rod(bm, (0, 0, 1.6), out * 0.13 + Vector((0, 0, 1.7)), 0.009)         # hooks
        su.add_sphere(bm, 0.016, out * 0.13 + Vector((0, 0, 1.7)), segments=10)
    arms = su.make_object(f"{prefix}_Feet_Hooks", coll, M("MAT_Bed_Wood"), bm)
    top = su.sphere(f"{prefix}_Top", coll, M("MAT_Bed_Wood"), 0.03, (0, 0, 1.76))
    coat = garment(f"{prefix}_Coat", coll, M("MAT_Fabric_Charcoal"), 1.05, (0.09, 0.09, 1.69))
    coat.rotation_euler.z = math.radians(45)
    return assemble([pole, arms, top, coat], location)


# ------------------------------------------------------------------- story props

def mug(coll, location, rotation=0, prefix="PROP_Mug"):
    bm = bmesh.new()
    su.add_cylinder(bm, 0.04, 0.095, (0, 0, 0.0475), caps=False, segments=32)
    su.add_cylinder(bm, 0.04, 0.006, (0, 0, 0.003), segments=32)
    body = su.make_object(prefix, coll, M("MAT_Ceramic"), bm, smooth_angle=60)
    su.add_modifier(body, "SOLIDIFY", "Wall Thickness", thickness=0.005)
    bm = bmesh.new()
    su.add_torus(bm, 0.025, 0.006, (0.06, 0, 0.05), rotation=(90, 0, 0), segments=24)
    handle = su.make_object(f"{prefix}_Handle", coll, M("MAT_Ceramic"), bm, smooth_angle=180)
    coffee = su.cylinder(f"{prefix}_Coffee", coll, M("MAT_Coffee"), 0.034, 0.004, (0, 0, 0.075), segments=32)
    return assemble([body, handle, coffee], location, rotation)


def bottle(coll, location, glass="MAT_Glass_Green", prefix="PROP_Bottle"):
    bm = bmesh.new()
    su.add_cylinder(bm, 0.035, 0.2, (0, 0, 0.1), segments=32)
    su.add_cylinder(bm, 0.035, 0.05, (0, 0, 0.225), radius_top=0.012, segments=32)
    su.add_cylinder(bm, 0.012, 0.07, (0, 0, 0.285), segments=24)
    body = su.make_object(prefix, coll, M(glass), bm, smooth_angle=50)
    cap = su.cylinder(f"{prefix}_Cap", coll, M("MAT_Brass"), 0.0135, 0.015, (0, 0, 0.325), segments=24)
    return assemble([body, cap], location)


def wall_clock(coll, location, rotation=0, radius=0.17, prefix="DECOR_Wall_Clock"):
    """Round wall clock stopped at 3:00. `location` = its centre on the wall; local +Y = wall."""
    bm = bmesh.new()
    su.add_torus(bm, radius, 0.018, (0, -0.02, 0), rotation=(90, 0, 0), segments=48)
    su.add_cylinder(bm, radius, 0.02, (0, -0.01, 0), rotation=(90, 0, 0), segments=48)
    rim = su.make_object(prefix, coll, M("MAT_Bed_Wood"), bm, smooth_angle=60)
    face = su.cylinder(f"{prefix}_Face", coll, M("MAT_Clock_Face"), radius - 0.01, 0.004, (0, -0.022, 0),
                       rotation=(90, 0, 0), segments=48)
    bm = bmesh.new()
    su.add_box(bm, (0.006, 0.002, radius * 0.75), (0, 0, radius * 0.33))           # minute hand on 12
    su.add_box(bm, (radius * 0.5, 0.002, 0.008), (radius * 0.23, 0, 0))            # hour hand on 3
    for i in range(12):
        a = math.radians(i * 30)
        su.add_box(bm, (0.006, 0.002, 0.02), (radius * 0.82 * math.sin(a), 0, radius * 0.82 * math.cos(a)),
                   rotation=(0, i * 30, 0))
    hands = su.make_object(f"{prefix}_Hands", coll, M("MAT_Plastic_Black"), bm, (0, -0.026, 0))
    return assemble([rim, face, hands], location, rotation)


def evidence_board(coll, location, rotation=0, width=1.2, height=0.8, prefix="DECOR_Evidence_Board"):
    """Crime-story cork board: photos and notes linked by red string.
    `location` = its centre on the wall; local +Y = wall."""
    hw, hh, b = width / 2, height / 2, 0.04
    bm = bmesh.new()
    for size, center in (((width, 0.03, b), (0, -0.015, hh - b / 2)), ((width, 0.03, b), (0, -0.015, -hh + b / 2)),
                         ((b, 0.03, height), (-hw + b / 2, -0.015, 0)), ((b, 0.03, height), (hw - b / 2, -0.015, 0))):
        su.add_box(bm, size, center)
    frame = su.make_object(prefix, coll, M("MAT_Bed_Wood"), bm, bevel=0.005)
    cork = su.box(f"{prefix}_Cork", coll, M("MAT_Cork"), (width - 2 * b + 0.01, 0.012, height - 2 * b + 0.01),
                  (0, -0.012, 0), bevel=0)
    # (x, z, width, height, kind, tilt): kind 0 = photo, 1 = note, 2 = sticky note
    items = ((-0.4, 0.17, 0.14, 0.18, 0, -5), (-0.12, 0.2, 0.16, 0.12, 0, 4), (0.2, 0.18, 0.12, 0.16, 0, -3),
             (0.42, 0.05, 0.13, 0.17, 1, 6), (-0.38, -0.15, 0.15, 0.11, 1, 3), (-0.05, -0.12, 0.17, 0.12, 0, -6),
             (0.22, -0.17, 0.09, 0.09, 2, 8), (0.05, 0.02, 0.08, 0.08, 2, -4))
    notes_bm, pins_bm, pins = bmesh.new(), bmesh.new(), []
    for x, z, w, h, kind, tilt in items:
        x, z = x * width / 1.2, z * height / 0.8
        su.add_box(notes_bm, (w, 0.002, h), (x, -0.02, z), material_index=kind, rotation=(0, tilt, 0))
        pin = Vector((x, -0.026, z + h / 2 - 0.02))
        su.add_sphere(pins_bm, 0.008, pin, segments=10)
        pins.append(pin)
    notes = su.make_object(f"{prefix}_Notes", coll, [M("MAT_Photo"), M("MAT_Paper"), M("MAT_Paper_Yellow")],
                           notes_bm)
    tacks = su.make_object(f"{prefix}_Pins", coll, M("MAT_Book_Red"), pins_bm, smooth_angle=180)
    bm = bmesh.new()
    for i, j in ((0, 1), (1, 2), (2, 3), (0, 4), (4, 5), (5, 6), (1, 5), (7, 3)):
        su.add_rod(bm, pins[i], pins[j], 0.0015, segments=6)
    string = su.make_object(f"{prefix}_String", coll, M("MAT_Red_String"), bm)
    return assemble([frame, cork, notes, tacks, string], location, rotation)


def flashlight(coll, light_coll, location, rotation=0, prefix="PROP_Flashlight", energy=20):
    """Torch lying on its side, switched on, shining toward local -Y."""
    z = 0.028
    body = su.cylinder(prefix, coll, M("MAT_Metal"), 0.022, 0.16, (0, 0.02, z), rotation=(90, 0, 0), bevel=0.003)
    head = su.cylinder(f"{prefix}_Head", coll, M("MAT_Metal"), 0.022, 0.05, (0, -0.085, z), rotation=(90, 0, 0),
                       radius_top=0.028, bevel=0.002)
    lens = su.cylinder(f"{prefix}_Lens", coll, M("MAT_Bulb"), 0.025, 0.003, (0, -0.111, z), rotation=(90, 0, 0))
    lens.visible_shadow = False
    beam = su.light(f"LIGHT_{prefix}_Beam", light_coll, "SPOT", (0, -0.115, z), energy, (1.0, 0.9, 0.75),
                    target=(0, -2, z), spot_size=math.radians(40), spot_blend=0.3, shadow_soft_size=0.01)
    return assemble([body, head, lens, beam], location, rotation)


def cardboard_box(coll, location, size=(0.45, 0.35, 0.3), rotation=0, prefix="PROP_Box"):
    w, d, h = size
    body = su.box(prefix, coll, M("MAT_Cardboard"), size, (0, 0, h / 2), bevel=0.004)
    bm = bmesh.new()
    su.add_box(bm, (0.06, d + 0.004, 0.002), (0, 0, h + 0.001))
    for side in (-1, 1):
        su.add_box(bm, (0.06, 0.002, 0.08), (0, side * (d / 2 + 0.001), h - 0.04))
    tape = su.make_object(f"{prefix}_Tape", coll, M("MAT_Tape"), bm)
    return assemble([body, tape], location, rotation)


def suitcase(coll, location, rotation=0, prefix="PROP_Suitcase"):
    """Vintage suitcase standing upright."""
    body = su.box(prefix, coll, M("MAT_Leather"), (0.55, 0.2, 0.4), (0, 0, 0.21), bevel=0.03)
    bm = bmesh.new()
    for side in (-1, 1):
        su.add_box(bm, (0.035, 0.205, 0.405), (side * 0.16, 0, 0.21))
    straps = su.make_object(f"{prefix}_Straps", coll, M("MAT_Bed_Wood"), bm, bevel=0.004)
    bm = bmesh.new()
    su.add_torus(bm, 0.06, 0.011, (0, 0, 0.41), rotation=(90, 0, 0), arc=180, segments=16)
    handle = su.make_object(f"{prefix}_Handle", coll, M("MAT_Plastic_Black"), bm, smooth_angle=180)
    return assemble([body, straps, handle], location, rotation)


def trash_bin(coll, location, prefix="PROP_Trash_Bin"):
    bm = bmesh.new()
    su.add_cylinder(bm, 0.11, 0.3, (0, 0, 0.15), radius_top=0.13, caps=False, segments=32)
    su.add_cylinder(bm, 0.11, 0.006, (0, 0, 0.003), segments=32)
    can = su.make_object(prefix, coll, M("MAT_Aluminium"), bm, smooth_angle=60)
    su.add_modifier(can, "SOLIDIFY", "Wall Thickness", thickness=0.004)
    bm = bmesh.new()
    for x, y, z, r in ((0.02, 0.03, 0.26, 0.05), (-0.05, -0.02, 0.25, 0.045), (0.04, -0.05, 0.28, 0.04)):
        verts = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)["verts"]
        bmesh.ops.translate(bm, vec=(x, y, z), verts=verts)
    paper = su.make_object(f"{prefix}_Paper", coll, M("MAT_Paper"), bm, flat=True)
    return assemble([can, paper], location)


def knife(coll, location, rotation=0, prefix="PROP_Knife"):
    """Kitchen knife lying flat, blade pointing toward local +X."""
    bm = bmesh.new()
    for v in su.add_box(bm, (0.2, 0.032, 0.002), (0.1, 0, 0.004)):
        if v.co.x > 0.15:
            v.co.y = 0.016                  # the edge sweeps up to the spine at the tip
    blade = su.make_object(prefix, coll, M("MAT_Steel"), bm)
    handle = su.box(f"{prefix}_Handle", coll, M("MAT_Bed_Wood"), (0.11, 0.026, 0.018), (-0.055, 0, 0.009),
                    bevel=0.006)
    return assemble([blade, handle], location, rotation)


def envelope(coll, location, rotation=0, prefix="PROP_Envelope"):
    """Sealed kraft envelope with a red wax seal."""
    body = su.box(prefix, coll, M("MAT_Cardboard"), (0.22, 0.11, 0.003), (0, 0, 0.0015), bevel=0)
    bm = bmesh.new()
    bm.faces.new([bm.verts.new(p) for p in ((-0.11, 0.055, 0.0032), (0, -0.01, 0.0032), (0.11, 0.055, 0.0032))])
    flap = su.make_object(f"{prefix}_Flap", coll, M("MAT_Tape"), bm, flat=True)
    seal = su.cylinder(f"{prefix}_Seal", coll, M("MAT_Book_Red"), 0.014, 0.003, (0, -0.005, 0.0045), segments=24)
    return assemble([body, flap, seal], location, rotation)


def pencil(coll, location, rotation=0, prefix="PROP_Pencil"):
    """Yellow pencil lying along local X, sharpened tip toward +X."""
    r, along_x = 0.0045, (0, 90, 0)
    bm = bmesh.new()
    su.add_cylinder(bm, r, 0.13, (-0.005, 0, 0), rotation=along_x, segments=6)                 # painted body
    su.add_cylinder(bm, r, 0.022, (0.071, 0, 0), rotation=along_x, radius_top=0.0012, segments=12,
                    material_index=1)                                                           # sharpened wood
    su.add_cylinder(bm, 0.0012, 0.005, (0.0845, 0, 0), rotation=along_x, radius_top=0.0002, segments=8,
                    material_index=2)                                                           # graphite
    su.add_cylinder(bm, r + 0.0005, 0.01, (-0.075, 0, 0), rotation=along_x, segments=12, material_index=3)
    su.add_cylinder(bm, r, 0.008, (-0.084, 0, 0), rotation=along_x, segments=12, material_index=4)
    mats = [M(m) for m in ("MAT_Pencil", "MAT_Wax", "MAT_Plastic_Black", "MAT_Aluminium", "MAT_Fabric_Rose")]
    return su.make_object(prefix, coll, mats, bm, (location[0], location[1], location[2] + r), (0, 0, rotation))


def notebook(coll, location, rotation=0, prefix="PROP_Notebook"):
    """Open spiral notebook lying flat, spine along local Y; pages are 0.01 above `location`."""
    cover = su.box(prefix, coll, M("MAT_Notebook_Cover"), (0.32, 0.22, 0.004), (0, 0, 0.002), bevel=0.002)
    bm = bmesh.new()
    for side in (-1, 1):
        su.add_box(bm, (0.148, 0.21, 0.006), (side * 0.079, 0, 0.007))
    pages = su.make_object(f"{prefix}_Pages", coll, M("MAT_Paper"), bm, bevel=0.001)
    bm = bmesh.new()
    for i in range(9):
        su.add_torus(bm, 0.008, 0.0012, (0, -0.096 + i * 0.024, 0.009), rotation=(90, 0, 0), segments=12, ring=6)
    rings = su.make_object(f"{prefix}_Rings", coll, M("MAT_Aluminium"), bm, smooth_angle=180)
    bm = bmesh.new()
    for side in (-1, 1):
        for i in range(8):
            su.add_box(bm, (0.13, 0.0012, 0.0004), (side * 0.079, 0.085 - i * 0.022, 0.0102))
    lines = su.make_object(f"{prefix}_Ruled_Lines", coll, M("MAT_Ruled_Line"), bm)
    return assemble([cover, pages, rings, lines], location, rotation)


def handwriting(name, coll, start, length, frame_start, frames, seed=0):
    """A line of scribbled 'handwriting' that appears left to right, as if being
    written, from `frame_start` over `frames` frames. `start` = left end on the page."""
    rng = random.Random(seed)
    points = []
    for i in range(121):
        t = i / 120
        wobble = 0.0035 * math.sin(t * 70 + rng.uniform(0, 0.4)) * (0.6 + 0.4 * math.sin(t * 9 + seed))
        points.append(Vector((t * length + 0.002 * math.sin(t * 110), wobble, 0)))
    bm = bmesh.new()
    for a, b in zip(points, points[1:]):
        side = (b - a).cross(Vector((0, 0, 1))).normalized() * 0.0007
        bm.faces.new([bm.verts.new(p) for p in (a - side, b - side, b + side, a + side)])
    ink = su.make_object(name, coll, M("MAT_Ink"), bm, Vector(start), flat=True)
    su.add_modifier(ink, "BUILD", "Write On", frame_start=frame_start, frame_duration=frames)
    return ink
