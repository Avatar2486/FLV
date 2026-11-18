"""
Package FLV's assets for Blender's Asset Browser (drag and drop, no Python).

    blender -b --factory-startup --python scripts/build_asset_library.py

Writes into assets/ (the folder registered as the "FLV" asset library, see README):
  FLV_Procedural_Assets.blend  every builder in asset_library.py: furniture, lamps, props
  FLV_PolyHaven_Assets.blend   downloaded Poly Haven models, night skies (Worlds) and
                               textures (Materials); needs download_assets.py first
  blender_assets.cats.txt      the catalog tree the Asset Browser shows on the left
Open either .blend directly to see its assets laid out like a showroom.
"""
import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy
from mathutils import Vector

import asset_library as lib
import scene_utils as su

ASSETS = su.PROJECT_ROOT / "assets"
MODEL_CATALOGS = ("seating", "table", "shelves", "furniture", "lighting", "electronics", "appliances",
                  "decorative")
catalogs = set()

# name: (catalog, build(collection, location)). Lamps put their lights in the same collection.
PROCEDURAL = {
    "Bed Double":        ("FLV/Furniture", lambda c, p: lib.bed(c, p)),
    "Bed Single":        ("FLV/Furniture", lambda c, p: lib.bed(c, p, width=1.0, length=2.0, prefix="BED_Single")),
    "Bedside Table":     ("FLV/Furniture", lambda c, p: lib.nightstand(c, p)),
    "Wardrobe":          ("FLV/Furniture", lambda c, p: lib.wardrobe(c, p)),
    "Open Closet":       ("FLV/Furniture", lambda c, p: lib.open_closet(c, p)),
    "Bookshelf":         ("FLV/Furniture", lambda c, p: lib.bookshelf(c, p)),
    "Desk":              ("FLV/Furniture", lambda c, p: lib.desk(c, p)),
    "Dining Table":      ("FLV/Furniture", lambda c, p: lib.desk(c, p, width=1.6, depth=0.9, drawer=False,
                                                                 prefix="TABLE_Dining")),
    "Chair":             ("FLV/Furniture", lambda c, p: lib.chair(c, p)),
    "Armchair":          ("FLV/Furniture", lambda c, p: lib.armchair(c, p)),
    "Sofa":              ("FLV/Furniture", lambda c, p: lib.sofa(c, p)),
    "Side Table":        ("FLV/Furniture", lambda c, p: lib.side_table(c, p)),
    "TV and Stand":      ("FLV/Furniture", lambda c, p: lib.tv_stand(c, p)),
    "Rug":               ("FLV/Furniture", lambda c, p: lib.rug(c, p, (2.4, 1.7))),
    "Coat Rack":         ("FLV/Furniture", lambda c, p: lib.coat_rack(c, p)),
    "Potted Plant":      ("FLV/Furniture", lambda c, p: lib.plant(c, p)),
    "Table Lamp":        ("FLV/Lighting", lambda c, p: lib.table_lamp(c, c, p)),
    "Floor Lamp":        ("FLV/Lighting", lambda c, p: lib.floor_lamp(c, c, p)),
    "Desk Lamp":         ("FLV/Lighting", lambda c, p: lib.desk_lamp(c, c, p)),
    "Pendant Lamp":      ("FLV/Lighting", lambda c, p: lib.pendant_lamp(c, c, (p[0], p[1], 2.8))),
    "Ceiling Light":     ("FLV/Lighting", lambda c, p: lib.ceiling_light(c, c, (p[0], p[1], 2.8))),
    "Candle":            ("FLV/Lighting", lambda c, p: lib.candle(c, c, p)),
    "Flashlight":        ("FLV/Lighting", lambda c, p: lib.flashlight(c, c, p)),
    "Door":              ("FLV/Architecture", lambda c, p: lib.door(c, p)),
    "Window":            ("FLV/Architecture", lambda c, p: lib.window(c, (p[0], p[1], 1.6), 1.4, 1.4, 0.15)),
    "Curtains":          ("FLV/Architecture", lambda c, p: lib.curtains(c, (p[0], p[1], 2.45), 2.0, 2.42)),
    "Wall Panels":       ("FLV/Architecture", lambda c, p: lib.strips("DECOR_Wall_Panels", c, lib.M("MAT_Wall_Panel"),
                                                                       2.0, 2.3, 7, 0.012, p)),
    "Painting":          ("FLV/Decor", lambda c, p: lib.wall_art(c, (p[0], p[1], 1.6))),
    "Wall Clock":        ("FLV/Decor", lambda c, p: lib.wall_clock(c, (p[0], p[1], 1.8))),
    "Evidence Board":    ("FLV/Decor", lambda c, p: lib.evidence_board(c, (p[0], p[1], 1.5))),
    "Book Stack":        ("FLV/Props", lambda c, p: lib.book_stack(c, p, [("MAT_Book_Green", (0.22, 0.16, 0.035)),
                                                                          ("MAT_Book_Red", (0.2, 0.15, 0.03))])[0]),
    "Alarm Clock":       ("FLV/Props", lambda c, p: lib.alarm_clock(c, p)),
    "Water Glass":       ("FLV/Props", lambda c, p: lib.water_glass(c, p)),
    "Picture Frame":     ("FLV/Props", lambda c, p: lib.picture_frame(c, p)),
    "Laptop":            ("FLV/Props", lambda c, p: lib.laptop(c, p)),
    "Vase with Branches": ("FLV/Props", lambda c, p: lib.vase(c, p)),
    "Mug":               ("FLV/Props", lambda c, p: lib.mug(c, p)),
    "Bottle":            ("FLV/Props", lambda c, p: lib.bottle(c, p)),
    "Cardboard Box":     ("FLV/Props", lambda c, p: lib.cardboard_box(c, p)),
    "Suitcase":          ("FLV/Props", lambda c, p: lib.suitcase(c, p)),
    "Trash Bin":         ("FLV/Props", lambda c, p: lib.trash_bin(c, p)),
    "Knife":             ("FLV/Props", lambda c, p: lib.knife(c, p)),
    "Sealed Envelope":   ("FLV/Props", lambda c, p: lib.envelope(c, p)),
}


def catalog_id(path):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"flv-asset-catalog/{path}"))   # stable across rebuilds


def mark(id_block, catalog, description, tags=(), author="FLV"):
    id_block.asset_mark()
    data = id_block.asset_data
    data.catalog_id = catalog_id(catalog)
    data.description, data.author = description, author
    for tag in tags:
        data.tags.new(tag, skip_if_exists=True)
    id_block.asset_generate_preview()
    catalogs.add(catalog)


def wait_for_previews(timeout=120):
    """Thumbnails render in the background; don't save before they are all done."""
    assets = [i for data in (bpy.data.collections, bpy.data.worlds, bpy.data.materials) for i in data
              if i.asset_data]
    end = time.time() + timeout
    while time.time() < end and not all(i.preview and i.preview.image_size[0] for i in assets):
        time.sleep(0.2)


def grid(i, spacing=3.0, per_row=8):
    return Vector(((i % per_row) * spacing, -(i // per_row) * spacing, 0))


def collection_asset(name, i):
    coll = su.collection(name)
    view_layer = bpy.context.view_layer
    view_layer.active_layer_collection = view_layer.layer_collection.children[coll.name]
    spot = grid(i)
    coll.instance_offset = spot            # the drop point is the asset's floor origin
    return coll, spot


def build_procedural():
    su.reset_scene()
    for i, (name, (catalog, build)) in enumerate(PROCEDURAL.items()):
        coll, spot = collection_asset(name, i)
        build(coll, tuple(spot))
        mark(coll, catalog, f"{name} (procedural FLV asset, editable parts)",
             tags=[catalog.split("/")[-1].lower(), "flv", "stylized"])
    wait_for_previews()
    su.save_blend(ASSETS / "FLV_Procedural_Assets.blend")
    print(f"Procedural library: {len(PROCEDURAL)} assets")


def image(path, color=True):
    img = bpy.data.images.load(str(path), check_existing=True)
    if not color:
        img.colorspace_settings.name = "Non-Color"
    return img


def texture_material(name, files):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    for row, path in enumerate(files):
        tex = nodes.new("ShaderNodeTexImage")
        tex.location = (-700, 300 - row * 300)
        if "_diff_" in path.name:
            tex.image = image(path)
            links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        elif "_rough_" in path.name:
            tex.image = image(path, color=False)
            links.new(tex.outputs["Color"], bsdf.inputs["Roughness"])
        elif "_nor_gl_" in path.name:
            tex.image = image(path, color=False)
            normal = nodes.new("ShaderNodeNormalMap")
            normal.location = (-300, 300 - row * 300)
            links.new(tex.outputs["Color"], normal.inputs["Color"])
            links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def sky_world(name, path):
    world = bpy.data.worlds.new(name)
    if world.node_tree is None:
        world.use_nodes = True
    env = world.node_tree.nodes.new("ShaderNodeTexEnvironment")
    env.image = image(path)
    env.location = (-300, 300)
    world.node_tree.links.new(env.outputs["Color"], world.node_tree.nodes["Background"].inputs["Color"])
    return world


def build_polyhaven():
    manifest_file = ASSETS / "polyhaven_manifest.json"
    if not manifest_file.is_file():
        print("Poly Haven library skipped: run scripts/download_assets.py first")
        return
    su.reset_scene()
    bpy.data.batch_remove(list(bpy.data.images))
    counts = {"models": 0, "hdris": 0, "textures": 0}
    for asset_id, info in sorted(json.loads(manifest_file.read_text()).items()):
        files = [ASSETS / f for f in info["files"]]
        kind, tags = info["type"], info["categories"]
        description = f"{info['name']} - CC0 from {info['source']}"
        author = ", ".join(info["authors"]) or "Poly Haven"
        if kind == "models":
            name = info["name"] if info["name"] not in bpy.data.collections else f"{info['name']} ({asset_id})"
            coll, spot = collection_asset(name, counts["models"])
            bpy.ops.import_scene.gltf(filepath=str(next(f for f in files if f.suffix == ".gltf")),
                                    import_pack_images=False)    # link textures, don't copy them
            for obj in coll.objects:
                if obj.parent is None:
                    obj.location += spot
            category = next(c for c in MODEL_CATALOGS if c in tags)
            mark(coll, f"Poly Haven/Models/{category.title()}", description, tags, author)
        elif kind == "hdris":
            mark(sky_world(info["name"], files[0]), "Poly Haven/Night Skies", description, tags, author)
        else:
            category = "Fabric" if "fabric" in tags else "Indoor"
            mark(texture_material(info["name"], files), f"Poly Haven/Materials/{category}", description, tags,
                 author)
        counts[kind] += 1
    wait_for_previews()
    su.save_blend(ASSETS / "FLV_PolyHaven_Assets.blend", compress=True)
    print(f"Poly Haven library: {counts}")


def write_catalogs():
    paths = {"/".join(p.split("/")[:i]) for p in catalogs for i in range(1, p.count("/") + 2)}
    lines = ["# Asset catalogs for the FLV asset library, written by scripts/build_asset_library.py",
             "VERSION 1", ""]
    lines += [f"{catalog_id(p)}:{p}:{p.replace('/', '-')}" for p in sorted(paths)]
    (ASSETS / "blender_assets.cats.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    build_procedural()
    build_polyhaven()
    write_catalogs()
