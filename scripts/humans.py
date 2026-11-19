"""
Realistic characters for FLV films, built with MPFB (MakeHuman for Blender) inside Blender.

    import humans
    rig = humans.build(SPEC)                       # body, skin, hair, eyes, clothes, face shapes, rig
    humans.relax_arms(rig)                         # out of the T/A pose
    humans.face(rig, frame, {"browInnerUp": 0.7})  # ARKit face units, keyframed
    humans.lip_sync(rig, "line.wav", start_frame=1)   # face from the voice (scripts/speech_face.py)
    humans.blinks(rig, 1, 240)
    humans.retarget(rig, "assets/mocap/cmu/77_14.bvh", start_frame=1)

A SPEC is a dict: name, age/weight/muscle/height (0-1 MakeHuman sliders; age 0.5 = 25 years, 1.0 = 90),
skin, hair (+ hair_material, hair_tint), eyebrows (+ brow_tint), eyes=(right, left) eye colours from MPFB's eyes/materials,
film_eye ("left"/"right": a pale filmed eye), clothes=[(asset, fabric or None, tint)] listed inner to
outer (socks/shoes, trousers, shirt), where fabric is a
Poly Haven texture id in assets/textures/polyhaven.

Needs the MPFB add-on and the MakeHuman packs (scripts/download_film_kit.sh). Self-check of the retargeter:
    blender -b --python scripts/humans.py -- --selfcheck
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent.parent
TEXTURES = ROOT / "assets" / "textures" / "polyhaven"

# BVH bone -> cmu_mb rig bone. CMU clips use the rig's own names; 100STYLE (XSens) needs a map.
CMU = {"LeftHandIndex1": "LeftHandFinger1", "RightHandIndex1": "RightHandFinger1"}
STYLE100 = {"Hips": "Hips", "Chest": "LowerBack", "Chest2": "Spine", "Chest4": "Spine1", "Neck": "Neck",
            "Head": "Head", "LeftCollar": "LeftShoulder", "LeftShoulder": "LeftArm", "LeftElbow": "LeftForeArm",
            "LeftWrist": "LeftHand", "RightCollar": "RightShoulder", "RightShoulder": "RightArm",
            "RightElbow": "RightForeArm", "RightWrist": "RightHand", "LeftHip": "LeftUpLeg", "LeftKnee": "LeftLeg",
            "LeftAnkle": "LeftFoot", "LeftToe": "LeftToeBase", "RightHip": "RightUpLeg", "RightKnee": "RightLeg",
            "RightAnkle": "RightFoot", "RightToe": "RightToeBase"}


def _mpfb():
    from bl_ext.blender_org.mpfb.services import FaceService, HumanService, LocationService
    return HumanService, FaceService, Path(LocationService.get_user_data())


def build(spec, location=(0, 0, 0)):
    """Create a character from a spec; returns its armature (meshes are its children)."""
    HumanService, FaceService, data = _mpfb()
    hair = spec.get("hair", "")
    alt = {}
    if spec.get("hair_material"):
        mhclo = data / "hair" / hair / f"{hair}.mhclo"
        uuid = next(l.split()[1] for l in mhclo.read_text().splitlines() if l.lower().startswith("uuid"))
        alt[uuid] = f"{hair}/{spec['hair_material']}/{spec['hair_material']}.mhmat"
    info = {
        "name": spec["name"],
        "phenotype": {"gender": spec.get("gender", 1.0), "age": spec["age"], "muscle": spec.get("muscle", 0.5),
                      "weight": spec.get("weight", 0.5), "proportions": spec.get("proportions", 0.5),
                      "height": spec.get("height", 0.5), "cupsize": 0.5, "firmness": 0.5,
                      "race": {"asian": 0.0, "caucasian": 1.0, "african": 0.0}},
        "rig": "cmu_mb", "proxy": "", "targets": [], "expressions": [],
        "eyes": "high-poly/high-poly.mhclo", "teeth": "teeth_base/teeth_base.mhclo", "tongue": "tongue01/tongue01.mhclo",
        "eyebrows": f"{spec['eyebrows']}/{spec['eyebrows']}.mhclo",
        "eyelashes": f"{spec.get('eyelashes', 'eyelashes01')}/{spec.get('eyelashes', 'eyelashes01')}.mhclo",
        "hair": f"{hair}/{hair}.mhclo" if hair else "",
        "clothes": [f"{c}/{c}.mhclo" for c, *_ in spec.get("clothes", [])],
        "skin_mhmat": f"{spec['skin']}/{spec['skin']}.mhmat", "skin_material_type": "ENHANCED_SSS",
        "eyes_material_type": "MAKESKIN", "skin_material_settings": {}, "eyes_material_settings": {},
        "alternative_materials": alt,
    }
    body = HumanService.deserialize_from_dict(info, HumanService.get_default_deserialization_settings())
    FaceService.load_targets(body, load_microsoft_visemes=False, load_arkit_faceunits=True)
    FaceService.interpolate_targets(body)
    rig = body.parent
    rig.location = location
    parts = {o.name.split(".", 1)[1]: o for o in rig.children}
    _eyes(parts["high-poly"], data, spec.get("eyes", ("grey", "grey")), spec.get("film_eye"))
    for asset, fabric_id, tint in spec.get("clothes", []):
        if fabric_id:
            fabric(parts[asset], fabric_id, tint, spec.get("fabric_scale", 6))
    for part, key in ((hair, "hair_tint"), (spec["eyebrows"], "brow_tint")):
        if spec.get(key) and part in parts:
            tint_material(parts[part], spec[key])
    for obj in face_meshes(rig):          # lips closed at rest (lip_sync fades this out while speaking)
        if "mouthShrugLower" in obj.data.shape_keys.key_blocks:
            obj.data.shape_keys.key_blocks["mouthShrugLower"].value = REST_SEAL
    garments = [parts[c] for c, *_ in spec.get("clothes", [])]
    hide_under(body, garments)
    for i, g in enumerate(garments):     # clothes are listed inner to outer: socks under trousers under shirt
        if garments[i + 1:]:
            hide_under(g, garments[i + 1:], poking=False)
    return rig


def hide_under(body, garments, reach=0.03, margin=0.006, poking=True):
    """Mask the parts of `body` (skin, or a garment) that sit under the given garments, so knees, elbows and
    sock tops don't poke through (some MakeHuman clothes ship without a delete group). poking=True also hides
    surface just outside a garment, away from its hems."""
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
        for i, co in enumerate(coords):
            p = to_local @ co
            loc, normal, _, dist = tree.find_nearest(p)
            if loc is None or dist > reach:
                continue
            inside = (p - loc).dot(normal) < margin
            outside_close = poking and dist < 0.015 and (not rim or edges.find(loc)[2] > 0.04)   # mid-garment
            if inside or outside_close:
                hidden.add(i)
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
        src = bsdf.inputs["Base Color"].links[0].from_socket
        mix = nodes.new("ShaderNodeMix")
        mix.data_type, mix.blend_type = "RGBA", "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs["B"].default_value = (*rgb, 1)
        links.new(src, mix.inputs["A"])
        links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])


def _eyes(obj, data, colours, film_eye):
    """Iris colour per eye (right, left) from MPFB's eye materials; film_eye gets a milky, pale-blue film."""
    base = obj.data.materials[0]
    mats = []
    for side, colour in zip(("right", "left"), colours):
        mat = base.copy()
        mat.name = f"{base.name}.{side}"
        tex = mat.node_tree.nodes["diffuseTexture"]
        tex.image = bpy.data.images.load(str(data / "eyes" / "materials" / f"{colour}_eye.png"), check_existing=True)
        if film_eye == side:
            nodes, links = mat.node_tree.nodes, mat.node_tree.links
            mix = nodes.new("ShaderNodeMix")
            mix.data_type, mix.blend_type = "RGBA", "MIX"
            mix.inputs["Factor"].default_value = 0.55
            mix.inputs["B"].default_value = (0.78, 0.84, 0.88, 1)          # "a pale blue eye, with a film over it"
            bsdf = nodes["Principled BSDF"]
            src = bsdf.inputs["Base Color"].links[0].from_socket
            links.new(src, mix.inputs["A"])
            links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
            bsdf.inputs["Roughness"].default_value = 0.45
        mats.append(mat)
    obj.data.materials.clear()
    for mat in mats:
        obj.data.materials.append(mat)
    for poly in obj.data.polygons:   # the character faces -Y, so its left eye is on +X
        poly.material_index = 1 if sum(obj.data.vertices[v].co.x for v in poly.vertices) > 0 else 0


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
    """Arms down by the sides, elbows slightly bent (MakeHuman rigs rest in a T/A pose)."""
    for side, sx in (("Left", 1), ("Right", -1)):
        aim(rig, f"{side}Arm", (sx * spread, -forward, -1))
        aim(rig, f"{side}ForeArm", (sx * spread * 0.6, -forward * 2.5, -1))


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


# MPFB's face units are weaker than ARKit's in the jaw and stronger in the lip raisers: without this the
# teeth stay clenched and the lips pull back off them (a grimace, not speech). Real speech opens mostly
# with the jaw, the teeth part, and the lips stay soft over the teeth. Prefix -> gain on the model output.
SPEECH_GAIN = {"jawOpen": 2.4, "mouthUpperUp": 0.4, "mouthLowerDown": 0.6, "mouthShrugUpper": 0.6}
REST_SEAL = 0.3     # mouthShrugLower: MakeHuman's neutral mouth hangs slightly open; a relaxed mouth is closed


def lip_sync(rig, wav, start_frame, fps=24, lead=1.0, gain=1.0):
    """Lips, jaw, cheeks and tongue driven by the voice itself: scripts/speech_face.py runs Wav2ARKit, a model
    learned from real talking faces, so the jaw opens only a little while the lips do most of the work, sounds
    blend into each other (coarticulation) and the lips close fully on m/b/p. The result is added on top of
    the expression already keyed (fear, a smile). `lead` frames: the face moves just before the sound, as lips
    shape a sound before it is heard. Blinks and eye direction stay with the shot (blinks(), face())."""
    import numpy as np
    out = Path(bpy.app.tempdir) / "speech_face.json"
    subprocess.run([str(ROOT / ".venv" / "bin" / "python"), "-I", str(ROOT / "scripts" / "speech_face.py"), str(wav),
                    str(out)], check=True, capture_output=True)
    data = json.loads(out.read_text())
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


def blinks(rig, start, end, seed=1, fps=24):
    rng = random.Random(seed)
    meshes = face_meshes(rig)
    frame = start + rng.uniform(0.5, 2) * fps
    while frame < end - 6:
        for f, v in ((frame - 1, 0.0), (frame + 1.5, 1.0), (frame + 3.5, 0.0)):
            face(rig, f, {"eyeBlinkLeft": v, "eyeBlinkRight": v}, meshes)
        frame += rng.uniform(2.0, 5.0) * fps


# --- motion capture -------------------------------------------------------------------------------

def retarget(rig, bvh, start_frame=1, bone_map=None, max_frames=None, root_motion=True, keep_source=False):
    """Bake a BVH clip onto `rig` at the scene frame rate: each bone copies its world-space rotation
    relative to its rest pose. A global turn aligns the two skeletons' facing; a per-bone swing corrects
    rest-pose differences (T-pose clips onto MakeHuman's pose). Hips motion is scaled by leg length.
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
    print(f"humans selfcheck OK: {len(target.pose.bones)} bones x {end} frames, worst error {math.degrees(worst):.5f} deg")


if __name__ == "__main__" and "--selfcheck" in sys.argv:
    bpy.context.scene.render.fps = 24
    _selfcheck()
