"""
Tell-Tale Heart v5: the parts the earlier previews didn't build - 00 Prologue, 01 The Eye, 02 Seven Nights,
05 Concealment, 07 Epilogue. One core here (sets, cast, timeline from the voices, cameras, cuts, lights, the shared
measured checks, stills); each part's shots and acting are an act module in stories/the_tell_tale_heart/parts/.
Everything a part writes goes in its own folder of the film (film_parts.part_dir).

    blender -b --factory-startup --python-exit-code 1 --python stories/the_tell_tale_heart/preview_v5.py -- build 01_the_eye
    blender -b blender/scenes/tell_tale_heart_v5_01_the_eye.blend --python-exit-code 1 \\
        --python stories/the_tell_tale_heart/preview_v5.py -- check 01_the_eye | stills 01_the_eye 1.2,1.4@3
    blender -b --factory-startup --python-exit-code 1 --python stories/the_tell_tale_heart/preview_v5.py -- selfcheck
    python3 stories/the_tell_tale_heart/preview_v5.py lines        (writes preview_v5/lines.json from film.py)
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(HERE)]

FPS = 24
VO = ROOT / "audio" / "voiceovers" / "the_tell_tale_heart_v5"
LINES = HERE / "preview_v5" / "lines.json"
SCENES = ROOT / "blender" / "scenes"
# part key -> its act module in stories/the_tell_tale_heart/parts/ (a module object stands in for a test part)
PART_MODULES = {"00_prologue": "p00_prologue", "01_the_eye": "p01_the_eye", "02_seven_nights": "p02_seven_nights",
                "05_concealment": "p05_concealment", "07_epilogue": "p07_epilogue"}
WHO = {"N": "Narrator", "NS": "Narrator", "OM": "OldMan"}          # voice code -> rig (N is the voice-over)
ON_SCREEN = ("NS", "OM")
REFS = {"N": ("audio/voice_refs/narrator.wav", 0.5), "NS": ("audio/voice_refs/narrator.wav", 0.6),
        "OM": ("audio/voice_refs/old_man.wav", 0.6)}
VOICED_SHOTS = [f"{q}.{i}" for q, n in ((0, 5), (1, 9), (2, 9), (4, 6), (6, 3)) for i in range(1, n + 1)] + \
               [f"3.{i}" for i in range(11, 22)]                  # parts 00, 01, 02, 05, 07 and 04 (the attack)


def voice(key):
    return VO / f"{key}.wav"


def write_lines():
    """preview_v5/lines.json: Chatterbox jobs for every line of the voiced shots (film.SHOTS, Poe's text), and
    3.2's narration for part 03 (into v2's voice folder, under v2's naming)."""
    import film
    jobs = []
    for s in film.SHOTS:
        if s["id"] not in VOICED_SHOTS and s["id"] != "3.2":
            continue
        for k, (who, text, _) in enumerate(s["lines"]):
            ref, exaggeration = REFS[who]
            out = (f"audio/voiceovers/the_tell_tale_heart_v2/{s['id']}_{who}.wav" if s["id"] == "3.2"
                   else str(voice(f"{s['id']}_{k}_{who}").relative_to(ROOT)))
            jobs.append(dict(text=text, ref=ref, exaggeration=exaggeration, cfg=0.5, out=out))
    LINES.parent.mkdir(parents=True, exist_ok=True)
    LINES.write_text(json.dumps(jobs, indent=1, ensure_ascii=False))
    print(f"preview_v5 lines: {len(jobs)} -> {LINES}")
    return LINES


def module(part):
    import importlib
    m = PART_MODULES[part]
    return importlib.import_module(f"parts.{m}") if isinstance(m, str) else m


def timeline(part):
    """The part's shots laid end to end, each as long as its lines (preview_v3.timeline), from its voices."""
    import preview_v3 as v3
    mod = module(part)
    return v3.timeline(mod.SHOTS, getattr(mod, "VOICE", voice))


def _out(part, out_dir=None):
    import film_parts
    return Path(out_dir) if out_dir else film_parts.part_dir(part)


def _blend(part, out_dir=None):
    return Path(out_dir) / f"{part}.blend" if out_dir else SCENES / f"tell_tale_heart_v5_{part}.blend"


def build(part, out_dir=None):
    """The part's scene: its sets, cast, cameras and per-shot lights; then its act; cuts on the shot markers;
    saved with its timeline (and the act's sound marks) in the part's folder. -> the .blend path."""
    import bpy
    from mathutils import Vector
    import humans
    import scene_utils as su
    import sets
    import cast3d
    mod = module(part)
    tl = timeline(part)
    start = {s["id"]: 1 + int(round(s["start"] * FPS)) for s in tl["shots"]}
    end = tl["frames"]

    def T(sid, sec=0.0):
        return start[sid] + int(round(sec * FPS))
    su.reset_scene()
    scene = bpy.context.scene
    su.configure_render(scene, width=1920, height=1080, fps=FPS, frame_end=end, samples=32)
    root = su.collection("V5_PART")
    C = {n: su.collection(n, root) for n in ("SET", "CAST", "PROPS", "CAMERAS")}
    lights, set_out = {}, {}
    for name in mod.SETS:
        set_out[name] = getattr(sets, name)(C["SET"], lights) or {}
    world = bpy.data.worlds.new("WORLD_Night")
    scene.world = world
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.002, 0.0025, 0.004, 1)
    specs = {"Narrator": cast3d.NARRATOR, "OldMan": cast3d.OLD_MAN}
    layer = bpy.context.view_layer
    layer.active_layer_collection = layer.layer_collection.children["V5_PART"].children["CAST"]
    rigs = {n: humans.build(specs[n]) for n in mod.CAST}
    for rig in rigs.values():
        humans.relax_arms(rig)
        for pb in rig.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=1)
    stand = {pb.name: pb.rotation_quaternion.copy() for pb in rigs[mod.CAST[0]].pose.bones} if rigs else {}
    cams = {}
    for name, (at, look, lens) in mod.CAMERAS.items():
        cam = su.camera(f"CAM_{name}", C["CAMERAS"], at, look, lens=lens)
        cam.data.dof.focus_distance = (Vector(look) - Vector(at)).length
        cams[name] = cam
    ids = [s["id"] for s in tl["shots"]]
    for light in lights.values():
        light.data.energy = 0
    for i, sid in enumerate(ids):                    # each shot's light holds and changes at the cut
        last = T(ids[i + 1]) - 1 if i + 1 < len(ids) else end
        for name, light in lights.items():
            light.data.energy = mod.LIGHTS.get(sid, {}).get(name, 0)
            for f in (T(sid), last):
                light.data.keyframe_insert("energy", frame=f)
    ctx = dict(bpy=bpy, humans=humans, su=su, sets=sets, cast3d=cast3d, tl=tl, T=T, start=start, end=end,
               rigs=rigs, props={}, cams=cams, lights=lights, set=set_out, C=C, marks={}, held=[], cache={},
               stand=stand, part=part)
    mod.act(ctx)
    for sid, sec, cam in list(mod.CUTS) + ctx.get("extra_cuts", []):
        scene.timeline_markers.new(f"SHOT_{sid}_{cam}_{sec:.1f}", frame=T(sid, sec)).camera = cams[cam]
    scene.camera = cams[mod.CUTS[0][2]]
    scene["v5_held"] = json.dumps(ctx["held"])
    out = _out(part, out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "timeline.json").write_text(json.dumps(
        dict(tl, marks={k: (v - 1) / FPS for k, v in ctx["marks"].items()}), indent=1))
    blend = _blend(part, out_dir)
    blend.parent.mkdir(parents=True, exist_ok=True)
    su.save_blend(blend, compress=True)
    print(f"V5 built {part}: {len(ids)} shots, {end} frames ({tl['seconds']:.1f} s) -> {blend}")
    return blend


def _spans(part, out_dir=None):
    tl = json.loads((_out(part, out_dir) / "timeline.json").read_text())
    return {s["id"]: (1 + int(round(s["start"] * FPS)), int(round((s["start"] + s["seconds"]) * FPS)))
            for s in tl["shots"]}, tl


def check(part, shots=None, out_dir=None, step=4):
    """The shared measured checks (preview_v4.run_checks) on this part's scene, with its cast and lines."""
    import bpy
    import preview_v3 as v3
    import preview_v4 as v4
    spans, tl = _spans(part, out_dir)
    cast = [n for n in ("Narrator", "OldMan") if n in bpy.data.objects]
    animated = any(len(fc.keyframe_points) > 1 for n in cast for fc in v3._fcurves(bpy.data.objects[n])
                   if fc.data_path.startswith("pose.bones"))
    on_camera = set(getattr(module(part), "ON_CAMERA", ()))         # voice-over spoken to us on screen (the void)
    spoken = [l for s in tl["shots"] for l in s["lines"] if l["who"] in ON_SCREEN or l["line"] in on_camera]
    import contextlib
    import io
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            v4.run_checks("V5", cast, ("V5_Chair_", "VO_Chair", "NR_Chair"),
                          json.loads(bpy.context.scene.get("v5_held", "[]")), spans, shots, spoken, WHO, step=step,
                          animated=animated)
    finally:
        print(buf.getvalue(), end="")
        (_out(part, out_dir) / "check.txt").write_text(buf.getvalue())


def stills(part, shots=None, out_dir=None):
    """One 480p frame per shot (or "<shot>@<seconds>") -> the part's stills/ folder."""
    import bpy
    scene = bpy.context.scene
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = 854, 480, 100
    scene.eevee.taa_render_samples = 16
    folder = _out(part, out_dir) / "stills"
    folder.mkdir(parents=True, exist_ok=True)
    spans, _ = _spans(part, out_dir)
    for want in shots or list(spans):
        sid, _, sec = want.partition("@")
        f0, f1 = spans[sid]
        scene.frame_set(f0 + int(float(sec) * FPS) if sec else (f0 + f1) // 2)
        r.filepath = str(folder / f"{want}.png")
        bpy.ops.render.render(write_still=True)
    print("V5 stills ->", folder)


def selfcheck():
    """A minimal part (one 3 s void shot; the narrator seated, saying one existing line) builds, saves, times its
    shot from the voice and passes the shared checks (lips move, nobody frozen)."""
    import tempfile
    import types
    import bpy
    import preview_v4 as v4
    tmp = Path(tempfile.mkdtemp(prefix="v5_selfcheck_"))

    def act(ctx):
        rig, chair = ctx["rigs"]["Narrator"], bpy.data.objects["VO_Chair"]
        v4._sit(ctx, rig, chair, ctx["T"]("X.1"), ["X.1"])
        tl, a, b = ctx["tl"], ctx["T"]("X.1"), ctx["end"]
        lines = [l for s in tl["shots"] for l in s["lines"]]
        v4._converse(ctx, lines, a, b, {"Narrator": 0.4}, lambda n, f: ((0.0, -5.0), "thinking"), who=WHO)
        ctx["humans"].breathe(rig, a, b, style="calm", seed=3)
    mod = types.SimpleNamespace(
        SHOTS=[("X.1", [("5.4_1_NS", "NS")], 3.0)], VOICE=lambda key: v4.VO / f"{key}.wav",
        CAMERAS={"void": ((100.0, 1.7, 1.3), (100.0, 0.0, 1.1), 50)}, CUTS=[("X.1", 0.0, "void")],
        LIGHTS={"X.1": {"vo_top": 400, "vo_rim": 40}}, SETS=["void"], CAST=["Narrator"], act=act)
    PART_MODULES["selftest"] = mod
    try:
        blend = build("selftest", out_dir=tmp)
        assert blend.exists(), blend
        tl = json.loads((tmp / "timeline.json").read_text())
        assert 3.0 <= tl["seconds"] <= 3.6, tl["seconds"]
        check("selftest", out_dir=tmp)
        print(f"preview_v5 selfcheck OK: {tl['seconds']} s, blend {blend.stat().st_size // 1024} KB, check passed")
    finally:
        PART_MODULES.pop("selftest", None)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    {"selfcheck": selfcheck, "lines": write_lines,
     "build": lambda: build(args[1]), "check": lambda: check(args[1]),
     "stills": lambda: stills(args[1], args[2].split(",") if len(args) > 2 else None)}[args[0]]()
