"""
FLV characters: a stylized rigged person, a sleeping figure, and animation helpers.

The standing character is one mesh skinned to an armature (rigid, mannequin-style
parts), the same set-up a Mixamo or AI-generated character uses. A downloaded
character can later replace it and reuse these helpers if it has the same bone names.
In Blender: click CHAR_<name>_Rig, press Ctrl+Tab for Pose Mode, then R to rotate bones.

Bones: hips, spine, neck, head, upper_arm / forearm / hand .L/.R, thigh / shin / foot .L/.R.
Each arm has an IK constraint aimed at an empty (CHAR_<name>_Hand_Target.L/.R) so a
hand can be sent to a point in the room, e.g. a pencil on the desk.
"""
import math

import bmesh
import bpy
from bpy_extras import anim_utils
from mathutils import Matrix, Vector

import scene_utils as su
from asset_library import assemble
from material_library import material as M

WALKER_LOOK = {"skin": "MAT_Skin", "hair": "MAT_Hair", "top": "MAT_Shirt", "legs": "MAT_Pants",
               "shoes": "MAT_Shoes"}
# Optional look keys: arms (sleeves, default = top), hair_style ("short", "white" fringe, "none"),
# coat (frock-coat skirt), gown (long nightshirt), hat (top hat), nightcap, cravat, mustache,
# badge, vulture_eye (True: a milky pale-blue left eye).

# Rest pose, standing at the origin and facing -Y: bone -> (head, tail, parent)
BONES = {"hips": ((0, 0, 0.92), (0, 0, 1.05), None),
         "spine": ((0, 0, 1.05), (0, 0, 1.45), "hips"),
         "neck": ((0, 0, 1.45), (0, 0, 1.56), "spine"),
         "head": ((0, 0, 1.56), (0, 0, 1.8), "neck"),
         "jaw": ((0, -0.085, 1.622), (0, -0.125, 1.622), "head")}
for _s, _x in (("L", 1), ("R", -1)):
    BONES.update({
        f"upper_arm.{_s}": ((0.2 * _x, 0, 1.41), (0.2 * _x, 0.03, 1.17), "spine"),
        f"forearm.{_s}": ((0.2 * _x, 0.03, 1.17), (0.2 * _x, 0, 0.93), f"upper_arm.{_s}"),
        f"hand.{_s}": ((0.2 * _x, 0, 0.93), (0.2 * _x, 0, 0.82), f"forearm.{_s}"),
        f"thigh.{_s}": ((0.09 * _x, 0, 0.92), (0.09 * _x, -0.02, 0.5), "hips"),
        f"shin.{_s}": ((0.09 * _x, -0.02, 0.5), (0.09 * _x, 0, 0.09), f"thigh.{_s}"),
        f"foot.{_s}": ((0.09 * _x, 0, 0.09), (0.09 * _x, -0.14, 0.03), f"shin.{_s}"),
        f"eye.{_s}": ((0.037 * _x, -0.09, 1.675), (0.037 * _x, -0.13, 1.675), "head"),
        f"brow.{_s}": ((0.037 * _x, -0.1, 1.71), (0.037 * _x, -0.14, 1.71), "head"),
    })
FACE_BONES = ["jaw", "eye.L", "eye.R", "brow.L", "brow.R"]
POSE_BONES = [b for b in BONES if not b.startswith("hand") and b not in FACE_BONES]

# Rotation about a bone's own X axis that bends it forward (toward where the person faces).
FORWARD = -1        # for bones hanging down (legs, arms)
BEND_DOWN = 1       # for bones pointing up (spine, neck, head): leans the upper body forward


def _hair(bm, center, material_index, style="short", hairline=0.04):
    """Hair: a cap around the head with the face cut away ("white" leaves a bald crown)."""
    verts = su.add_sphere(bm, 0.115, center, scale=(0.98, 1.0, 1.08), segments=24, material_index=material_index)
    cx, cy, cz = center
    face = [v for v in verts if (v.co.z < cz + hairline and v.co.y < cy - 0.005) or v.co.z < cz - 0.09
            or (style == "white" and v.co.z > cz + 0.035)]
    bmesh.ops.delete(bm, geom=face, context="VERTS")
    return [v for v in verts if v.is_valid]


def _body(name, coll, look):
    keys, mats = {}, []

    def mat(key, default=None):
        name_ = look.get(key) or default
        if name_ not in keys:
            keys[name_] = len(mats)
            mats.append(M(name_))
        return keys[name_]

    SKIN, TOP, LEGS, SHOES = mat("skin"), mat("top"), mat("legs"), mat("shoes")
    ARMS, HAIR, DARK = mat("arms", look["top"]), mat("hair"), mat("eyes", "MAT_Plastic_Black")
    WHITE, MOUTH = mat("sclera", "MAT_Eye_White"), mat("mouth", "MAT_Mouth")
    bm, groups = bmesh.new(), {}

    def add(bone, verts):
        groups.setdefault(bone, []).extend(verts)

    def limb(bone, a, b, r, m):
        add(bone, su.add_rod(bm, a, b, r, segments=12, material_index=m))
        for p in (a, b):
            add(bone, su.add_sphere(bm, r, p, segments=12, material_index=m))

    add("head", su.add_sphere(bm, 0.105, (0, 0, 1.67), scale=(0.95, 1.0, 1.12), material_index=SKIN))
    if look.get("hair_style", "short") != "none":
        add("head", _hair(bm, (0, 0.012, 1.69), HAIR, look.get("hair_style", "short")))
    for s, x in (("L", 1), ("R", -1)):
        add(f"eye.{s}", su.add_sphere(bm, 0.017, (0.037 * x, -0.09, 1.675), segments=12, material_index=WHITE))
        iris = mat("vulture", "MAT_Vulture_Eye") if (look.get("vulture_eye") and s == "L") else DARK
        size = 0.012 if iris != DARK else 0.008
        add(f"eye.{s}", su.add_sphere(bm, size, (0.037 * x, -0.103, 1.675), segments=10, material_index=iris))
        add(f"brow.{s}", su.add_box(bm, (0.034, 0.008, 0.008), (0.037 * x, -0.1, 1.71), material_index=HAIR))
    add("jaw", su.add_sphere(bm, 1.0, (0, -0.098, 1.622), scale=(0.026, 0.01, 0.007), segments=12,
                             material_index=MOUTH))
    add("head", su.add_sphere(bm, 0.017, (0, -0.108, 1.648), scale=(0.8, 1.0, 1.1), segments=10,
                              material_index=SKIN))                                     # nose
    if look.get("mustache"):
        add("head", su.add_sphere(bm, 1.0, (0, -0.104, 1.636), scale=(0.036, 0.012, 0.009), segments=12,
                                  material_index=mat("mustache")))
    if look.get("hat"):
        HAT = mat("hat")
        add("head", su.add_cylinder(bm, 0.098, 0.17, (0, 0.005, 1.87), segments=24, material_index=HAT))
        add("head", su.add_cylinder(bm, 0.15, 0.012, (0, 0.005, 1.79), segments=24, material_index=HAT))
    if look.get("nightcap"):
        add("head", su.add_cylinder(bm, 0.112, 0.2, (0, 0.03, 1.79), radius_top=0.02, rotation=(-35, 0, 0),
                                    segments=16, material_index=mat("nightcap")))
    limb("neck", (0, 0, 1.47), (0, 0, 1.56), 0.05, SKIN)
    if look.get("cravat"):
        add("neck", su.add_sphere(bm, 1.0, (0, -0.045, 1.49), scale=(0.05, 0.03, 0.04), segments=12,
                                  material_index=mat("cravat")))
    add("spine", su.add_sphere(bm, 1.0, (0, 0, 1.25), scale=(0.19, 0.115, 0.27), material_index=TOP))
    if look.get("badge"):
        add("spine", su.add_sphere(bm, 0.016, (0.08, -0.108, 1.33), segments=10, material_index=mat("badge")))
    add("hips", su.add_sphere(bm, 1.0, (0, 0, 0.98), scale=(0.165, 0.105, 0.12), material_index=LEGS))
    if look.get("coat"):
        add("hips", su.add_cylinder(bm, 0.235, 0.5, (0, 0.01, 0.78), radius_top=0.175, caps=False, segments=24,
                                    material_index=mat("coat")))
    if look.get("gown"):
        add("hips", su.add_cylinder(bm, 0.27, 0.95, (0, 0, 0.85), radius_top=0.19, caps=False, segments=24,
                                    material_index=mat("gown")))
    for s, x in (("L", 1), ("R", -1)):
        add(f"upper_arm.{s}", su.add_sphere(bm, 0.056, (0.19 * x, 0.01, 1.4), material_index=TOP))
        limb(f"upper_arm.{s}", (0.2 * x, 0.01, 1.4), (0.2 * x, 0.03, 1.18), 0.044, ARMS)
        limb(f"forearm.{s}", (0.2 * x, 0.03, 1.16), (0.2 * x, 0, 0.95), 0.038, ARMS)
        add(f"hand.{s}", su.add_sphere(bm, 0.045, (0.2 * x, 0, 0.88), scale=(0.7, 0.55, 1.1), material_index=SKIN))
        limb(f"thigh.{s}", (0.09 * x, 0, 0.9), (0.09 * x, -0.02, 0.51), 0.066, LEGS)
        limb(f"shin.{s}", (0.09 * x, -0.02, 0.49), (0.09 * x, 0, 0.13), 0.053, LEGS)
        add(f"foot.{s}", su.add_sphere(bm, 1.0, (0.09 * x, -0.05, 0.045), scale=(0.055, 0.13, 0.045),
                                       material_index=SHOES))
    bm.verts.index_update()
    weights = {bone: [v.index for v in verts if v.is_valid] for bone, verts in groups.items()}
    body = su.make_object(f"{name}_Body", coll, mats, bm, smooth_angle=180)
    for bone, indices in weights.items():
        body.vertex_groups.new(name=bone).add(indices, 1.0, "REPLACE")
    return body


def character(coll, name="CHAR_Walker", look=WALKER_LOOK):
    """Rigged person standing at the origin, facing -Y. Returns the armature object."""
    rig = bpy.data.objects.new(f"{name}_Rig", bpy.data.armatures.new(f"{name}_Rig"))
    coll.objects.link(rig)
    rig.show_in_front = True               # bones stay clickable through the body
    view_layer = bpy.context.view_layer
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    edit = rig.data.edit_bones
    for bone, (head, tail, _) in BONES.items():
        eb = edit.new(bone)
        eb.head, eb.tail = head, tail
    for bone, (head, _, parent) in BONES.items():
        if parent:
            edit[bone].parent = edit[parent]
            edit[bone].use_connect = (Vector(BONES[parent][1]) - Vector(head)).length < 1e-6
    bpy.ops.object.mode_set(mode="OBJECT")
    for pose_bone in rig.pose.bones:
        pose_bone.rotation_mode = "XYZ"

    body = _body(name, coll, look)
    body.parent = rig
    su.add_modifier(body, "ARMATURE", "Armature", object=rig)
    for side in ("L", "R"):
        target = bpy.data.objects.new(f"{name}_Hand_Target.{side}", None)
        coll.objects.link(target)
        target.empty_display_type, target.empty_display_size = "SPHERE", 0.04
        ik = rig.pose.bones[f"forearm.{side}"].constraints.new("IK")
        ik.target, ik.chain_count, ik.influence = target, 2, 0.0
    return rig


def attach(obj, rig, bone):
    """Parent `obj` to a bone, keeping where it is now (call while the rig is at rest)."""
    tail = rig.matrix_world @ rig.data.bones[bone].matrix_local @ Matrix.Translation(
        (0, rig.data.bones[bone].length, 0))
    obj.parent, obj.parent_type, obj.parent_bone = rig, "BONE", bone
    obj.matrix_parent_inverse = tail.inverted()


# -------------------------------------------------------------------- animation

def key_pose(rig, frame, pose):
    """Keyframe bone rotations. pose = {bone: degrees about its X axis, or an (x, y, z) tuple}."""
    for bone, deg in pose.items():
        pb = rig.pose.bones[bone]
        pb.rotation_euler = [math.radians(a) for a in (deg if isinstance(deg, tuple) else (deg, 0, 0))]
        pb.keyframe_insert("rotation_euler", frame=frame)


def rest(rig, frame):
    key_pose(rig, frame, {b: 0 for b in POSE_BONES})
    rig.pose.bones["hips"].location = (0, 0, 0)
    rig.pose.bones["hips"].keyframe_insert("location", frame=frame)


def heading_to(direction):
    """Z rotation that turns a -Y-facing character toward `direction`."""
    return math.atan2(direction[0], -direction[1])


def _nearest_angle(angle, reference):
    return angle + 2 * math.pi * round((reference - angle) / (2 * math.pi))


def _smooth(points, steps=24):
    """Catmull-Rom curve through floor points [(x, y), ...]."""
    pts = [Vector((*p, 0)) for p in points]
    pts = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1:i + 3]
        for k in range(steps):
            t = k / steps
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-2])
    return out


def walk(rig, points, start, speed=0.75, stride=0.8, fps=24, every=2):
    """Walk through floor `points` from frame `start`, easing in and out.
    Returns the frame of arrival."""
    path = _smooth(points)
    lengths = [0.0]
    for a, b in zip(path, path[1:]):
        lengths.append(lengths[-1] + (b - a).length)
    total = lengths[-1]
    frames = round(total / speed * fps)
    heading, seg = None, 0
    for f in list(range(0, frames, every)) + [frames]:
        d = total * f / frames
        while seg < len(path) - 2 and lengths[seg + 1] < d:
            seg += 1
        a, b = path[seg], path[seg + 1]
        t = (d - lengths[seg]) / max(lengths[seg + 1] - lengths[seg], 1e-9)
        h = heading_to(b - a)
        heading = h if heading is None else _nearest_angle(h, heading)
        rig.location = a.lerp(b, t)
        rig.rotation_euler = (0, 0, heading)
        rig.keyframe_insert("location", frame=start + f)
        rig.keyframe_insert("rotation_euler", frame=start + f)

        phase = 2 * math.pi * d / stride
        ramp = min(1.0, d / 0.35, (total - d) / 0.35)        # ease into and out of the stride
        s, c = math.sin(phase) * ramp, math.cos(phase) * ramp
        key_pose(rig, start + f, {
            "thigh.L": FORWARD * 24 * s, "thigh.R": -FORWARD * 24 * s,
            "shin.L": -FORWARD * 38 * max(0.0, c), "shin.R": -FORWARD * 38 * max(0.0, -c),
            "foot.L": FORWARD * 10 * max(0.0, c), "foot.R": FORWARD * 10 * max(0.0, -c),
            "upper_arm.L": -FORWARD * 16 * s, "upper_arm.R": FORWARD * 16 * s,
            "forearm.L": FORWARD * 14, "forearm.R": FORWARD * 14,
            "spine": (BEND_DOWN * 3, 4 * s, 0), "neck": 0, "head": 0, "hips": (0, -4 * s, 0),
        })
        hips = rig.pose.bones["hips"]
        hips.location = (0, -0.025 * abs(s), 0)            # body dips as the legs spread
        hips.keyframe_insert("location", frame=start + f)
    return start + frames


def turn(rig, start, end, direction):
    """Turn on the spot between two frames to face `direction` (x, y)."""
    rig.keyframe_insert("rotation_euler", frame=start)
    rig.rotation_euler.z = _nearest_angle(heading_to(direction), rig.rotation_euler.z)
    rig.keyframe_insert("rotation_euler", frame=end)


def reach(rig, side, frame, influence, target=None):
    """Key an arm's IK: 0 = arm follows its pose, 1 = wrist goes to `target` (world point)."""
    ik = rig.pose.bones[f"forearm.{side}"].constraints["IK"]
    if target is not None:
        ik.target.location = target
        ik.target.keyframe_insert("location", frame=frame)
    ik.influence = influence
    ik.keyframe_insert("influence", frame=frame)


def breathe(obj, amount=0.07, period=96, start=1):
    """Gentle, endlessly repeating rise and fall (scales the object's height)."""
    base = obj.scale.z
    for f, k in ((0, 0.0), (period // 2, 1.0), (period, 0.0)):
        obj.scale.z = base * (1 + amount * k)
        obj.keyframe_insert("scale", index=2, frame=start + f)
    obj.scale.z = base
    anim = obj.animation_data
    bag = anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot)
    bag.fcurves.find("scale", index=2).modifiers.new("CYCLES")


def sleeper(coll, location, rotation=0, prefix="CHAR_Sleeper"):
    """Someone asleep on their back under the covers. `location` = centre of the head
    on the pillow; the body runs toward local -Y. The covers rise as they breathe."""
    body = su.pillow(f"{prefix}_Under_Covers", coll, M("MAT_Blanket"), (0.64, 1.5, 0.17), (0, -0.86, -0.13),
                     puff=0.6)
    bm = bmesh.new()                       # head lying face-up, crown toward +Y
    su.add_sphere(bm, 0.105, scale=(0.95, 1.12, 1.0), material_index=0)
    hair = su.add_sphere(bm, 0.115, (0, 0.02, -0.015), scale=(0.98, 1.08, 1.0), segments=24, material_index=1)
    bmesh.ops.delete(bm, geom=[v for v in hair if v.co.z > -0.01 and v.co.y < 0.045], context="VERTS")
    for x in (-0.038, 0.038):              # closed eyes
        su.add_box(bm, (0.034, 0.007, 0.006), (x, 0.01, 0.096), material_index=2)
    su.add_sphere(bm, 0.019, (0, -0.03, 0.104), scale=(0.8, 1.1, 0.9), segments=10)      # nose
    su.add_box(bm, (0.03, 0.005, 0.005), (0, -0.07, 0.088), material_index=2)            # mouth
    head = su.make_object(f"{prefix}_Head", coll, [M("MAT_Skin"), M("MAT_Hair"), M("MAT_Plastic_Black")], bm,
                          rotation=(0, 25, 0), smooth_angle=180)
    bm = bmesh.new()                       # one arm resting on top of the covers
    shoulder, elbow, wrist = Vector((0.2, -0.24, -0.06)), Vector((0.25, -0.5, -0.03)), Vector((0.1, -0.68, 0.0))
    for a, b in ((shoulder, elbow), (elbow, wrist)):
        su.add_rod(bm, a, b, 0.042, segments=12)
        su.add_sphere(bm, 0.042, b, segments=12)
    su.add_sphere(bm, 0.045, wrist + Vector((-0.04, -0.03, 0)), scale=(1.1, 0.7, 0.55), material_index=1)
    arm = su.make_object(f"{prefix}_Arm", coll, [M("MAT_Pajama"), M("MAT_Skin")], bm, smooth_angle=180)
    arm.parent = body                      # the arm rises and falls with the covers
    arm.matrix_parent_inverse = body.matrix_basis.inverted()
    root = assemble([head, body], location, rotation)
    breathe(body)
    return root
