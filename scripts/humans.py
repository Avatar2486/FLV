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
from mathutils import Matrix, Quaternion, Vector

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
    for pb in rig.pose.bones:                # one rotation channel for poses, mocap and the living-body layers
        pb.rotation_mode = "QUATERNION"
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
    """Arms down by the sides, elbows slightly bent (MakeHuman rigs rest in a T/A pose). Directions are in
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
    shape a sound before it is heard. Blinks and eye direction stay with the shot (eyes(), face()).
    Returns {"phrases": [(first, last frame)], "pauses": [frame]} for breathe() and eyes()."""
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
# MPFB eye shapes, measured on the mesh: weight 1 turns the eye ~38 deg out/in, 18 deg up, 27 deg down
#   (looking down also lowers the upper lid, as real lids follow the eye).
EYE_DEG = {"out": 37.6, "in": 39.5, "up": 18.1, "down": 27.0}
SACCADE_DIRS = ((0, 15.54), (45, 6.46), (90, 17.69), (135, 7.44), (180, 16.80), (225, 7.89), (270, 20.38),
                (315, 7.79))
GAZE_MODES = {   # (mutual mean, sd), (away mean, sd) in seconds; blinks per minute; largest saccade
    "talking": ((3.13, 3.16), (0.93, 0.80), 24, 25),
    "listening": ((7.92, 1.57), (0.43, 0.24), 12, 20),
    "fear": ((0.6, 0.35), (0.5, 0.3), 7, 30),            # scanning the dark, blinking suppressed
    "thinking": ((1.0, 0.6), (1.6, 0.9), 15, 20),        # looking away while recalling
}


def _layer(rig, start, end, offsets):
    """Add small rotations on top of the motion already there, every frame from start to end.
    offsets(frame) -> {bone: (yaw, pitch, roll)} in degrees, in the character's frame: yaw turns to the
    character's left, pitch nods forward/down, roll tilts to the left. The underlying motion is read for
    every frame first, so layers stack instead of feeding on their own keys."""
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
        for name, (yaw, pitch, roll) in offs.items():
            q, orient = base[f][name]
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
    pauses (blinks gather there). Head turns join big gaze shifts unless head=False."""
    rng = random.Random(seed)
    (mm, ms), (am, asd), blink_rate, biggest = GAZE_MODES[mode]
    meshes = face_meshes(rig)
    targets, f, away = [], float(start), False          # alternate mutual-gaze and gaze-away spells
    while f < end:
        if away:
            size = min(rng.expovariate(1 / 6.9), biggest)                      # P(A) ~ e^(-A/6.9)
            angle = math.radians(rng.choices([d for d, _ in SACCADE_DIRS], [w for _, w in SACCADE_DIRS])[0])
            targets.append((f, (look[0] + size * math.cos(angle), look[1] + size * math.sin(angle))))
        else:
            targets.append((f, tuple(look)))
        mean, sd = (am, asd) if away else (mm, ms)
        f += max(0.12, rng.gauss(mean, sd)) * fps
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
    yaw, pitch = gaze
    left = {"eyeLookOutLeft": max(yaw, 0) / EYE_DEG["out"], "eyeLookInLeft": max(-yaw, 0) / EYE_DEG["in"]}
    right = {"eyeLookInRight": max(yaw, 0) / EYE_DEG["in"], "eyeLookOutRight": max(-yaw, 0) / EYE_DEG["out"]}
    vertical = {f"eyeLook{d}{s}": v for s in ("Left", "Right") for d, v in
                (("Up", max(pitch, 0) / EYE_DEG["up"]), ("Down", max(-pitch, 0) / EYE_DEG["down"]))}
    face(rig, frame, {k: min(1.0, v) for k, v in {**left, **right, **vertical}.items()}, meshes)


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


def _two_bone(rig, rest, pose, frame, up, low, foot, target, pole=(0, -1, 0), end_rot=None):
    """Analytic two-bone IK in armature space; keys the thigh, shin and foot rotations at `frame`."""
    from mathutils import Matrix
    H, K, A = pose[up].translation, pose[low].translation, pose[foot].translation
    l1, l2 = (K - H).length, (A - K).length
    reach = target - H
    d = max(abs(l1 - l2) + 1e-4, min(l1 + l2 - 1e-4, reach.length))
    u = reach.normalized()
    bend = (K - H) - (K - H).project(A - H)                                    # the knee's mocap direction
    bend = bend if bend.length > 0.01 * l1 else Vector(pole)          # straight limb: use the natural bend
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
    turned = end_rot if end_rot is not None else pose[foot].to_3x3()          # the foot keeps its own angle
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
def reach(rig, side, start, end, target, blend=8, hand=None):
    """Arm IK: the hand (wrist) goes to target(frame) -> world point (or None = free), with `blend`-frame
    ease in and out. Elbows bend back and down. hand: a world 3x3 rotation for the hand (its Y axis along
    the fingers, Z out of the palm), or a function frame -> rotation, else it keeps its own angle. For hands on doors, latches, lanterns:
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
    to_arm = rig.matrix_world.inverted()
    weight = {}
    for f in frames:
        w = 1.0 if first <= f <= last else 0.0
        if f < first and first - f <= blend:
            w = 1 - (first - f) / (blend + 1)
        if f > last and f - last <= blend:
            w = 1 - (f - last) / (blend + 1)
        if w > 0:
            weight[f] = w
    poses = {}
    for f in weight:                          # the arm as it was, before any IK key (else the blends drift)
        scene.frame_set(f)
        poses[f] = {n: rig.pose.bones[n].matrix.copy() for n in chain + (parent,)}
    for f, w in weight.items():
        goal = goals[f] if goals[f] is not None else goals[first if f < first else last]
        pose = poses[f]
        wrist = pose[chain[2]].translation
        ease = 0.5 - 0.5 * math.cos(math.pi * w)
        aim_at = wrist.lerp(to_arm @ Vector(goal), ease)
        turned = None
        rot = hand(f) if callable(hand) else hand
        if rot is not None:
            want = (to_arm.to_3x3() @ rot).to_quaternion()
            turned = pose[chain[2]].to_quaternion().slerp(want, ease).to_matrix()
        _two_bone(rig, rest, pose, f, *chain, aim_at, pole=(0, 0.6, -0.4), end_rot=turned)


def hand_frame(fingers, palm):
    """World rotation for reach(hand=...): fingers point along `fingers`, the palm faces `palm`.
    MPFB cmu_mb hands: Y runs along the fingers and the palm is on -Z (measured on both hands of both
    characters: curling the fingers (+X) moves the tips toward -Z)."""
    y = Vector(fingers).normalized()
    z = -(Vector(palm) - Vector(palm).project(y)).normalized()
    return Matrix((y.cross(z), y, z)).transposed()


def grip(rig, side, frame=1, curl=1.0):
    """Close the fingers round a handle from `frame` on (MPFB cmu_mb: one finger chain, +X curls)."""
    scene = bpy.context.scene
    thumb = "LThumb" if side == "Left" else "RThumb"
    for name, deg in ((f"{side}FingerBase", 25), (f"{side}HandFinger1", 55), (thumb, 15)):
        pb = rig.pose.bones[name]
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


def chuckle(rig, start, end, fps=24):
    """A stifled laugh: shoulders and chest bounce ~4.5 times a second, lips pressed into a smile."""
    meshes = face_meshes(rig)
    face(rig, start - 3, {"mouthSmileLeft": 0.0, "mouthSmileRight": 0.0, "mouthPressLeft": 0.0,
                          "mouthPressRight": 0.0, "cheekSquintLeft": 0.0, "cheekSquintRight": 0.0}, meshes)
    for f in range(start, end + 1, 3):
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * 4.5 * (f - start) / fps)
        face(rig, f, {"mouthSmileLeft": 0.45, "mouthSmileRight": 0.4, "mouthPressLeft": 0.35 + 0.2 * pulse,
                      "mouthPressRight": 0.35 + 0.2 * pulse, "cheekSquintLeft": 0.3, "cheekSquintRight": 0.3,
                      "noseSneerLeft": 0.15 * pulse, "noseSneerRight": 0.15 * pulse}, meshes)
    face(rig, end + 6, {"mouthSmileLeft": 0.15, "mouthSmileRight": 0.1, "mouthPressLeft": 0.0,
                        "mouthPressRight": 0.0, "cheekSquintLeft": 0.0, "cheekSquintRight": 0.0,
                        "noseSneerLeft": 0.0, "noseSneerRight": 0.0}, meshes)

    def offsets(f):
        env = min(1.0, (f - start) / 6, (end - f) / 6) if start <= f <= end else 0.0
        b = math.sin(2 * math.pi * 4.5 * (f - start) / fps) * env
        return {"Spine1": (0, 1.2 * b, 0), "LeftShoulder": (0, 0, -1.8 * b), "RightShoulder": (0, 0, 1.8 * b),
                "Head": (0, -0.8 * b, 0)}
    _layer(rig, start, end + 6, offsets)


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
    assert back < 0.1, f"reach left the arm {back:.2f} degrees off after letting go"
    print(f"humans selfcheck OK: {len(target.pose.bones)} bones x {end} frames, worst error {math.degrees(worst):.5f} deg; "
          f"plant_feet knee change {drift:.2f} deg, lowest toe {lowest * 100:+.1f} cm; "
          f"reach miss {missed * 100:.2f} cm, arm after release {back:.3f} deg")


if __name__ == "__main__" and "--selfcheck" in sys.argv:
    bpy.context.scene.render.fps = 24
    _selfcheck()
