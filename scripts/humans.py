"""
Realistic characters for FLV films: our own generated characters (assets/characters/<Name>/<Name>.blend, made
by the Generated_Characters pipeline: rigged, skinned, textured, dressed, with 47 ARKit-named face shapes).

    import humans
    rig = humans.build(SPEC)                       # appends the character: body, eyes, hair, clothes, face shapes, rig
    humans.relax_arms(rig)                         # out of the A pose
    humans.face(rig, frame, {"browInnerUp": 0.7})  # ARKit face units, keyframed
    humans.lip_sync(rig, "line.wav", start_frame=1)   # face from the voice (scripts/speech_face.py)
    humans.blinks(rig, 1, 240)
    humans.retarget(rig, "assets/mocap/cmu/77_14.bvh", start_frame=1)

A SPEC is a dict: name (object names in the scene), character (folder in assets/characters), film_eye
("left"/"right": a pale filmed eye), fabrics={garment: (Poly Haven texture id in assets/textures/polyhaven,
tint, scale)} to re-dress a garment (garments are named after the character's meshes: shirt, trousers,
nightshirt ...), hair_tint / brow_tint / beard_tint (multiplied onto the hair / eyebrow / beard colour),
height (metres: the character scaled to it, for stand-ins).

Our rigs use Mixamo bone names; build() renames them to the names this toolkit's motion code uses
(BONE_NAMES: Spine -> LowerBack, Spine1 -> Spine, Spine2 -> Spine1, Neck -> Neck1, fingers LeftHandIndex1 ...),
and re-rolls the hands so the palm faces the hand bone's -Z and +X curls a finger toward the palm.
Eyes turn with the LeftEye / RightEye bones; the eyeLookUp/Down face shapes move the lids with them.

Self-check (retargeter, feet, reach, and one of our characters):
    blender -b --python scripts/humans.py -- --selfcheck
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parent.parent
TEXTURES = ROOT / "assets" / "textures" / "polyhaven"
CHARACTERS = ROOT / "assets" / "characters"

# our rig (Mixamo names, prefix dropped) -> the toolkit's names, applied in this order
BONE_NAMES = (("Spine", "LowerBack"), ("Spine1", "Spine"), ("Spine2", "Spine1"), ("Neck", "Neck1"))
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")

# BVH bone -> rig bone. CMU clips mostly use the rig's own names (their single finger chain is not mapped:
# our hands have five fingers, posed by grip()); 100STYLE (XSens) needs a map.
CMU = {n: "" for s in ("Left", "Right") for n in (f"{s}HandIndex1", f"{s}FingerBase", f"{s[0]}Thumb")}
CMU.update({"LThumb": "", "RThumb": ""})
STYLE100 = {"Hips": "Hips", "Chest": "LowerBack", "Chest2": "Spine", "Chest4": "Spine1", "Neck": "Neck1",
            "Head": "Head", "LeftCollar": "LeftShoulder", "LeftShoulder": "LeftArm", "LeftElbow": "LeftForeArm",
            "LeftWrist": "LeftHand", "RightCollar": "RightShoulder", "RightShoulder": "RightArm",
            "RightElbow": "RightForeArm", "RightWrist": "RightHand", "LeftHip": "LeftUpLeg", "LeftKnee": "LeftLeg",
            "LeftAnkle": "LeftFoot", "LeftToe": "LeftToeBase", "RightHip": "RightUpLeg", "RightKnee": "RightLeg",
            "RightAnkle": "RightFoot", "RightToe": "RightToeBase"}


def build(spec, location=(0, 0, 0)):
    """Append one of our characters (assets/characters/<character>/<character>.blend) into the current scene,
    named after spec["name"]; returns its armature (meshes are its children, named <name>.body, .eyes, .mouth,
    .hair, .brows, .lashes, .beard and one per garment). Skin under the clothes was already removed when the
    character was generated, so nothing pokes through."""
    folder = CHARACTERS / spec["character"]
    path = folder / f"{spec['character']}.blend"
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = list(src.objects)
    rig = next(o for o in dst.objects if o.type == "ARMATURE")
    keep = {rig} | {o for o in dst.objects if o.type == "MESH" and o.parent is rig}
    coll = bpy.context.collection
    for o in dst.objects:
        if o in keep:
            coll.objects.link(o)
        else:                                     # preview cameras and lights saved with the character
            bpy.data.objects.remove(o)
    name = spec["name"]
    prefix = spec["character"] + "_"
    rig.name = rig.data.name = name
    for o in rig.children:
        part = o.name[len(prefix):] if o.name.startswith(prefix) else o.name
        o.name = o.data.name = f"{name}.{part.lower()}"
    _rename_bones(rig)
    _hands_like_toolkit(rig)
    for obj in rig.children:                  # textures saved with the generator's own (Windows) paths: use ours
        for mat in obj.data.materials:
            for node in mat.node_tree.nodes if mat and mat.node_tree else ():
                img = node.image if node.type == "TEX_IMAGE" else None
                if img and not Path(bpy.path.abspath(img.filepath)).exists():
                    mine = folder / "textures" / img.filepath.replace("\\", "/").rsplit("/", 1)[-1]
                    if mine.exists():
                        img.filepath = str(mine)
                        img.reload()
    rig.location = location
    for pb in rig.pose.bones:                # one rotation channel for poses, mocap and the living-body layers
        pb.rotation_mode = "QUATERNION"
    parts = {o.name.split(".", 1)[1]: o for o in rig.children}
    if spec.get("film_eye"):
        _film_eye(parts["eyes"], spec["film_eye"])
    for garment, (fabric_id, tint, scale) in spec.get("fabrics", {}).items():
        fabric(parts[garment], fabric_id, tint, scale)
    for part, key in (("hair", "hair_tint"), ("brows", "brow_tint"), ("beard", "beard_tint")):
        if spec.get(key) and part in parts:
            tint_material(parts[part], spec[key])
    for obj in face_meshes(rig):          # lips closed at rest (lip_sync fades this out while speaking)
        if "mouthShrugLower" in obj.data.shape_keys.key_blocks:
            obj.data.shape_keys.key_blocks["mouthShrugLower"].value = REST_SEAL
    bpy.context.view_layer.update()
    if spec.get("height"):                # the same character made taller or shorter (stand-ins)
        top = max((parts["body"].matrix_world @ v.co).z for v in parts["body"].data.vertices) - rig.location.z
        rig.scale = (spec["height"] / top,) * 3
        bpy.context.view_layer.update()
    return rig


def _rename_bones(rig):
    """mixamorig:Spine -> LowerBack and so on (BONE_NAMES); vertex groups follow the bone names."""
    for b in rig.data.bones:
        if b.name.startswith("mixamorig:"):
            b.name = b.name[len("mixamorig:"):]
    for old, new in BONE_NAMES:
        if old in rig.data.bones:
            rig.data.bones[old].name = new
    for o in rig.children:
        for m in o.modifiers:
            if m.type == "ARMATURE":
                m.object = rig


def _hands_like_toolkit(rig):
    """Re-roll hand and finger bones (rest pose only; the skin does not move): the hand's palm faces its -Z
    (as hand_frame() expects) and each finger's +X rotation curls it toward the palm (as grip() expects)."""
    view = bpy.context.view_layer
    active = view.objects.active
    view.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = rig.data.edit_bones
    for side in ("Left", "Right"):
        hand, i1, p1 = (eb[f"{side}Hand"].head, eb[f"{side}HandIndex1"].head, eb[f"{side}HandPinky1"].head)
        back = (i1 - hand).cross(p1 - hand)                  # normal of the plane of the knuckles and wrist
        thumb = eb[f"{side}HandThumb2"].head - (hand + i1 + p1) / 3
        if back.dot(thumb) > 0:                              # the thumb sits on the palm side, a few cm off it
            back = -back
        back.normalize()
        eb[f"{side}Hand"].align_roll(back)                   # +Z = back of the hand, palm on -Z
        for finger in FINGERS:
            for j in (1, 2, 3):
                bone = eb.get(f"{side}Hand{finger}{j}")
                if bone is not None:
                    bone.align_roll(-back)                   # +Z toward the palm: +X curls the finger in
    bpy.ops.object.mode_set(mode="OBJECT")
    view.objects.active = active


def hide_under(body, garments, reach=0.03, margin=0.006, poking=True, keep_rim=0.06):
    """Mask the parts of `body` (skin, or a garment) that sit under the given garments, so knees, elbows and
    sock tops don't poke through (some MakeHuman clothes ship without a delete group). poking=True also hides
    surface just outside a garment, away from its hems. Skin within `keep_rim` of an opening (collar, cuff,
    hem) stays - also when the pack's own Delete.<garment> group hid it: it shows through the opening, and
    hiding it left a dark hole inside the collar."""
    from mathutils.bvhtree import BVHTree
    deps = bpy.context.evaluated_depsgraph_get()
    saved = [(m, m.show_viewport) for m in body.modifiers]
    for m, _ in saved:                     # shape keys only: keep the original vertex order
        m.show_viewport = False
    deps.update()
    coords = [v.co.copy() for v in body.evaluated_get(deps).to_mesh().vertices]
    body.evaluated_get(deps).to_mesh_clear()
    for m, shown in saved:
        m.show_viewport = shown
    from mathutils.kdtree import KDTree
    hidden = set()
    for garment in garments:
        tree = BVHTree.FromObject(garment, deps)
        mesh = garment.data
        edge_faces = {}
        for poly in mesh.polygons:
            for key in poly.edge_keys:
                edge_faces[key] = edge_faces.get(key, 0) + 1
        rim = {v for key, n in edge_faces.items() if n == 1 for v in key}     # cuffs, collar, hems
        edges = KDTree(max(len(rim), 1))
        for v in rim:
            edges.insert(mesh.vertices[v].co, v)
        edges.balance()
        to_local = garment.matrix_world.inverted() @ body.matrix_world
        packed = body.vertex_groups.get("Delete." + garment.name.split(".", 1)[-1])   # the pack's own group
        reopen = []
        for i, co in enumerate(coords):
            p = to_local @ co
            loc, normal, _, dist = tree.find_nearest(p)
            if loc is None or dist > reach:
                continue
            to_rim = edges.find(loc)[2] if rim else 1.0
            if to_rim <= keep_rim:
                reopen.append(i)
            inside = (p - loc).dot(normal) < margin and to_rim > keep_rim
            outside_close = poking and dist < 0.015 and to_rim > 0.04                  # mid-garment
            if inside or outside_close:
                hidden.add(i)
        if packed is not None and reopen:
            packed.remove(reopen)
    if not hidden:
        return
    group = body.vertex_groups.new(name="Delete.under_clothes")
    group.add(sorted(hidden), 1.0, "ADD")
    mask = body.modifiers.new("Delete.under_clothes", "MASK")
    mask.vertex_group, mask.invert_vertex_group = group.name, True


def tint_material(obj, rgb):
    """Multiply a mesh's base colour by rgb (darker hair or eyebrows than the asset's own texture)."""
    for mat in obj.data.materials:
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
        if not bsdf.inputs["Base Color"].links:                  # a flat colour
            c = bsdf.inputs["Base Color"].default_value
            bsdf.inputs["Base Color"].default_value = (c[0] * rgb[0], c[1] * rgb[1], c[2] * rgb[2], c[3])
            continue
        src = bsdf.inputs["Base Color"].links[0].from_socket
        mix = nodes.new("ShaderNodeMix")
        mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs["B"].default_value = (*rgb, 1)
        links.new(src, mix.inputs["A"])
        links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])


def _film_eye(obj, film_eye):
    """One eye ("left" / "right") gets a milky, pale-blue film over the iris; the other keeps its colour."""
    base = obj.data.materials[0]
    mat = base.copy()
    mat.name = f"{base.name}.film"
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    mix = nodes.new("ShaderNodeMix")
    mix.data_type, mix.blend_type = "RGBA", "MIX"
    mix.inputs["Factor"].default_value = 0.55
    mix.inputs["B"].default_value = (0.78, 0.84, 0.88, 1)          # "a pale blue eye, with a film over it"
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    src = bsdf.inputs["Base Color"].links[0].from_socket
    links.new(src, mix.inputs["A"])
    links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    obj.data.materials.append(mat)
    film = len(obj.data.materials) - 1
    sign = 1 if film_eye == "left" else -1          # the character faces -Y, so its left eye is on +X
    for poly in obj.data.polygons:
        if sign * sum(obj.data.vertices[v].co.x for v in poly.vertices) > 0:
            poly.material_index = film


def fabric(obj, texture_id, tint=(1, 1, 1), scale=6):
    """Replace a garment's material with a Poly Haven fabric, tinted."""
    folder = TEXTURES / texture_id
    mat = bpy.data.materials.new(f"{obj.name}.{texture_id}")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    uv = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (scale, scale, scale)
    links.new(uv.outputs["UV"], mapping.inputs["Vector"])

    def image(kind, colour=True):
        files = list(folder.glob(f"*_{kind}_*.jpg"))
        if not files:
            return None
        node = nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(str(files[0]), check_existing=True)
        node.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        links.new(mapping.outputs["Vector"], node.inputs["Vector"])
        return node

    diff = image("diff")
    grey = nodes.new("ShaderNodeHueSaturation")          # keep the weave, drop the texture's own colour
    grey.inputs["Saturation"].default_value = 0.0
    links.new(diff.outputs["Color"], grey.inputs["Color"])
    tinted = nodes.new("ShaderNodeMix")
    tinted.data_type, tinted.blend_type = "RGBA", "MULTIPLY"
    tinted.inputs["Factor"].default_value = 1.0
    tinted.inputs["B"].default_value = (*tint, 1)
    links.new(grey.outputs["Color"], tinted.inputs["A"])
    links.new(tinted.outputs["Result"], bsdf.inputs["Base Color"])
    rough = image("rough", colour=False)
    if rough:
        links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = 0.85
    nor = image("nor_gl", colour=False)
    if nor:
        normal = nodes.new("ShaderNodeNormalMap")
        links.new(nor.outputs["Color"], normal.inputs["Color"])
        links.new(normal.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Sheen Weight"].default_value = 0.3       # cloth catches light at grazing angles
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:      # faces that used a second slot would otherwise render default grey
        poly.material_index = 0


# --- posing ---------------------------------------------------------------------------------------

def aim(rig, bone, direction):
    """Rotate a pose bone (in world space) so it points along `direction`."""
    pb = rig.pose.bones[bone]
    world = rig.matrix_world @ pb.matrix
    current = (world.to_3x3() @ Vector((0, 1, 0))).normalized()
    turn = current.rotation_difference(Vector(direction).normalized()).to_matrix()
    new = Matrix.Translation(world.translation) @ (turn @ world.to_3x3()).to_4x4()
    pb.matrix = rig.matrix_world.inverted() @ new
    bpy.context.view_layer.update()


def relax_arms(rig, spread=0.12, forward=0.08):
    """Arms down by the sides, elbows slightly bent (our rigs rest in an A pose). Directions are in
    the character's own frame, so this works standing or lying."""
    bpy.context.view_layer.update()
    to_world = rig.matrix_world.to_3x3()
    for side, sx in (("Left", 1), ("Right", -1)):
        aim(rig, f"{side}Arm", to_world @ Vector((sx * spread, -forward, -1)))
        aim(rig, f"{side}ForeArm", to_world @ Vector((sx * spread * 0.6, -forward * 2.5, -1)))


# --- face -----------------------------------------------------------------------------------------

def face_meshes(rig):
    return [o for o in rig.children if o.type == "MESH" and o.data.shape_keys]


def face(rig, frame, values, meshes=None):
    """Keyframe face units/visemes (shape key name -> weight) on the body and everything that follows it."""
    for obj in meshes or face_meshes(rig):
        keys = obj.data.shape_keys.key_blocks
        for name, value in values.items():
            if name in keys:
                keys[name].value = value
                keys[name].keyframe_insert("value", frame=frame)


# Gain on the speech model's output per shape prefix. Our jawOpen is a real hinge rotation (18 degrees at 1)
# and the lip raisers are moderate, so speech needs only a little help opening the jaw: real speech opens
# mostly with the jaw, the teeth part, and the lips stay soft over the teeth.
SPEECH_GAIN = {"jawOpen": 1.3, "mouthUpperUp": 0.7, "mouthLowerDown": 0.8, "mouthShrugUpper": 0.8}
REST_SEAL = 0.0     # mouthShrugLower at rest: our characters' neutral mouth is already closed


def wear(rig, keys):
    """A face worn by sleepless nights: keys [(frame, w 0..1)], each held from its frame on (it never eases). w
    drains the skin (saturation 1 - 0.35 w, value 1 - 0.18 w) and weighs the lids (blinks + 0.15 w); kept on
    rig["worn"] for the continuity check. Call after every face/eyes key: the lids are added to the blinks there."""
    keys = sorted(keys)
    assert all(b[1] >= a[1] for a, b in zip(keys, keys[1:])), f"worn eases: {keys}"
    steps = [(max(1, keys[0][0] - 1), 0.0)] + keys
    at = lambda f: max([w for k, w in steps if k <= f] or [0.0])

    def fcurves(idb):
        ad = idb.animation_data
        return [fc for layer in ad.action.layers for strip in layer.strips
                for fc in strip.channelbag(ad.action_slot).fcurves] if ad and ad.action else []
    skin = next(m for o in rig.children if o.type == "MESH" for m in o.data.materials if m and "Skin" in m.name)
    nodes = skin.node_tree.nodes
    hs = nodes.get("Worn")
    if hs is None:
        bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
        src = bsdf.inputs["Base Color"].links[0].from_socket
        hs = nodes.new("ShaderNodeHueSaturation")
        hs.name = "Worn"
        skin.node_tree.links.new(src, hs.inputs["Color"])
        skin.node_tree.links.new(hs.outputs["Color"], bsdf.inputs["Base Color"])
    for f, w in steps:
        rig["worn"] = w
        rig.keyframe_insert('["worn"]', frame=f)
        hs.inputs["Saturation"].default_value, hs.inputs["Value"].default_value = 1 - 0.35 * w, 1 - 0.18 * w
        hs.inputs["Saturation"].keyframe_insert("default_value", frame=f)
        hs.inputs["Value"].keyframe_insert("default_value", frame=f)
    for fc in fcurves(rig) + fcurves(skin.node_tree):
        if "worn" in fc.data_path or "Worn" in fc.data_path:
            for k in fc.keyframe_points:
                k.interpolation = "CONSTANT"
    names = ('key_blocks["eyeBlinkLeft"].value', 'key_blocks["eyeBlinkRight"].value')
    for obj in face_meshes(rig):
        sk = obj.data.shape_keys
        for path in names:
            if not any(fc.data_path == path for fc in fcurves(sk)):
                kb = sk.key_blocks.get(path.split('"')[1])
                if kb is None:
                    continue
                kb.keyframe_insert("value", frame=1)
        for fc in fcurves(sk):
            if fc.data_path not in names:
                continue
            for f, _ in steps:                       # step edges, so the lids drop at each night and not before
                for e in (f - 1, f):
                    fc.keyframe_points.insert(e, fc.evaluate(e), options={"FAST"})
            for k in fc.keyframe_points:
                d = 0.15 * at(k.co.x) * (1 - k.co.y)
                k.co.y += d
                k.handle_left.y += d
                k.handle_right.y += d
            fc.update()


def lip_sync(rig, wav, start_frame, fps=24, lead=1.0, gain=1.0):
    """Lips, jaw, cheeks and tongue driven by the voice itself: scripts/speech_face.py runs Wav2ARKit, a model
    learned from real talking faces, so the jaw opens only a little while the lips do most of the work, sounds
    blend into each other (coarticulation) and the lips close fully on m/b/p. The result is added on top of
    the expression already keyed (fear, a smile). `lead` frames: the face moves just before the sound, as lips
    shape a sound before it is heard. Blinks and eye direction stay with the shot (eyes(), face()).
    Returns {"phrases": [(first, last frame)], "pauses": [frame]} for breathe() and eyes()."""
    import numpy as np
    data = _speech_face(wav)
    weights, src_fps = np.array(data["frames"]), data["fps"]
    # the model's own resting face is slightly open: measure each shape at its quietest and subtract that,
    # then gate by voice activity so pauses between phrases close the mouth
    weights = np.clip(weights - np.percentile(weights, 10, axis=0), 0, None) * np.array(data["voice"])[:, None]
    scale = {}
    for name in data["names"]:
        if name.startswith(("eyeBlink", "eyeLook")):
            continue                                   # the shot owns blinks and gaze
        scale[name] = 0.6 if name.startswith("brow") else 0.5 if name.startswith(("eyeSquint", "eyeWide")) else gain
        scale[name] *= next((g for prefix, g in SPEECH_GAIN.items() if name.startswith(prefix)), 1.0)
    meshes = face_meshes(rig)
    body = next(o for o in meshes if o.name.endswith(".body"))
    keys = body.data.shape_keys.key_blocks
    frames = int(len(weights) / src_fps * fps) + 2
    columns = {n: i for i, n in enumerate(data["names"])}
    scene = bpy.context.scene
    base = {}                                          # the expression underneath, read before we key anything
    for i in range(frames):
        scene.frame_set(start_frame + i)
        base[i] = {n: keys[n].value for n in scale if n in keys}
    seal = "mouthShrugLower"
    for i in range(frames):
        s = min(max((i + lead) / fps * src_fps, 0), len(weights) - 1)      # sample the 30 fps model at 24 fps
        a, frac = int(s), s - int(s)
        b = min(a + 1, len(weights) - 1)
        row = weights[a] * (1 - frac) + weights[b] * frac
        opening = row[columns["jawOpen"]] + row[columns["mouthLowerDownLeft"]]
        rest = max(0.0, 1 - opening / 0.12)            # the resting lip seal (REST_SEAL) gives way as the mouth opens
        values = {n: min(1.0, base[i][n] * (rest if n == seal else 1) + row[columns[n]] * k)
                  for n, k in scale.items() if n in base[i]}
        face(rig, start_frame + i, values, meshes)
    face(rig, start_frame + frames, base[frames - 1], meshes)          # back to the expression after the line
    # phrases (voice on, gaps under 0.25 s merged) and the pauses between them, in scene frames
    voice = np.array(data["voice"]) > 0.5
    spans, on = [], None
    for i, v in enumerate(voice):
        if v and on is None:
            on = i
        if not v and on is not None:
            spans.append([on, i - 1])
            on = None
    if on is not None:
        spans.append([on, len(voice) - 1])
    merged = []
    for a, b in spans:
        if merged and (a - merged[-1][1]) / src_fps < 0.25:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    to_frame = lambda i: start_frame + i / src_fps * fps - lead
    phrases = [(to_frame(a), to_frame(b)) for a, b in merged]
    return {"phrases": phrases, "pauses": [(b1 + a2) / 2 for (_, b1), (a2, _) in zip(phrases, phrases[1:])]}


def _speech_face(wav):
    """Face-unit weights for a voice line: Wav2ARKit (scripts/speech_face.py) when its Python environment and
    model are installed (scripts/download_film_kit.sh), else _speech_envelope()."""
    python = next((p for p in (ROOT / ".venv" / "bin" / "python", ROOT / ".venv" / "Scripts" / "python.exe")
                   if p.exists()), None)
    if python is not None and (ROOT / "voices" / "wav2arkit" / "config.json").exists():
        out = Path(bpy.app.tempdir) / "speech_face.json"
        subprocess.run([str(python), "-I", str(ROOT / "scripts" / "speech_face.py"), str(wav), str(out)],
                       check=True, capture_output=True)
        return json.loads(out.read_text())
    print(f"humans.lip_sync: Wav2ARKit not installed, using the loudness/spectrum fallback for {Path(wav).name}")
    return _speech_envelope(wav)


def _speech_envelope(wav, fps=30):
    """Fallback lips from the sound alone (16-bit PCM WAV): the jaw follows loudness, dark (low spectral
    centroid) vowels round the lips, bright sounds (s, f, ee) spread them and close the jaw. Same output as
    speech_face.py, so lip_sync() treats both alike. Coarser than the model: no m/b/p closures."""
    import wave
    import numpy as np
    with wave.open(str(wav)) as w:
        rate, chans, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    pcm = np.frombuffer(raw, {1: np.int8, 2: np.int16, 4: np.int32}[width]).astype(np.float32)
    pcm = pcm.reshape(-1, chans).mean(1) / float(2 ** (8 * width - 1))
    hop = rate // fps
    n = len(pcm) // hop
    win = np.hanning(2 * hop)
    rms, cent = np.zeros(n), np.zeros(n)
    freqs = np.fft.rfftfreq(2 * hop, 1 / rate)
    for i in range(n):
        seg = pcm[max(0, i * hop - hop // 2): i * hop - hop // 2 + 2 * hop]
        seg = np.pad(seg, (0, 2 * hop - len(seg)))
        rms[i] = np.sqrt(np.mean(seg ** 2) + 1e-12)
        spec = np.abs(np.fft.rfft(seg * win))
        cent[i] = (spec * freqs).sum() / (spec.sum() + 1e-9)
    db = 20 * np.log10(rms / (rms.max() + 1e-12))
    voice = np.convolve(np.clip((db + 50) / 18, 0, 1), np.ones(3) / 3, mode="same")
    loud = np.clip((db + 38) / 30, 0, 1) ** 0.8
    rounded = np.clip((1400 - cent) / 800, 0, 1) * voice
    spread = np.clip((cent - 1800) / 1500, 0, 1) * voice

    def follow(x, up=0.6, down=0.35):                   # muscles: quick to open, slower to relax
        out, y = np.zeros_like(x), 0.0
        for i, v in enumerate(x):
            y += (up if v > y else down) * (v - y)
            out[i] = y
        return out
    jaw = follow(0.30 * loud * (1 - 0.5 * spread))
    shapes = {"jawOpen": jaw, "mouthLowerDownLeft": follow(0.25 * loud), "mouthLowerDownRight": follow(0.25 * loud),
              "mouthUpperUpLeft": follow(0.12 * loud), "mouthUpperUpRight": follow(0.12 * loud),
              "mouthFunnel": follow(0.35 * rounded * loud), "mouthPucker": follow(0.15 * rounded * loud),
              "mouthStretchLeft": follow(0.25 * spread), "mouthStretchRight": follow(0.25 * spread)}
    names = list(shapes)
    frames = np.stack([shapes[k] for k in names], 1)
    return {"fps": fps, "names": names, "frames": np.clip(frames, 0, 1).round(4).tolist(), "voice": voice.round(3).tolist()}


# --- living body: eyes, breathing, sway, startle --------------------------------------------------------
# Layers add on top of whatever the bones already do (mocap or a held pose), frame by frame, so they combine.
#
# Eyes: "Eyes Alive" (Lee, Badler & Badler, SIGGRAPH 2002), measured at 30 fps:
#   saccade size P(A) ~ e^(-A/6.9) (90% under 15 deg); direction (deg: %) 0:15.5 45:6.5 90:17.7 135:7.4
#   180:16.8 225:7.9 270:20.4 315:7.8; duration D = 25 ms + 2.4 ms/deg; mutual-gaze / gaze-away spells:
#   talking 3.1+-3.2 s / 0.93+-0.8 s, listening 7.9+-1.6 s / 0.43+-0.24 s. Gaze shifts over ~15 deg bring
#   the head (eyes lead, head follows ~2 frames later and the eyes counter-rotate as it arrives).
# Blinks: ~17/min at rest, more while speaking, fewer while listening hard or afraid; the lid closes in ~80 ms
#   and reopens in ~150 ms; big saccades and speech pauses often carry a blink; some blinks are partial.
# Gaze range per eyeLook weight: 1 = ~38 deg out/in, 18 deg up, 27 deg down. Our eyeballs turn on their eye
#   bones by the exact angle; the eyeLookUp/Down shapes move the lids with them (up 9 deg, down 15 deg at 1:
#   looking down lowers the upper lid, as real lids follow the eye).
EYE_DEG = {"out": 37.6, "in": 39.5, "up": 18.1, "down": 27.0}
SACCADE_DIRS = ((0, 15.54), (45, 6.46), (90, 17.69), (135, 7.44), (180, 16.80), (225, 7.89), (270, 20.38),
                (315, 7.79))
GAZE_MODES = {   # (mutual mean, sd), (away mean, sd) in seconds; blinks per minute; largest saccade
    "talking": ((3.13, 3.16), (0.93, 0.80), 24, 25),
    "listening": ((7.92, 1.57), (0.43, 0.24), 12, 20),
    "fear": ((0.6, 0.35), (0.5, 0.3), 7, 30),            # scanning the dark, blinking suppressed
    "thinking": ((1.0, 0.6), (1.6, 0.9), 15, 20),        # looking away while recalling
}


def _layer(rig, start, end, offsets, local=False):
    """Add small rotations on top of the motion already there, every frame from start to end.
    offsets(frame) -> {bone: (yaw, pitch, roll)} in degrees, in the character's frame: yaw turns to the
    character's left, pitch nods forward/down, roll tilts to the left. local=True: offsets(frame) ->
    {bone: Quaternion}, applied in the bone's own space after its current rotation (mocap gesture deltas).
    The underlying motion is read for every frame first, so layers stack instead of feeding on their own keys."""
    from mathutils import Quaternion
    scene = bpy.context.scene
    plan = {f: offsets(f) for f in range(start, end + 1)}
    bones = {b for offs in plan.values() for b in offs}
    for name in bones:
        pb = rig.pose.bones[name]
        if pb.rotation_mode != "QUATERNION":
            pb.rotation_quaternion = pb.rotation_euler.to_quaternion()
            pb.rotation_mode = "QUATERNION"
    base = {}
    for f in plan:
        scene.frame_set(f)
        base[f] = {n: (rig.pose.bones[n].rotation_quaternion.copy(), rig.pose.bones[n].matrix.to_3x3().normalized())
                   for n in bones}
    for f, offs in plan.items():
        for name, off in offs.items():
            q, orient = base[f][name]
            if local:
                pb = rig.pose.bones[name]
                pb.rotation_quaternion = q @ off
                pb.keyframe_insert("rotation_quaternion", frame=f)
                continue
            yaw, pitch, roll = off
            to_local = orient.inverted()             # rotate about the bone as it is posed now, not at rest
            for axis, deg in (((0, 0, 1), yaw), ((1, 0, 0), pitch), ((0, 1, 0), roll)):
                if deg:
                    q = q @ Quaternion((to_local @ Vector(axis)).normalized(), math.radians(deg))
            pb = rig.pose.bones[name]
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f)


def eyes(rig, start, end, mode="talking", look=(0.0, 0.0), pauses=(), seed=1, fps=24, head=True):
    """Gaze, saccades, eyelids and blinks for frames start..end. `look` = where mutual gaze points, as
    (degrees to the character's left, degrees up) from straight ahead; `pauses` = frames where speech
    pauses (blinks gather there). Head turns join big gaze shifts unless head=False. `look` and `mode` may
    also be functions of the frame (whom to look at and how, as a scene goes on): one call then covers a whole
    scene and the head turns smoothly from one person to the next instead of snapping back between calls."""
    rng = random.Random(seed)
    look_at = look if callable(look) else (lambda f, v=tuple(look): v)
    mode_at = mode if callable(mode) else (lambda f, m=mode: m)
    blink_rate = GAZE_MODES[mode_at(start)][2]
    meshes = face_meshes(rig)
    targets, f, away = [], float(start), False          # alternate mutual-gaze and gaze-away spells
    while f < end:
        (mm, ms), (am, asd), _, biggest = GAZE_MODES[mode_at(f)]
        look = look_at(f)
        if away:
            size = min(rng.expovariate(1 / 6.9), biggest)                      # P(A) ~ e^(-A/6.9)
            angle = math.radians(rng.choices([d for d, _ in SACCADE_DIRS], [w for _, w in SACCADE_DIRS])[0])
            targets.append((f, (look[0] + size * math.cos(angle), look[1] + size * math.sin(angle))))
        else:
            targets.append((f, tuple(look)))
        mean, sd = (am, asd) if away else (mm, ms)
        nxt = f + max(0.12, rng.gauss(mean, sd)) * fps
        moved = next((g for g in range(int(f) + 1, int(min(nxt, end))) if
                      math.hypot(look_at(g)[0] - look[0], look_at(g)[1] - look[1]) > 2.0), None)
        if moved is not None:                         # the person to look at changed: look at them now
            f, away = float(moved), False
            continue
        f = nxt
        away = not away
    plans, head_now, previous = [], (0.0, 0.0), (0.0, 0.0)
    for f, gaze in targets:
        jump = math.hypot(gaze[0] - previous[0], gaze[1] - previous[1])
        travel = max(1.0, (0.025 + 0.0024 * jump) * fps)                         # D = 25 ms + 2.4 ms/deg
        rel = gaze                                   # head share is measured from straight ahead
        reach = math.hypot(*rel)
        share = max(0.0, 1 - 15 / reach) * 0.65 if (head and reach > 15) else 0.0   # head takes the excess
        head_next = (rel[0] * share, rel[1] * share)
        _key_eyes(rig, meshes, f, (previous[0] - head_now[0], previous[1] - head_now[1]))
        _key_eyes(rig, meshes, f + travel, (gaze[0] - head_now[0], gaze[1] - head_now[1]))   # eyes land first
        if head_next != head_now:            # ...then the head follows and the eyes counter-rotate (VOR)
            a, b = f + 2, f + 2 + 0.25 * fps
            plans.append((a, b, head_now, head_next))
            _key_eyes(rig, meshes, b, (gaze[0] - head_next[0], gaze[1] - head_next[1]))
            head_now = head_next
        if jump > 20 and rng.random() < 0.6:                                     # gaze-evoked blink
            _blink(meshes, f, rng)
        previous = gaze
    t = start + rng.expovariate(blink_rate / 60) * fps                          # spontaneous blinks
    while t < end - 6:
        _blink(meshes, t, rng)
        t += max(0.5 * fps, rng.expovariate(blink_rate / 60) * fps)
    for pause in pauses:                                                         # blinks gather at pauses
        if rng.random() < 0.5:
            _blink(meshes, pause, rng)
    if plans:
        def head_turns(frame):
            yaw = pitch = 0.0
            for a, b, h0, h1 in plans:
                if frame >= b:
                    yaw, pitch = h1
                elif frame >= a:
                    k = 0.5 - 0.5 * math.cos(math.pi * (frame - a) / (b - a))
                    yaw, pitch = h0[0] + (h1[0] - h0[0]) * k, h0[1] + (h1[1] - h0[1]) * k
                    break
                else:
                    break
            return {"Head": (yaw * 0.6, -pitch * 0.6, 0), "Neck1": (yaw * 0.4, -pitch * 0.4, 0)}
        _layer(rig, int(start), int(end), head_turns)


def _key_eyes(rig, meshes, frame, gaze):
    """Turn the eyes to gaze = (degrees to the character's left, degrees up), relative to the head. The
    eyeballs turn on their LeftEye / RightEye bones; the eyeLook face shapes (on our characters: the lids
    following the eyes up and down) get the matching weights."""
    yaw, pitch = gaze
    left = {"eyeLookOutLeft": max(yaw, 0) / EYE_DEG["out"], "eyeLookInLeft": max(-yaw, 0) / EYE_DEG["in"]}
    right = {"eyeLookInRight": max(yaw, 0) / EYE_DEG["in"], "eyeLookOutRight": max(-yaw, 0) / EYE_DEG["out"]}
    vertical = {f"eyeLook{d}{s}": v for s in ("Left", "Right") for d, v in
                (("Up", max(pitch, 0) / EYE_DEG["up"]), ("Down", max(-pitch, 0) / EYE_DEG["down"]))}
    face(rig, frame, {k: min(1.0, v) for k, v in {**left, **right, **vertical}.items()}, meshes)
    # armature space: the character faces -Y, +X is its left, +Z up. Yaw turns about +Z (toward +X = left);
    # looking up turns the forward axis toward +Z, i.e. about -X.
    turn = Quaternion((0, 0, 1), math.radians(yaw)) @ Quaternion((1, 0, 0), math.radians(-pitch))
    for side in ("Left", "Right"):
        pb = rig.pose.bones.get(f"{side}Eye")
        if pb is None:
            continue
        rest = pb.bone.matrix_local.to_quaternion()
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rest.inverted() @ turn @ rest
        pb.keyframe_insert("rotation_quaternion", frame=frame)


def _blink(meshes, frame, rng):
    depth = 1.0 if rng.random() > 0.15 else rng.uniform(0.5, 0.75)             # some blinks are partial
    for f, v in ((frame - 0.5, 0.0), (frame + 2, depth), (frame + 2.8, depth), (frame + 6.5, 0.0)):
        for obj in meshes:                       # closes in ~80 ms, reopens in ~150 ms
            keys = obj.data.shape_keys.key_blocks
            for name in ("eyeBlinkLeft", "eyeBlinkRight"):
                if name in keys:
                    keys[name].value = v
                    keys[name].keyframe_insert("value", frame=f)


def blinks(rig, start, end, seed=1, fps=24):
    """Spontaneous blinks only (eyes() adds gaze-coupled ones); kept for shots without gaze work."""
    rng = random.Random(seed)
    meshes = face_meshes(rig)
    t = start + rng.uniform(0.5, 2) * fps
    while t < end - 6:
        _blink(meshes, t, rng)
        t += max(0.5 * fps, rng.expovariate(17 / 60) * fps)


# Breathing: inhale ~40% of a breath, exhale ~60%, then a short rest; chest, shoulders and neck move slightly
# out of step; anxious breathing is faster and rides higher in the chest and shoulders; speech is spoken on
# the out-breath after a quick in-breath (~0.35 s) before each phrase.
BREATH = {   # breaths per minute, chest lift (deg), shoulder rise (deg)
    "calm": (13, 1.0, 0.5), "anxious": (22, 1.6, 1.4), "panic": (32, 2.2, 2.6), "held": (0, 0.0, 0.0),
    "old": (17, 0.8, 0.9), "sleep": (12, 0.9, 0.2),
}


def breathe(rig, start, end, style="calm", phrases=(), fps=24, seed=1):
    """Breathing layer. `phrases` = [(first frame, last frame), ...] of speech: a quick in-breath lands just
    before each phrase and the phrase is spoken on a slow out-breath."""
    rate, chest, shoulder = BREATH[style]
    rng = random.Random(seed)
    curve = {}                       # frame -> lung fill 0..1
    if rate:
        period = 60 / rate * fps
        t = start - rng.uniform(0, period)
        while t < end:
            p = period * rng.uniform(0.9, 1.1)
            for f in range(int(t), int(t + p) + 1):
                x = (f - t) / p
                curve[f] = (0.5 - 0.5 * math.cos(math.pi * x / 0.4)) if x < 0.4 else \
                           (0.5 + 0.5 * math.cos(math.pi * (x - 0.4) / 0.45)) if x < 0.85 else 0.0
            t += p
    for a, b in phrases:              # in-breath before speaking, then a long out-breath through the phrase
        for f in range(int(a - 0.35 * fps), int(b) + 1):
            curve[f] = (f - (a - 0.35 * fps)) / (0.35 * fps) if f < a else 1 - 0.85 * (f - a) / max(1, b - a)

    def offsets(f):
        fill = curve.get(f, 0.0)
        lag = curve.get(f - 2, 0.0)   # shoulders and neck follow the chest a little later
        return {"Spine1": (0, -chest * fill, 0), "Spine": (0, -chest * 0.4 * fill, 0),
                "Neck1": (0, chest * 0.7 * lag, 0),                               # keep the head level
                "LeftShoulder": (0, 0, -shoulder * lag), "RightShoulder": (0, 0, shoulder * lag)}
    _layer(rig, start, end, offsets)


def sway(rig, start, end, amount=1.0, seed=1):
    """Postural sway: nobody stands or sits perfectly still (slow, small, never-repeating drift)."""
    rng = random.Random(seed)
    waves = [(rng.uniform(0.07, 0.35), rng.uniform(0, 6.3)) for _ in range(6)]

    def drift(f, k):
        return sum(math.sin(2 * math.pi * w * f / 24 + ph + k) for w, ph in waves) / len(waves)

    def offsets(f):
        return {"LowerBack": (0.6 * amount * drift(f, 0), 0.5 * amount * drift(f, 1), 0.5 * amount * drift(f, 2)),
                "Neck1": (0.8 * amount * drift(f, 3), 0.6 * amount * drift(f, 4), 0.4 * amount * drift(f, 5))}
    _layer(rig, start, end, offsets)


# Startle (acoustic startle reflex, Brown et al. 1991): a cranio-caudal wave - blink ~20-40 ms, head and neck
# 60-120 ms, shoulders 100-120 ms, arms 125-195 ms, legs 145-395 ms - flexing the neck and trunk, raising the
# shoulders, bending the elbows; it peaks fast and settles over most of a second.
def startle(rig, frame, strength=1.0, fps=24, face_too=True, until=None, legs=True):
    """face_too=False: a jerk in sleep (eyes stay shut). until: hold the layer's keys to this frame.
    legs=False: legs stay put (under a blanket in bed)."""
    meshes = face_meshes(rig)
    if face_too:
        _startle_face(rig, meshes, frame, strength, fps)
    _startle_body(rig, frame, strength, fps, until, legs)


def _startle_face(rig, meshes, frame, strength, fps):
    face(rig, frame - 1, {"eyeBlinkLeft": 0.0, "eyeBlinkRight": 0.0, "eyeWideLeft": 0.0, "eyeWideRight": 0.0,
                          "browInnerUp": 0.0}, meshes)
    face(rig, frame + 0.03 * fps, {"eyeBlinkLeft": strength, "eyeBlinkRight": strength}, meshes)
    face(rig, frame + 0.2 * fps, {"eyeBlinkLeft": 0.0, "eyeBlinkRight": 0.0, "eyeWideLeft": 0.8 * strength,
                                  "eyeWideRight": 0.8 * strength, "browInnerUp": 0.9 * strength}, meshes)


def _startle_body(rig, frame, strength, fps, until, legs=True):
    wave = {"Head": (0.09, (0, 2, 0)), "Neck1": (0.08, (0, 6, 0)), "Spine1": (0.11, (0, 5, 0)),
            "LeftShoulder": (0.11, (0, 0, -9)), "RightShoulder": (0.11, (0, 0, 9)),
            "LeftArm": (0.16, (0, 0, -6)), "RightArm": (0.16, (0, 0, 6)),
            "LeftForeArm": (0.16, (0, -14, 0)), "RightForeArm": (0.16, (0, -14, 0)),
            "LeftUpLeg": (0.25, (0, -4, 0)), "RightUpLeg": (0.25, (0, -4, 0))}

    def offsets(f):
        out = {}
        for bone, (delay, rot) in wave.items():
            if bone not in rig.pose.bones or (not legs and "Leg" in bone):
                continue
            t = (f - frame) / fps - delay
            k = 0.0 if t < 0 else (t / 0.08 if t < 0.08 else math.exp(-(t - 0.08) / 0.35))   # snap, then settle
            out[bone] = tuple(r * k * strength for r in rot)
        return out
    _layer(rig, int(frame), int(until or frame + 1.6 * fps), offsets)


# --- motion capture -------------------------------------------------------------------------------

def retarget(rig, bvh, start_frame=1, bone_map=None, max_frames=None, root_motion=True, keep_source=False):
    """Bake a BVH clip onto `rig` at the scene frame rate: each bone copies its world-space rotation
    relative to its rest pose. A global turn aligns the two skeletons' facing; a per-bone swing corrects
    rest-pose differences (T-pose clips onto our A pose). Hips motion is scaled by leg length.
    Returns the last frame written."""
    if bone_map is None:
        bone_map = STYLE100 if "100style" in str(bvh).lower() else CMU
    scene = bpy.context.scene
    before = set(bpy.data.objects)
    bpy.ops.import_anim.bvh(filepath=str(bvh), use_fps_scale=True, update_scene_fps=False,
                            update_scene_duration=False)
    src = (set(bpy.data.objects) - before).pop()
    pairs = [(s.name, bone_map.get(s.name, s.name)) for s in src.pose.bones]
    pairs = [(s, t) for s, t in pairs if t in rig.pose.bones]
    a, b = (int(x) for x in src.animation_data.action.frame_range)
    if max_frames:
        b = min(b, a + max_frames - 1)

    def rest_world(obj, name):
        return obj.matrix_world @ obj.data.bones[name].matrix_local

    def lateral(obj, left, right):
        return (rest_world(obj, left).translation - rest_world(obj, right).translation).normalized()

    sl, sr, sf = ("LeftHip", "RightHip", "LeftAnkle") if bone_map is STYLE100 else ("LeftUpLeg", "RightUpLeg", "LeftFoot")
    turn = lateral(src, sl, sr).rotation_difference(lateral(rig, "LeftUpLeg", "RightUpLeg")).to_matrix()

    def leg(obj, hip, foot):
        return (rest_world(obj, foot).translation - rest_world(obj, hip).translation).length
    s_rest = {s: turn @ rest_world(src, s).to_3x3().normalized() for s, _ in pairs}
    t_rest = {b_.name: (rig.matrix_world @ b_.matrix_local).to_3x3().normalized() for b_ in rig.data.bones}
    swing = {}
    for s, t in pairs:
        src_dir = s_rest[s] @ Vector((0, 1, 0))
        swing[t] = (t_rest[t] @ Vector((0, 1, 0))).rotation_difference(src_dir).to_matrix()
    s_of = {t: s for s, t in pairs}
    hips_s, hips_t = pairs[0][0], pairs[0][1]
    scale = leg(rig, "LeftUpLeg", "LeftFoot") / leg(src, sl, sf)          # hips travel scales with leg length
    s_hips0 = turn @ rest_world(src, hips_s).translation
    order = [b_ for b_ in rig.data.bones]               # parents come before children
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    last_q = {}
    for i, f in enumerate(range(a, b + 1)):
        scene.frame_set(f)
        posed = {}
        for bone in order:
            name = bone.name
            parent = bone.parent.name if bone.parent else None
            rest_local = (t_rest[parent].inverted() @ t_rest[name]) if parent else t_rest[name]
            if name in s_of:
                s = s_of[name]
                s_pose = turn @ (src.matrix_world @ src.pose.bones[s].matrix).to_3x3().normalized()
                posed[name] = s_pose @ s_rest[s].inverted() @ swing[name] @ t_rest[name]
            else:
                posed[name] = (posed[parent] if parent else Matrix.Identity(3)) @ rest_local
            basis = rest_local.inverted() @ ((posed[parent].inverted() if parent else Matrix.Identity(3)) @ posed[name])
            q = basis.to_quaternion()
            if name in last_q and last_q[name].dot(q) < 0:
                q.negate()
            last_q[name] = q
            pb = rig.pose.bones[name]
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=start_frame + i)
        if root_motion:
            s_now = turn @ (src.matrix_world @ src.pose.bones[hips_s].matrix).translation
            delta = (s_now - s_hips0) * scale
            local = (rig.matrix_world @ rig.data.bones[hips_t].matrix_local).inverted().to_3x3() @ delta
            rig.pose.bones[hips_t].location = local
            rig.pose.bones[hips_t].keyframe_insert("location", frame=start_frame + i)
    if not keep_source:
        bpy.data.objects.remove(src)
    return start_frame + (b - a)


def straight_stretch(bvh, frames, fps=24):
    """Frames to skip so a `frames`-long window of a clip is its straightest walking (100STYLE actors walk
    back and forth and turn at the ends of the capture area): the window where the hips travel farthest."""
    scene = bpy.context.scene
    old = scene.render.fps
    scene.render.fps = fps
    before = set(bpy.data.objects)
    bpy.ops.import_anim.bvh(filepath=str(bvh), use_fps_scale=True, update_scene_fps=False, update_scene_duration=False)
    src = (set(bpy.data.objects) - before).pop()
    a, b = (int(x) for x in src.animation_data.action.frame_range)
    path = []
    for f in range(a, b + 1):
        scene.frame_set(f)
        path.append((src.matrix_world @ src.pose.bones[0].head).xy.copy())
    bpy.data.objects.remove(src)
    scene.render.fps = old
    if len(path) <= frames:
        return 0
    return max(range(len(path) - frames), key=lambda s: (path[s + frames] - path[s]).length)


def plant_feet(rig, start, end, floor=0.0, blend=3):
    """Footskate cleanup (Kovar et al. 2002; contact locking as in Skeleton-Aware Networks 2020).
    The ball of the foot is the contact point in creeping and tiptoeing (the heel rises around it), so:
    find the frames each ball is planted (low and nearly still); set the whole body's height once so planted
    balls rest on the floor (moving the body, not stretching the legs); lock each planted ball to its average
    spot for that contact; solve the leg with two-bone IK (knee keeps its mocap direction, foot keeps its own
    angle); blend in and out over `blend` frames so nothing pops. Returns the height change applied."""
    import statistics
    scene = bpy.context.scene
    bpy.context.view_layer.update()              # the rig may just have been moved: refresh its matrix first
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    frames = list(range(start, end + 1))
    sides = {"Left": ("LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase"),
             "Right": ("RightUpLeg", "RightLeg", "RightFoot", "RightToeBase")}
    names = [n for c in sides.values() for n in c] + [rig.pose.bones[c[0]].parent.name for c in sides.values()]
    pose = {}
    for f in frames:
        scene.frame_set(f)
        pose[f] = {n: rig.pose.bones[n].matrix.copy() for n in names}
    floor_local = (rig.matrix_world.inverted() @ Vector((0, 0, floor))).z
    ball_rest = {s: rest[c[3]].translation.z - min(rest[c[3]].translation.z, rest[c[2]].translation.z) + 0.022
                 for s, c in sides.items()}                                     # ball joint height when flat
    ball = {s: {f: pose[f][c[3]].translation.copy() for f in frames} for s, c in sides.items()}
    lowest = min(min(ball[s][f].z for f in frames) for s in sides)

    def planted_flags(s):
        flags = []
        for i, f in enumerate(frames):
            prev = frames[max(0, i - 1)]
            speed = (ball[s][f].xy - ball[s][prev].xy).length * scene.render.fps
            flags.append(ball[s][f].z - lowest < 0.04 and speed < 0.2)
        for i in range(1, len(flags) - 1):                                       # fill 1-frame gaps
            flags[i] = flags[i] or (flags[i - 1] and flags[i + 1])
        return flags

    flags = {s: planted_flags(s) for s in sides}
    heights = [ball[s][f].z for s in sides for i, f in enumerate(frames) if flags[s][i]]
    lift = (floor_local + ball_rest["Left"]) - (statistics.median(heights) if heights else lowest)
    rig.location.z += lift                       # the body comes down (or up) to the floor as a whole
    bpy.context.view_layer.update()
    for side, (up, low, foot, toe) in sides.items():
        spans, i = [], 0
        while i < len(frames):
            if flags[side][i]:
                j = i
                while j + 1 < len(frames) and flags[side][j + 1]:
                    j += 1
                if j - i >= 2:
                    spans.append((i, j))
                i = j + 1
            else:
                i += 1
        weight, target = {}, {}
        for i, j in spans:
            fs = frames[i:j + 1]
            spot = sum((ball[side][f] for f in fs), Vector()) / len(fs)
            for k in range(max(0, i - blend), min(len(frames), j + blend + 1)):
                f = frames[k]
                w = 1.0 if i <= k <= j else 1 - min(abs(k - i), abs(k - j)) / (blend + 1)
                if w > weight.get(f, 0.0):
                    weight[f] = w
                    b = ball[side][f]
                    locked = Vector((spot.x, spot.y, b.z))          # lock where it is, keep its height
                    target[f] = pose[f][foot].translation + (b.lerp(locked, w) - b)
        for f, w in weight.items():
            _two_bone(rig, rest, pose[f], f, up, low, foot, target[f])
    return lift


def _two_bone(rig, rest, pose, frame, up, low, foot, target, pole=(0, -1, 0), end_rot=None, wrist=None, ease=1.0,
              force_pole=False):
    """Analytic two-bone IK in armature space; keys the thigh, shin and foot rotations at `frame`. The knee/elbow
    bends the way it already does (the mocap's), or toward `pole` when straight or force_pole."""
    from mathutils import Matrix
    H, K, A = pose[up].translation, pose[low].translation, pose[foot].translation
    l1, l2 = (K - H).length, (A - K).length
    reach = target - H
    d = max(abs(l1 - l2) + 1e-4, min(l1 + l2 - 1e-4, reach.length))
    u = reach.normalized()
    bend = (K - H) - (K - H).project(A - H)                                    # the knee's mocap direction
    bend = bend if bend.length > 0.01 * l1 and not force_pole else Vector(pole)   # straight limb: the natural bend
    bend = (bend - bend.project(u)).normalized()
    a = (l1 * l1 + d * d - l2 * l2) / (2 * d)
    knee = H + u * a + bend * math.sqrt(max(0.0, l1 * l1 - a * a))
    ankle = H + u * d

    def aimed(matrix, head, old_dir, new_dir):
        turn = old_dir.rotation_difference(new_dir).to_matrix().to_4x4()
        return Matrix.Translation(head) @ turn @ Matrix.Translation(-matrix.translation) @ matrix

    thigh = aimed(pose[up], H, K - H, knee - H)
    shin_start = thigh @ (pose[up].inverted() @ pose[low])                    # shin carried by the new thigh
    shin = aimed(shin_start, knee, (shin_start @ (pose[low].inverted() @ pose[foot])).translation - knee, ankle - knee)
    if wrist is not None:                     # the hand carries on the forearm's line, bent toward the palm
        bend, palm = wrist
        line = (ankle - knee).normalized()
        side = (palm - palm.project(line)).normalized()
        y = (line * math.cos(bend) + side * math.sin(bend)).normalized()
        z = -(palm - palm.project(y)).normalized()
        want = Matrix((y.cross(z), y, z)).transposed()
        end_rot = pose[foot].to_quaternion().slerp(want.to_quaternion(), ease).to_matrix()
    turned = end_rot if end_rot is not None else pose[foot].to_3x3()          # the foot keeps its own angle
    if end_rot is not None:
        # turning the hand palm up or down happens mostly in the forearm (pronation/supination), not at the
        # wrist: give the forearm 3/4 of the hand's twist about its own axis, so sleeves and wrists don't
        # wring (a shirt cuff flipped out into a flap when the wrist took it all)
        neutral = rest[low].inverted() @ rest[foot]
        rel = ((shin.to_3x3() @ neutral.to_3x3()).inverted() @ turned).to_quaternion()
        axis = (neutral.to_3x3().inverted() @ Vector((0, 1, 0))).normalized()
        along = Vector((rel.x, rel.y, rel.z)).dot(axis)
        angle = 2 * math.atan2(along, rel.w)
        angle = (angle + math.pi) % (2 * math.pi) - math.pi
        shin = shin @ Matrix.Rotation(0.75 * angle, 4, "Y")
    foot_m = Matrix.Translation(ankle) @ turned.to_4x4()
    for name, matrix, parent in ((up, thigh, None), (low, shin, thigh), (foot, foot_m, shin)):
        pb = rig.pose.bones[name]
        parent_pose = parent if parent is not None else pb.parent.matrix
        rest_rel = rest[pb.parent.name].inverted() @ rest[name]
        if parent is None:                       # the hip joint is unchanged: its pose at this frame
            parent_pose = pose[pb.parent.name]
        basis = (parent_pose @ rest_rel).inverted() @ matrix
        pb.rotation_quaternion = basis.to_quaternion()
        pb.keyframe_insert("rotation_quaternion", frame=frame)


# --- hands, props, beds -------------------------------------------------------------------------------
def reach(rig, side, start, end, target, blend=8, hand=None, wrist=None, pole=None):
    """Arm IK: the hand (wrist) goes to target(frame) -> world point (or None = free), with `blend`-frame
    ease in and out. Elbows bend back and down. hand: a world 3x3 rotation for the hand (its Y axis along
    the fingers, palm on -Z), or a function frame -> rotation, else it keeps its own angle. wrist:
    (bend degrees, palm direction in world) instead - the hand carries on the line of the solved forearm,
    bent that much toward the palm side, so the wrist stays in a natural range (holding things). pole: the
    elbow's direction (armature space) instead of the way the arm already bends. For hands on doors, latches, lanterns:
    in FLV nothing moves unless a hand moves it."""
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    chain = (f"{side}Arm", f"{side}ForeArm", f"{side}Hand")
    parent = rig.pose.bones[chain[0]].parent.name
    frames = list(range(start, end + 1))
    goals = {f: target(f) for f in frames}
    on = [f for f in frames if goals[f] is not None]
    if not on:
        return
    first, last = on[0], on[-1]
    weight = {}
    for f in frames:
        w = 1.0 if first <= f <= last else 0.0
        if f < first and first - f <= blend:
            w = 1 - (first - f) / (blend + 1)
        if f > last and f - last <= blend:
            w = 1 - (f - last) / (blend + 1)
        if w > 0:
            weight[f] = w
    poses, to_arms = {}, {}
    for f in weight:                          # the arm as it was, before any IK key (else the blends drift)
        scene.frame_set(f)
        poses[f] = {n: rig.pose.bones[n].matrix.copy() for n in chain + (parent,)}
        to_arms[f] = rig.matrix_world.inverted()          # per frame: the whole body may be moving
    for f, w in weight.items():
        goal = goals[f] if goals[f] is not None else goals[first if f < first else last]
        pose = poses[f]
        to_arm = to_arms[f]
        at_wrist = pose[chain[2]].translation
        ease = 0.5 - 0.5 * math.cos(math.pi * w)
        aim_at = at_wrist.lerp(to_arm @ Vector(goal), ease)
        turned = None
        rot = hand(f) if callable(hand) else hand
        if rot is not None:
            want = (to_arm.to_3x3() @ rot).to_quaternion()
            turned = pose[chain[2]].to_quaternion().slerp(want, ease).to_matrix()
        bent = None if wrist is None else (math.radians(wrist[0]), (to_arm.to_3x3() @ Vector(wrist[1])).normalized())
        _two_bone(rig, rest, pose, f, *chain, aim_at, pole=pole or (0, 0.6, -0.4), end_rot=turned, wrist=bent,
                  ease=ease, force_pole=pole is not None)


def hand_frame(fingers, palm):
    """World rotation for reach(hand=...): fingers point along `fingers`, the palm faces `palm`.
    Hand bones (build() re-rolls ours this way): Y runs along the fingers and the palm is on -Z."""
    y = Vector(fingers).normalized()
    z = -(Vector(palm) - Vector(palm).project(y)).normalized()
    return Matrix((y.cross(z), y, z)).transposed()


# degrees per joint (knuckle, middle, tip) at curl=1: about 80 degrees per finger in all, like a loose hook
GRIP = {"Thumb": (6, 8, 6), "Index": (20, 35, 25), "Middle": (22, 36, 25), "Ring": (24, 37, 25), "Pinky": (26, 38, 25)}
THUMB = {"Left": "LeftHandThumb1", "Right": "RightHandThumb1"}


def grip(rig, side, frame=1, curl=1.0):
    """Close the fingers round a handle from `frame` on (each finger's three joints; +X curls toward the palm).
    curl < 0 straightens them a little (a flat hand on a door)."""
    scene = bpy.context.scene
    for finger, degs in GRIP.items():
        for j, deg in enumerate(degs, 1):
            pb = rig.pose.bones.get(f"{side}Hand{finger}{j}")
            if pb is None:
                continue
            scene.frame_set(frame)
            pb.keyframe_insert("rotation_quaternion", frame=frame - 4)
            pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion((1, 0, 0), math.radians(deg * curl))
            pb.keyframe_insert("rotation_quaternion", frame=frame)


LEG_BONES = [f"{s}{b}" for s in ("Left", "Right") for b in ("UpLeg", "Leg", "Foot", "ToeBase")]


def bedsheet(name, coll, material, rig, center, size, top, drop=0.3, clearance=0.035, step=0.025, frames=(1,)):
    """A blanket over someone in bed, tucked in at the foot end (-y), open at +y. Its heights are cast
    down onto the legs and feet (body and clothes), so hands rest on top and the sleeper can sit up out
    of it; it is spread and smoothed the way fabric spans gaps, and the long sides hang `drop` metres.
    With several `frames` it follows the legs (one shape key per frame, blended), so it moves only when
    the legs under it move. Returns (object, height(x, y) at the first frame)."""
    import bmesh
    import numpy as np
    from mathutils.bvhtree import BVHTree
    scene = bpy.context.scene
    hw, hl = size[0] / 2, size[1] / 2
    nx, ny = int(size[0] / step) + 1, int(size[1] / step) + 1
    xs, ys = np.linspace(-hw, hw, nx), np.linspace(-hl, hl, ny)
    k = int(drop / step)
    us = np.concatenate([-hw - step * np.arange(k, 0, -1), xs, hw + step * np.arange(1, k + 1)])

    def heights(frame):
        scene.frame_set(frame)
        deps = bpy.context.evaluated_depsgraph_get()
        trees = []
        for obj in [o for o in rig.children if o.type == "MESH"]:
            legs = {obj.vertex_groups[b].index for b in LEG_BONES if b in obj.vertex_groups}
            bm = bmesh.new()
            bm.from_object(obj, deps)
            bm.transform(obj.matrix_world)
            layer = bm.verts.layers.deform.active
            if not legs or layer is None:
                bm.free()
                continue
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if sum(w for g, w in v[layer].items() if g in legs) < 0.5],
                             context="VERTS")
            if bm.verts:
                trees.append(BVHTree.FromBMesh(bm))
            bm.free()
        assert trees, f"bedsheet: no leg geometry found on {rig.name}"
        H = np.full((ny, nx), float(top))
        for j, y in enumerate(ys):
            for i, x in enumerate(xs):
                for tree in trees:
                    hit = tree.ray_cast(Vector((center[0] + x, center[1] + y, top + 2.0)), Vector((0, 0, -1)))[0]
                    if hit is not None:
                        H[j, i] = max(H[j, i], hit.z)
        raw = H.copy()
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):        # small peaks (toes) fall between samples
            raw = np.maximum(raw, np.roll(H, d, (0, 1)))
        H = raw + clearance
        spread = H.copy()                                   # fabric spans gaps: dilate a little, then smooth
        for dj in range(-2, 3):
            for di in range(-2, 3):
                if dj * dj + di * di <= 4:
                    spread = np.maximum(spread, np.roll(np.roll(H, dj, 0), di, 1))
        kernel = np.exp(-0.5 * (np.arange(-10, 11) / 3.5) ** 2)
        kernel /= kernel.sum()
        pad = np.pad(spread, 10, mode="edge")
        pad = np.apply_along_axis(lambda r: np.convolve(r, kernel, "same"), 0, pad)
        pad = np.apply_along_axis(lambda r: np.convolve(r, kernel, "same"), 1, pad)
        H = np.maximum(pad[10:-10, 10:-10], H)
        H[0, :] = np.minimum(H[0, :], top + 0.01)            # tucked in at the foot
        H[1, :] = (H[0, :] + H[2, :]) / 2
        return H

    def coords(H):                                          # the two long sides hang from the edge
        out = []
        for j in range(ny):
            for u in us:
                over = max(abs(u) - hw, 0.0)
                i = int(round((min(max(u, -hw), hw) + hw) / step))
                out.append((center[0] + math.copysign(min(abs(u), hw) + 0.15 * over, u), center[1] + ys[j],
                            H[j, min(i, nx - 1)] - over))
        return out

    shapes = [heights(f) for f in frames]
    bm = bmesh.new()
    verts = [bm.verts.new(c) for c in coords(shapes[0])]
    width = len(us)
    for j in range(ny - 1):
        for i in range(width - 1):
            a = j * width + i
            bm.faces.new((verts[a], verts[a + 1], verts[a + width + 1], verts[a + width]))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    obj.data.materials.append(material)
    if len(frames) > 1:
        obj.shape_key_add(name="Basis")
        for n, (f, H) in enumerate(zip(frames, shapes)):
            if n == 0:
                continue
            key = obj.shape_key_add(name=f"legs_{f}", from_mix=False)
            for point, c in zip(key.data, coords(H)):
                point.co = c
            keys = [(frames[n - 1], 0.0), (f, 1.0)] + ([(frames[n + 1], 0.0)] if n + 1 < len(frames) else [])
            for at, value in keys:
                key.value = value
                key.keyframe_insert("value", frame=at)
    obj.modifiers.new("Thickness", "SOLIDIFY").thickness = 0.01
    obj.modifiers.new("Soft", "SUBSURF").render_levels = 1
    first = shapes[0]
    return obj, (lambda x, y: float(first[min(max(int(round((y - center[1] + hl) / step)), 0), ny - 1),
                                            min(max(int(round((x - center[0] + hw) / step)), 0), nx - 1)]))


def hold(rig, prop, side="Right", frame=1):
    """Put a prop in a hand: from `frame` on it moves only with that hand (bone parent, world pose kept)."""
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    world = prop.matrix_world.copy()
    prop.parent, prop.parent_type, prop.parent_bone = rig, "BONE", f"{side}Hand"
    bpy.context.view_layer.update()
    prop.matrix_world = world


def hang(prop, rig, side, start, end, ring=(0.0, 0.0, 0.255), length=0.155, fps=24, damping=2.5, yaw=0.0):
    """A prop hanging from a hand by its ring (a lantern, a pail): the ring follows the grip point (in the
    crook of the curled fingers) while the prop hangs plumb under gravity and swings as a damped
    pendulum when the hand accelerates - so it moves only because the hand moves. `length`: ring to
    centre of mass; yaw: radians, or frame -> radians (the lantern turns with the one carrying it). Keys
    location and rotation every frame from start to end."""
    scene = bpy.context.scene
    pb = rig.pose.bones
    grips = {}
    for f in range(start - 1, end + 2):
        scene.frame_set(f)
        grips[f] = rig.matrix_world @ pb[f"{side}HandMiddle1"].head.lerp(pb[f"{side}HandMiddle3"].tail, 0.3)
    g, sub = 9.81, 8
    dt = 1.0 / (fps * sub)
    angle = [0.0, 0.0]                                   # tilt toward +x and +y, radians
    speed = [0.0, 0.0]
    prop.animation_data_clear()
    prop.parent = None
    for f in range(start, end + 1):
        accel = (grips[f + 1] - 2 * grips[f] + grips[f - 1]) * fps * fps if start < f < end else Vector((0, 0, 0))
        for _ in range(sub):
            for i, a in enumerate((accel.x, accel.y)):
                # pivot accelerating one way swings the weight the other way: theta'' = -(g sin + a cos)/L
                acc = -(g * math.sin(angle[i]) + a * math.cos(angle[i])) / length - damping * speed[i]
                speed[i] += acc * dt
                angle[i] += speed[i] * dt
        turn = Euler((-angle[1], angle[0], 0.0)).to_matrix() @ Euler((0.0, 0.0, yaw(f) if callable(yaw) else yaw)).to_matrix()
        prop.rotation_euler = turn.to_euler()
        prop.location = grips[f] - turn @ Vector(ring)
        prop.keyframe_insert("rotation_euler", frame=f)
        prop.keyframe_insert("location", frame=f)


def rise_in_bed(rig, frame, until, seconds=1.1, fps=24, lead="Left"):
    """Sit up from lying on the back the way older people do (Watanabe et al. 2019, J Phys Ther Sci):
    the head lifts first, the trunk turns a little toward the propping elbow, the trunk curls only ~37
    degrees (young people ~63) while the hips and the arms' push do the rest, the head comes upright, and
    the knees draw up late (they reached ~75 degrees in the study; 40 here, under a blanket). `seconds`
    is the rise; place the arms with reach() (elbow prop, then a push on the mattress)."""
    span = seconds * fps
    turn = 1 if lead == "Left" else -1

    def ease(a, b, x):
        u = min(1.0, max(0.0, (x - a) / (b - a)))
        return u * u * (3 - 2 * u)

    def offsets(f):
        x = (f - frame) / span
        if x <= 0:
            return {}
        settle = 0.05 * math.exp(-(x - 1) * 4) * math.sin((x - 1) * 10) if x > 1 else 0.0
        hinge = 64 * (ease(0.30, 1.0, x) + settle)                         # the hips lift the trunk
        curl = 37 * ease(0.15, 0.54, x) - 22 * ease(0.54, 1.0, x)          # curls, then straightens to 15
        neck = 30 * ease(0.0, 0.26, x) - 34 * ease(0.40, 0.85, x)          # head first, then upright
        twist = turn * (9 * ease(0.10, 0.34, x) - 9 * ease(0.40, 0.70, x))  # toward the propping elbow
        knee = ease(0.62, 0.90, x)
        return {"Hips": (0, hinge, 0), "LeftUpLeg": (0, -hinge - 20 * knee, 0), "RightUpLeg": (0, -hinge - 20 * knee, 0),
                "LeftLeg": (0, 40 * knee, 0), "RightLeg": (0, 40 * knee, 0),
                "LowerBack": (0.4 * twist, 0.40 * curl, 0), "Spine": (0.3 * twist, 0.35 * curl, 0),
                "Spine1": (0.3 * twist, 0.25 * curl, 0), "Neck1": (0, 0.6 * neck, 0), "Head": (0, 0.4 * neck, 0)}
    _layer(rig, frame, until, offsets)


def chuckle(rig, start, fps=24, rest=None, seed=1):
    """A stifled, silent laugh (about half of real laughs are unvoiced). A quick in-breath, then two small
    'ha' pulses and, after a catch, a bigger run (animators break a laugh into small-small-big rather than
    even beats). Each pulse is a sharp contraction ~75 ms long, ~210 ms apart (Provine 1996; laughter's
    ~5 Hz bursts), all on one out-breath, so the chest sinks and the head bows as the lungs empty; the
    shoulders lead each pulse and the head follows. The face holds a felt smile - lip corners up (AU12)
    with the cheeks raised (AU6) - but the mouth stays shut (no AU25/26): the lips press and the nostrils
    flare a little on each pulse. rest: the expression to settle back to. Returns the last frame."""
    rng = random.Random(seed)
    meshes = face_meshes(rig)
    rest = dict(rest or {})
    pulses, t = [], 0.22
    for amp in (0.5, 0.42):                                          # two small ones
        pulses.append((t, amp))
        t += 0.21 + rng.uniform(-0.02, 0.02)
    t += 0.25                                                        # a catch of breath
    for amp in (1.0, 0.85, 0.7, 0.55, 0.4):                          # then the bigger run, dying away
        pulses.append((t, amp))
        t += 0.21 + rng.uniform(-0.02, 0.02)
    last = pulses[-1][0]
    length = last + 1.6

    def pulse(x):
        total = 0.0
        for at, amp in pulses:
            d = x - at
            if 0 <= d < 0.08:
                total += amp * d / 0.08                             # the sharp 'ha' contraction
            elif d >= 0.08:
                total += amp * math.exp(-(d - 0.08) / 0.07)         # and its release
        return total

    def smooth(a, b, x):
        u = min(1.0, max(0.0, (x - a) / (b - a)))
        return u * u * (3 - 2 * u)

    def empty(x):                                                    # lungs emptying, then the in-breath
        spent = sum(amp * 0.17 for at, amp in pulses if x >= at)
        return min(1.0, spent) * (1 - smooth(last + 0.35, last + 0.9, x))

    def inhale(x):
        return smooth(0.0, 0.18, x) * (1 - smooth(0.22, 0.45, x)) + 0.6 * smooth(last + 0.35, last + 0.9, x) * (
            1 - smooth(last + 0.9, last + 1.4, x))

    def smile(x):                                                    # builds, holds, lingers, fades
        return 0.55 * smooth(0.0, 0.3, x) * (1 - 0.6 * smooth(last + 0.2, last + 0.8, x)) * (
            1 - smooth(last + 0.9, length, x))

    def offsets(f):
        x = (f - start) / fps
        p, e, i = pulse(x), empty(x), inhale(x)
        lead, follow = pulse(x + 0.04), pulse(x - 0.04)
        return {"Spine": (0, 1.4 * p + 3.0 * e - 0.8 * i, 0), "Spine1": (0, 0.9 * p + 1.5 * e - 0.6 * i, 0),
                "LeftShoulder": (0, 0, -(2.0 * lead + 2.5 * i)), "RightShoulder": (0, 0, 2.0 * lead + 2.5 * i),
                "Neck1": (0, 0.5 * follow + 2.0 * e, 0), "Head": (0, 1.2 * follow + 2.0 * e - 1.0 * i, 0)}
    end = start + int(math.ceil(length * fps))
    _layer(rig, start, end, offsets)
    for f in range(start - 4, end + 1):
        x = (f - start) / fps
        s, p = smile(x), pulse(x)
        k = s / 0.55
        values = {"mouthSmileLeft": s + 0.05 * p * k, "mouthSmileRight": 0.85 * s + 0.05 * p * k,
                  "cheekSquintLeft": 1.0 * s, "cheekSquintRight": 0.95 * s,     # AU6 narrows the eyes
                  "eyeSquintLeft": 0.65 * s + rest.get("eyeSquintLeft", 0.0) * (1 - k),
                  "eyeSquintRight": 0.65 * s + rest.get("eyeSquintRight", 0.0) * (1 - k),
                  "mouthPressLeft": rest.get("mouthPressLeft", 0.0) + 0.25 * k + 0.15 * p,
                  "mouthPressRight": rest.get("mouthPressRight", 0.0) + 0.25 * k + 0.15 * p,
                  "mouthRollLower": rest.get("mouthRollLower", 0.0) + 0.12 * k,
                  "noseSneerLeft": rest.get("noseSneerLeft", 0.0) + 0.12 * p,
                  "noseSneerRight": rest.get("noseSneerRight", 0.0) + 0.12 * p}
        for brow in ("browDownLeft", "browDownRight"):                # amusement eases the frown
            values[brow] = rest.get(brow, 0.0) * (1 - 0.6 * k)
        face(rig, f, values, meshes)
    return end


def tremble(rig, start, end, strength=1.0, seed=1):
    """Lips trembling in fear: small fast irregular movements of the lips and chin."""
    rng = random.Random(seed)
    meshes = face_meshes(rig)
    for f in range(start, end + 1, 2):
        face(rig, f, {"mouthPressLeft": strength * rng.uniform(0.05, 0.35),
                      "mouthPressRight": strength * rng.uniform(0.05, 0.35),
                      "mouthShrugLower": strength * rng.uniform(0.1, 0.45),
                      "mouthRollLower": strength * rng.uniform(0.0, 0.2),
                      "mouthFrownLeft": strength * 0.3, "mouthFrownRight": strength * 0.3}, meshes)


# --- co-speech gestures and listening -------------------------------------------------------------------
# A gesture is preparation, stroke, holds and retraction; only the stroke is required (Kendon; McNeill). The
# stroke comes before or on the stressed (pitch-accented) syllable, never after it: it overlaps the accent in
# 80-90% of cases (Frontiers in Psychology 2018, 10.3389/fpsyg.2018.01514); the moment of peak effort (~50 ms)
# lines up with it (Pouw et al. 2019). Holds stretch a gesture over the phrase; the hands go back to rest only at
# real pauses. Beats are short, uniformly fast flicks; bigger gestures last longer (Myslyvyi et al.). The commonest
# conversational gesture is the palm-up open hand: forearm supine, palm up, fingers loosely extended and together
# (Kendon 2004 "open hand supine"; Mueller 2004 PUOH), offering an idea. Seated people gesture compactly, elbows in
# (seated-at-table interaction makes movements compact: Glasgow), into the space shared with the listener
# (Haviland). The head nods slightly on the strokes ("visual prosody", Munhall et al. 2004). Angry gestures are
# larger, faster and higher (Wallbott 1998). So a gesture here is a hand path in the speaker's own body space -
# from the chest, angled toward the listener - reached by arm IK, with the palm and the fingers set per gesture.
# (Replaying a standing actor's mocap joint rotations on a seated arm swung the hands out sideways, flat.)
CMU_LIBRARY = ROOT / "assets" / "mocap" / "library" / "cmu"
# (forward of the chest, up from the chest, out to the gesturing side) in m for a 1.76 m man; palm "up"/"down"/"in";
# fingers; the flick at each stroke and beat (m); both hands?
# Heights: most gestures happen at the centre of the gesture space, about chest height (McNeill 1992); a seated
# person's hands rest on the thighs, already ~30 cm in front of and ~25 cm below the chest, so a gesture has to
# come clearly up off the lap (the first poses here, 10 cm lower, moved a hand only 6 cm: nothing to see).
# Palms carry meaning: palm up (Kendon's "open hand supine") offers, shows, presents a topic - friendly talk;
# palm down ("open hand prone") halts, denies, interrupts - never for a raised hand in friendly talk. The default
# beat is an open palm flicking up and down (Shattuck-Hufnagel et al.; McNeill): here palm up, turned in ("upin").
# Where: from the SHOULDER, not the chest - a hand placed relative to the chest of a seated man leaning back ended
# 51 cm from the shoulder, the arm all but straight and swung out sideways: a puppet. The wrist goes along `dir`
# (forward, up, out to the gesturing side; out < 0 is across toward the midline) at the distance that bends the
# elbow to `elbow` degrees: 90-110 in conversation, the upper arm hanging near the body and the forearm doing the
# work (the elbow at ~90 with the upper arm by the trunk is the arm's relaxed working posture: AAO ergonomics).
GESTURES = {
    "offer": dict(dir=(0.75, -0.62, -0.05), elbow=100, palm="up", fingers="open", dip=0.03),   # palm-up open hand
    "present": dict(dir=(0.78, -0.64, 0.12), elbow=100, palm="up", fingers="open", dip=0.025, both=True),
    "beat": dict(dir=(0.70, -0.70, -0.08), elbow=105, palm="upin", fingers="open", dip=0.04),  # open palm flicks
    "chop": dict(dir=(0.85, -0.35, -0.05), elbow=100, palm="in", fingers="open", dip=0.09),   # agitated: the edge chops
    "fist": dict(dir=(0.80, -0.40, -0.02), elbow=90, palm="in", fingers="fist", dip=0.08),    # knuckles forward
    "spread": dict(dir=(0.62, -0.38, 0.45), elbow=110, palm="up", fingers="open", dip=0.05, both=True),
    # asked for at a word only (gestures(force=...)): brushing an idea away - the open hand flicks out and down,
    # palm turned away (Kendon's "away" gestures of the open-hand-prone family: dismissing, "nothing in it");
    # and the welcoming arm - it opens out to the side, palm up, the elbow more extended (an inviting sweep)
    "wave": dict(dir=(0.60, -0.45, 0.35), elbow=110, palm="away", fingers="open", dip=0.07),
    "welcome": dict(dir=(0.55, -0.50, 0.70), elbow=135, palm="up", fingers="open", dip=0.03),
    # pointing at something on the floor in front ("here, here!"): the arm reaches out and down, the index
    # finger straight, the others closed (asked for at a word only)
    "point": dict(dir=(0.60, -0.80, 0.00), elbow=160, palm="down", fingers="point", dip=0.03),
}
# The joints that hang off the forearm move like it: a relaxed wrist sags ~22 deg under gravity and the hand
# and fingers settle into a new pose in 0.38-0.48 s (Neff & Seidel 2006, Tables 1-2); gesturing, the wrist is
# held a little firmer, so here half the sag, and the hand trails the forearm on a damped spring that settles in
# ~0.45 s (2-3 frames behind a fast move, a slight overshoot: drag and follow-through). The shoulder girdle
# rises and comes forward with the arm (scapulohumeral rhythm: ~1 deg of scapula per 2 of arm, Inman).
WRIST_SAG = 0.2              # tan of the wrist's sag below the forearm line while gesturing (~11 deg)
DRAG = (2.2, 0.65)           # the hand's spring: natural frequency (Hz), damping ratio
NEW_GESTURE_AFTER = 1.6     # s: a long phrase gets a fresh gesture on a stress this long after the last one
CALM, AGITATED = (("offer", 0.45), ("beat", 0.3), ("present", 0.25)), (("chop", 0.4), ("fist", 0.3), ("spread", 0.3))
# Finger shapes, degrees at (knuckle MCP, middle PIP, tip DIP). A relaxed hand is never flat: it rests in the
# flexion cascade, least bent at the index (measured means, non-power-grip adults, dominant hand: Varghese et al.,
# J Clin Diagn Res 2020, 14(5) YC01; the wrist rests 15-20 degrees extended). An open gesturing hand is that
# cascade loosened, not straightened ("loosely extended", Kendon; animators: no flat "spatula hands").
# The fingers lie nearly parallel, not fanned: abduction from the middle finger at rest, index +1, ring -1.5,
# little -6 deg (Neff & Seidel 2006, Table 2; + toward the thumb there, + toward the little finger here). Our rigs
# rest with the hand fanned (ring 8, little 18 deg out), so _finger_shape turns each finger to these. The thumb
# sits in front of the palm, not in its plane: CMC palmar abduction 42, flexion 28, MCP 36, IP 24 (same table);
# here (palmar, MCP, IP) about the bone X and THUMB_ACROSS deg across toward the fingers about its Z.
SPREAD = {"Index": -1.0, "Middle": 0.0, "Ring": 1.5, "Pinky": 6.0}
RELAXED_HAND = {"Thumb": (12, 30, 20), "Index": (27, 39, 14), "Middle": (33, 41, 14), "Ring": (29, 45, 14),
                "Pinky": (26, 43, 16)}
HAND_SHAPES = {"relaxed": RELAXED_HAND,
               "open": {**{k: tuple(round(a * 0.35) for a in v) for k, v in RELAXED_HAND.items()}, "Thumb": (4, 8, 5)},
               "fist": {"Thumb": (45, 40, 30), "Index": (85, 100, 70), "Middle": (88, 100, 70), "Ring": (88, 100, 70),
                        "Pinky": (85, 95, 65)}}
HAND_SHAPES["point"] = {**HAND_SHAPES["fist"], "Index": (5, 5, 3), "Thumb": (30, 30, 20)}
THUMB_ACROSS = {"relaxed": 15, "open": -5, "fist": 25, "point": 20}   # open: a soft L beside the index, not sticking up
# The thumb is turned ~55-60 deg against the fingers (opposition), so its own knuckles (MCP, IP) bend across the
# palm toward the little finger, not up out of it; our rigs' thumbs are rolled like fingers (bending them about X
# stood the relaxed thumb 77 deg out of the palm, a hitchhiker's). They bend about an axis tilted OPPOSE degrees.
OPPOSE = 55
_REST_SPREAD = {}


def _voicing(wav):
    """Per 10 ms: time (s), loudness (dB), pitch (Hz, 0 when unvoiced), voiced (bool), from a PCM WAV."""
    import wave
    import numpy as np
    with wave.open(str(wav)) as w:
        rate, chans, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    pcm = np.frombuffer(raw, {1: np.int8, 2: np.int16, 4: np.int32}[width]).astype(np.float32)
    pcm = pcm.reshape(-1, chans).mean(1) / float(2 ** (8 * width - 1))
    hop, win = rate // 100, rate // 25
    lo, hi = rate // 300, rate // 70                               # pitch 70-300 Hz
    n = max(0, (len(pcm) - win) // hop)
    times, db, pitch = np.zeros(n), np.zeros(n), np.zeros(n)
    for i in range(n):
        seg = pcm[i * hop: i * hop + win]
        times[i] = (i * hop + win / 2) / rate
        db[i] = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)
        seg = seg - seg.mean()
        ac = np.correlate(seg, seg, "full")[win - 1:]
        if ac[0] <= 0:
            continue
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] / ac[0] > 0.3:
            pitch[i] = rate / lag
    voiced = (pitch > 0) & (db > (db.max() if n else 0) - 35)
    pitch[~voiced] = 0
    return times, db, pitch, voiced


def stress_times(wav):
    """Seconds of the stressed syllables in a voice line, from loudness and pitch peaks (no transcript):
    score = z(loudness) + 0.5 z(pitch rise over 50 ms), smoothed over a syllable (~110 ms); peaks above 1.0
    and at least 0.25 s apart, inside voiced speech."""
    import numpy as np
    times, db, pitch, voiced = _voicing(wav)
    if voiced.sum() < 3:
        return []

    def z(x):
        v = x[voiced]
        return (x - v.mean()) / (v.std() + 1e-9)
    rise = np.zeros_like(pitch)
    rise[5:] = np.where(voiced[5:] & voiced[:-5], pitch[5:] - pitch[:-5], 0.0)
    score = z(db) + 0.5 * z(rise)
    score[~voiced] = score[voiced].min()
    kernel = np.hanning(11)
    score = np.convolve(score, kernel / kernel.sum(), mode="same")
    peaks = [i for i in range(1, len(score) - 1)
             if voiced[i] and score[i] > 1.0 and score[i] >= score[i - 1] and score[i] >= score[i + 1]]
    kept = []
    for i in sorted(peaks, key=lambda i: -score[i]):
        if all(abs(times[i] - times[k]) >= 0.25 for k in kept):
            kept.append(i)
    return sorted(round(float(times[i]), 3) for i in kept)


def _rest_spread(rig, side):
    """{finger: (degrees from the middle finger in the palm plane, + toward the little finger; the sign of a
    bone-Z turn toward the little finger)} in the rig's rest pose."""
    key = (rig.data.name, side)
    if key not in _REST_SPREAD:
        B = rig.data.bones
        g = lambda n: B[f"{side}Hand{n}1"]
        along = lambda b: (b.tail_local - b.head_local).normalized()
        wrist = B[f"{side}Hand"].head_local
        n = (g("Index").head_local - wrist).cross(g("Pinky").head_local - wrist).normalized()
        k = (g("Pinky").head_local - g("Index").head_local).normalized()
        flat = lambda v: (v - v.project(n)).normalized()
        mid = flat(along(g("Middle")))
        out = {}
        for j in (2, 3):                         # the thumb's own knuckles: which way is across the palm
            b = B[f"{side}HandThumb{j}"]
            out[f"Thumb{j}"] = (0.0, 1 if b.matrix_local.to_3x3().col[2].cross(along(b)).dot(k) > 0 else -1)
        for finger in ("Thumb", *SPREAD):
            v = flat(along(g(finger)))
            ang = math.degrees(mid.angle(v)) if finger != "Middle" else 0.0
            out[finger] = (ang if v.dot(k) > mid.dot(k) else -ang,
                           1 if (g(finger).matrix_local.to_3x3().col[2]).cross(along(g(finger))).dot(k) > 0 else -1)
        _REST_SPREAD[key] = out
    return _REST_SPREAD[key]


def _finger_shape(rig, side, frame, shape):
    """Key one hand's fingers to a HAND_SHAPES shape at `frame`: flexion, the fingers brought nearly parallel
    (SPREAD) and the thumb in front of the palm, settling one after another (index first, little finger 3 frames
    later: fingers don't move as one block)."""
    spread = _rest_spread(rig, side)
    for k, (finger, degs) in enumerate(HAND_SHAPES[shape].items()):
        for j, deg in enumerate(degs, 1):
            pb = rig.pose.bones.get(f"{side}Hand{finger}{j}")
            if pb is not None:
                q = Quaternion((1, 0, 0), math.radians(deg))
                if finger == "Thumb" and j > 1:  # opposed: across the palm
                    o = math.radians(OPPOSE)
                    q = Quaternion((math.cos(o), 0, spread[f"Thumb{j}"][1] * math.sin(o)), math.radians(deg))
                if j == 1:
                    rest, sign = spread[finger]
                    turn = THUMB_ACROSS[shape] if finger == "Thumb" else SPREAD[finger] - rest
                    q = Quaternion((0, 0, 1), math.radians(sign * turn)) @ q
                pb.rotation_quaternion = q
                pb.keyframe_insert("rotation_quaternion", frame=frame + max(0, k - 1))


def _follow(target, fps, freq=DRAG[0], zeta=DRAG[1]):
    """Drag and follow-through: an orientation trailing `target` ({frame: Quaternion}) on a damped spring - a few
    frames behind a fast turn, settling with a slight overshoot. -> {frame: Quaternion}."""
    w0, dt = 2 * math.pi * freq, 1.0 / fps
    frames = sorted(target)
    cur, vel, out = target[frames[0]].copy(), Vector(), {}
    for f in frames:
        err = target[f] @ cur.inverted()
        if err.w < 0:
            err.negate()
        vel += (Vector(err.axis) * err.angle * w0 * w0 - 2 * zeta * w0 * vel) * dt
        if vel.length > 1e-9:
            cur = Quaternion(vel.normalized(), vel.length * dt) @ cur
            cur.normalize()
        out[f] = cur.copy()
    return out


def fidget(rig, start, end, seed=1, sides=("Left", "Right"), fps=24):
    """Hands are never frozen, not even at rest: the fingers drift a few degrees, and every 3-7 s a hand does
    something small - the fingers lift off the thigh and settle back (index first), the index taps twice, or the
    thumb rubs. Layered on whatever the hand does (call it after gestures())."""
    rng = random.Random(seed)
    names = ("Thumb", "Index", "Middle", "Ring", "Pinky")
    events = {}
    for s in sides:
        t, events[s] = start + rng.uniform(1, 4) * fps, []
        while t < end - fps:
            events[s].append((t, rng.choice(("lift", "lift", "tap", "rub"))))
            t += rng.uniform(3, 7) * fps
    phase = {(s, n): rng.uniform(0, 2 * math.pi) for s in sides for n in names}

    def env(x, rise, hold, fall):                # 0 -> 1 -> 0, eased
        if x <= 0 or x >= rise + hold + fall:
            return 0.0
        u = min(1.0, x / rise) if x < rise + hold else 1 - (x - rise - hold) / fall
        return u * u * (3 - 2 * u)

    def offsets(f):
        out = {}
        for s in sides:
            for k, n in enumerate(names):
                deg = 2.5 * math.sin(2 * math.pi * 0.15 * f / fps + phase[(s, n)])
                for t, kind in events[s]:
                    x = (f - t) / fps
                    if kind == "lift" and n != "Thumb":
                        deg -= 14 * env(x - 0.04 * k, 0.25, 0.3, 0.6)
                    elif kind == "tap" and n == "Index":
                        deg -= 12 * (env(x, 0.12, 0.0, 0.15) + env(x - 0.35, 0.12, 0.0, 0.15))
                    elif kind == "rub" and n == "Thumb":
                        deg += 8 * math.sin(2 * math.pi * x / 0.5) * env(x, 0.2, 0.6, 0.2)
                out[f"{s}Hand{n}1"] = Quaternion((1, 0, 0), math.radians(deg))
                out[f"{s}Hand{n}2"] = Quaternion((1, 0, 0), math.radians(0.6 * deg))
        return out
    _layer(rig, int(start), int(end), offsets, local=True)


def _gesture_units(wav, start_frame, energy, hands, seed, fps, force=()):
    """Plan the gestures of one line: one per phrase (voiced speech between pauses over 0.5 s) that has a
    stressed syllable, and a fresh one on a stress NEW_GESTURE_AFTER s after the last; its stroke lands 1-3 frames
    before the stress, the stresses in between are beats on it. force: [(seconds into the line, kind)] - that
    gesture on that word instead of what its stretch of the phrase would get."""
    rng = random.Random(seed)
    times, _, _, voiced = _voicing(wav)
    phrases, on, last_on = [], None, None
    for t, v in zip(times, voiced):
        if v:
            if on is None or (last_on is not None and t - last_on > 0.5):
                if on is not None:
                    phrases.append((on, last_on))
                on = t
            last_on = t
    if on is not None:
        phrases.append((on, last_on))
    stresses = stress_times(wav)
    pool = AGITATED if energy >= 0.6 else CALM
    units, shown = [], None
    groups = []
    for a, b in phrases:
        ss = [t for t in stresses if a - 0.05 <= t <= b + 0.05]
        group = []
        for t in ss:
            if group and t - group[0] >= NEW_GESTURE_AFTER:
                groups.append((group, t - 0.25))
                group = []
            group.append(t)
        if group:
            groups.append((group, b))
    groups = [(ss, b, None) for ss, b in groups]
    for t, kind in force:                        # a gesture asked for on a word: it replaces that stretch's own
        a, b = next(((a, b) for a, b in phrases if a - 0.3 <= t <= b + 0.3), (t, t + 0.6))
        near = [g for g in groups if a - 0.05 <= g[0][0] <= b + 0.05 and abs(g[0][0] - t) < NEW_GESTURE_AFTER]
        groups = [g for g in groups if g not in near] + [([t], max([b] + [g[1] for g in near]), kind)]
    groups.sort(key=lambda g: g[0][0])
    for ss, b, forced in groups:
        choices = [(k, w) for k, w in pool if (len(hands) == 2 or not GESTURES[k].get("both")) and k != shown]
        kind = forced or rng.choices([k for k, _ in choices], [w for _, w in choices])[0]
        if kind != "beat":
            shown = kind
        if GESTURES[kind].get("both"):
            used = tuple(hands)
        else:
            used = (hands[0],) if len(hands) == 1 else (("Right",) if rng.random() < 0.6 else ("Left",))
        stroke = start_frame + ss[0] * fps - rng.randint(1, 3)
        beats = [start_frame + t * fps - rng.randint(1, 2) for t in ss[1:]]
        hold = min(start_frame + b * fps + 0.25 * fps, (beats[-1] if beats else stroke) + 2.0 * fps)
        units.append(dict(kind=kind, hands=used, stroke=stroke, beats=beats, hold=max(hold, stroke + 4)))
    return units


def gestures(rig, wav, start_frame, energy=0.5, hands=("Left", "Right"), toward=None, seed=1, force=()):
    """Co-speech gestures for a voice line starting at start_frame (see the research above): per phrase, a hand
    (or both) rises from where it rests into the space in front of the chest, angled toward `toward` (the
    listener's head, a world point), the palm and fingers shaped for the gesture (palm-up open hand, open-palm
    beats turned up and in; agitated: chop, fist, spread), in an arc, the palm turning as the hand leaves the lap
    and the fingers settling after the wrist, arriving with a small flick 1-3 frames before the stressed syllable;
    later stresses in the phrase are quick beats; it holds (drifting a little) through the phrase and goes back
    to rest at a pause over 0.5 s. energy 0..1: calm (small, low) to agitated (>= 0.6: larger, higher, faster).
    Only the hands in `hands` move (one holding something stays put). The head nods 2-4 degrees on each stroke.
    force: [(seconds into the line, kind)] puts that gesture on that word (a wave-off on "dream").
    Returns the stroke frames (gestures and beats); rig["gesture_log"] has each stroke's kind."""
    scene = bpy.context.scene
    fps = scene.render.fps
    rng = random.Random(seed + 7)
    units = _gesture_units(wav, start_frame, energy, hands, seed, fps, force)
    rig["gesture_log"] = []
    if not units:
        return []
    base_size = (0.75 + 0.5 * energy) * rig.matrix_world.to_scale().x
    prep = (0.22 if energy >= 0.6 else 0.35) * fps
    back = (0.35 if energy >= 0.6 else 0.5) * fps
    strokes = []
    for side in ("Left", "Right"):
        mine = [u for u in units if side in u["hands"]]
        if not mine:
            continue
        twin = side == "Left"                        # two-handed: the left hand 2 frames behind and a little smaller
        size = base_size * (0.92 if twin else 1.0)
        mine = [dict(u, stroke=u["stroke"] + 2, beats=[b + 2 for b in u["beats"]], hold=u["hold"] + 2)
                if twin and len(u["hands"]) == 2 else u for u in mine]
        keys, pose = [], None                        # (frame, kind or None for rest)
        for i, u in enumerate(mine):
            begin = max(u["stroke"] - prep, keys[-1][0] + 2 if keys else start_frame - prep)
            keys += [(begin, pose), (u["stroke"], u["kind"])]
            nxt = mine[i + 1] if i + 1 < len(mine) else None
            if nxt is not None and nxt["stroke"] - prep <= u["hold"] + back:
                pose = u["kind"]                     # straight on into the next gesture
                continue
            keys += [(u["hold"], u["kind"]), (u["hold"] + back, None)]
            pose = None
        first, last = int(keys[0][0]), int(math.ceil(keys[-1][0])) + 1
        pb = rig.pose.bones
        frames = range(first, last + 1)

        def seg(f):                                  # (kind from, kind to, linear 0..1, eased 0..1)
            for (fa, ka), (fb, kb) in zip(keys, keys[1:]):
                if fa <= f <= fb:
                    raw = 1.0 if ka == kb else min(1.0, max(0.0, (f - fa) / max(fb - fa, 1)))
                    return ka, kb, raw, raw * raw * (3 - 2 * raw)
            return None, None, 0.0, 0.0

        def weight(f):                               # 0 at rest .. 1 gesturing
            ka, kb, _, w = seg(f)
            return (w if kb else 1 - w) if (ka is None) != (kb is None) else (1.0 if ka else 0.0)
        sx = 1 if side == "Left" else -1             # the shoulder girdle rises and comes forward with the arm
        lift, ahead = 4 + 4 * energy, 3 + 2 * energy
        _layer(rig, first, last, lambda f: {f"{side}Shoulder": (-sx * ahead * weight(f), 0, -sx * lift * weight(f))})
        l1 = pb[f"{side}Arm"].length * rig.matrix_world.to_scale().x
        l2 = pb[f"{side}ForeArm"].length * rig.matrix_world.to_scale().x
        pole = Vector((0.3 * sx, 0.45, -0.85))       # elbows down, back and a little out (armature space)
        reach_to = lambda deg: math.sqrt(l1 * l1 + l2 * l2 - 2 * l1 * l2 * math.cos(math.radians(deg)))
        rest, body = {}, {}
        for f in frames:                             # where the hand rests and where the body is, before any key
            scene.frame_set(f)
            m = rig.matrix_world
            rest[f] = (m @ pb[f"{side}Hand"].head, (m.to_3x3().normalized() @ pb[f"{side}Hand"].matrix.to_3x3()).normalized())
            fwd = (m.to_3x3() @ Vector((0, -1, 0)))
            fwd.z = 0
            fwd.normalize()
            out = (m.to_3x3() @ Vector((1, 0, 0))).normalized() * sx
            if toward is not None:                   # angled into the space shared with the listener (~15 deg)
                to = Vector(toward) - m @ pb["Spine1"].head
                to.z = 0
                if to.length > 0.1:
                    fwd = (fwd + 0.3 * to.normalized()).normalized()
                    out = (out - out.project(fwd)).normalized()
            body[f] = (m @ pb[f"{side}Arm"].head, fwd, out, (m.to_3x3() @ pole).normalized())

        def place(kind, f):
            g = GESTURES[kind]
            shoulder, fwd, out, bend = body[f]
            a, b, c = g["dir"]
            u = (fwd * a + Vector((0, 0, b)) + out * c).normalized()
            d = reach_to(g["elbow"] + (energy - 0.5) * 24)
            p = shoulder + u * d + Vector((0, 0, 0.012 * math.sin(2 * math.pi * 0.4 * f / fps + (sx > 0))))
            u = (p - shoulder).normalized()          # the elbow as the IK will put it, so the hand carries on
            e = (l1 * l1 + d * d - l2 * l2) / (2 * d)  # the forearm's line (no wrist bent at the hand's whim)
            elbow = shoulder + u * e + (bend - bend.project(u)).normalized() * math.sqrt(max(0.0, l1 * l1 - e * e))
            line = (p - elbow).normalized()
            sag = Vector((0, 0, -1)) - Vector((0, 0, -1)).project(line)
            fingers = line + WRIST_SAG * sag.normalized() if sag.length > 1e-3 else line
            palm = {"up": Vector((0, 0, 1)), "upin": Vector((0, 0, 0.75)) - out * 0.65, "in": -out,
                    "away": out * 0.75 + fwd * 0.35 - Vector((0, 0, 0.35)), "down": Vector((0, 0, -1))}[g["palm"]]
            return p, hand_frame(fingers, palm)

        def at(f):
            ka, kb, raw, w = seg(f)
            pa = place(ka, f) if ka else rest[f]
            if ka == kb:
                return pa
            # the forearm turns the palm as the hand leaves the lap, and back only as it lands
            rw = min(1.0, raw * 1.6) if ka is None else max(0.0, raw * 1.6 - 0.6) if kb is None else raw
            rw = rw * rw * (3 - 2 * rw)
            pb_ = place(kb, f) if kb else rest[f]
            fwd = body[f][1]
            arc = (Vector((0, 0, 0.035)) + fwd * 0.02) * size * math.sin(math.pi * raw)   # hands move in arcs
            return (pa[0].lerp(pb_[0], w) + arc, pa[1].to_quaternion().slerp(pb_[1].to_quaternion(), rw).to_matrix())
        flicks = [(u["stroke"], GESTURES[u["kind"]]) for u in mine] + \
                 [(b_, GESTURES[u["kind"]]) for u in mine for b_ in u["beats"]]
        targets, turns = {}, {}
        for f in frames:
            p, rot = at(f)
            for t, g in flicks:                      # the stroke: a quick flick down (and out, offering)
                d = (f - t) / (0.07 * fps)
                if abs(d) < 3:
                    fwd = body[f][1]
                    dirn = Vector((0, 0, -1)) + (fwd * 0.6 if g["palm"] in ("up", "upin") else Vector())
                    if g["palm"] == "away":          # brushed away: the flick goes out to the side
                        dirn = body[f][2] * 0.9 + Vector((0, 0, -0.3))
                    p = p + dirn.normalized() * g["dip"] * size * weight(f) * math.exp(-d * d)
            targets[f], turns[f] = p, rot.to_quaternion()
        dragged = _follow(turns, fps)                # the hand trails the forearm and settles
        reach(rig, side, first, last, target=lambda f: targets[f], hand=lambda f: dragged[f].to_matrix(), blend=1,
              pole=tuple(pole))
        shape = lambda k: GESTURES[k]["fingers"] if k else "relaxed"
        for (fa, ka), (fb, kb) in zip(keys, keys[1:]):
            if kb != ka:                             # the fingers follow the wrist, a couple of frames behind
                _finger_shape(rig, side, int(fa) + 2, shape(ka))
                _finger_shape(rig, side, int(fb) + 2, shape(kb))
        strokes += [(int(round(u["stroke"])), u["kind"]) for u in mine] + \
                   [(int(round(b_)), "beat") for u in mine for b_ in u["beats"]]
    strokes = sorted(set(strokes))
    nods = [(f, rng.uniform(2, 4)) for f, _ in strokes]
    lo, hi = min(f for f, _ in strokes) - 10, max(f for f, _ in strokes) + 10
    nod = lambda f: sum(a * math.exp(-((f - s_) / (0.12 * fps)) ** 2) for s_, a in nods)
    _layer(rig, lo, hi, lambda f: {"Head": (0, nod(f), 0), "Spine1": (0, 0.35 * nod(f), 0)})   # leaning into it
    rig["gesture_log"] = [k for _, k in strokes]
    return [f for f, _ in strokes]



def listen(rig, start, end, speaker_rig, phrase_ends=(), seed=1, gaze=True, shift="Hips"):
    """A listener: gaze on the speaker's head with the listening statistics of eyes() (long mutual gaze, short
    glances away), a nod (3-6 degrees, ~0.5 s) at the speaker's phrase ends (the first always, then 70%),
    and a slow weight shift (hips roll 1-2 degrees) every 4-8 s. gaze=False: only the nods and weight shifts
    (the gaze then comes from one eyes() call over the whole scene). shift: the bone the weight shift rolls
    (a seated person shifts in the lower back: rolling the hips would slide the feet on the floor)."""
    fps = bpy.context.scene.render.fps
    bpy.context.view_layer.update()
    me = rig.matrix_world @ rig.pose.bones["Head"].head
    them = speaker_rig.matrix_world @ speaker_rig.pose.bones["Head"].head
    d = rig.matrix_world.inverted().to_3x3() @ (them - me)      # armature space: faces -Y, +X is its left
    yaw = math.degrees(math.atan2(d.x, -d.y))
    pitch = math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
    if gaze:
        eyes(rig, start, end, mode="listening", look=(yaw, pitch), seed=seed)
    rng = random.Random(seed + 1)
    nods = [(f, rng.uniform(3, 6)) for k, f in enumerate(phrase_ends)
            if start <= f <= end and (k == 0 or rng.random() < 0.7)]
    shifts, t, side = [], start + rng.uniform(1, 3) * fps, 1
    while t < end:
        shifts.append((t, side * rng.uniform(1, 2)))
        side, t = -side, t + rng.uniform(4, 8) * fps

    def offsets(f):
        nod = sum(a * math.sin(math.pi * (f - s) / (0.5 * fps)) for s, a in nods if s <= f <= s + 0.5 * fps)
        roll, prev = 0.0, 0.0
        for s, r in shifts:
            if f < s:
                break
            k = min(1.0, (f - s) / fps)
            roll, prev = prev + (r - prev) * k * k * (3 - 2 * k), r
        return {"Head": (0, nod, 0), "Neck1": (0, nod / 3, 0), shift: (0, 0, roll)}
    _layer(rig, int(start), int(end), offsets)


def _selfcheck():
    """Retarget a CMU clip onto a second copy of its own skeleton: world rotations must match."""
    bvh = ROOT / "assets" / "mocap" / "cmu" / "77_14.bvh"
    before = set(bpy.data.objects)
    bpy.ops.import_anim.bvh(filepath=str(bvh), use_fps_scale=True, update_scene_fps=False)
    target = (set(bpy.data.objects) - before).pop()
    target.animation_data_clear()
    target.location.x += 2
    bpy.context.view_layer.update()
    end = retarget(target, bvh, start_frame=1, bone_map={}, max_frames=40, keep_source=True)
    source = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o is not target)
    worst = 0.0
    for f in (1, 20, end):
        bpy.context.scene.frame_set(f)
        for pb in target.pose.bones:
            a = (target.matrix_world @ pb.matrix).to_quaternion()
            b = (source.matrix_world @ source.pose.bones[pb.name].matrix).to_quaternion()
            angle = a.rotation_difference(b).angle
            worst = max(worst, min(angle, 2 * math.pi - angle))     # q and -q are the same rotation
        hips = lambda o: o.matrix_world @ o.pose.bones["Hips"].head
        moved = (hips(target) - hips(source) - Vector((2, 0, 0))).length
        assert moved < 1e-4, f"hips off by {moved:.5f} at frame {f}"
    assert worst < 1e-3, f"retarget drifted by {math.degrees(worst):.3f} degrees"
    # plant_feet: knees keep their mocap bend and no foot ends up below the floor
    def knees():
        out = []
        for f in range(1, end + 1):
            bpy.context.scene.frame_set(f)
            for s in ("Left", "Right"):
                h, k, a = (target.pose.bones[n].head for n in (f"{s}UpLeg", f"{s}Leg", f"{s}Foot"))
                out.append(math.degrees((h - k).angle(a - k)))
        return out
    before = knees()
    plant_feet(target, 1, end)
    after = knees()
    drift = sum(abs(x - y) for x, y in zip(before, after)) / len(before)
    lowest = min((target.matrix_world @ target.pose.bones[f"{s}ToeBase"].tail).z
                 for f in range(1, end + 1) if not bpy.context.scene.frame_set(f) for s in ("Left", "Right"))
    assert drift < 3.0, f"plant_feet changed knee bend by {drift:.1f} degrees on average"
    assert lowest > -0.01, f"a foot went {-lowest * 100:.1f} cm through the floor"
    # reach: the wrist gets to its target, and once let go the arm is exactly as it was
    scene = bpy.context.scene
    arm = lambda f: [not scene.frame_set(f) and (target.matrix_world @ target.pose.bones[n].matrix).to_quaternion()
                     for n in ("LeftArm", "LeftForeArm", "LeftHand")]
    wrist = lambda f: not scene.frame_set(f) and target.matrix_world @ target.pose.bones["LeftHand"].head
    goal = wrist(20) + Vector((0.12, 0.08, 0.15))
    untouched = {f: arm(f) for f in (8, 34)}
    reach(target, "Left", 1, end, lambda f: goal if 15 <= f <= 25 else None, blend=5)
    missed = (wrist(20) - goal).length
    back = max(math.degrees(min(x.rotation_difference(y).angle, 2 * math.pi - x.rotation_difference(y).angle))
               for f, qs in untouched.items() for x, y in zip(qs, arm(f)))
    assert missed < 0.01, f"reach missed its target by {missed * 100:.1f} cm"
    want = Matrix.Rotation(math.radians(70), 3, "X") @ Matrix.Rotation(math.radians(40), 3, "Z")
    reach(target, "Right", 1, end, lambda f: None if f < 15 or f > 25 else
          (not scene.frame_set(f) and target.matrix_world @ target.pose.bones["RightHand"].head), hand=want)
    scene.frame_set(20)
    got = (target.matrix_world @ target.pose.bones["RightHand"].matrix).to_quaternion()
    off = math.degrees(got.rotation_difference(want.to_quaternion()).angle)
    off = min(off, 360 - off)
    assert off < 1.0, f"reach left the hand {off:.2f} degrees off the requested angle"
    assert back < 0.1, f"reach left the arm {back:.2f} degrees off after letting go"
    print(f"humans selfcheck OK: {len(target.pose.bones)} bones x {end} frames, worst error {math.degrees(worst):.5f} deg; "
          f"plant_feet knee change {drift:.2f} deg, lowest toe {lowest * 100:+.1f} cm; "
          f"reach miss {missed * 100:.2f} cm, arm after release {back:.3f} deg, hand angle off {off:.2f} deg")


def _selfcheck_character(character="OldMan"):
    """One of our characters: bone and vertex-group names, the hand/finger convention, the gaze direction of the
    eye bones, and that eyeBlink really covers the eye."""
    from mathutils.bvhtree import BVHTree
    scene = bpy.context.scene
    who = f"Check{character}"
    rig = build({"name": who, "character": character})
    for obj in rig.children:                 # every texture loads on this machine (not just the one it was made on)
        for mat in obj.data.materials:
            for node in mat.node_tree.nodes if mat and mat.node_tree else ():
                if node.type == "TEX_IMAGE" and node.image:
                    assert Path(bpy.path.abspath(node.image.filepath)).exists(), \
                        f"{character}: missing texture {node.image.filepath}"
    for bone in ("Hips", "LowerBack", "Spine", "Spine1", "Neck1", "Head", "LeftArm", "LeftHand", "LeftHandIndex1",
                 "RightHandThumb1", "LeftUpLeg", "LeftToeBase", "LeftEye", "RightEye"):
        assert bone in rig.pose.bones, f"{character}: no bone {bone}"
    body = next(o for o in rig.children if o.name == f"{who}.body")
    assert "LowerBack" in body.vertex_groups and "Neck1" in body.vertex_groups, "vertex groups not renamed"
    keys = body.data.shape_keys.key_blocks
    for k in ("eyeBlinkLeft", "eyeBlinkRight", "jawOpen", "browInnerUp", "mouthSmileLeft", "eyeLookUpLeft"):
        assert k in keys, f"{character}: no face shape {k}"
    # a finger's +X curls toward the palm (-Z of the hand bone)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    pb = rig.pose.bones
    tip0 = pb["LeftHandIndex3"].tail.copy()
    palm = -(pb["LeftHand"].matrix.to_3x3() @ Vector((0, 0, 1)))
    for j in (1, 2, 3):
        pb[f"LeftHandIndex{j}"].rotation_quaternion = Quaternion((1, 0, 0), math.radians(30))
    bpy.context.view_layer.update()
    toward_palm = (pb["LeftHandIndex3"].tail - tip0).dot(palm)
    for j in (1, 2, 3):
        pb[f"LeftHandIndex{j}"].rotation_quaternion = Quaternion()
    assert toward_palm > 0.01, f"finger curl moved the tip {toward_palm * 100:.1f} cm toward the palm"
    # gaze 20 degrees to the character's left (+X in armature space)
    _key_eyes(rig, face_meshes(rig), 1, (20.0, 10.0))
    bpy.context.view_layer.update()
    look = pb["LeftEye"].matrix.to_3x3() @ Vector((0, 1, 0))
    yaw, pitch = math.degrees(math.atan2(look.x, -look.y)), math.degrees(math.asin(look.z))
    assert abs(yaw - 20) < 1 and abs(pitch - 10) < 1, f"eye looks {yaw:.1f} left, {pitch:.1f} up"
    # a closed eye: a ray straight at the left eyeball hits the eyelid first
    _key_eyes(rig, face_meshes(rig), 1, (0.0, 0.0))
    eyes = next(o for o in rig.children if o.name == f"{who}.eyes")
    deps = bpy.context.evaluated_depsgraph_get()
    centre = sum((eyes.matrix_world @ v.co for v in eyes.data.vertices if v.co.x > 0), Vector()) / \
        sum(1 for v in eyes.data.vertices if v.co.x > 0)
    start = centre + Vector((0, -0.2, 0))

    def first_hit():
        deps.update()
        hb = BVHTree.FromObject(body, deps).ray_cast(start, Vector((0, 1, 0)), 0.4)
        he = BVHTree.FromObject(eyes, deps).ray_cast(start, Vector((0, 1, 0)), 0.4)
        return "lid" if hb[0] is not None and (he[0] is None or hb[3] < he[3]) else "eye"
    open_ = first_hit()
    keys["eyeBlinkLeft"].value = 1.0
    shut = first_hit()
    keys["eyeBlinkLeft"].value = 0.0
    assert (open_, shut) == ("eye", "lid"), f"blink: open eye shows the {open_}, closed shows the {shut}"
    print(f"humans selfcheck OK ({character}): {len(rig.pose.bones)} bones, {len(keys) - 1} face shapes; finger curl "
          f"{toward_palm * 100:.1f} cm toward the palm; gaze {yaw:.1f} left {pitch:.1f} up; blink covers the eye")


def _selfcheck_gestures():
    """Stressed syllables found in a synthetic voice; gesture strokes land on them (0-0.15 s early, never late);
    no gesture unit twice in a row; a hand left out of `hands` (holding something) stays still; a listener
    nods at a phrase end."""
    import wave
    import numpy as np
    rate, bursts = 16000, (0.6, 1.5, 2.4)
    t = np.arange(int(3.0 * rate)) / rate
    x = 0.02 * np.sin(2 * np.pi * 160 * t)                       # a quiet voiced hum
    for b in bursts:                                              # stressed syllables: +18 dB, +60 Hz
        on = np.abs(t - b) < 0.06
        x[on] = 0.02 * 10 ** (18 / 20) * np.sin(2 * np.pi * 220 * t[on])
    wav = Path(bpy.app.tempdir) / "stress_check.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    found = stress_times(wav)
    assert len(found) == 3 and all(abs(f - b) <= 0.05 for f, b in zip(found, bursts)), f"stresses {found}"

    fps = 24
    rig = build({"name": "GestureCheck", "character": "Narrator"})
    relax_arms(rig)
    left = [b.name for b in rig.pose.bones if b.name.startswith("Left") and
            any(b.name.endswith(p) for p in ("Shoulder", "Arm", "ForeArm", "Hand"))]
    scene = bpy.context.scene
    before = {}
    for f in range(1, 73):
        scene.frame_set(f)
        before[f] = {n: rig.pose.bones[n].rotation_quaternion.copy() for n in left}
    rest = {}
    for f in range(1, 73):
        scene.frame_set(f)
        rest[f] = (rig.matrix_world @ rig.pose.bones["RightHand"].head).copy()
    strokes = gestures(rig, wav, 1, hands=("Right",), toward=Vector((-1.5, -0.8, 1.4)), seed=4)   # listener to his right
    assert strokes, "no strokes"
    for f in strokes:
        assert any(b * fps + 1 - 0.15 * fps - 1 <= f <= b * fps + 1 + 1 for b in bursts), f"stroke at {f} off the stress"
    kinds = list(rig["gesture_log"])
    shown = [k for k in kinds if k != "beat"]
    assert all(a != b for a, b in zip(shown, shown[1:])), f"the same gesture twice in a row: {kinds}"
    pb = rig.pose.bones
    scene.frame_set(1)
    clav0 = pb["RightShoulder"].matrix.to_quaternion()
    shrug0 = pb["RightArm"].head.z - pb["Neck1"].head.z
    for f, kind in zip(strokes, kinds):          # research-based gesture space (compact, in front, toward the listener)
        scene.frame_set(f)
        m = rig.matrix_world
        S, E, W = (m @ pb[f"Right{b}"].head for b in ("Arm", "ForeArm", "Hand"))
        elbow = math.degrees((S - E).angle(W - E))   # a gesturing elbow is bent, the upper arm near the body
        assert 70 <= elbow <= 135, f"{kind} at {f}: elbow at {elbow:.0f} deg (a near-straight arm reads as a rig)"
        clav = math.degrees(clav0.rotation_difference(pb["RightShoulder"].matrix.to_quaternion()).angle)
        assert clav >= 2.0, f"{kind} at {f}: the shoulder girdle doesn't move ({clav:.1f} deg; scapulohumeral rhythm)"
        shrug = pb["RightArm"].head.z - pb["Neck1"].head.z - shrug0
        assert shrug >= 0.004, f"{kind} at {f}: the shoulder doesn't rise with the arm ({shrug * 100:+.1f} cm)"
        fwd = (m.to_3x3() @ Vector((0, -1, 0))).normalized()
        chest, wrist = m @ pb["Spine1"].head, m @ pb["RightHand"].head
        ahead, up = (wrist - chest).dot(fwd), wrist.z - chest.z
        assert ahead >= 0.15, f"{kind} at {f}: the hand is not in front of the body ({ahead:.2f} m)"
        assert -0.42 <= up <= 0.12, f"{kind} at {f}: the hand is out of the gesture space ({up:+.2f} m from the chest)"
        if kind == "offer":                      # palm-up open hand: the forearm supine, the palm facing up
            palm = (m.to_3x3() @ pb["RightHand"].matrix.to_3x3() @ Vector((0, 0, -1))).normalized()
            assert palm.z > 0.5, f"offer at {f}: the palm faces {tuple(round(c, 2) for c in palm)}, not up"
    low = 9.0
    path = {}
    for f in range(1, 73):
        scene.frame_set(f)
        m = rig.matrix_world
        assert (m @ pb["RightForeArm"].head).z < (m @ pb["RightArm"].head).z, f"the elbow rises above the shoulder at {f}"
        wrist = m @ pb["RightHand"].head
        path[f] = wrist
        low = min(low, wrist.z - rest[f].z)
        palm = (m.to_3x3() @ pb["RightHand"].matrix.to_3x3() @ Vector((0, 0, -1))).normalized()
        if wrist.z - rest[f].z > 0.05:   # a raised hand in friendly talk is never palm down (Kendon: halting, negating)
            assert palm.z > -0.2, f"raised hand palm down at {f} (palm {palm.z:+.2f})"
    assert low >= -0.02, f"the hand goes {-low * 100:.1f} cm below where it rests (into the lap)"
    s0 = strokes[0]                     # hands move in arcs (animators; successive breaking of joints), not lines
    a_, b_ = path[max(1, s0 - 8)], path[s0]
    bow = max(((path[f] - a_) - (path[f] - a_).project(b_ - a_)).length for f in range(max(1, s0 - 8), s0 + 1))
    assert bow >= 0.015, f"the hand rises in a straight line (bow {bow * 100:.1f} cm)"
    _finger_shape(rig, "Left", 300, "relaxed")      # the resting hand's flexion cascade (Varghese et al. 2020)
    scene.frame_set(300)
    bent = {fg: sum(math.degrees(pb[f"LeftHand{fg}{j}"].rotation_quaternion.angle) for j in (1, 2, 3))
            for fg in ("Index", "Middle", "Ring", "Pinky")}
    assert min(bent.values()) >= 60 and bent["Index"] == min(bent.values()), f"relaxed fingers not a cascade: {bent}"
    for shape in ("relaxed", "open"):              # fingers nearly parallel, the thumb in front of the palm
        _finger_shape(rig, "Left", 300, shape)     # (Neff & Seidel 2006: index +1, ring -1.5, little -6 deg; thumb
        scene.frame_set(300)                       # CMC palmar abduction 42 deg)
        wrist = pb["LeftHand"].head
        n = (pb["LeftHandIndex1"].head - wrist).cross(pb["LeftHandPinky1"].head - wrist).normalized()
        if (pb["LeftHandMiddle3"].tail - pb["LeftHandMiddle1"].head).dot(n) < 0:
            n = -n                                 # n: out of the palm side
        k = pb["LeftHandPinky1"].head - pb["LeftHandIndex1"].head

        def flat(v):
            return v - v.project(n)
        mid = flat(pb["LeftHandMiddle1"].vector)
        ang = {fg: math.degrees(mid.angle(flat(pb[f"LeftHand{fg}1"].vector))) *
              (1 if flat(pb[f"LeftHand{fg}1"].vector).dot(k) > mid.dot(k) else -1) for fg in ("Index", "Ring", "Pinky")}
        assert ang["Pinky"] - ang["Index"] <= 12, f"{shape} fingers fan out {ang} (splayed: a claw)"
        thumb = pb["LeftHandThumb3"].tail - pb["LeftHandThumb1"].head
        lift = math.degrees(math.asin(max(-1.0, min(1.0, thumb.normalized().dot(n)))))
        assert (12 if shape == "open" else 20) <= lift <= 45, \
            f"{shape} thumb {lift:.0f} deg in front of the palm (flat in its plane, or sticking up like a hitchhiker's)"
    lagged = _follow({f: Quaternion() if f < 10 else Quaternion((1, 0, 0), math.radians(60)) for f in range(1, 40)},
                     fps)                          # the hand trails the forearm (drag), settles, barely overshoots
    turned = {f: math.degrees(q.angle) for f, q in lagged.items()}
    assert turned[10] < 30 and turned[11] < 45, f"no drag: {turned[10]:.0f}, {turned[11]:.0f} deg right after the turn"
    assert abs(turned[39] - 60) < 1 and max(turned.values()) < 69, f"drag doesn't settle: {turned}"
    angry = build({"name": "AngryGestureCheck", "character": "Narrator"}, location=(-3, 0, 0))
    relax_arms(angry)
    gestures(angry, wav, 1, hands=("Right",), energy=0.9, seed=4)

    def highest(r):
        top = -9.0
        for f in range(1, 73):
            scene.frame_set(f)
            top = max(top, (r.matrix_world @ r.pose.bones["RightHand"].head).z - r.matrix_world.translation.z)
        return top
    assert highest(angry) > highest(rig) + 0.05, "agitated gestures are no larger than calm ones"
    asked = build({"name": "ForceCheck", "character": "Narrator"}, location=(-6, 0, 0))   # a gesture on a word
    relax_arms(asked)
    got = dict(zip(gestures(asked, wav, 1, hands=("Left",), seed=4, force=[(1.5, "welcome")]), asked["gesture_log"]))
    assert any(k == "welcome" and abs(f - (1 + 1.5 * fps)) <= 3 for f, k in got.items()), f"no welcome at 1.5 s: {got}"
    pointer = build({"name": "PointCheck", "character": "Narrator"}, location=(-9, 0, 0))   # "here, here!"
    relax_arms(pointer)
    got = dict(zip(gestures(pointer, wav, 1, hands=("Right",), seed=4, force=[(1.5, "point")]), pointer["gesture_log"]))
    at = next((f for f, k in got.items() if k == "point"), None)
    assert at is not None, f"no point stroke: {got}"
    scene.frame_set(at + 2)
    pp = pointer.pose.bones
    S, E, W = (pp[f"Right{b}"].head for b in ("Arm", "ForeArm", "Hand"))
    reach_out = math.degrees((S - E).angle(W - E))
    assert reach_out >= 140, f"pointing with the elbow at {reach_out:.0f} deg (a point reaches out)"
    curl = {fg: sum(math.degrees(pp[f"RightHand{fg}{j}"].rotation_quaternion.angle) for j in (1, 2, 3))
            for fg in ("Index", "Middle")}
    assert curl["Index"] < 25 < 150 < curl["Middle"], f"not a pointing hand: {curl}"
    for f in range(1, 73):
        scene.frame_set(f)
        for n in left:
            q = rig.pose.bones[n].rotation_quaternion
            assert min((q - before[f][n]).magnitude, (q + before[f][n]).magnitude) < 1e-4, f"{n} moved at {f}"

    tired = build({"name": "WearCheck", "character": "Narrator"}, location=(-12, 0, 0))   # seven sleepless nights
    face(tired, 1, {"eyeBlinkLeft": 0.0, "eyeBlinkRight": 0.0})
    face(tired, 40, {"eyeBlinkLeft": 0.0, "eyeBlinkRight": 0.0})
    wear(tired, [(10, 0.2), (20, 0.6)])
    lid = face_meshes(tired)[0].data.shape_keys.key_blocks["eyeBlinkLeft"]
    skin = next(m for o in tired.children if o.type == "MESH" for m in o.data.materials if m and "Skin" in m.name)
    for f, w in ((5, 0.0), (15, 0.2), (30, 0.6)):
        scene.frame_set(f)
        sat = skin.node_tree.nodes["Worn"].inputs["Saturation"].default_value
        assert abs(lid.value - 0.15 * w) < 2e-3 and abs(sat - (1 - 0.35 * w)) < 1e-3 and abs(tired["worn"] - w) < 1e-6, \
            f"worn {w} at {f}: lids {lid.value:.3f}, saturation {sat:.3f}, worn {tired['worn']}"
    speaker = build({"name": "SpeakerCheck", "character": "Narrator"}, location=(0, -2.0, 0))
    speaker.rotation_euler.z = math.pi                            # facing the listeners
    nodder = build({"name": "NodCheck", "character": "Narrator"}, location=(3, 0, 0))
    still = build({"name": "NoNodCheck", "character": "Narrator"}, location=(3, 0, 0))
    bpy.context.view_layer.update()
    listen(nodder, 1, 72, speaker, phrase_ends=[36])
    listen(still, 1, 72, speaker, phrase_ends=[])

    def head_dir(r):
        return (r.matrix_world @ r.pose.bones["Head"].matrix).to_3x3() @ Vector((0, 1, 0))
    nod = 0.0
    for f in range(36, 49):
        scene.frame_set(f)
        nod = max(nod, math.degrees(head_dir(nodder).angle(head_dir(still))))
    assert nod >= 3.0, f"listener nod only {nod:.1f} deg"
    sitter = build({"name": "SitCheck", "character": "Narrator"}, location=(4.5, 0, 0))
    scene.frame_set(1)
    hips0 = sitter.pose.bones["Hips"].matrix.copy()
    listen(sitter, 1, 300, speaker, phrase_ends=[36], gaze=False, shift="LowerBack")   # seated: hips stay put
    for f in (100, 200, 290):
        scene.frame_set(f)
        assert max(abs(x) for row in (sitter.pose.bones["Hips"].matrix - hips0) for x in row) < 1e-5, "seated hips moved"
    print(f"humans gestures OK: {len(found)} stresses, strokes on time, held hand still, listener nods "
          f"(gestures {kinds} at {strokes}: in front of the chest, palm up when offering, elbow below the "
          f"shoulder, never below the lap; agitated higher; nod {nod:.1f} deg)")

    # eyes() with a look target and gaze mode that change over time (one call per character per scene, so the
    # head never snaps back to centre between spans): far left until frame 60, then far right
    looker = build({"name": "LookCheck", "character": "Narrator"}, location=(6, 0, 0))
    eyes(looker, 1, 140, mode=lambda f: "listening", look=lambda f: (40.0, 0.0) if f < 60 else (-40.0, 0.0), seed=3)

    def gaze(f):
        scene.frame_set(f)
        return looker.pose.bones["LeftEye"].matrix.to_3x3() @ Vector((0, 1, 0))
    early, late = gaze(50), gaze(130)
    turned = math.degrees(early.angle(late))
    assert turned > 30, f"gaze did not follow the moving target ({turned:.1f} deg)"
    print(f"humans eyes OK: gaze follows a moving target ({turned:.0f} deg between targets)")


if __name__ == "__main__" and "--selfcheck" in sys.argv:
    bpy.context.scene.render.fps = 24
    _selfcheck()
    for name in ("OldMan", "Narrator"):
        _selfcheck_character(name)
    _selfcheck_gestures()
