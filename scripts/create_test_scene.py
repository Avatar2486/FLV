"""
FLV - AI Story Studio | Phase 2: stylized night-time bedroom.

Run from the FLV folder:
    blender --background --factory-startup --python scripts/create_test_scene.py

Builds the room, furniture, props, lights and cameras, then saves
blender/scenes/test_bedroom.blend. Re-running rebuilds the scene from scratch;
Blender keeps the previous file as test_bedroom.blend1.

Units are metres. X runs left -> right, Y front -> back, Z up. The room is an
open "dollhouse" corner: back wall + left wall, open at the front and right.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # find the FLV modules

import bmesh
import bpy
from mathutils import Vector

import asset_library as lib
import scene_utils as su
from material_library import haze_material, material as M

SCENE_FILE = su.SCENES_DIR / "test_bedroom.blend"

ROOM_W, ROOM_D, ROOM_H, WALL_T = 6.5, 5.5, 2.8, 0.15
X0, X1 = -ROOM_W / 2, ROOM_W / 2          # left wall face .. open right side
Y0, Y1 = -ROOM_D / 2, ROOM_D / 2          # open front .. back wall face
PANEL_FACE = Y1 - 0.03                    # front of the panelling behind the bed

WIN_X, WIN_W, WIN_Z0, WIN_Z1 = -1.45, 1.4, 0.9, 2.3     # window in the back wall
BED_X, BED_Y = 1.3, PANEL_FACE - 1.23
STAND_Y = PANEL_FACE - 0.225              # bedside tables against the panelling
DOOR_Y = -1.8                             # door in the left wall
COLLECTIONS = ("ROOM", "BED", "FURNITURE", "WINDOW", "PROPS", "LIGHTING", "CAMERAS")


def build_room(coll):
    lib.plank_floor("ROOM_Floor", coll, [M("MAT_Floor_Wood"), M("MAT_Floor_Wood_Alt")], ROOM_W, ROOM_D)
    su.box("ROOM_Floor_Base", coll, M("MAT_Base_Dark"), (ROOM_W + WALL_T, ROOM_D + WALL_T, 0.3),
           (-WALL_T / 2, WALL_T / 2, -0.2))

    # Walls start 5 cm below the floor surface so there is no gap at the base.
    wall_start = X0 - WALL_T
    opening = (WIN_X - WIN_W / 2 - wall_start, WIN_X + WIN_W / 2 - wall_start, WIN_Z0 + 0.05, WIN_Z1 + 0.05)
    lib.wall("ROOM_BackWall", coll, M("MAT_Wall_Cream"), ROOM_W + WALL_T, ROOM_H + 0.05, WALL_T,
             (wall_start, Y1, -0.05), opening=opening)
    lib.wall("ROOM_LeftWall", coll, M("MAT_Wall_Cream"), ROOM_D, ROOM_H + 0.05, WALL_T, (X0, Y0, -0.05),
             rotation=90)

    door_gap = (DOOR_Y - 0.53 - Y0, DOOR_Y + 0.53 - Y0, 0, 0.1)
    lib.wall("ROOM_Skirting_Back", coll, M("MAT_Trim_White"), ROOM_W, 0.1, 0.018, (X0, Y1 - 0.018, 0))
    lib.wall("ROOM_Skirting_Left", coll, M("MAT_Trim_White"), ROOM_D, 0.1, 0.018, (X0 + 0.018, Y0, 0),
             rotation=90, opening=door_gap)

    # A ceiling cameras can't see: it keeps the moon from shining in over the walls.
    ceiling = su.box("ROOM_Ceiling_ShadowOnly", coll, M("MAT_Wall_Cream"),
                     (ROOM_W + WALL_T, ROOM_D + WALL_T, 0.1), (-WALL_T / 2, WALL_T / 2, ROOM_H + 0.05), bevel=0)
    ceiling.visible_camera = ceiling.visible_glossy = False
    ceiling.display_type = "WIRE"
    ceiling.hide_select = True

    lib.strips("ROOM_Wall_Panels", coll, M("MAT_Wall_Panel"), 3.0, 2.3, 10, 0.012, (BED_X, Y1, 0))
    lib.strips("DECOR_Wall_Slats", coll, M("MAT_Furniture_Wood"), 0.3, 2.6, 5, 0.03, (3.05, Y1, 0), depth=0.04)
    lib.wall_art(coll, (BED_X, PANEL_FACE, 1.75))
    lib.door(coll, (X0, DOOR_Y, 0), rotation=90)


def build_window(coll):
    lib.window(coll, (WIN_X, Y1, (WIN_Z0 + WIN_Z1) / 2), WIN_W, WIN_Z1 - WIN_Z0, WALL_T)
    lib.curtains(coll, (WIN_X, Y1 - 0.09, WIN_Z1 + 0.15), WIN_W + 0.6, WIN_Z1 + 0.12)

    # Night outside: a painted backdrop behind the window (no full 3D world needed).
    outside_y = Y1 + WALL_T + 0.25     # close, so it never peeks over the wall
    sky = su.box("WINDOW_Exterior_Sky", coll, M("MAT_Night_Sky"), (4.0, 0.02, 2.2),
                 (WIN_X, outside_y, 1.3), bevel=0)
    moon = su.cylinder("WINDOW_Exterior_Moon", coll, M("MAT_Moon"), 0.13, 0.01,
                       (WIN_X - 0.55, outside_y - 0.03, 2.05), rotation=(90, 0, 0), segments=48)
    bm = bmesh.new()
    n, width = 30, 4.0
    ground = [(-width / 2, 0.0), (width / 2, 0.0)] + [
        (width / 2 - width * i / n, 1.0 + 0.08 * math.sin(i * 0.6) + 0.04 * math.sin(i * 1.7))
        for i in range(n + 1)]
    bm.faces.new([bm.verts.new((x, 0, z)) for x, z in ground])
    for x, h in ((-0.95, 1.25), (-0.55, 1.6), (0.4, 1.35), (0.85, 1.05)):   # fir-tree silhouettes
        for i in range(3):
            z0, w = 0.75 + h * i * 0.25, 0.5 * h * (1 - i * 0.25)
            bm.faces.new([bm.verts.new(p) for p in
                          ((x - w / 2, 0, z0), (x + w / 2, 0, z0), (x, 0, z0 + h * 0.45))])
    trees = su.make_object("WINDOW_Exterior_Trees", coll, M("MAT_Tree_Silhouette"), bm,
                           (WIN_X, outside_y - 0.06, 0), flat=True)
    for obj in (sky, moon, trees):
        obj.visible_shadow = False         # the backdrop must not block the moonlight


def build_furniture(coll, light_coll):
    lib.nightstand(coll, (BED_X - 1.2, STAND_Y, 0), prefix="TABLE_Bedside_Left")
    lib.nightstand(coll, (BED_X + 1.2, STAND_Y, 0), prefix="TABLE_Bedside_Right")
    lib.table_lamp(coll, light_coll, (BED_X + 1.25, STAND_Y + 0.05, 0.62))
    lib.pendant_lamp(coll, light_coll, (BED_X - 1.2, STAND_Y - 0.02, ROOM_H), drop=1.05)
    lib.wardrobe(coll, (X0 + 0.31, 0.525, 0), rotation=90)
    lib.open_closet(coll, (X0 + 0.25, 2.15, 0), rotation=90)
    lib.desk(coll, (WIN_X, Y1 - 0.275, 0))
    lib.chair(coll, (WIN_X, Y1 - 0.85, 0), rotation=180, prefix="CHAIR_Desk")
    lib.armchair(coll, (-1.75, -1.2, 0), rotation=115)
    lib.side_table(coll, (-2.4, -0.7, 0))
    lib.tv_stand(coll, (BED_X, -1.35, 0), rotation=180)
    lib.rug(coll, (BED_X, 0.75, 0), (2.9, 2.5), prefix="RUG_Bedroom")
    lib.plant(coll, (X0 + 0.35, -0.95, 0))


def build_props(coll):
    left_x, right_x, top = BED_X - 1.2, BED_X + 1.2, 0.62
    _, pile = lib.book_stack(coll, (left_x - 0.08, STAND_Y + 0.06, top),
                             [("MAT_Book_Red", (0.2, 0.15, 0.03)), ("MAT_Book_Tan", (0.18, 0.13, 0.025))],
                             rotation=10, prefix="PROP_Book_Nightstand")
    lib.alarm_clock(coll, (left_x - 0.08, STAND_Y + 0.06, top + pile), rotation=25)
    lib.water_glass(coll, (left_x + 0.15, STAND_Y - 0.08, top))
    lib.picture_frame(coll, (right_x - 0.12, STAND_Y - 0.1, top), rotation=25)
    lib.laptop(coll, (WIN_X + 0.1, Y1 - 0.3, 0.75))
    lib.book_stack(coll, (WIN_X - 0.3, Y1 - 0.2, 0.75),
                   [("MAT_Book_Green", (0.22, 0.16, 0.035)), ("MAT_Book_Blue", (0.2, 0.15, 0.03)),
                    ("MAT_Book_Red", (0.17, 0.12, 0.025))], rotation=-5, prefix="PROP_Book_Desk")
    lib.vase(coll, (-2.4, -0.7, 0.57))


def build_lighting(coll, scene):
    window_centre = Vector((WIN_X, Y1, (WIN_Z0 + WIN_Z1) / 2))
    moon_dir = Vector((0.3, -0.8, -0.5)).normalized()          # direction the moonlight travels
    su.light("LIGHT_Moon", coll, "SUN", window_centre - moon_dir * 5, 2.5, (0.55, 0.68, 1.0),
             target=window_centre, angle=math.radians(1.5))
    su.light("LIGHT_Moon_Window_Fill", coll, "AREA", (WIN_X, Y1 + 0.45, 1.6), 60, (0.45, 0.6, 1.0),
             target=(WIN_X + 0.6, Y1 - 2.5, 0.4), shape="RECTANGLE", size=WIN_W, size_y=WIN_Z1 - WIN_Z0)
    su.light("LIGHT_Room_Ambient", coll, "AREA", (3.6, -4.6, 2.6), 320, (0.72, 0.8, 1.0),
             target=(-0.5, 1.0, 0.8), shape="DISK", size=5)

    world = bpy.data.worlds.new("WORLD_Night")
    scene.world = world
    if world.node_tree is None:
        world.use_nodes = True
    background = world.node_tree.nodes["Background"].inputs
    background["Color"].default_value = (0.012, 0.018, 0.04, 1)
    background["Strength"].default_value = 1.0

    bm = bmesh.new()
    su.add_box(bm, (ROOM_W, ROOM_D, ROOM_H), (0, 0, ROOM_H / 2))
    haze = su.make_object("ATMOS_Haze", coll, haze_material(), bm)
    haze.display_type = "BOUNDS"           # don't hide the room in the viewport
    haze.hide_select = True                # clicks go to the furniture, not the fog


def build_cameras(coll, scene):
    frames = (scene.frame_start, scene.frame_end)
    shots = {   # name: (location, look-at point, lens mm, how far it drifts toward the target)
        "CAMERA_Main": ((5.0, -6.4, 8.2), (0.15, 1.0, 0.6), 40, 0.08),
        "CAMERA_Bed": ((3.3, -0.9, 1.75), (1.2, 1.9, 0.75), 30, 0.06),
        "CAMERA_Window": ((0.9, -0.6, 1.5), (WIN_X, Y1, 1.45), 28, 0.06),
    }
    for name, (location, target, lens, push) in shots.items():
        cam = su.camera(name, coll, location, target, lens)
        su.animate_move(cam, Vector(location).lerp(Vector(target), push), *frames)
    scene.camera = bpy.data.objects["CAMERA_Main"]
    return shots["CAMERA_Main"][:2]


def main():
    su.reset_scene()
    scene = bpy.context.scene
    su.configure_render(scene)             # 1080x1920, 24 fps, frames 1-120, Eevee, AgX

    root = su.collection("FLV_BEDROOM")
    c = {name: su.collection(name, root) for name in COLLECTIONS}
    build_room(c["ROOM"])
    lib.bed(c["BED"], (BED_X, BED_Y, 0))
    build_furniture(c["FURNITURE"], c["LIGHTING"])
    build_window(c["WINDOW"])
    build_props(c["PROPS"])
    build_lighting(c["LIGHTING"], scene)
    main_view, main_target = build_cameras(c["CAMERAS"], scene)

    # Ctrl+F12 in Blender renders the MP4 next to the other renders (path relative to the .blend).
    su.set_mp4_output(scene, "//../../output/renders/bedroom_main.mp4")
    scene.frame_set(scene.frame_start)
    su.set_viewport(target=main_target, view_from=main_view)   # open looking like the main shot

    bed = bpy.data.objects["BED_Frame"]
    for obj in scene.objects:
        obj.select_set(False)
    bed.select_set(True)
    bpy.context.view_layer.objects.active = bed

    su.save_blend(SCENE_FILE)
    print(f"FLV bedroom saved: {SCENE_FILE} ({len(scene.objects)} objects, {len(bpy.data.materials)} materials)")


if __name__ == "__main__":
    main()
