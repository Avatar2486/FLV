"""Part 07, the Epilogue (6.1-6.3): black and one heartbeat; the narrator in the void, close, whispering "Hearken.";
the credits, fading out. (design: docs/superpowers/specs/2026-11-24-tell-tale-heart-whole-film-design.md)"""
VOID_X = 100.0                         # sets.SET_X["void"]
CREDITS_AT = (170.0, 0.0, -40.0)       # on the title stage's x, well below the title
CREDITS = ("THE TELL-TALE HEART\n\n"
           "Based on 'The Tell-Tale Heart' by Edgar Allan Poe (1843)\n\n"
           "An FLV film\n\n"
           "Motion: The 100STYLE Dataset – Ian Mason (CC BY 4.0);\n"
           "CMU Graphics Lab Motion Capture Database\n"
           "(mocap.cs.cmu.edu, created with funding from NSF EIA-0196217)\n"
           "Music: Frédéric Chopin, recordings from Musopen (CC0)\n"
           "Sound: Freesound (CC0)\n"
           "Voices: Chatterbox (Resemble AI, MIT)\n"
           "Lip sync: Wav2ARKit\n"
           "Props and textures: Poly Haven (CC0)    Made with Blender")

SHOTS = [("6.1", [], 3.0), ("6.2", [("6.2_0_N", "N")], 5.0), ("6.3", [], 9.0)]
ON_CAMERA = ("6.2_0_N",)
SETS = ["void"]
CAST = ["Narrator"]
CAMERAS = {
    "black": ((VOID_X, 30.0, 1.5), (VOID_X, 40.0, 1.5), 50),
    "cu": ((VOID_X, 1.05, 1.21), (VOID_X, 0.0, 1.17), 85),
    "credits": ((CREDITS_AT[0], -7.2, CREDITS_AT[2]), CREDITS_AT, 50),
}
CUTS = [("6.1", 0.0, "black"), ("6.2", 0.0, "cu"), ("6.3", 0.0, "credits")]
LIGHTS = {"6.2": {"vo_top": 450, "vo_rim": 45}}


def act(ctx):
    bpy, humans, cast3d, sets = ctx["bpy"], ctx["humans"], ctx["cast3d"], ctx["sets"]
    import preview_v4 as v4
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    T, tl, cams, end = ctx["T"], ctx["tl"], ctx["cams"], ctx["end"]
    scene = bpy.context.scene
    nar = ctx["rigs"]["Narrator"]
    # ---- 6.2: in the void, close; he leans to us and whispers
    a, b = T("6.2"), T("6.3") - 1
    v4._sit(ctx, nar, bpy.data.objects["VO_Chair"], 1, ["6.1", "6.2", "6.3"])
    lens = Vector(CAMERAS["cu"][0])
    lines = [l for s in tl["shots"] for l in s["lines"] if l["line"] in ON_CAMERA]
    events, phrases = v4._converse(ctx, lines, a, b, {"Narrator": 0.2}, lambda n, f: (tuple(lens), "talking"),
                                   seated=True, who={"N": "Narrator"})
    humans.breathe(nar, a, b, style="calm", phrases=[p for e in events for p in phrases[e]], seed=61)
    humans.face(nar, a, {**cast3d.NEUTRAL, **cast3d.SLY, "browInnerUp": 0.2})
    humans._layer(nar, a, b, lambda f: {"LowerBack": (0, 6 * min(1.0, (f - a) / 30), 0),
                                        "Spine": (0, 4 * min(1.0, (f - a) / 30), 0)})     # leaning in to us
    ctx["su"].animate_camera(cams["cu"], [(a, CAMERAS["cu"][0], CAMERAS["cu"][1]),
                                          (b, (VOID_X, 0.85, 1.2), (VOID_X, 0.0, 1.17))])
    # ---- 6.3: the credits, fading out over their last 1.5 s
    text = sets.text("V5_Credits", ctx["C"]["SET"], CREDITS, CREDITS_AT, 0.11)
    text.data.align_y = "CENTER"
    for f, ev in ((1, 0.0), (end - 36, 0.0), (end, -12.0)):
        scene.view_settings.exposure = ev
        scene.view_settings.keyframe_insert("exposure", frame=f)
    scene.frame_set(T("6.3"))
    bpy.context.view_layer.update()
    corners = [text.matrix_world @ Vector(c) for c in text.bound_box]
    seen = [world_to_camera_view(scene, cams["credits"], c) for c in corners]
    assert all(0.02 < p.x < 0.98 and 0.02 < p.y < 0.98 and p.z > 0 for p in seen), \
        f"the credits leave the frame: {[tuple(round(v, 2) for v in p) for p in seen]}"
