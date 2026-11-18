"""
FLV scene helpers: geometry, collections, lights, cameras, render settings, files.

Everything here creates ordinary Blender data, so results stay editable in the
Blender UI: objects are named, scale is applied, and modifiers (bevel,
subdivision, cloth wrinkles) stay live in the Modifier Properties tab.
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from bpy_extras import anim_utils
from mathutils import Euler, Vector

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENES_DIR = PROJECT_ROOT / "blender" / "scenes"
PREVIEW_DIR = PROJECT_ROOT / "output" / "previews"
RENDER_DIR = PROJECT_ROOT / "output" / "renders"


# --------------------------------------------------------------------------- files

def reset_scene():
    """Remove all objects and their data so a rebuild starts from nothing."""
    for data in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.collections, bpy.data.worlds,
                 bpy.data.textures, bpy.data.actions):
        bpy.data.batch_remove(list(data))


def save_blend(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))


def open_blend(path):
    """Open `path`, unless Blender was already started with a .blend file."""
    if not bpy.data.filepath:
        bpy.ops.wm.open_mainfile(filepath=str(path))


def script_args():
    """Arguments given after `--` on the Blender command line."""
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def collection(name, parent=None):
    coll = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if coll.name not in parent.children:
        parent.children.link(coll)
    return coll


# ------------------------------------------------------------- mesh building blocks
# add_* functions append a shape to a bmesh; several shapes can share one object.

def _set_material(verts, index):
    for face in {f for v in verts for f in v.link_faces}:
        face.material_index = index


def _place(bm, verts, center, rotation=(0, 0, 0)):
    if any(rotation):
        rot = Euler([math.radians(a) for a in rotation]).to_matrix()
        bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=rot, verts=verts)
    bmesh.ops.translate(bm, vec=center, verts=verts)


def add_box(bm, size, center=(0, 0, 0), material_index=0):
    verts = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    bmesh.ops.scale(bm, vec=size, verts=verts)
    _place(bm, verts, center)
    _set_material(verts, material_index)
    return verts


def add_cylinder(bm, radius, depth, center=(0, 0, 0), rotation=(0, 0, 0), radius_top=None,
                 segments=24, caps=True, material_index=0):
    """Cylinder along Z (radius at the bottom, radius_top at the top) - a cone if they differ."""
    verts = bmesh.ops.create_cone(
        bm, cap_ends=caps, segments=segments, radius1=radius,
        radius2=radius if radius_top is None else radius_top, depth=depth)["verts"]
    _place(bm, verts, center, rotation)
    _set_material(verts, material_index)
    return verts


def add_sphere(bm, radius, center=(0, 0, 0), scale=(1, 1, 1), segments=24, material_index=0):
    verts = bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=segments // 2,
                                      radius=radius)["verts"]
    bmesh.ops.scale(bm, vec=scale, verts=verts)
    _place(bm, verts, center)
    _set_material(verts, material_index)
    return verts


def add_modifier(obj, kind, name, **settings):
    mod = obj.modifiers.new(name, kind)
    for key, value in settings.items():
        setattr(mod, key, value)
    return mod


def make_object(name, coll, materials, bm, location=(0, 0, 0), rotation=(0, 0, 0),
                bevel=0.0, subdivide=0, smooth_angle=35.0, flat=False):
    """Turn a bmesh into a named object with materials and optional soft edges."""
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in materials if isinstance(materials, (list, tuple)) else [materials]:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    obj.location = location
    obj.rotation_euler = [math.radians(a) for a in rotation]
    if flat:
        mesh.shade_flat()
    else:
        mesh.shade_smooth()
        if not subdivide and smooth_angle < 180:
            mesh.set_sharp_from_angle(angle=math.radians(smooth_angle))
    if bevel:
        add_modifier(obj, "BEVEL", "Soft Edges", width=bevel, segments=3,
                     limit_method="ANGLE", harden_normals=True)
    if subdivide:
        add_modifier(obj, "SUBSURF", "Soft Shape", levels=subdivide, render_levels=subdivide)
    return obj


# ------------------------------------------------------------------ simple shapes

def box(name, coll, material, size, location=(0, 0, 0), rotation=(0, 0, 0), bevel=0.01):
    bm = bmesh.new()
    add_box(bm, size)
    return make_object(name, coll, material, bm, location, rotation, bevel=bevel)


def cylinder(name, coll, material, radius, depth, location=(0, 0, 0), rotation=(0, 0, 0),
             radius_top=None, segments=32, caps=True, bevel=0.0):
    bm = bmesh.new()
    add_cylinder(bm, radius, depth, radius_top=radius_top, segments=segments, caps=caps)
    return make_object(name, coll, material, bm, location, rotation, bevel=bevel)


def sphere(name, coll, material, radius, location=(0, 0, 0), scale=(1, 1, 1), segments=24):
    bm = bmesh.new()
    add_sphere(bm, radius, scale=scale, segments=segments)
    return make_object(name, coll, material, bm, location, smooth_angle=180)


# -------------------------------------------------------------------- soft shapes

def pillow(name, coll, material, size, location, rotation=(0, 0, 0), puff=0.6):
    """Cushion: a subdivided box, full in the middle and pinched thin at the rim."""
    w, d, h = size
    bm = bmesh.new()
    add_box(bm, size)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=4, use_grid_fill=True)
    for v in bm.verts:
        rim = max(abs(v.co.x) / (w / 2), abs(v.co.y) / (d / 2))   # 0 centre .. 1 edge
        v.co.z *= 1 - puff * rim ** 2
    return make_object(name, coll, material, bm, location, rotation, subdivide=2)


def _wrinkle_texture():
    tex = bpy.data.textures.get("TEX_Fabric_Wrinkles")
    if not tex:
        tex = bpy.data.textures.new("TEX_Fabric_Wrinkles", "CLOUDS")
        tex.noise_scale = 0.18
    return tex


def drape(name, coll, material, width, length, drop, location,
          sides=("left", "right", "front"), flare=0.05, wrinkles=0.015, thickness=0.015):
    """Fabric laid over a box (sheet, duvet, throw): a flat top whose `sides` hang
    `drop` metres down. `location` is the centre of the top; local -y is the front."""
    hw, hl = width / 2, length / 2
    bm = bmesh.new()
    add_box(bm, (width, length, drop), (0, 0, -drop / 2))
    eps = 1e-4
    open_faces = []
    for f in bm.faces:
        c = f.calc_center_median()
        if (c.z < -drop + eps
                or (c.x < -hw + eps and "left" not in sides)
                or (c.x > hw - eps and "right" not in sides)
                or (c.y < -hl + eps and "front" not in sides)
                or (c.y > hl - eps and "back" not in sides)):
            open_faces.append(f)
    bmesh.ops.delete(bm, geom=open_faces, context="FACES")
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=10, use_grid_fill=True)
    for v in bm.verts:   # hems swing slightly outward, like real fabric
        hang = -v.co.z / drop
        if abs(v.co.x) > hw - eps:
            v.co.x += math.copysign(flare * hang, v.co.x)
        if abs(v.co.y) > hl - eps:
            v.co.y += math.copysign(flare * hang, v.co.y)
    obj = make_object(name, coll, material, bm, location, smooth_angle=180)
    if wrinkles:
        add_modifier(obj, "DISPLACE", "Wrinkles", texture=_wrinkle_texture(), strength=wrinkles)
    add_modifier(obj, "SOLIDIFY", "Fabric Thickness", thickness=thickness)
    add_modifier(obj, "SUBSURF", "Soft Shape", levels=2, render_levels=2)
    return obj


def curtain(name, coll, material, width, height, location, pleats=5, depth=0.07):
    """Pleated panel hanging down from `location` (centre of its top edge)."""
    cols, rows = pleats * 8, 12
    bm = bmesh.new()
    grid = []
    for r in range(rows + 1):
        spread = 1 + 0.15 * r / rows             # a little wider at the hem
        row = []
        for c in range(cols + 1):
            u = c / cols
            row.append(bm.verts.new(((u - 0.5) * width * spread,
                                     depth / 2 * math.sin(u * pleats * 2 * math.pi),
                                     -height * r / rows)))
        grid.append(row)
    for r in range(rows):
        for c in range(cols):
            bm.faces.new((grid[r][c], grid[r + 1][c], grid[r + 1][c + 1], grid[r][c + 1]))
    obj = make_object(name, coll, material, bm, location, smooth_angle=180)
    add_modifier(obj, "SOLIDIFY", "Fabric Thickness", thickness=0.01)
    add_modifier(obj, "SUBSURF", "Soft Shape", levels=1, render_levels=2)
    return obj


# ------------------------------------------------------------ lights and cameras

def look_at(obj, target):
    direction = Vector(target) - Vector(obj.location)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def light(name, coll, kind, location, energy, color, target=None, **settings):
    """kind: POINT, SUN, SPOT or AREA. energy is Watts (Strength for SUN)."""
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    for key, value in settings.items():
        setattr(data, key, value)
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    obj.location = location
    if target:
        look_at(obj, target)
    return obj


def camera(name, coll, location, target, lens=35):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_start, data.clip_end = 0.05, 100
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


def animate_move(obj, end_location, frame_start, frame_end):
    """Smooth ease-in/ease-out move from the current location to `end_location`."""
    start = obj.location.copy()
    obj.keyframe_insert("location", frame=frame_start)
    obj.location = end_location
    obj.keyframe_insert("location", frame=frame_end)
    obj.location = start
    anim = obj.animation_data
    for fcurve in anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot).fcurves:
        for key in fcurve.keyframe_points:
            key.interpolation = "BEZIER"     # auto-clamped Bezier handles = gentle ease
            key.handle_left_type = key.handle_right_type = "AUTO_CLAMPED"


# ---------------------------------------------------------------- render settings

def eevee_engine():
    """Blender 4.2-4.x calls Eevee BLENDER_EEVEE_NEXT; Blender 5 calls it BLENDER_EEVEE."""
    engines = {e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    return "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"


def configure_render(scene, width=1080, height=1920, fps=24, frame_start=1, frame_end=120,
                     samples=64):
    render = scene.render
    render.engine = eevee_engine()
    render.resolution_x, render.resolution_y, render.resolution_percentage = width, height, 100
    render.fps, render.fps_base = fps, 1.0
    scene.frame_start, scene.frame_end = frame_start, frame_end
    render.film_transparent = False

    eevee = scene.eevee
    eevee.taa_render_samples = samples
    eevee.use_shadows = True
    eevee.use_raytracing = True            # reflections on wood, mirror and floor
    eevee.use_volumetric_shadows = True    # moonbeams through the window haze
    eevee.volumetric_tile_size = "4"

    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:                      # very old Blender without AgX
        scene.view_settings.view_transform = "Filmic"


def set_png_output(scene, filepath):
    settings = scene.render.image_settings
    if hasattr(settings, "media_type"):    # Blender 5+
        settings.media_type = "IMAGE"
    settings.file_format = "PNG"
    settings.color_mode = "RGB"
    scene.render.filepath = str(filepath)


def set_mp4_output(scene, filepath):
    settings = scene.render.image_settings
    if hasattr(settings, "media_type"):    # Blender 5+
        settings.media_type = "VIDEO"
    settings.file_format = "FFMPEG"
    ffmpeg = scene.render.ffmpeg
    ffmpeg.format, ffmpeg.codec = "MPEG4", "H264"
    ffmpeg.constant_rate_factor, ffmpeg.ffmpeg_preset = "HIGH", "GOOD"
    ffmpeg.gopsize = scene.render.fps
    ffmpeg.audio_codec = "NONE"            # audio is added later in the edit
    scene.render.filepath = str(filepath)


def set_viewport(target, view_from, shading="MATERIAL"):
    """Make every 3D Viewport open looking at `target` from `view_from`."""
    offset = Vector(view_from) - Vector(target)
    rotation = (-offset).to_track_quat("-Z", "Y")
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            space.shading.type = shading
            space.clip_end = 200
            view = space.region_3d
            view.view_perspective = "PERSP"
            view.view_location = target
            view.view_rotation = rotation
            view.view_distance = offset.length
