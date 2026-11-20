"""
Tell-Tale Heart v2 preview: "the eighth night" (film shots 3.1-3.10) with the new pipeline:
MPFB characters, the living-body layers (eyes, breath, sway, startle), voice-driven lips, props moved
only by hands, Chatterbox voices, recorded sound and Chopin.

    tools/chatterbox/.venv/bin/python -I scripts/chatterbox_lines.py stories/the_tell_tale_heart/preview_v2/lines.json
    blender -b --python stories/the_tell_tale_heart/preview_v2.py -- build      # -> blender/scenes/..._v2_preview.blend
    blender -b blender/scenes/tell_tale_heart_v2_preview.blend --python stories/the_tell_tale_heart/preview_v2.py -- render A B
    .venv/bin/python -I stories/the_tell_tale_heart/preview_v2.py mix           # soundtrack + final mp4
    (soundtrack alone, to check it before the frames are done: ... preview_v2.py soundtrack)
"""
import functools
import json
import math
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
VO = ROOT / "audio" / "voiceovers" / "the_tell_tale_heart_v2"
OUT = ROOT / "output" / "renders" / "the_tell_tale_heart_v2_preview"
BLEND = ROOT / "blender" / "scenes" / "tell_tale_heart_v2_preview.blend"
FPS, LEAD, GAP, TAIL = 24, 0.4, 0.35, 0.7

# shot id, camera, lines (voice files in VO, who), minimum seconds - the film's own shot list, 3.1-3.10
SHOTS = [
    ("3.1", "door_from_room", [("3.1_N", "N")], 7.0),
    ("3.3", "gap", [("3.3_N", "N")], 4.5),
    ("3.4", "corner", [("3.4_N", "N")], 4.5),
    ("3.5", "gap", [("3.5_N", "N")], 6.0),
    ("3.6", "lantern", [("3.6_N", "N")], 5.5),
    ("3.7", "bed", [("3.7_N", "N"), ("3.7_OM", "OM")], 5.0),
    ("3.8", "corner", [("3.8_N", "N")], 7.0),
    ("3.10", "old_face", [("3.10_N", "N"), ("3.10_OM_groan", "OM")], 6.0),
]


def seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def timeline():
    """Shot starts and line times (seconds), sized so each shot's lines fit with air around them."""
    t, shots = 0.0, []
    for sid, cam, lines, minimum in SHOTS:
        at, placed = LEAD, []
        for name, who in lines:
            placed.append({"file": f"{name}.wav", "who": who, "start": round(t + at, 3),
                           "seconds": round(seconds(VO / f"{name}.wav"), 3)})
            at += placed[-1]["seconds"] + GAP
        length = max(minimum, at - GAP + TAIL)
        shots.append({"id": sid, "camera": cam, "start": round(t, 3), "seconds": round(length, 3), "lines": placed})
        t += length
    return {"fps": FPS, "seconds": round(t, 3), "frames": int(round(t * FPS)), "shots": shots}


# ----------------------------------------------------------------------------------------------- build
def build():
    import bpy
    from mathutils import Euler, Quaternion, Vector
    sys.path[:0] = [str(ROOT / "scripts"), str(HERE)]
    import humans
    import scene_utils as su
    import sets
    import cast3d
    from material_library import material as M

    tl = timeline()
    frame = {s["id"]: 1 + int(round(s["start"] * FPS)) for s in tl["shots"]}
    end = tl["frames"]
    line_frame = {Path(l["file"]).stem: 1 + int(round(l["start"] * FPS)) for s in tl["shots"] for l in s["lines"]}
    su.reset_scene()
    scene = bpy.context.scene
    su.configure_render(scene, width=1920, height=1080, fps=FPS, frame_end=end, samples=48)   # 16 left speckle
    scene.eevee.volumetric_tile_size = "8"
    scene.eevee.volumetric_samples = 48
    scene.eevee.volumetric_shadow_samples = 8
    root = su.collection("V2_PREVIEW")
    C = {n: su.collection(n, root) for n in ("SET", "CAST", "PROPS", "CAMERAS")}
    lights = {}
    room = sets.chamber(C["SET"], lights)
    for name, energy in (("moon", 700), ("fill", 30), ("warm", 0), ("sun", 0), ("shadow", 0)):
        lights[name].data.energy = energy
    world = bpy.data.worlds.new("WORLD_Night")
    scene.world = world
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.002, 0.0025, 0.004, 1)
    lights["fill"].data.use_shadow = False         # a bounce stand-in: no shadow (as in the film)
    room["blanket"].hide_render = room["blanket"].hide_viewport = True     # replaced by one shaped over him
    haze = room["haze"].active_material.node_tree.nodes.get("Principled Volume")
    if haze:
        haze.inputs["Density"].default_value = 0.02                  # thinner haze: far less volumetric speckle

    # the cast
    om = humans.build(cast3d.OLD_MAN)
    MATTRESS = 0.44                                                  # the bed's top, raycast
    om.location, om.rotation_euler = (0.9, 0.38, 0.56), Euler((math.radians(-90), 0, 0))   # back on the mattress; soles clear the footboard (y 0.30)
    nar = humans.build(cast3d.NARRATOR)
    # in the corridor, square in the doorway (x -1.85..-0.95; wall 0.15 m thick, corridor face y -2.40):
    # his head and shoulders stay inside the opening, never in the wall or the jamb
    nar.location, nar.rotation_euler = (-1.58, -2.53, 0.0), Euler((0, 0, math.radians(180)))
    for rig in (om, nar):
        humans.relax_arms(rig)
        for pb in rig.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=1)

    # the door opens into the room, steadily, through 3.1-3.5 - pushed by the narrator's right hand
    door = room["door"]
    door_from, push_until = frame["3.1"] + 12, frame["3.6"] - 6
    door.rotation_euler.z = 0.0
    door.keyframe_insert("rotation_euler", frame=door_from)
    door.rotation_euler.z = math.radians(-30)
    door.keyframe_insert("rotation_euler", frame=push_until)
    for fc in _fcurves(door):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"
    opened = lambda f: min(1.0, max(0.0, (f - door_from) / (push_until - door_from)))     # 0..1 of 30 degrees

    # he leans in only as far as the opening door lets him: "I had my head in" once it is open
    def lean(f):
        x = min(1.0, max(0.0, (opened(f) - 0.15) / 0.85))
        x = x * x * (3 - 2 * x)
        return {"Hips": (0, 9 * x, 0), "LeftUpLeg": (0, -9 * x, 0), "RightUpLeg": (0, -9 * x, 0),
                "LowerBack": (0, 3 + 4 * x, 0), "Spine": (0, 2 + 3 * x, 0), "Spine1": (0, 4 * x, 0),
                "Neck1": (0, -6 * x, 0), "Head": (0, -6 * x, 0)}
    humans._layer(nar, 1, end, lean)
    humans.sway(nar, 1, end, amount=0.35, seed=11)

    # his right palm flat on the door's corridor face, at chest height and away from the handle
    @functools.lru_cache(maxsize=None)
    def door_frame(f):
        scene.frame_set(min(f, push_until))
        m = door.matrix_world
        out = (m.to_3x3() @ Vector((0, 1, 0))).normalized()             # the corridor-side normal
        along = (m.to_3x3() @ Vector((1, 0, 0))).normalized()            # hinge -> free edge
        fingers = (Vector((0, 0, 1)) + 0.35 * along).normalized()
        fingers = (fingers * math.cos(math.radians(12)) + out * math.sin(math.radians(12))).normalized()
        # (the rig's fingers curve toward the palm: tilted 12 degrees off the door, with the wrist 4.8 cm
        # out, the palm rests on it and the fingertips just clear it - measured, instead of sinking 4-5 cm in)
        return m, out, fingers

    def on_door(f):
        m, out, fingers = door_frame(f)
        return m @ Vector((0.40, 0.02, 1.25)) - fingers * 0.05 + out * 0.048    # wrist, palm on the panel
    humans.grip(nar, "Right", frame=1, curl=-0.6)                    # a flat hand: fingers straightened
    humans.reach(nar, "Right", 1, end, on_door,
                 hand=lambda f: humans.hand_frame(door_frame(f)[2], -door_frame(f)[1]))

    # the dark lantern, closed, in his left hand: held low at his side behind the door until he has his
    # head in, then raised into the gap for 3.6
    lantern, shutter, beam, glow = sets.dark_lantern(C["PROPS"])
    beam.data.energy, glow.data.energy = 0.0, 6.0                    # a closed dark lantern leaks at its seams
    spill = su.light("V2_LIGHT_Moon_Spill", C["SET"], "AREA", (-1.75, -1.6, 1.9), 15, (0.55, 0.65, 1.0),
                     target=(-1.6, -2.4, 1.55), size=0.2)           # moonlight from the room through the gap
    spill.data.use_shadow_jitter, spill.data.shadow_jitter_overblur = True, 0.0
    low, high = Vector((-1.81, -2.575, 1.02)), Vector((-1.70, -2.27, 1.29))   # lantern clear of wall and thigh
    raise_from, raise_to = frame["3.6"] - 36, frame["3.6"]

    def lantern_hand(f):
        x = min(1.0, max(0.0, (f - raise_from) / (raise_to - raise_from)))
        x = x * x * (3 - 2 * x)
        return low.lerp(high, x) + Vector((0, 0, 0.05 * math.sin(math.pi * x)))
    humans.grip(nar, "Left", frame=1)                                # palm down, fingers through the ring
    humans.reach(nar, "Left", 1, end, lantern_hand, hand=humans.hand_frame((0, 0.85, -0.5), (0, 0, -1)))
    scene.frame_set(1)
    pb = nar.pose.bones
    ring = nar.matrix_world @ ((pb["LeftFingerBase"].tail + pb["LeftHandFinger1"].tail) / 2)
    lantern.location = ring - Vector((0, 0, 0.255))
    lantern.rotation_euler = (0, 0, math.radians(180))               # the lens faces into the room
    humans.hold(nar, lantern, "Left", frame=1)

    humans.face(nar, 1, cast3d.TENSE)
    humans.eyes(nar, 1, end, mode="listening", look=(-18.0, -12.0), seed=12, head=False)
    humans.chuckle(nar, line_frame["3.3_N"] + 4, line_frame["3.3_N"] + 48)
    click = line_frame["3.6_N"] + int(seconds(VO / "3.6_N.wav") * FPS) - 6     # "...upon the tin fastening"
    thumb = nar.pose.bones["LThumb"]                                                # the thumb slips on the catch
    scene.frame_set(click - 2)
    rest_thumb = thumb.rotation_quaternion.copy()
    for at, deg in ((click - 2, 0), (click, 28), (click + 10, 8)):
        thumb.rotation_quaternion = rest_thumb @ Quaternion((1, 0, 0), math.radians(deg))
        thumb.keyframe_insert("rotation_quaternion", frame=at)
    humans.startle(nar, click + 2, strength=0.45)                                   # his own slip makes him jump
    humans.face(nar, click + 30, cast3d.TENSE)

    # the old man: asleep; a jerk at 3.4; at 3.7 the startle wakes him (eyes open, a blink, the jerk), a
    # beat to register, then he rises the way older people do (rise_in_bed), turning toward the door
    meshes = humans.face_meshes(om)
    wake = frame["3.7"] + 6
    rise = wake + 7                                                  # ~0.3 s to register the sound
    humans.face(om, 1, {"eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0}, meshes)
    humans.face(om, wake - 1, {"eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0}, meshes)
    humans.breathe(om, 1, wake, style="sleep", seed=3)
    humans.startle(om, line_frame["3.4_N"] + 6, strength=0.35, face_too=False, legs=False)
    humans.startle(om, wake, strength=1.0, until=end, legs=False)
    humans.rise_in_bed(om, rise, end, seconds=1.1, lead="Right")

    def pillow(f):                                                  # the pillow props his head; gone as he rises
        x = min(1.0, max(0.0, (f - rise) / (0.6 * 1.1 * FPS)))
        k = 1 - x * x * (3 - 2 * x)
        return {"Neck1": (0, 8 * k, 0), "Head": (0, 4 * k, 0)}
    humans._layer(om, 1, end, pillow)
    humans.face(om, wake + 8, {**cast3d.NEUTRAL, **cast3d.FEAR}, meshes)
    who = humans.lip_sync(om, VO / "3.7_OM.wav", start_frame=line_frame["3.7_OM"])
    humans.eyes(om, wake + 4, end, mode="fear", look=(-35.0, -5.0), pauses=who["pauses"], seed=21)
    humans.breathe(om, wake + 60, end, style="panic", phrases=who["phrases"], seed=4)
    groan = line_frame["3.10_OM_groan"]
    humans.tremble(om, frame["3.10"], end, strength=0.8)
    humans.lip_sync(om, VO / "3.10_OM_groan.wav", start_frame=groan)

    # the blanket over his legs and feet; it moves only as his knees draw up under it
    sheet, height = humans.bedsheet("V2_Blanket", C["SET"], room["blanket"].active_material, om,
                                    center=(0.9, 0.725), size=(1.35, 0.85), top=MATTRESS,
                                    frames=[1] + list(range(rise, rise + 40, 2)))
    # his hands: at his sides on the blanket in sleep; on the rise one elbow props and both hands push on
    # the mattress beside his hips (right first, toward the door), and stay planted as he sits listening
    def hands(side, dx, lead_in):
        rest = Vector((0.9 + dx, 1.12, height(0.9 + dx, 1.12) + 0.03))
        push = Vector((0.9 + dx * 1.25, 1.40, MATTRESS + 0.035))
        a, b = rise + lead_in, rise + lead_in + 7

        def at(f):
            x = min(1.0, max(0.0, (f - a) / (b - a)))
            x = x * x * (3 - 2 * x)
            return rest.lerp(push, x) + Vector((0, 0, 0.06 * math.sin(math.pi * x)))
        return at
    for side, dx, lead_in in (("Right", -0.24, 0), ("Left", 0.24, 3)):
        humans.reach(om, side, 1, end, hands(side, dx, lead_in),
                     hand=humans.hand_frame((0.3 * (1 if dx > 0 else -1), -1, 0), (0, 0, -1)))

    # cameras, cut on markers
    scene.frame_set(frame["3.10"] + 10)
    face_at = om.matrix_world @ om.pose.bones["Head"].head + Vector((0, -0.08, 0.0))
    rigs = {
        "door_from_room": dict(at=(0.25, 0.1, 1.25), look=(-1.45, -2.2, 1.25), lens=28, focus=(-1.6, -2.2, 1.3)),
        # his face is only visible through the slot between the jamb and the door's edge: 123-151 degrees
        # round from his head (measured on the set), so the camera sits at ~140
        "gap": dict(at=(-2.31, -1.79, 1.62), look=(-1.60, -2.36, 1.58), lens=75, focus=(-1.58, -2.34, 1.6)),
        "corner": dict(at=(2.25, -1.95, 2.7), look=(-0.2, 0.4, 0.7), lens=22, focus=(0.6, 0.2, 0.9)),
        "lantern": dict(at=(-2.35, -1.40, 1.45), look=(-1.64, -2.20, 1.36), lens=26, focus=(-1.70, -2.18, 1.25)),
        "bed": dict(at=(2.05, -0.75, 1.35), look=(0.85, 1.15, 1.0), lens=30, focus=(0.9, 1.0, 1.1)),
        "old_face": dict(at=tuple(face_at + Vector((0.18, -0.95, 0.0))), look=tuple(face_at), lens=85,
                         focus=tuple(face_at)),
    }
    cams = {}
    for name, c in rigs.items():
        cam = su.camera(f"CAM_{name}", C["CAMERAS"], c["at"], c["look"], lens=c["lens"])
        cam.data.dof.use_dof = True
        cam.data.dof.aperture_fstop = 2.8
        cam.data.dof.focus_distance = (Vector(c["focus"]) - Vector(c["at"])).length
        cams[name] = cam
    for s in tl["shots"]:
        marker = scene.timeline_markers.new(f"SHOT_{s['id']}", frame=frame[s["id"]])
        marker.camera = cams[s["camera"]]
    scene.camera = cams[tl["shots"][0]["camera"]]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "timeline.json").write_text(json.dumps(dict(tl, click=(click - 1) / FPS, wake=(wake - 1) / FPS, rise=(rise - 1) / FPS), indent=1))
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    su.save_blend(BLEND, compress=True)
    print(f"PREVIEW built: {len(tl['shots'])} shots, {end} frames ({tl['seconds']:.1f} s) -> {BLEND.name}")


def _fcurves(obj):
    """F-curves of an object's action (Blender 5 layered actions)."""
    action = obj.animation_data.action
    slot = obj.animation_data.action_slot
    for layer in action.layers:
        for strip in layer.strips:
            yield from strip.channelbag(slot).fcurves


def render(part, parts):
    """Render one share of the frames as PNGs (run several Blender processes side by side)."""
    import bpy
    scene = bpy.context.scene
    frames = list(range(scene.frame_start, scene.frame_end + 1))
    share = frames[int(part) - 1::int(parts)]
    (OUT / "frames").mkdir(parents=True, exist_ok=True)
    for f in share:
        target = OUT / "frames" / f"{f:05d}.png"
        if target.exists():
            continue
        scene.frame_set(f)
        scene.render.filepath = str(target)
        scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=True)
    print(f"PREVIEW rendered part {part}/{parts}: {len(share)} frames")


# ----------------------------------------------------------------------------------------------- sound
def soundtrack():
    """Room tone, Chopin, recorded effects and the voices -> soundtrack_raw.wav (before loudness)."""
    import subprocess
    import numpy as np
    sys.path.insert(0, str(ROOT / "scripts"))
    from mix_story import RATE, Mix, fitted, read_audio
    from story_tools import FX
    tl = json.loads((OUT / "timeline.json").read_text())
    mix = Mix(tl["seconds"] + 1)
    sfx = ROOT / "audio" / "sfx" / "freesound"
    room = read_audio(sfx / "room_tone_night_635732.mp3")
    mix.put(fitted(room, tl["seconds"] + 1, fade=1.0) * 0.12, 0.0)
    piano = read_audio(ROOT / "audio" / "music" / "chopin" / "prelude_op28_no15.mp3")
    start = int(122 * RATE)                                              # the dark middle section
    bed = piano[start:start + int((tl["seconds"] + 1) * RATE)]
    mix.put(fitted(bed, tl["seconds"] + 1, fade=2.0) * 0.16, 0.0)
    shot = {s["id"]: s for s in tl["shots"]}
    events = [("door_creak_275471.mp3", shot["3.1"]["start"] + 0.8, 0.12, 4.0),     # hinges, barely: he is
              ("door_creak_275471.mp3", shot["3.5"]["start"] + 1.5, 0.08, 3.0),     # opening it silently
              ("floorboard_creak_506661.mp3", shot["3.4"]["start"] + LEAD + 0.25, 0.45, 1.7),   # he stirs
              ("lantern_shutter_278204.mp3", tl["click"], 0.9, 0.5),                     # CLINK
              ("floorboard_creak_506662.mp3", tl["rise"], 0.6, 1.6)]                     # the bed as he rises
    for name, at, gain, longest in events:
        x = read_audio(sfx / name)
        mix.put(fitted(x, min(longest, len(x) / RATE)) * gain, at)
    for s in tl["shots"]:
        for line in s["lines"]:
            raw = VO / line["file"]
            fx = FX["narration" if line["who"] == "N" else "old"]
            done = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(raw), "-af",
                                   f"aresample=22050,{fx},aresample={RATE}", "-ac", "1", "-f", "f32le", "-"],
                                  capture_output=True, check=True).stdout
            voice = np.frombuffer(done, np.float32).copy()
            voice *= 10 ** (-18 / 20) / (np.sqrt(np.mean(voice ** 2)) + 1e-9)
            mix.put(voice, line["start"], 1.0 if line["who"] == "N" else 0.95, -0.1 if line["who"] == "OM" else 0.0)
    data = mix.buf / max(1e-6, np.max(np.abs(mix.buf))) * 0.95
    raw = OUT / "soundtrack_raw.wav"
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes((data * 32767).astype(np.int16).tobytes())
    print(f"PREVIEW soundtrack: {raw}")
    return raw


def mix():
    import subprocess
    tl = json.loads((OUT / "timeline.json").read_text())
    missing = [f for f in range(1, tl["frames"] + 1) if not (OUT / "frames" / f"{f:05d}.png").exists()]
    assert not missing, f"{len(missing)} frames not rendered yet, first {missing[0]}"
    raw = soundtrack()
    final = OUT / "the_tell_tale_heart_v2_preview.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i", str(OUT / "frames" / "%05d.png"),
                    "-i", str(raw), "-af", "loudnorm=I=-16:TP=-1.5:LRA=14", "-c:v", "libx264", "-preset", "slow",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", str(final)], check=True)
    raw.unlink()
    print(f"PREVIEW film: {final} ({tl['seconds']:.1f} s)")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    {"build": build, "render": lambda: render(*args[1:3]), "soundtrack": soundtrack, "mix": mix}[args[0]]()
