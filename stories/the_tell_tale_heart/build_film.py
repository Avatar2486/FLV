"""
Build THE TELL-TALE HEART as one Blender scene, shot by shot.

    blender --background --factory-startup --python stories/the_tell_tale_heart/build_film.py

Reads film.py (the shot list) and timeline.json (shot lengths from the recorded voices),
builds the sets, cast and props, then stages every shot: a camera per shot (bound to
timeline markers, so Blender cuts between them), lighting state, prop states, character
blocking, lip sync from the voice files and in-shot animation. Saves
blender/scenes/tell_tale_heart.blend. Every animated property is keyed at every shot
start and end, so nothing drifts from one shot into the next.
"""
import json
import math
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent / "scripts"), str(HERE)]

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

import asset_library as lib
import character_library as ch
import film
import scene_utils as su
import sets
from material_library import material as M

TL = json.loads((HERE / "timeline.json").read_text())
SHOTS = {s["id"]: s for s in TL["shots"]}
ORDER = [s["id"] for s in TL["shots"]]
FPS = TL["fps"]
OUT_FILE = su.SCENES_DIR / "tell_tale_heart.blend"
F, B = ch.FORWARD, ch.BEND_DOWN
PARK = (0, 0, -60)


def f0(sid):
    return SHOTS[sid]["start"]


def f1(sid):
    return SHOTS[sid]["start"] + SHOTS[sid]["frames"] - 1


def at(sid, seconds):
    return min(f1(sid), f0(sid) + round(seconds * FPS))


# --------------------------------------------------------------------------- poses
SIT = {"thigh.L": F * 90, "thigh.R": F * 90, "shin.L": -F * 90, "shin.R": -F * 90,
       "upper_arm.L": F * 12, "upper_arm.R": F * 12, "forearm.L": F * 35, "forearm.R": F * 35}
SIT_BED = {"thigh.L": F * 88, "thigh.R": F * 88, "forearm.L": F * 25, "forearm.R": F * 25, "spine": B * 6}
PEEK = {"spine": B * 22, "neck": B * 10, "head": B * -6, "upper_arm.L": F * 8, "forearm.L": F * 20}
HOLD = {"forearm.L": F * 15}
KNEEL = {"thigh.L": F * 95, "shin.L": -F * 100, "thigh.R": F * 10, "shin.R": -F * 100, "spine": B * 25,
         "neck": B * 10}


def pose(*parts, **extra):
    out = {}
    for p in parts:
        out.update(p)
    out.update({k.replace("_L", ".L").replace("_R", ".R"): v for k, v in extra.items()})
    return out


# ------------------------------------------------------------------------- the build
def build():
    su.reset_scene()
    scene = bpy.context.scene
    su.configure_render(scene, width=film.RESOLUTION[0], height=film.RESOLUTION[1], fps=FPS,
                        frame_end=TL["frame_end"], samples=16)
    scene.eevee.volumetric_tile_size = "8"
    root = su.collection("TELL_TALE_HEART")
    C = {n: su.collection(n, root) for n in ("SETS", "CAST", "PROPS", "LIGHTS", "CAMERAS", "CARDS")}
    L = {}
    S = {"chamber": sets.chamber(C["SETS"], L), "corridor": sets.corridor(C["SETS"], L),
         "entry": sets.entry(C["SETS"], L), "kitchen": sets.kitchen(C["SETS"], L),
         "narrator_room": sets.narrator_room(C["SETS"], L), "void": sets.void(C["SETS"], L),
         "exterior": sets.exterior(C["SETS"], L), "eye": sets.eye_macro(C["SETS"], L),
         "watch": sets.watch_macro(C["SETS"], L), "beetle": sets.beetle_macro(C["SETS"], L),
         "title": sets.title_stage(C["CARDS"], L)}
    world = bpy.data.worlds.new("WORLD_Film")
    scene.world = world
    bg = world.node_tree.nodes["Background"]

    # ---- the cast
    looks = {
        "N": dict(skin="MAT_Skin_Pale", hair="MAT_Hair", top="MAT_Waistcoat", arms="MAT_Shirt_White",
                  legs="MAT_Waistcoat", shoes="MAT_Shoes", cravat="MAT_Cravat"),
        "OM": dict(skin="MAT_Skin_Pale", hair="MAT_Hair_White", hair_style="white", top="MAT_Nightshirt",
                   legs="MAT_Skin_Pale", shoes="MAT_Skin_Pale", gown="MAT_Nightshirt", nightcap="MAT_Nightshirt",
                   vulture_eye=True),
        "O1": dict(skin="MAT_Skin", hair="MAT_Hair_White", top="MAT_Police_Coat", legs="MAT_Trousers_Grey",
                   shoes="MAT_Shoes", coat="MAT_Police_Coat", hat="MAT_Plastic_Black", badge="MAT_Brass",
                   mustache="MAT_Hair_White"),
        "O2": dict(skin="MAT_Skin_Pale", hair="MAT_Hair", top="MAT_Police_Coat", legs="MAT_Trousers_Grey",
                   shoes="MAT_Shoes", coat="MAT_Police_Coat", hat="MAT_Plastic_Black", badge="MAT_Brass"),
        "O3": dict(skin="MAT_Skin", hair="MAT_Hair", top="MAT_Police_Coat", legs="MAT_Trousers_Grey",
                   shoes="MAT_Shoes", coat="MAT_Police_Coat", hat="MAT_Plastic_Black", badge="MAT_Brass",
                   mustache="MAT_Hair"),
    }
    names = {"N": "CHAR_Narrator", "OM": "CHAR_OldMan", "O1": "CHAR_Officer_Hale", "O2": "CHAR_Officer_Brandt",
             "O3": "CHAR_Officer_Mercer"}
    R = {k: ch.character(C["CAST"], names[k], looks[k]) for k in looks}
    R["NS"] = R["N"]

    # ---- hand props
    lantern, shutter, beam, glow = sets.dark_lantern(C["PROPS"])
    lantern.visible_shadow = shutter.visible_shadow = False      # its own light must get out
    # ponytail: the half-open chamber door sits right in front of the lens, so it casts no shadows at all;
    # restage the door to hinge on the west side if its missing shadow ever shows.
    bpy.data.objects["CH_DOOR_Panel"].visible_shadow = False
    for m in bpy.data.materials:                    # Poly Haven clock glass renders opaque in Eevee: see the dial
        if m.name.endswith("_glass") and m.node_tree:
            alpha = m.node_tree.nodes["Principled BSDF"].inputs["Alpha"]
            for link in list(alpha.links):
                m.node_tree.links.remove(link)
            alpha.default_value = 0.12
    for hand, now, then in (("HourHand", 312.7, 120.0), ("MinuteHand", 222.7, 0.0)):    # "it was four o'clock"
        obj = bpy.data.objects[f"CO_Long_Case_Clock_vintage_grandfather_clock_01_{hand}"]
        pivot = Matrix.Translation(obj.location)               # origin sits on the arbor; +Y turns clockwise
        obj.matrix_basis = pivot @ Matrix.Rotation(math.radians(then - now), 4, "Y") @ pivot.inverted() @ obj.matrix_basis
    candle = lib.candle(C["PROPS"], C["PROPS"], (0, 0, 0), height=0.1, prefix="PROP_Hand_Candle")
    candle_light = bpy.data.objects["LIGHT_PROP_Hand_Candle_Flame"]
    off_lights = []
    for k in ("O1", "O2", "O3"):                       # each officer carries a lantern in his right hand
        lamp = sets.ph("Lantern_01", C["PROPS"], f"PROP_Lantern_{k}", (-0.24, -0.22, 0.62))
        lamp.parent = R[k]
        light = su.light(f"LIGHT_Lantern_{k}", C["PROPS"], "POINT", (-0.24, -0.22, 0.75), 0, (1.0, 0.68, 0.38),
                         shadow_soft_size=0.04)
        light.parent = R[k]
        off_lights.append(light)
        target = R[k].pose.bones["forearm.R"].constraints["IK"].target
        target.parent, target.location = R[k], (-0.24, -0.22, 0.88)
    police_chairs = [sets.ph("dining_chair_02", C["PROPS"], f"PROP_Police_Chair_{i}", PARK) for i in range(4)]
    dust = su.make_object("PROP_Dust", C["PROPS"], M("MAT_Paper"), _dust_bm(), PARK, flat=True)
    cotton = su.make_object("PROP_Cotton", C["PROPS"], M("MAT_Pillow"), _cotton_bm(), (150, 0.005, 0.02))
    cards = {n: sets.text(f"TXT_Night_{n}", C["CARDS"], f"NIGHT  {n}", PARK, 0.06, align="LEFT")
             for n in ("II", "III", "IV", "V", "VI", "VII", "VIII")}

    ch_ = S["chamber"]
    bed = ch_["bed"]
    for obj in (ch_["blanket"], ch_["pillow"]):                       # bedclothes tip with the bed
        obj.parent = bed
        obj.matrix_parent_inverse = bed.matrix_basis.inverted()
    ch_["blanket"].location.z = 0.93

    neighbour = bpy.data.materials["MAT_Lamp_Shade"].copy()
    neighbour.name = "MAT_Neighbour_Window"
    S["exterior"]["neighbour_window"].data.materials[0] = neighbour
    sky_mat = bpy.data.materials["MAT_Night_Sky"].copy()
    sky_mat.name = "MAT_Narrator_Window_Sky"
    S["narrator_room"]["sky"].data.materials[0] = sky_mat
    for name in ("VO_Chair",):
        bpy.data.objects[name].rotation_euler.z = 0

    # Everything keyed per shot, with its resting value
    managed = {
        "candle": (candle, {"location": PARK}),
        "ch_door": (ch_["door"], {"rotation_euler": (0, 0, 0)}),
        "co_door": (S["corridor"]["door"], {"rotation_euler": (0, 0, 0)}),
        "co_handle": (S["corridor"]["handle"], {"rotation_euler": (0, 0, 0)}),
        "en_door": (S["entry"]["door"], {"rotation_euler": (0, 0, 0)}),
        "bed": (bed, {"location": tuple(bed.location), "rotation_euler": (0, 0, 0)}),
        "sh_L": (ch_["shutters"][0], {"rotation_euler": tuple(ch_["shutters"][0].rotation_euler)}),
        "sh_R": (ch_["shutters"][1], {"rotation_euler": tuple(ch_["shutters"][1].rotation_euler)}),
        "chest": (ch_["chest_lid"], {"rotation_euler": tuple(ch_["chest_lid"].rotation_euler)}) if ch_["chest_lid"] else None,
        "hands": (ch_["clock_hands"], {"rotation_euler": tuple(ch_["clock_hands"].rotation_euler)}),
        "mouse": (ch_["mouse"], {"location": tuple(ch_["mouse"].location)}),
        "soot": (ch_["soot"], {"location": tuple(ch_["soot"].location)}),
        "tray": (S["kitchen"]["tray"], {"location": tuple(S["kitchen"]["tray"].location),
                                        "rotation_euler": (0, 0, 0)}),
        "minute": (S["watch"]["minute"], {"rotation_euler": (0, 0, 0)}),
        "beetle": (S["beetle"]["head"], {"rotation_euler": (0, 0, 0)}),
        "lid": (S["eye"]["lid_upper"], {"rotation_euler": (-35, 0, 0)}),
        "dust": (dust, {"location": PARK}),
        "ceiling": (ch_["ceiling"], {"hide_render": False}),
        "cotton": (cotton, {"hide_render": True}),
    }
    managed = {k: v for k, v in managed.items() if v}
    for i, plank in enumerate(ch_["planks"]):
        managed[f"plank{i}"] = (plank, {"location": tuple(plank.location), "rotation_euler": (0, 0, 0)})
    for i, chair in enumerate(police_chairs):
        managed[f"chair{i}"] = (chair, {"location": PARK, "rotation_euler": (0, 0, 0)})
    for n, card in cards.items():
        managed[f"card{n}"] = (card, {"hide_render": True})
    lights = dict(L)
    lights.update({"beam": beam, "glow": glow, "candle": candle_light, "o1": off_lights[0], "o2": off_lights[1],
                   "o3": off_lights[2]})
    keep_in_fog = {"moon", "beam", "glow", "co_moon", "en_lamp", "ex_lamp", "shadow"}
    for name, light in lights.items():
        light.data.energy = 0
        if name not in keep_in_fog:                    # only key beams light the haze: much faster
            light.data.volume_factor = 0.0
        if name in ("o1", "o2", "o3", "candle", "fill", "warm", "co_fill", "en_fill", "ki_fill", "nr_fill"):
            light.data.use_shadow = False
    scene.eevee.volumetric_samples = 32
    scene.eevee.volumetric_shadow_samples = 4
    ctx = dict(scene=scene, C=C, S=S, R=R, lights=lights, managed=managed, bg=bg, cards=cards,
               lantern=lantern, beam=beam, glow=glow, shutter=shutter, neighbour=neighbour, sky_mat=sky_mat, dust=dust,
               chairs=police_chairs)
    return ctx


def _dust_bm():
    bm = bmesh.new()
    for i in range(14):
        v = bmesh.ops.create_icosphere(bm, subdivisions=0, radius=0.0012 + (i % 3) * 0.0006)["verts"]
        bmesh.ops.translate(bm, vec=((i * 37 % 40) / 1000 - 0.02, (i * 13 % 16) / 1000 - 0.008, 0.002), verts=v)
    return bm


def _cotton_bm():
    bm = bmesh.new()
    for i in range(22):
        a = i * 0.9
        v = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.012 + (i % 3) * 0.004)["verts"]
        bmesh.ops.translate(bm, vec=(0.03 * math.cos(a), 0.03 * math.sin(a), (i % 4) * 0.004), verts=v)
    return bm


# ------------------------------------------------------------------ keying helpers
def kset(owner, prop, frame, value):
    setattr(owner, prop, value)
    owner.keyframe_insert(prop, frame=frame)


def deg(t):
    return tuple(math.radians(a) for a in t)


def rig_matrix(loc, rot):
    return Matrix.Translation(Vector(loc)) @ Euler(deg(rot)).to_matrix().to_4x4()


def rig_state(rig, spec):
    """(owner, property, value) list putting a rig in a shot: loc, rot (deg) or heading, pose, ik, face."""
    rot = spec.get("rot", (0, 0, spec.get("heading", 0)))
    out = [(rig, "location", Vector(spec.get("loc", PARK))), (rig, "rotation_euler", Euler(deg(rot)))]
    body = {b: 0 for b in ch.POSE_BONES}
    body.update(spec.get("pose", {}))
    for bone, d in body.items():
        out.append((rig.pose.bones[bone], "rotation_euler", Euler(deg(d if isinstance(d, tuple) else (d, 0, 0)))))
    out.append((rig.pose.bones["hips"], "location", Vector((0, 0, 0))))
    for side in ("L", "R"):
        ik = rig.pose.bones[f"forearm.{side}"].constraints["IK"]
        point = spec.get("ik", {}).get(side)
        held = ik.target.parent is not None                    # officers always hold their lantern
        if point is not None and not held:
            out.append((ik.target, "location", Vector(point)))
        out.append((ik, "influence", 1.0 if (point is not None or held) else 0.0))
    for bone in ch.FACE_BONES:
        pb = rig.pose.bones[bone]
        shut = spec.get("asleep") and bone.startswith("eye")
        out.append((pb, "scale", Vector((1, 1, 0.12 if shut else 1))))
        out.append((pb, "rotation_euler", Euler(deg(spec.get("face", {}).get(bone, (0, 0, 0))))))
    return out


def place_rig(rig, frame, spec):
    for owner, prop, value in rig_state(rig, spec):
        kset(owner, prop, frame, value)


def has_keys(owner, prop, a, b):
    """Does `owner.prop` already have a keyframe in frames (a, b]?"""
    from bpy_extras import anim_utils
    ad = owner.id_data.animation_data
    if not ad or not ad.action:
        return False
    bag = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    if bag is None:
        return False
    path = owner.path_from_id(prop)
    for i in range(4):
        fc = bag.fcurves.find(path, index=i)
        if fc is None:
            break
        if any(a < k.co[0] <= b for k in fc.keyframe_points):
            return True
    return False


def lip_sync(rig, line, frame0):
    """Open the jaw with the loudness of the recorded line."""
    with wave.open(str(su.PROJECT_ROOT / line["file"])) as w:
        rate, data = w.getframerate(), np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
    step = rate // FPS
    rms = np.array([np.sqrt(np.mean(data[i:i + step] ** 2)) for i in range(0, len(data) - step, step)])
    if not len(rms):
        return
    env = np.clip(rms / (np.percentile(rms, 95) + 1e-6), 0, 1)
    jaw = rig.pose.bones["jaw"]
    start = frame0 + round(line["offset"] * FPS)
    for i in range(0, len(env), 2):
        kset(jaw, "scale", start + i, Vector((1 + 0.2 * env[i], 1, 1 + 3.2 * env[i])))
    kset(jaw, "scale", start + len(env) + 2, Vector((1, 1, 1)))


# --------------------------------------------------------------------------- cameras
def make_camera(ctx, name, frame_a, frame_b, spec):
    cam = su.camera(name, ctx["C"]["CAMERAS"], spec["at"], spec["look"], spec.get("lens", 35))
    cam.data.sensor_width = 36
    cam.data.dof.use_dof = spec.get("f", 0) > 0
    cam.data.dof.aperture_fstop = spec.get("f", 8)
    keys = [(frame_a, spec["at"], spec["look"], spec.get("roll", 0), spec.get("lens", 35)),
            (frame_b, spec.get("to", spec["at"]), spec.get("look_to", spec["look"]), spec.get("roll_to",
             spec.get("roll", 0)), spec.get("lens_to", spec.get("lens", 35)))]
    prev = None
    for frame, loc, look, roll, lens in keys:
        cam.location = loc
        direction = Vector(look) - Vector(loc)
        q = direction.to_track_quat("-Z", "Y") @ Quaternion((0, 0, 1), math.radians(roll))
        e = q.to_euler()
        if prev:
            e.make_compatible(prev)
        prev = e
        cam.rotation_euler = e
        cam.keyframe_insert("location", frame=frame)
        cam.keyframe_insert("rotation_euler", frame=frame)
        kset(cam.data, "lens", frame, lens)
        focus = spec.get("focus_to" if frame == frame_b and "focus_to" in spec else "focus", look)
        kset(cam.data.dof, "focus_distance", frame, (Vector(focus) - Vector(loc)).length)
    if spec.get("hand"):
        anim = cam.animation_data
        from bpy_extras import anim_utils
        for fc in anim_utils.action_get_channelbag_for_slot(anim.action, anim.action_slot).fcurves:
            if fc.data_path == "rotation_euler":
                mod = fc.modifiers.new("NOISE")
                mod.strength, mod.scale, mod.phase = math.radians(spec["hand"]), 18, fc.array_index * 7.3
    marker = ctx["scene"].timeline_markers.new(name, frame=frame_a)
    marker.camera = cam
    return cam


# --------------------------------------------------------------------- lighting states
LIGHT_STATES = {
    "black": {},
    "void": {"vo_top": 260, "vo_rim": 25},
    "chamber_night": {"moon": 1100, "fill": 35},
    "chamber_dark": {"moon": 700, "fill": 40},
    "chamber_day": {"sun": 6, "warm": 70, "fill": 10},
    "chamber_open": {"sun": 7, "warm": 140, "fill": 25},
    "chamber_lantern": {"moon": 600, "fill": 15},
    "chamber_lantern_eye": {"moon": 600, "fill": 15, "eye_key": 6, "eye_rim": 2.5},     # 3.16 cuts to the eye
    "chamber_police": {"moon": 300, "warm": 160, "fill": 30, "o1": 35, "o2": 35, "o3": 35},
    "chamber_police_cold": {"moon": 500, "warm": 40, "fill": 60, "o1": 20, "o2": 20, "o3": 20},
    "corridor": {"co_moon": 400, "co_fill": 15},
    "entry_day": {"en_day": 260, "en_fill": 60},
    "entry_night": {"en_lamp": 400, "en_fill": 25, "candle": 40},
    "kitchen_day": {"ki_sun": 320, "ki_fill": 90},
    "kitchen_night": {"ki_fill": 12, "o1": 40, "o2": 40, "o3": 40},
    "narrator_day": {"nr_sun": 220, "nr_fill": 40},
    "exterior_dusk": {"ex_lamp": 90, "ex_moon": 1.2},
    "exterior_night": {"ex_lamp": 250, "ex_moon": 1.5},
    "eye": {"eye_key": 6, "eye_rim": 2.5},
    "watch": {"watch_moon": 2.5},
    "beetle": {"beetle_moon": 1.0},
}
WORLDS = {"night": ((0.004, 0.006, 0.014), 1.0), "black": ((0, 0, 0), 0.0), "dusk": ((0.05, 0.06, 0.12), 1.0),
          "day": ((0.25, 0.27, 0.3), 0.6)}


# ----------------------------------------------------------------- shot staging
def stage_all(ctx):
    R, S = ctx["R"], ctx["S"]
    cx, co, en, ki, nr, vo, ex = (sets.SET_X[k] for k in ("chamber", "corridor", "entry", "kitchen",
                                                         "narrator_room", "void", "exterior"))
    door_out = dict(loc=(-1.65, -2.45, 0), heading=180)
    lant_door = (-1.52, -1.98, 1.45)
    om_lie = dict(loc=(0.9, 0.3, 0.8), rot=(-90, 0, 0), asleep=True)
    om_sit = dict(loc=(0.9, 1.4, -0.2), heading=0, pose=SIT_BED)
    om_floor = dict(loc=(-0.05, 0.25, 0.12), rot=(-90, 0, 12))
    eye_om = Vector((0.937, 1.975, 0.89))      # vulture eye, lying down
    eye_sit = Vector((0.937, 1.23, 1.462))     # vulture eye, sitting up (om_sit)
    lant_cam = dict(at=(-2.05, -1.45, 1.6), look=(-1.55, -2.0, 1.42), lens=85, f=4, focus=(-1.52, -1.98, 1.42))
    face_cam = dict(at=(0.55, 0.5, 1.5), look=(0.9, 1.4, 1.42), lens=85, f=2.8, focus=(0.9, 1.22, 1.46))
    n_void = dict(loc=(vo, -0.12, -0.4), heading=0, pose=SIT)
    seated = {"O1": dict(loc=(0.75, -0.55, -0.4), heading=-112, pose=SIT),       # all face the narrator's chair
              "O2": dict(loc=(-0.15, 1.0, -0.4), heading=-24, pose=SIT),
              "O3": dict(loc=(0.15, -1.35, -0.4), heading=-151, pose=SIT)}
    chairs = [((0.75, -0.55, 0), -112), ((-0.15, 1.0, 0), -24), ((0.15, -1.35, 0), -151), ((-0.6, 0.0, 0), 90)]
    n_seated = dict(loc=(-0.6, 0.0, -0.4), heading=90, pose=SIT)
    seats = {f"chair{i}": dict(location=loc, rotation_euler=(0, 0, rot)) for i, (loc, rot) in enumerate(chairs)}
    void_cam = dict(at=(vo, -1.6, 1.3), look=(vo, 0, 1.22), lens=50, f=2.8, to=(vo, -1.25, 1.3))

    def lant(point, aim, mode):
        return dict(point=point, aim=aim, mode=mode)

    P = {}   # shot id -> staging

    def st(sid, light, world="night", chars=None, props=None, cams=None, lant_=None, extra=None):
        P[sid] = dict(light=light, world=world, chars=chars or {}, props=props or {}, cams=cams, lant=lant_,
                      extra=extra)

    # ---------------- 0. prologue
    st("0.1", "black", "black", cams=[dict(at=(170, -6, 30), look=(170, 0, 30))])
    st("0.2", "chamber_night", chars={"OM": om_lie}, lant_=lant((-0.6, -1.6, 1.7), (-0.6, 0.0, 0.0), "crack"),
       cams=[dict(at=(-0.6, -0.55, 0.07), look=(-0.6, 0.4, 0.0), lens=100, f=2, focus=(-0.6, 0.0, 0),
                  to=(-0.6, -0.3, 0.06))], props={"dust": (-0.6, 0.0, 0.001)})
    st("0.3", "void", "black", chars={"N": n_void}, cams=[void_cam])
    st("0.4", "void", "black", chars={"N": n_void},
       cams=[dict(at=(vo, -0.75, 1.3), look=(vo, -0.05, 1.29), lens=85, f=8)],
       extra=lambda c, sid: _dart_eyes(c["R"]["N"], sid))
    st("0.5", "void", "black", chars={"N": dict(n_void, face={"brow.L": (0, 12, 0), "brow.R": (0, -12, 0)})},
       cams=[dict(void_cam, to=(vo, -0.75, 1.24), look_to=(vo, 0, 1.24))])
    st("T", "black", "black", cams=[dict(at=(170, -5.2, -0.1), look=(170, 0, -0.1), lens=50,
                                          to=(170, -4.9, -0.1))])
    # ---------------- 1. the eye
    st("1.1", "exterior_dusk", "dusk", cams=[dict(at=(ex, -11, 7.5), look=(ex, 0, 6.0), lens=35,
                                                   to=(ex, -9.5, 1.8), look_to=(ex, 0, 2.2))])
    tray_hands = dict(R=(ki - 0.31, -0.05, 0.78), L=(ki + 0.11, -0.05, 0.78))
    st("1.2", "kitchen_day", "day",
       chars={"N": dict(loc=(ki - 0.1, -0.55, 0), heading=180, pose=pose(spine=B * 20, neck=B * 10),
                        ik=tray_hands)},
       cams=[dict(at=(ki + 2.4, -2.1, 1.9), look=(ki, 0.0, 0.9), lens=24, to=(ki + 2.4, -1.2, 1.9))])
    st("1.3", "entry_day", "day",
       chars={"N": dict(loc=(en - 1.45, -1.6, 0), heading=180, ik=dict(R=(en - 1.65, -1.25, 1.05),
                                                                    L=(en - 1.25, -1.25, 1.05)))},
       props={"tray": dict(location=(en - 1.45, -1.25, 1.0))},
       cams=[dict(at=(en + 0.4, -1.9, 1.9), look=(en - 1.45, -0.6, 1.7), lens=35, to=(en + 0.3, 0.6, 3.4),
                  look_to=(en - 1.45, 1.3, 4.1))],
       extra=lambda c, sid: _climb(c, sid, (en - 1.45, -1.6), (en - 1.45, 1.4), 0.0, 3.0))
    day_n = dict(loc=(0.05, 0.75, 0), heading=90, pose=HOLD)
    st("1.4", "chamber_day", chars={"OM": om_sit, "N": dict(day_n, ik=dict(R=(0.35, 0.55, 0.95), L=(0.35, 0.95, 0.95)))},
       props={"tray": dict(location=(0.35, 0.75, 0.93), rotation_euler=(0, 0, 90))},
       cams=[dict(at=(2.0, -1.0, 1.5), look=(0.6, 1.2, 1.1), lens=35, f=4, to=(1.7, -0.6, 1.45))],
       extra=lambda c, sid: _set_tray_down(c, sid))
    st("1.5", "chamber_day", chars={"OM": om_sit, "N": day_n}, props={"chest": dict(rotation_euler=(-70, 0, 0))},
       cams=[dict(at=(1.25, -0.85, 1.15), look=(2.0, -1.3, 0.5), lens=50, f=8)])
    st("1.6", "chamber_day", chars={"OM": dict(om_sit, heading=-30), "N": day_n},
       cams=[dict(at=(-0.6, 0.2, 1.78), look=(0.9, 1.45, 1.4), lens=50, f=2.8, focus=(0.05, 0.75, 1.65),
                  focus_to=(0.9, 1.45, 1.6))])
    st("1.7", "eye", "black", props={"lid": dict(rotation_euler=(80, 0, 0))},
       cams=[dict(at=(140, -0.95, 5.06), look=(140, -0.12, 5.0), lens=100, f=8, to=(140, -0.8, 5.04))],
       extra=lambda c, sid: _eye_blink(c, sid, open_at=1.0))
    st("1.8", "chamber_day", chars={"OM": om_sit, "N": dict(day_n, face={"brow.L": (0, -15, 0),
                                                                         "brow.R": (0, 15, 0)})},
       cams=[dict(at=(0.75, 0.35, 1.62), look=(0.05, 0.75, 1.65), lens=85, f=2.8, focus=(0.16, 0.75, 1.67))])
    st("1.9", "narrator_day", "day",
       chars={"N": dict(loc=(nr, 0.95, -0.4), heading=180, pose=SIT)},
       cams=[dict(at=(nr + 1.6, -1.7, 1.7), look=(nr, 1.3, 1.0), lens=24)],
       extra=lambda c, sid: _timelapse(c, sid))
    # ---------------- 2. seven nights
    st("2.1", "corridor", chars={"N": dict(loc=(co - 0.55, -2.2, 0), heading=-90)},
       cams=[dict(at=(co + 0.2, 3.2, 0.45), look=(co, -2.0, 1.2), lens=24, to=(co + 0.2, 3.45, 0.45))],
       extra=lambda c, sid: _corridor_walk(c, sid))
    st("2.2", "watch", "black", props={"minute": dict(rotation_euler=(0, 0, 12))},
       cams=[dict(at=(150, -0.05, 0.32), look=(150, 0.01, 0.02), lens=100, f=11)],
       extra=lambda c, sid: _watch_tick(c, sid))
    latch = (co + 0.849, 0.83, 1.0)
    st("2.3", "corridor", chars={"N": dict(loc=(co + 0.45, 1.05, 0), heading=90, pose=PEEK,
                                           ik=dict(R=latch))},
       cams=[dict(at=(co + 0.55, 0.3, 1.25), look=(co + 0.84, 0.83, 1.0), lens=50, f=4, focus=latch)],
       extra=lambda c, sid: _latch(c, sid))
    peek = dict(door_out, pose=PEEK, ik=dict(R=(lant_door[0], lant_door[1], lant_door[2] + 0.17)))
    st("2.4", "chamber_night", chars={"OM": om_lie, "N": dict(peek, loc=(-1.65, -2.95, 0))},
       props={"ch_door": dict(rotation_euler=(0, 0, 0))},
       lant_=lant((lant_door[0], -2.5, 1.45), eye_om, "closed"),
       cams=[dict(at=(0.35, 1.2, 1.15), look=(-1.4, -2.25, 1.35), lens=35, f=2.8)],
       extra=lambda c, sid: _door_creep(c, sid, 0, 35, enter=True))
    st("2.5", "chamber_night", chars={"OM": om_lie, "N": peek}, props={"ch_door": dict(rotation_euler=(0, 0, -35))},
       lant_=lant(lant_door, eye_om, "closed"),
       cams=[dict(at=(-2.15, -1.5, 1.6), look=(-1.64, -2.25, 1.55), lens=50, f=4)],
       extra=lambda c, sid: _clock_spin(c, sid))
    st("2.6", "chamber_night", chars={"OM": om_lie, "N": peek}, props={"ch_door": dict(rotation_euler=(0, 0, -35))},
       lant_=lant(lant_door, eye_om, "closed"),
       cams=[dict(lant_cam, to=(-1.95, -1.56, 1.57))],
       extra=lambda c, sid: _open_shutter(c, sid, 0.55, 18))
    st("2.7", "chamber_night", chars={"OM": om_lie, "N": peek}, props={"ch_door": dict(rotation_euler=(0, 0, -35))},
       lant_=lant(lant_door, eye_om, "crack"),
       cams=[dict(at=(2.1, -1.9, 1.9), look=(-0.4, 0.2, 1.1), lens=24, f=0, to=(1.7, -1.0, 1.9),
                  look_to=(0.4, 1.2, 0.95))])
    night_cams = [dict(at=(1.6, -1.4, 1.35), look=(0.6, 1.6, 0.95), lens=50),
                  dict(at=(-0.4, 0.9, 1.5), look=(0.95, 1.95, 0.85), lens=50),
                  dict(at=(1.9, -1.8, 2.2), look=(-0.5, 0.0, 1.0), lens=28),
                  dict(at=(0.4, 0.6, 1.3), look=(0.94, 1.95, 0.88), lens=85),
                  dict(at=(-2.05, -1.45, 1.6), look=(-1.64, -2.3, 1.6), lens=85),
                  dict(at=(0.94, 1.2, 1.75), look=(0.94, 1.95, 0.88), lens=50)]
    st("2.8", "chamber_night", chars={"OM": om_lie, "N": peek}, props={"ch_door": dict(rotation_euler=(0, 0, -35))},
       lant_=lant(lant_door, eye_om, "crack"), cams=night_cams,
       extra=lambda c, sid: _night_cards(c, sid, len(night_cams)))
    st("2.9", "chamber_open", "day",
       chars={"OM": om_sit, "N": dict(loc=(0.15, 0.4, 0), heading=60)},
       props={"sh_L": "open", "sh_R": "open"},
       cams=[dict(at=(2.0, -0.9, 1.55), look=(0.5, 1.1, 1.25), lens=35, f=4, hand=0.25)],
       extra=lambda c, sid: (_talk(c, sid), _open_shutters_anim(c, sid)))
    # ---------------- 3. the eighth night
    st("3.1", "corridor", chars={"N": dict(loc=(co + 0.45, 1.05, 0), heading=90, pose=HOLD)},
       cams=[dict(at=(co - 0.1, -3.2, 1.6), look=(co + 0.6, 1.2, 1.3), lens=24, to=(co - 0.05, -2.4, 1.6))],
       extra=lambda c, sid: _card(c, sid, "VIII"))
    st("3.2", "corridor", chars={"N": dict(loc=(co + 0.45, 1.05, 0), heading=90, pose=PEEK, ik=dict(R=latch))},
       cams=[dict(at=(co + 0.15, 2.3, 1.45), look=(co + 0.85, 1.3, 1.2), lens=40)],
       extra=lambda c, sid: _door_open_slow(c, sid))
    gap_cam = dict(at=(-2.05, -1.45, 1.6), look=(-1.64, -2.3, 1.6), lens=85, f=2.8, focus=(-1.65, -2.11, 1.58))
    dark_peek = dict(peek, face={"brow.L": (0, -10, 0), "brow.R": (0, 10, 0)})
    st("3.3", "chamber_lantern", chars={"OM": om_lie, "N": dark_peek},
       props={"ch_door": dict(rotation_euler=(0, 0, -35))}, lant_=lant(lant_door, eye_om, "closed"), cams=[gap_cam],
       extra=lambda c, sid: _chuckle(c, sid))
    st("3.4", "chamber_dark", chars={"OM": dict(om_lie, rot=(-90, 0, 6)), "N": peek},
       props={"ch_door": dict(rotation_euler=(0, 0, -35))}, lant_=lant(lant_door, eye_om, "closed"),
       cams=[dict(at=(2.2, -2.0, 1.8), look=(0.0, 1.0, 0.8), lens=24)],
       extra=lambda c, sid: _om_shift(c, sid))
    st("3.5", "chamber_lantern", chars={"OM": om_lie, "N": dark_peek},
       props={"ch_door": dict(rotation_euler=(0, 0, -35))}, lant_=lant(lant_door, eye_om, "closed"),
       cams=[dict(gap_cam, to=(-1.95, -1.65, 1.6))])
    st("3.6", "chamber_lantern", chars={"OM": om_lie, "N": peek}, props={"ch_door": dict(rotation_euler=(0, 0, -35))},
       lant_=lant(lant_door, eye_om, "closed"),
       cams=[lant_cam],
       extra=lambda c, sid: _slip(c, sid))
    st("3.7", "chamber_dark", chars={"OM": om_lie, "N": peek}, props={"ch_door": dict(rotation_euler=(0, 0, -35))},
       lant_=lant(lant_door, eye_om, "closed"),
       cams=[dict(at=(2.1, -1.9, 1.45), look=(0.9, 1.2, 1.1), lens=24, to=(1.7, -1.2, 1.4))],
       extra=lambda c, sid: _spring_up(c, sid))
    st("3.8", "chamber_dark", chars={"OM": om_sit, "N": peek}, props={"ch_door": dict(rotation_euler=(0, 0, -35))},
       lant_=lant(lant_door, eye_om, "closed"),
       cams=[dict(at=(2.3, -2.05, 2.8), look=(-0.3, 0.2, 0.9), lens=24)],
       extra=lambda c, sid: _moon_crawl(c, sid))
    st("3.9", "beetle", "black", cams=[dict(at=(160, -0.065, 0.014), look=(160, 0.008, 0.012), lens=100, f=5.6)],
       extra=lambda c, sid: _beetle(c, sid))
    st("3.10", "chamber_dark", chars={"OM": dict(om_sit, face={"brow.L": (0, 15, 0), "brow.R": (0, -15, 0)}),
                                      "N": peek},
       props={"ch_door": dict(rotation_euler=(0, 0, -35))}, lant_=lant(lant_door, eye_om, "closed"),
       cams=[dict(face_cam, to=(0.6, 0.65, 1.48))],
       extra=lambda c, sid: _tremble(c, sid))
    st("3.11", "chamber_dark", chars={"OM": om_sit, "N": peek}, props={"ch_door": dict(rotation_euler=(0, 0, -35))},
       lant_=lant(lant_door, eye_om, "closed"),
       cams=[face_cam,
             dict(at=(-0.6, 0.2, 1.0), look=(-2.3, 0.5, 0.7), lens=35),
             dict(at=(-1.2, -1.1, 0.25), look=(-1.6, -0.3, 0.0), lens=50, f=2.8),
             dict(at=(2.0, 0.3, 1.3), look=(0.9, 1.3, 1.3), lens=50)],
       extra=lambda c, sid: _suppositions(c, sid))
    st("3.12", "chamber_dark", chars={"OM": om_sit, "N": peek}, props={"ch_door": dict(rotation_euler=(0, 0, -35))},
       lant_=lant(lant_door, eye_om, "closed"),
       cams=[dict(at=(-0.4, -1.2, 1.8), look=(0.9, 2.2, 2.0), lens=24, look_to=(0.9, 2.2, 1.2))],
       extra=lambda c, sid: _shadow_of_death(c, sid))
    st("3.13", "chamber_dark", chars={"OM": om_sit, "N": peek}, props={"ch_door": dict(rotation_euler=(0, 0, -35))},
       lant_=lant(lant_door, eye_sit, "crack"),
       cams=[lant_cam, dict(at=(-1.85, -1.75, 1.75), look=eye_sit, lens=24, to=(-1.7, -1.5, 1.72)),
             dict(face_cam, focus=eye_sit)],
       extra=lambda c, sid: _open_shutter(c, sid, 0.2, 6))
    st("3.14", "eye", "black", props={"lid": dict(rotation_euler=(-40, 0, 0))},
       cams=[dict(at=(140, -1.3, 5.08), look=(140, -0.12, 5.0), lens=60, f=8, to=(140, -0.85, 5.05),
                  lens_to=100)])
    st("3.15", "chamber_lantern", chars={"OM": om_sit, "N": dict(dark_peek, pose=pose(PEEK, head=(B * -6, 0, 12)))},
       props={"ch_door": dict(rotation_euler=(0, 0, -35))}, lant_=lant(lant_door, eye_sit, "crack"),
       cams=[dict(gap_cam, to=(-1.98, -1.6, 1.6)), dict(at=(150, -0.05, 0.3), look=(150, 0.01, 0.02), lens=85, f=11),
             dict(gap_cam, at=(-1.95, -1.65, 1.6))],
       extra=lambda c, sid: _cotton_insert(c, sid))
    esc = [dict(at=(140, -0.85, 5.05), look=(140, -0.12, 5.0), lens=100, f=8),
           dict(gap_cam, at=(-1.98, -1.7, 1.6)),
           lant_cam]
    st("3.16", "chamber_lantern_eye", chars={"OM": om_sit, "N": dark_peek},
       props={"ch_door": dict(rotation_euler=(0, 0, -35)), "lid": dict(rotation_euler=(-40, 0, 0))},
       lant_=lant(lant_door, eye_sit, "crack"),
       cams=[dict(esc[i % 3], roll=3 * i, roll_to=3 * i + 2, hand=0.3 + 0.1 * i) for i in range(9)],
       extra=lambda c, sid: None)
    st("3.17", "chamber_night", chars={"OM": om_sit, "N": dict(loc=(-1.35, -1.9, 0), heading=170,
                                                                pose=pose(spine=B * 25, upper_arm_L=F * 70,
                                                                          upper_arm_R=F * 70))},
       props={"ch_door": dict(rotation_euler=(0, 0, -80))}, lant_=lant((-1.1, -1.75, 1.2), eye_om, "open"),
       cams=[dict(at=(1.9, -1.7, 1.5), look=(-1.0, -1.6, 1.3), lens=24, look_to=(0.4, 1.0, 1.1), hand=0.8)],
       extra=lambda c, sid: _leap(c, sid))
    st("3.18", "chamber_night", chars={"OM": om_floor, "N": dict(loc=(-0.45, -0.3, 0), heading=60)},
       props={"ch_door": dict(rotation_euler=(0, 0, -80)), "ceiling": dict(hide_render=True)},
       lant_=lant((-0.9, -0.9, 0.09), (0.5, 1.0, 1.0), "open"),
       cams=[dict(at=(0.4, 0.4, 5.6), look=(0.4, 0.45, 0), lens=24)],
       extra=lambda c, sid: _tip_bed(c, sid))
    st("3.19", "exterior_night", cams=[dict(at=(ex + 1.5, -2.5, 1.8), look=(ex - 2.3, -12, 2.2), lens=50, f=2.8)],
       extra=lambda c, sid: _neighbour(c, sid))
    tipped = dict(location=(0.344, 1.2, 0.724), rotation_euler=(0, -75, 0))
    st("3.20", "chamber_night", chars={"OM": om_floor, "N": dict(loc=(-0.9, -0.8, 0), heading=40)},
       props={"ch_door": dict(rotation_euler=(0, 0, -80)), "bed": tipped},
       lant_=lant((-0.9, -0.9, 0.09), (0.5, 1.0, 1.0), "open"),
       cams=[dict(at=(0.6, -1.4, 1.2), look=(-0.05, 0.3, 0.2), lens=28)])
    st("3.21", "chamber_night",
       chars={"OM": dict(om_floor, loc=(-0.3, 0.2, 0.12)),
              "N": dict(loc=(-1.2, 1.25, -0.35), heading=90, pose=KNEEL, ik=dict(R=(-0.58, 1.45, 0.26)))},
       props={"ch_door": dict(rotation_euler=(0, 0, -80))}, lant_=lant((-0.9, -0.2, 0.09), (0.0, 1.0, 0.5), "open"),
       cams=[dict(at=(-0.15, 0.85, 0.85), look=(-0.58, 1.45, 0.22), lens=50, f=2.8)])
    # ---------------- 4. concealment
    st("4.1", "void", "black", chars={"N": n_void}, cams=[void_cam])
    st("4.2", "chamber_night", chars={"N": dict(loc=(-1.3, 0.3, -0.45), heading=-90, pose=KNEEL)},
       props={"ch_door": dict(rotation_euler=(0, 0, -80))}, lant_=lant((-0.6, 0.3, 0.09), (-2.5, 0.3, 1.5), "open"),
       cams=[dict(at=(0.6, 0.3, 1.5), look=(-2.48, 0.3, 1.4), lens=35, f=0)],
       extra=lambda c, sid: _work(c, sid))
    st("4.3", "chamber_night", props={"ch_door": dict(rotation_euler=(0, 0, -80))},
       lant_=lant((0.2, -0.6, 0.09), (-0.6, 0.0, 0.0), "open"),
       cams=[dict(at=(-0.6, -1.25, 0.7), look=(-0.6, 0.0, 0.0), lens=50, f=4, to=(-0.6, -1.4, 1.3))],
       extra=lambda c, sid: _planks(c, sid, up=True))
    st("4.4", "chamber_night", props={"ch_door": dict(rotation_euler=(0, 0, -80)), "ceiling": dict(hide_render=True)},
       lant_=lant((0.2, -0.6, 0.09), (-0.6, 0.0, 0.0), "open"),
       cams=[dict(at=(-0.6, 0.0, 3.2), look=(-0.6, 0.01, 0.0), lens=35)],
       extra=lambda c, sid: _planks(c, sid, up=False))
    st("4.5", "chamber_night", chars={"N": dict(loc=(-0.6, -0.4, 0), heading=-20,
                                                ik=dict(R=(-0.66, -0.68, 1.0), L=(-0.5, -0.66, 1.0)))},
       props={"ch_door": dict(rotation_euler=(0, 0, -80))}, lant_=lant((0.2, -0.6, 0.09), (-0.6, 0.0, 1.0), "open"),
       cams=[dict(at=(-0.1, -2.0, 1.6), look=(-0.6, -0.45, 1.5), lens=45, f=2.8, focus=(-0.6, -0.5, 1.67))],
       extra=lambda c, sid: _laugh(c, sid))
    st("4.6", "corridor", cams=[dict(at=(co, 2.6, 1.75), look=(co - 0.03, 3.58, 1.72), lens=50, f=2.8)])
    # ---------------- 5. the visitors
    st("5.1", "entry_night", chars={"N": dict(loc=(en - 1.45, 1.4, 3.0), heading=0)},
       cams=[dict(at=(en - 1.45, -1.6, 0.9), look=(en - 1.45, 1.4, 3.5), lens=35, to=(en - 0.6, -1.5, 1.4),
                  look_to=(en - 1.3, 0.0, 1.0))],
       extra=lambda c, sid: _descend(c, sid))
    officers_door = {"O1": dict(loc=(en - 0.05, -2.85, 0), heading=180),
                     "O2": dict(loc=(en - 0.65, -3.15, 0), heading=170),
                     "O3": dict(loc=(en + 0.6, -3.1, 0), heading=190)}
    n_hall = dict(loc=(en + 0.25, -0.75, 0), heading=0, ik=dict(R=(en + 0.07, -0.95, 1.05)))
    hand_candle = (en + 0.07, -0.95, 1.0)
    st("5.2", "entry_night", chars=dict(officers_door, N=n_hall), props={"en_door": dict(rotation_euler=(0, 0, 0)),
                                                                          "candle": hand_candle},
       cams=[dict(at=(en + 0.7, 1.5, 1.65), look=(en, -2.7, 1.5), lens=35, f=4)],
       extra=lambda c, sid: (_street_door(c, sid), _talk(c, sid)))
    st("5.3", "entry_night", chars=dict(officers_door, N=n_hall), props={"en_door": dict(rotation_euler=(0, 0, -95)),
                                                                          "candle": hand_candle},
       cams=[dict(at=(en + 0.15, -1.75, 1.63), look=(en + 0.25, -0.75, 1.66), lens=50, f=2.8)],
       extra=lambda c, sid: _talk(c, sid))
    st("5.4", "kitchen_night",
       chars={"N": dict(loc=(ki - 1.6, -1.5, 0), heading=-40), "O1": dict(loc=(ki - 0.3, -1.7, 0), heading=200),
              "O2": dict(loc=(ki + 1.3, 1.2, 0), heading=150), "O3": dict(loc=(ki + 1.9, -1.2, 0), heading=120)},
       cams=[dict(at=(ki + 2.6, -2.2, 2.0), look=(ki - 1.0, 0.5, 0.9), lens=24, look_to=(ki + 1.6, 1.4, 0.9))],
       extra=lambda c, sid: _talk(c, sid))
    police = dict(seated)
    stand_by_chest = dict(loc=(1.35, -1.3, 0), heading=-90)
    st("5.5", "chamber_police",
       chars={"N": stand_by_chest, "O1": dict(loc=(1.5, -0.4, 0), heading=-160),
              "O2": dict(loc=(0.8, -1.0, 0), heading=-120), "O3": dict(loc=(1.4, -2.0, 0), heading=-30)},
       props={"chest": dict(rotation_euler=(-70, 0, 0))},
       cams=[dict(at=(0.2, -1.6, 1.6), look=(1.9, -1.2, 0.6), lens=35, f=4, to=(0.4, -1.5, 1.5))])
    st("5.6", "chamber_police", chars=dict(police, N=dict(loc=(-1.1, -0.6, 0), heading=60)), props=dict(seats),
       cams=[dict(at=(-0.6, -1.3, 0.13), look=(-0.6, 0.0, 0.1), lens=24, f=4)],
       extra=lambda c, sid: _chairs(c, sid))
    st("5.7", "chamber_police", chars=dict(police, N=n_seated), props=dict(seats),
       cams=[dict(at=(1.9, -1.9, 1.6), look=(-0.2, 0.0, 0.8), lens=24, to=(2.2, -1.1, 1.6))],
       extra=lambda c, sid: _talk(c, sid))
    st("5.8", "chamber_police", props=dict(seats), chars=dict(police, N=dict(n_seated, face={"brow.L": (0, -12, 0),
                                                                                         "brow.R": (0, 12, 0)})),
       cams=[dict(at=(0.35, -0.25, 1.25), look=(-0.6, 0.0, 1.23), lens=85, f=2.0, to=(0.2, -0.2, 1.25))])
    st("5.9", "chamber_police", chars=dict(police, N=n_seated), props=dict(seats, dust=(-0.6, -0.17, 0.0005)),
       cams=[dict(at=(-0.42, -0.5, 0.05), look=(-0.6, -0.12, 0.0), lens=100, f=2.8, focus=(-0.6, -0.17, 0))],
       extra=lambda c, sid: _dust_beats(c, sid))
    worried = dict(n_seated, face={"brow.L": (0, -18, 0), "brow.R": (0, 18, 0)})
    st("5.10", "chamber_police_cold", chars=dict(police, N=worried), props=dict(seats),
       cams=[dict(at=(0.3, -0.25, 1.25), look=(-0.6, 0.0, 1.23), lens=85, f=2.0, hand=0.4),
             dict(at=(0.1, -0.75, 1.25), look=(0.75, -0.55, 1.25), lens=16, hand=0.5),
             dict(at=(0.25, -0.2, 1.25), look=(-0.6, 0.0, 1.23), lens=100, f=2.0, hand=0.5),
             dict(at=(0.25, 0.15, 1.25), look=(-0.15, 0.95, 1.25), lens=16, hand=0.6)],
       extra=lambda c, sid: None)
    st("5.11", "chamber_police_cold", chars=dict(police, N=dict(loc=(-0.9, -0.6, 0), heading=0)), props=dict(seats),
       cams=[dict(at=(-0.6 + 2.0, -0.4, 1.5), look=(-0.6, -0.4, 1.3), lens=35, hand=0.4)],
       extra=lambda c, sid: _pace(c, sid))
    st("5.12", "chamber_police_cold", chars=dict(police, N=dict(loc=(-0.6, -0.5, 0), heading=0, pose=HOLD)),
       props=dict(seats, ceiling=dict(hide_render=True)),
       cams=[dict(at=(-0.2, -0.2, 4.4), look=(-0.2, -0.19, 0), lens=24)],
       extra=lambda c, sid: _chair_grate(c, sid))
    smiling = {k: dict(v, face={"jaw": (0, 0, 0)}) for k, v in police.items()}
    st("5.13", "chamber_police_cold", chars=dict(smiling, N=dict(loc=(-0.6, -0.6, 0), heading=60)), props=dict(seats),
       cams=[dict(at=(-0.3, -0.75, 1.3), look=(0.75, -0.55, 1.25), lens=24, to=(-0.9, -0.85, 1.3), lens_to=50)],
       extra=lambda c, sid: _laughs(c, sid))
    quick = [dict(at=(0.25, -0.2, 1.25), look=(-0.6, 0.0, 1.23), lens=100, f=2.0, hand=1.2),
             dict(at=(0.1, -0.75, 1.25), look=(0.75, -0.55, 1.25), lens=16, hand=1.2),
             dict(at=(-0.42, -0.5, 0.05), look=(-0.6, -0.12, 0.0), lens=100, f=2.8, hand=1.0),
             dict(at=(0.1, 0.2, 1.25), look=(0.55, 0.65, 1.25), lens=16, hand=1.2)]
    st("5.14", "chamber_police_cold", chars=dict(police, N=worried),
       props=dict(seats, dust=(-0.6, -0.17, 0.0005)),
       cams=[dict(quick[i % 4], roll=(-1) ** i * 6) for i in range(8)], extra=lambda c, sid: _dust_beats(c, sid))
    st("5.15", "chamber_police_cold",
       chars=dict(police, N=dict(loc=(-0.6, -0.3, 0), heading=40,
                                 pose=pose(spine=B * 15, upper_arm_R=F * 60, forearm_R=F * 10),
                                 face={"brow.L": (0, -22, 0), "brow.R": (0, 22, 0)})),
       props=dict(seats),
       cams=[dict(at=(1.0, -2.0, 1.6), look=(-0.6, -0.3, 1.5), lens=35, f=2.8, to=(0.6, -1.5, 1.6), hand=0.6)],
       extra=lambda c, sid: (_talk(c, sid), _stomp(c, sid)))
    # ---------------- 6. epilogue
    st("6.1", "black", "black", cams=[dict(at=(170, -6, 30), look=(170, 0, 30))])
    st("6.2", "void", "black", chars={"N": n_void},
       cams=[dict(at=(vo, -0.62, 1.29), look=(vo, -0.04, 1.27), lens=85, f=2.8, focus=(vo, -0.21, 1.275))],
       extra=lambda c, sid: _talk(c, sid))
    st("6.3", "black", "black", cams=[dict(at=(170, -6.5, -19.6), look=(170, 0, -19.6), lens=50,
                                            to=(170, -6.5, -19.3))])
    for sid in ("0.3", "0.5", "4.1"):                     # direct address: lips move with the narration
        P[sid]["extra_talk"] = True
    return P


# --------------------------------------------------------------- in-shot animation
def _key_rig_heading(rig, frame, heading_deg, loc=None):
    if loc is not None:
        kset(rig, "location", frame, Vector(loc))
    kset(rig, "rotation_euler", frame, Euler((0, 0, math.radians(heading_deg))))


def _dart_eyes(rig, sid):
    for t, yaw in ((0.9, 28), (1.6, 0), (2.7, -28), (3.4, 0), (4.3, 0)):
        for side in ("L", "R"):
            pb = rig.pose.bones[f"eye.{side}"]
            kset(pb, "rotation_euler", at(sid, t), Euler((math.radians(-12 if t == 4.3 else 0), 0,
                                                          math.radians(yaw))))


def _climb(ctx, sid, a, b, z0, z1):
    rig = ctx["R"]["N"]
    tray = ctx["managed"]["tray"][0]
    n = SHOTS[sid]["frames"]
    for i in list(range(0, n, 2)) + [n - 1]:
        t = i / n
        x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        z = z0 + (z1 - z0) * max(0.0, (y + 1.4) / 2.86) if y > -1.4 else z0
        kset(rig, "location", f0(sid) + i, Vector((x, y, z)))
        phase = 2 * math.pi * t * 6
        ch.key_pose(rig, f0(sid) + i, {"thigh.L": F * (35 * max(0, math.sin(phase)) + 5),
                                       "thigh.R": F * (35 * max(0, -math.sin(phase)) + 5),
                                       "shin.L": -F * 40 * max(0, math.sin(phase)),
                                       "shin.R": -F * 40 * max(0, -math.sin(phase))})
        kset(tray, "location", f0(sid) + i, Vector((x, y + 0.35, z + 1.0)))
        for side, dx in (("R", -0.2), ("L", 0.2)):
            ik = rig.pose.bones[f"forearm.{side}"].constraints["IK"]
            kset(ik.target, "location", f0(sid) + i, Vector((x + dx, y + 0.35, z + 1.05)))


def _set_tray_down(ctx, sid):
    tray = ctx["managed"]["tray"][0]
    kset(tray, "location", at(sid, 2.5), Vector((0.35, 0.75, 0.93)))
    kset(tray, "location", at(sid, 4.5), Vector((0.75, 0.75, 0.95)))
    kset(tray, "location", f1(sid), Vector((0.75, 0.75, 0.95)))


def _eye_blink(ctx, sid, open_at):
    lid = ctx["managed"]["lid"][0]
    for t, a in ((0, 80), (open_at, 80), (open_at + 1.2, -35), (4.5, -35), (4.7, 75), (4.9, -35)):
        kset(lid, "rotation_euler", at(sid, t), Euler((math.radians(a), 0, 0)))


def _timelapse(ctx, sid):
    sky, L = ctx["sky_mat"], ctx["lights"]
    emit = sky.node_tree.nodes["Principled BSDF"].inputs
    for t, col, strength, sun, candle in ((0, (0.45, 0.55, 0.7), 3.0, 220, 0), (0.45, (0.8, 0.35, 0.12), 2.0, 120, 0),
                                         (0.75, (0.05, 0.06, 0.14), 1.0, 10, 4), (1.0, (0.01, 0.02, 0.06), 1.0, 0, 6)):
        frame = f0(sid) + round(t * (SHOTS[sid]["frames"] - 1))
        kset(emit["Emission Color"], "default_value", frame, (*col, 1))
        kset(emit["Emission Strength"], "default_value", frame, strength)
        kset(L["nr_sun"].data, "energy", frame, sun)
        kset(L["nr_candle"].data, "energy", frame, candle)


def _corridor_walk(ctx, sid):
    rig = ctx["R"]["N"]
    co = sets.SET_X["corridor"]
    end = ch.walk(rig, [(co - 0.55, -2.2), (co, -1.0), (co + 0.3, 0.4), (co + 0.45, 1.05)], at(sid, 1.2),
                  speed=0.42, stride=0.55)
    ch.turn(rig, end, min(end + 12, f1(sid)), (1, 0))
    if end + 12 < f1(sid):
        kset(rig, "location", f1(sid), rig.location.copy())
        kset(rig, "rotation_euler", f1(sid), rig.rotation_euler.copy())
    _hold_lantern(ctx, sid, rig)


def _hold_lantern(ctx, sid, rig):
    """Lantern follows the narrator's right hand through a walking shot."""
    lantern = ctx["lantern"]
    for frame in range(f0(sid), f1(sid) + 1, 2):
        ctx["scene"].frame_set(frame)
        hand = rig.matrix_world @ rig.pose.bones["hand.R"].tail
        kset(lantern, "location", frame, hand - Vector((0, 0, 0.27)))
        kset(lantern, "rotation_euler", frame, Euler((0, 0, rig.rotation_euler.z)))


def _watch_tick(ctx, sid):
    minute = ctx["managed"]["minute"][0]
    n = SHOTS[sid]["frames"]
    for i in range(0, n, 24):
        kset(minute, "rotation_euler", f0(sid) + i, Euler((0, 0, math.radians(12 - 12 * i / n))))
    kset(minute, "rotation_euler", f1(sid), Euler((0, 0, 0)))


def _latch(ctx, sid):
    handle = ctx["managed"]["co_handle"][0]
    kset(handle, "rotation_euler", at(sid, 0.8), Euler((0, 0, 0)))
    kset(handle, "rotation_euler", at(sid, 3.5), Euler((0, math.radians(-35), 0)))


def _door_creep(ctx, sid, a, b, enter=False):
    door = ctx["managed"]["ch_door"][0]
    kset(door, "rotation_euler", at(sid, 0.5), Euler((0, 0, math.radians(-a))))
    kset(door, "rotation_euler", at(sid, 4.5), Euler((0, 0, math.radians(-b))))
    if enter:
        rig, lantern = ctx["R"]["N"], ctx["lantern"]
        kset(rig, "location", at(sid, 4.0), Vector((-1.65, -2.95, 0)))
        kset(rig, "location", f1(sid), Vector((-1.65, -2.45, 0)))
        kset(lantern, "location", at(sid, 4.0), Vector((-1.52, -2.5, 1.36)))
        kset(lantern, "location", f1(sid), Vector((-1.52, -1.98, 1.36)))
        ik = rig.pose.bones["forearm.R"].constraints["IK"]
        kset(ik.target, "location", at(sid, 4.0), Vector((-1.52, -2.5, 1.62)))
        kset(ik.target, "location", f1(sid), Vector((-1.52, -1.98, 1.62)))


def _clock_spin(ctx, sid):
    hands = ctx["managed"]["hands"][0]
    base = hands.rotation_euler.copy()
    kset(hands, "rotation_euler", f0(sid), base)
    turned = base.copy()
    turned.y += math.radians(-360)
    kset(hands, "rotation_euler", f1(sid), turned)


def _open_shutter(ctx, sid, t, angle):
    shutter = ctx["shutter"]
    kset(shutter, "rotation_euler", at(sid, t), Euler((0, 0, 0)))
    kset(shutter, "rotation_euler", at(sid, t + 2.5), Euler((0, 0, math.radians(angle))))


def _night_cards(ctx, sid, n):
    names = ["II", "III", "IV", "V", "VI", "VII"]
    for i in range(n):
        a = f0(sid) + i * SHOTS[sid]["frames"] // n
        b = f0(sid) + (i + 1) * SHOTS[sid]["frames"] // n - 1
        _show_card(ctx, names[i], a, min(b, a + 40))


def _card(ctx, sid, name):
    _show_card(ctx, name, f0(sid), at(sid, 2.5))


def _show_card(ctx, name, a, b):
    card = ctx["cards"][name]
    cam = max((m for m in ctx["scene"].timeline_markers if m.frame <= a), key=lambda m: m.frame).camera
    half_w = 18.0 / cam.data.lens                        # half frame width at 1 m in front of the lens
    card.parent, card.matrix_parent_inverse = cam, Matrix()
    d = 0.3                                              # close to the lens: in front of anything in shot
    card.location = (-0.8 * half_w * d, -0.8 * half_w * 9 / 16 * d, -d)
    card.rotation_euler, card.scale = (0, 0, 0), (half_w * d / 0.36,) * 3
    kset(card, "hide_render", a - 1, True)
    kset(card, "hide_render", a, False)
    kset(card, "hide_render", b, True)


def _talk(ctx, sid):
    for line in SHOTS[sid]["lines"]:
        rig = ctx["R"].get(line["who"])
        if rig is not None and (line["who"] != "N" or film_shot(sid)["set"] == "void"):
            lip_sync(rig, line, f0(sid))


def film_shot(sid):
    return next(s for s in film.SHOTS if s["id"] == sid)


def _open_shutters_anim(ctx, sid):
    m = ctx["managed"]
    for key, sign in (("sh_L", 1), ("sh_R", -1)):
        leaf = m[key][0]
        rest = Euler(m[key][1]["rotation_euler"])
        kset(leaf, "rotation_euler", f0(sid), rest)
        opened = rest.copy()
        opened.z += math.radians(105 * sign)
        kset(leaf, "rotation_euler", at(sid, 1.2), opened)
        kset(leaf, "rotation_euler", f1(sid), opened)


def _door_open_slow(ctx, sid):
    door = ctx["managed"]["co_door"][0]
    kset(door, "rotation_euler", f1(sid), Euler((0, 0, math.radians(-8))))


def _chuckle(ctx, sid):
    rig = ctx["R"]["N"]
    for i, t in enumerate((0.8, 1.0, 1.2, 1.4, 1.6, 1.8)):
        ch.key_pose(rig, at(sid, t), {"spine": (B * (22 + (3 if i % 2 else 0)), 0, 0)})


def _om_shift(ctx, sid):
    rig = ctx["R"]["OM"]
    kset(rig, "rotation_euler", at(sid, 0.2), Euler(deg((-90, 0, 0))))
    kset(rig, "rotation_euler", at(sid, 0.9), Euler(deg((-90, 0, 8))))


def _slip(ctx, sid):
    shutter = ctx["shutter"]
    t = SHOTS[sid]["seconds"] - 0.6
    kset(shutter, "rotation_euler", at(sid, t - 0.05), Euler((0, 0, 0)))
    kset(shutter, "rotation_euler", at(sid, t), Euler((0, 0, math.radians(7))))
    kset(shutter, "rotation_euler", at(sid, t + 0.25), Euler((0, 0, 0)))


def _spring_up(ctx, sid):
    rig = ctx["R"]["OM"]
    t = 1.5
    place_rig(rig, at(sid, t), dict(loc=(0.9, 0.3, 0.8), rot=(-90, 0, 0), asleep=True))
    place_rig(rig, at(sid, t + 0.35), dict(loc=(0.9, 1.4, -0.2), heading=0, pose=SIT_BED))
    place_rig(rig, f1(sid), dict(loc=(0.9, 1.4, -0.2), heading=0, pose=SIT_BED))


def _moon_crawl(ctx, sid):
    moon = ctx["lights"]["moon"]
    a = moon.rotation_euler.copy()
    kset(moon, "rotation_euler", f0(sid), a)
    b = a.copy()
    b.z += math.radians(-14)
    kset(moon, "rotation_euler", f1(sid), b)
    kset(moon, "rotation_euler", f1(sid) + 1, a)


def _beetle(ctx, sid):
    head = ctx["managed"]["beetle"][0]
    for t in (0.3, 1.6):
        kset(head, "rotation_euler", at(sid, t), Euler((0, 0, 0)))
        kset(head, "rotation_euler", at(sid, t + 0.06), Euler((math.radians(25), 0, 0)))
        kset(head, "rotation_euler", at(sid, t + 0.14), Euler((0, 0, 0)))


def _tremble(ctx, sid):
    jaw = ctx["R"]["OM"].pose.bones["jaw"]
    for i in range(0, SHOTS[sid]["frames"], 3):
        kset(jaw, "scale", f0(sid) + i, Vector((1, 1, 1.0 + 0.8 * (i // 3 % 2))))


def _suppositions(ctx, sid):
    m = ctx["managed"]
    shot = SHOTS[sid]
    cut = [f0(sid) + round(f * shot["frames"]) for f in (0.0, 0.3, 0.55, 0.78)]
    soot, mouse = m["soot"][0], m["mouse"][0]
    kset(soot, "location", cut[1], Vector((-2.3, 0.5, 1.6)))
    kset(soot, "location", cut[2] - 1, Vector((-2.3, 0.5, 0.05)))
    kset(mouse, "location", cut[2], Vector((-1.9, -0.6, 0)))
    kset(mouse, "location", cut[3] - 1, Vector((-1.3, 0.1, 0)))
    _talk(ctx, sid)


def _shadow_of_death(ctx, sid):
    light = ctx["lights"]["shadow"]
    kset(light.data, "energy", f0(sid), 0)
    kset(light.data, "energy", at(sid, 1.5), 600)
    kset(light.data, "energy", f1(sid), 900)
    kset(light.data, "energy", f1(sid) + 1, 0)


def _cotton_insert(ctx, sid):
    cot = ctx["managed"]["cotton"][0]
    a, b = f0(sid) + SHOTS[sid]["frames"] // 3, f0(sid) + 2 * SHOTS[sid]["frames"] // 3
    kset(cot, "hide_render", a - 1, True)
    kset(cot, "hide_render", a, False)
    kset(cot, "hide_render", b, True)


def _leap(ctx, sid):
    rig = ctx["R"]["N"]
    kset(rig, "location", at(sid, 0.3), Vector((-1.35, -1.9, 0)))
    kset(rig, "location", at(sid, 1.2), Vector((0.1, 0.6, 0.15)))
    kset(rig, "location", f1(sid), Vector((0.1, 0.6, 0.15)))
    om = ctx["R"]["OM"]
    ch.key_pose(om, at(sid, 0.5), {"spine": B * -15, "head": B * -20})


def _tip_bed(ctx, sid):
    bed = ctx["managed"]["bed"][0]
    kset(bed, "location", at(sid, 0.8), Vector((0.9, 1.2, 0)))
    kset(bed, "rotation_euler", at(sid, 0.8), Euler((0, 0, 0)))
    kset(bed, "location", at(sid, 2.8), Vector((0.344, 1.2, 0.724)))
    kset(bed, "rotation_euler", at(sid, 2.8), Euler((0, math.radians(-75), 0)))
    kset(bed, "location", f1(sid), Vector((0.344, 1.2, 0.724)))
    kset(bed, "rotation_euler", f1(sid), Euler((0, math.radians(-75), 0)))


def _neighbour(ctx, sid):
    mat, light = ctx["neighbour"], ctx["lights"]["ex_window"]
    strength = mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
    for frame, s, e in ((f0(sid), 0.0, 0), (at(sid, 1.2), 0.0, 0), (at(sid, 1.8), 3.0, 40), (f1(sid), 3.0, 40),
                        (f1(sid) + 1, 0.0, 0)):
        kset(strength, "default_value", frame, s)
        kset(light.data, "energy", frame, e)


def _work(ctx, sid):
    rig = ctx["R"]["N"]
    for i, t in enumerate(range(0, int(SHOTS[sid]["seconds"] * 2))):
        swing = 50 if i % 2 else 20
        ch.key_pose(rig, at(sid, t / 2), {"upper_arm.R": F * swing, "upper_arm.L": F * (70 - swing)})


def _planks(ctx, sid, up):
    m = ctx["managed"]
    shot = SHOTS[sid]
    for i in range(3):
        plank, rest = m[f"plank{i}"]
        lifted = Vector(rest["location"]) + Vector((0.15 * i, -0.7 - 0.25 * i, 0.06 + 0.06 * i))
        a, b = (at(sid, 0.6 + 2.2 * i), at(sid, 1.6 + 2.2 * i))
        start, end = (Vector(rest["location"]), lifted) if up else (lifted, Vector(rest["location"]))
        kset(plank, "location", f0(sid), start)
        kset(plank, "location", a, start)
        kset(plank, "location", b, end)
        kset(plank, "location", f1(sid), end)
        rot = Euler((0, 0, math.radians(8 * (i - 1)))) if up else Euler((0, 0, 0))
        kset(plank, "rotation_euler", b, rot)
    del shot


def _laugh(ctx, sid):
    jaw = ctx["R"]["N"].pose.bones["jaw"]
    t = SHOTS[sid]["seconds"] - 1.8
    for i in range(6):
        kset(jaw, "scale", at(sid, t + i * 0.15), Vector((1.2, 1, 3.5 if i % 2 == 0 else 1.5)))


def _descend(ctx, sid):
    rig, candle = ctx["R"]["N"], ctx["managed"]["candle"][0]
    en = sets.SET_X["entry"]
    n = SHOTS[sid]["frames"]
    for i in list(range(0, n, 2)) + [n - 1]:
        t = min(1.0, i / (n * 0.8))
        y = 1.4 - 3.0 * t
        z = max(0.0, 3.0 * (y + 1.4) / 2.86)
        x = en - 1.45 + (0.5 * max(0.0, (i / n - 0.8) / 0.2))
        kset(rig, "location", f0(sid) + i, Vector((x, y, z)))
        phase = 2 * math.pi * t * 6
        ch.key_pose(rig, f0(sid) + i, {"thigh.L": F * 25 * max(0, math.sin(phase)),
                                       "thigh.R": F * 25 * max(0, -math.sin(phase)),
                                       "shin.L": -F * 30 * max(0, math.sin(phase)),
                                       "shin.R": -F * 30 * max(0, -math.sin(phase))})
        hand = Vector((x - 0.18, y - 0.3, z + 1.05))
        kset(candle, "location", f0(sid) + i, hand - Vector((0, 0, 0.05)))
        kset(rig.pose.bones["forearm.R"].constraints["IK"].target, "location", f0(sid) + i, hand)
    ik = rig.pose.bones["forearm.R"].constraints["IK"]
    kset(ik, "influence", f0(sid), 1.0)
    kset(ik, "influence", f1(sid), 1.0)


def _street_door(ctx, sid):
    door = ctx["managed"]["en_door"][0]
    kset(door, "rotation_euler", at(sid, 0.2), Euler((0, 0, 0)))
    kset(door, "rotation_euler", at(sid, 1.4), Euler((0, 0, math.radians(-95))))


def _chairs(ctx, sid):
    chairs = ctx["chairs"]
    places = [((0.75, -0.55, 0), -90), ((0.55, 0.65, 0), -120), ((0.15, -1.35, 0), -60), ((-0.6, 0.0, 0), 90)]
    kset(chairs[3], "location", f0(sid), Vector((-1.4, -0.9, 0)))
    kset(chairs[3], "location", at(sid, 8.2), Vector((-1.4, -0.9, 0)))
    kset(chairs[3], "location", at(sid, 9.3), Vector(places[3][0]))
    kset(chairs[3], "location", f1(sid), Vector(places[3][0]))
    del places


def _dust_beats(ctx, sid):
    dust = ctx["managed"]["dust"][0]
    base = Vector((-0.6, -0.17, 0.0005))
    for beat in heartbeat_times():
        frame = round(beat * FPS) + 1
        if f0(sid) <= frame <= f1(sid) - 3:
            kset(dust, "location", frame - 1, base)
            kset(dust, "location", frame + 1, base + Vector((0, 0, 0.004)))
            kset(dust, "location", frame + 3, base)


def heartbeat_times():
    """Absolute seconds of every heartbeat (shared with the audio mix)."""
    times = []
    for s_id, s_off, bpm0, bpm1, e_id, e_off, _muffled, *_ in film.HEARTBEATS:
        t0 = (f0(s_id) - 1) / FPS + s_off
        t1 = (f0(e_id) - 1) / FPS + e_off
        t = t0
        while t < t1:
            times.append(t)
            frac = (t - t0) / max(t1 - t0, 1e-6)
            t += 60.0 / (bpm0 + (bpm1 - bpm0) * frac)
    return times


def _pace(ctx, sid):
    rig = ctx["R"]["N"]
    pts = [(-0.9, -0.6), (-0.3, 0.3), (-0.9, 0.9), (-1.3, 0.0), (-0.9, -0.6)]
    ch.walk(rig, pts, f0(sid) + 6, speed=1.1, stride=0.75)
    cam = ctx["scene"].timeline_markers[sid].camera
    center = Vector((-0.7, 0.0, 1.3))                  # ellipse checked by ray-cast: clears walls and furniture
    for i in range(0, SHOTS[sid]["frames"] + 1, 6):
        a = 2 * math.pi * i / SHOTS[sid]["frames"]
        loc = center + Vector((1.3 * math.cos(a), 1.1 * math.sin(a), 0.5))
        cam.location = loc
        e = (center - loc).to_track_quat("-Z", "Y").to_euler()
        e.make_compatible(cam.rotation_euler)
        cam.rotation_euler = e
        cam.keyframe_insert("location", frame=f0(sid) + i)
        cam.keyframe_insert("rotation_euler", frame=f0(sid) + i)


def _chair_grate(ctx, sid):
    chair = ctx["chairs"][3]
    rig = ctx["R"]["N"]
    seq = [(0.0, (-0.6, 0.0, 0), 90), (2.0, (-0.6, -0.15, 0.25), 60), (3.5, (-0.4, 0.0, 0.3), 140),
           (5.0, (-0.6, 0.05, 0), 100), (7.0, (0.1, 0.2, 0), 120), (SHOTS[sid]["seconds"], (0.2, 0.25, 0), 120)]
    for t, loc, rot in seq:
        kset(chair, "location", at(sid, t), Vector(loc))
        kset(chair, "rotation_euler", at(sid, t), Euler((0, 0, math.radians(rot))))
        for side, dx in (("R", -0.18), ("L", 0.18)):
            ik = rig.pose.bones[f"forearm.{side}"].constraints["IK"]
            kset(ik.target, "location", at(sid, t), Vector((loc[0] + dx, loc[1] - 0.15, loc[2] + 0.85)))
            kset(ik, "influence", at(sid, t), 1.0)
        kset(rig, "location", at(sid, t), Vector((loc[0], loc[1] - 0.55, 0)))


def _laughs(ctx, sid):
    for k in ("O1", "O2", "O3"):
        jaw = ctx["R"][k].pose.bones["jaw"]
        for i in range(0, SHOTS[sid]["frames"], 8):
            kset(jaw, "scale", f0(sid) + i, Vector((1.3, 1, 1.0 + (1.6 if (i // 8 + len(k)) % 3 == 0 else 0.3))))


def _stomp(ctx, sid):
    rig = ctx["R"]["N"]
    t = 2.3
    ch.key_pose(rig, at(sid, t), {"thigh.R": F * 40, "shin.R": -F * 50})
    ch.key_pose(rig, at(sid, t + 0.25), {"thigh.R": 0, "shin.R": 0})


# ------------------------------------------------------------------- run every shot
def shot_state(ctx, p):
    """Everything a shot sets: world, lights, props, lantern, characters."""
    out = []
    col, strength = WORLDS[p["world"]]
    out += [(ctx["bg"].inputs["Color"], "default_value", (*col, 1)),
            (ctx["bg"].inputs["Strength"], "default_value", strength)]
    state = LIGHT_STATES[p["light"]]
    for name, light in ctx["lights"].items():
        if name not in ("beam", "glow"):
            out.append((light.data, "energy", state.get(name, 0)))
    for key, (obj, rest) in ctx["managed"].items():
        override = p["props"].get(key, {})
        override = {} if isinstance(override, str) else {"location": override} if isinstance(override, tuple) \
            else override
        values = dict(rest)
        values.update(override)
        for prop, value in values.items():
            if prop == "rotation_euler":
                radians_already = key in ("sh_L", "sh_R", "chest", "hands") and "rotation_euler" not in override
                value = Euler(value) if radians_already else Euler(deg(value))
            elif prop == "location":
                value = Vector(value)
            out.append((obj, prop, value))
    out += lantern_state(ctx, p["lant"])
    for who in ("N", "OM", "O1", "O2", "O3"):
        out += rig_state(ctx["R"][who], p["chars"].get(who, dict(loc=PARK)))
    return out


def lantern_state(ctx, lan):
    lantern, beam, glow, shutter = ctx["lantern"], ctx["beam"], ctx["glow"], ctx["shutter"]
    if not lan:
        return [(lantern, "location", Vector(PARK)), (beam.data, "energy", 0), (glow.data, "energy", 0)]
    point, aim = Vector(lan["point"]), Vector(lan["aim"])
    d = aim - point
    yaw, pitch = math.atan2(d.x, -d.y), math.atan2(-d.z, math.hypot(d.x, d.y))
    mode = lan["mode"]
    return [(lantern, "location", point - Vector((0, 0, 0.09))), (lantern, "rotation_euler", Euler((pitch, 0, yaw))),
            (beam.data, "energy", {"closed": 0, "crack": 600, "open": 400}[mode]),
            (beam.data, "spot_size", math.radians({"closed": 2, "crack": 2.2, "open": 75}[mode])),
            (glow.data, "energy", {"closed": 9, "crack": 10, "open": 80}[mode]),
            (shutter, "rotation_euler", Euler((0, 0, math.radians({"closed": 0, "crack": 18, "open": 120}[mode]))))]


def apply_shots(ctx, P):
    scene = ctx["scene"]
    for sid in ORDER:
        p = P[sid]
        a, b = f0(sid), f1(sid)
        n = len(p["cams"])
        for i, spec in enumerate(p["cams"]):          # sub-cuts split the shot evenly
            ca = a + i * SHOTS[sid]["frames"] // n
            cb = a + (i + 1) * SHOTS[sid]["frames"] // n - 1
            make_camera(ctx, sid if i == 0 else f"{sid}.{i}", ca, cb, spec)
        state = shot_state(ctx, p)
        for owner, prop, value in state:
            kset(owner, prop, a, value)
        if p.get("extra_talk"):
            _talk(ctx, sid)
        if p["extra"]:
            p["extra"](ctx, sid)
        if "N" in p["chars"] and SHOTS[sid]["seconds"] > 3:
            for t in np.arange(1.7, SHOTS[sid]["seconds"] - 0.5, 3.3):
                _blink(ctx["R"]["N"], at(sid, t))
        for owner, prop, value in state:               # hold whatever the shot didn't animate
            if not has_keys(owner, prop, a, b):
                kset(owner, prop, b, value)
        print(f"  shot {sid:5} frames {a}-{b}", flush=True)
    scene.frame_set(1)


def _blink(rig, frame):
    for side in ("L", "R"):
        pb = rig.pose.bones[f"eye.{side}"]
        for df, s in ((-1, 1.0), (1, 0.12), (3, 1.0)):
            kset(pb, "scale", frame + df, Vector((1, 1, s)))


if __name__ == "__main__":
    ctx = build()
    P = stage_all(ctx)
    apply_shots(ctx, P)
    scene = ctx["scene"]
    su.set_mp4_output(scene, "//../../output/renders/tell_tale_heart_picture.mp4")
    su.set_viewport(target=(0, 0.5, 1.0), view_from=(3.5, -3.5, 2.5))
    su.save_blend(OUT_FILE, compress=True)            # 74 MB -> 23 MB in git
    print(f"Tell-Tale Heart saved: {OUT_FILE} — {len(ORDER)} shots, {len(scene.timeline_markers)} camera cuts, "
          f"{scene.frame_end} frames")
