"""Part 00, the Prologue (0.1-0.5, T): a heartbeat in the dark; dust in a cold ray over the boards; the narrator in a
chair in a black void, speaking to us under a hard top light, his eyes darting to each sound; a thin smile; the
title. (production_plan.md, design: docs/superpowers/specs/2026-11-24-tell-tale-heart-whole-film-design.md)"""
import math
import random

VOID_X = 100.0                         # sets.SET_X["void"]; the chair faces +y
TITLE_X = 170.0                        # sets.SET_X["title"]
SEAM = (-0.72, -0.09, 0.0)             # a seam between the loose planks, by where his chair will stand

SHOTS = [("0.1", [], 3.0), ("0.2", [("0.2_0_N", "N")], 7.0), ("0.3", [("0.3_0_N", "N")], 10.0),
         ("0.4", [("0.4_0_N", "N")], 7.0), ("0.5", [("0.5_0_N", "N")], 8.0), ("T", [], 5.0)]
ON_CAMERA = ("0.3_0_N", "0.4_0_N", "0.5_0_N")       # Poe's narration, spoken to us in the void (lips move)
SETS = ["chamber", "void", "title_stage"]
CAST = ["Narrator"]
CAMERAS = {
    "black": ((VOID_X, 30.0, 1.5), (VOID_X, 40.0, 1.5), 50),
    "seam": ((SEAM[0] + 0.22, SEAM[1] - 0.20, 0.18), SEAM, 100),      # looking down along the seam
    "void": ((VOID_X, 1.95, 1.25), (VOID_X, 0.0, 1.12), 50),
    "eyes": ((VOID_X, 0.55, 1.2), (VOID_X, 0.0, 1.18), 85),
    "void_cu": ((VOID_X, 1.6, 1.24), (VOID_X, 0.0, 1.15), 50),
    "title": ((TITLE_X, -5.2, -0.12), (TITLE_X, 0.0, -0.12), 50),     # the whole title in frame
}
CUTS = [("0.1", 0.0, "black"), ("0.2", 0.0, "seam"), ("0.3", 0.0, "void"), ("0.4", 0.0, "eyes"),
        ("0.5", 0.0, "void_cu"), ("T", 0.0, "title")]
LIGHTS = {"0.2": {"fill": 3}, "0.3": {"vo_top": 450, "vo_rim": 45}, "0.4": {"vo_top": 450, "vo_rim": 45},
          "0.5": {"vo_top": 450, "vo_rim": 45}}


def act(ctx):
    bpy, humans, cast3d, su = ctx["bpy"], ctx["humans"], ctx["cast3d"], ctx["su"]
    import preview_v4 as v4
    from mathutils import Vector
    from material_library import material as M
    T, tl, cams = ctx["T"], ctx["tl"], ctx["cams"]
    scene = bpy.context.scene
    nar = ctx["rigs"]["Narrator"]
    face = lambda f, e: humans.face(nar, f, {**cast3d.NEUTRAL, **e})
    # ---- the fades at the part's edges, rendered in its own frames: in to 0.2, out of the title
    for f, ev in ((1, -12.0), (T("0.2") - 1, -12.0), (T("0.2"), -6.0), (T("0.2", 0.9), 0.0),
                  (ctx["end"] - 24, 0.0), (ctx["end"], -12.0)):
        scene.view_settings.exposure = ev
        scene.view_settings.keyframe_insert("exposure", frame=f)
    # ---- 0.2: one cold ray through the shutter gap rakes the boards; dust drifts in it (air moves dust: no hand)
    ray = su.light("V5_Ray", ctx["C"]["SET"], "SPOT", (2.3, -0.15, 1.5), 0, (0.62, 0.74, 1.0), target=SEAM,
                   spot_size=math.radians(5), spot_blend=0.25, shadow_soft_size=0.01)
    for f, e in ((1, 0), (T("0.2") - 1, 0), (T("0.2"), 2600), (T("0.3") - 1, 2600), (T("0.3"), 0)):
        ray.data.energy = e
        ray.data.keyframe_insert("energy", frame=f)
    rng = random.Random(2)
    a2, b2 = T("0.2"), T("0.3") - 1
    to_ray = (Vector(SEAM) - Vector((2.3, -0.15, 1.5))).normalized()
    lens = Vector(CAMERAS["seam"][0])
    for i in range(60):                               # real dust: a fifth of a millimetre to a third
        speck = su.sphere(f"V5_Dust_{i}", ctx["C"]["PROPS"], M("MAT_Plaster_Old"), 0.00015 + 0.0002 * rng.random(),
                          segments=6)
        base = Vector(SEAM) - to_ray * rng.uniform(0.02, 0.45) + Vector((rng.uniform(-0.03, 0.03),) * 2 + (0,))
        if (base - lens).length < 0.15:               # nothing drifts against the lens
            base += (base - lens).normalized() * 0.15
        drift = Vector((rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02), rng.uniform(-0.012, 0.004)))
        ph = rng.uniform(0, 6.28)
        for f in range(a2, b2 + 1, 4):
            u = (f - a2) / 24
            speck.location = base + drift * u + Vector((0.004 * math.sin(0.9 * u + ph), 0, 0.003 * math.sin(0.6 * u + ph)))
            speck.keyframe_insert("location", frame=f)
    seam_cam = cams["seam"]
    su.animate_camera(seam_cam, [(a2, CAMERAS["seam"][0], SEAM),
                                 (b2, (SEAM[0] + 0.12, SEAM[1] - 0.11, 0.12), (SEAM[0] - 0.1, SEAM[1] + 0.01, 0.0))])
    seam_cam.data.dof.use_dof, seam_cam.data.dof.aperture_fstop = True, 4.0
    seam_cam.data.dof.focus_distance = (lens - Vector(SEAM)).length          # the seam sharp
    # ---- 0.3-0.5: the void. He sits, speaks to us; his eyes go to each sound in 0.4; a thin smile in 0.5
    chair = bpy.data.objects["VO_Chair"]
    a3, end = T("0.3"), T("T") - 1
    v4._sit(ctx, nar, chair, 1, ["0.1", "0.2", "0.3", "0.4", "0.5", "T"])      # seated from the start (off camera)
    lens_at = {n: Vector(CAMERAS[n][0]) for n in ("void", "eyes", "void_cu")}
    sounds = [(T("0.4", 0.8), (35.0, 2.0)), (T("0.4", 2.6), (-35.0, -4.0)), (T("0.4", 4.2), (6.0, 28.0))]

    def idle(n, f):
        for at, look in sounds:                       # cricket left, mouse right, wind above: he looks
            if at <= f < at + 22:
                return look, "thinking"
        cam = "void" if f < T("0.4") else "eyes" if f < T("0.5") else "void_cu"
        return tuple(lens_at[cam]), "talking"         # otherwise at us (into the lens)
    lines = [l for s in tl["shots"] for l in s["lines"] if l["line"] in ON_CAMERA]
    events, phrases = v4._converse(ctx, lines, a3, end, {"Narrator": 0.4}, idle, seated=True,
                                   who={"N": "Narrator"})
    mine = [p for e in events for p in phrases[e]]
    humans.breathe(nar, a3, end, style="calm", phrases=mine, seed=5)
    face(a3, cast3d.SLY)
    face(T("0.4"), {"browInnerUp": 0.25, "eyeWideLeft": 0.2, "eyeWideRight": 0.2})     # listening, acute
    face(T("0.5"), cast3d.SLY)
    face(T("0.5", 5.6), {**cast3d.SLY, "mouthSmileLeft": 0.32, "mouthSmileRight": 0.18})  # a thin smile
    su.animate_camera(cams["void"], [(a3, CAMERAS["void"][0], CAMERAS["void"][1]),
                                     (T("0.4") - 1, (VOID_X, 1.55, 1.24), CAMERAS["void"][1])])
    su.animate_camera(cams["void_cu"], [(T("0.5"), CAMERAS["void_cu"][0], CAMERAS["void_cu"][1]),
                                        (end, (VOID_X, 0.85, 1.2), (VOID_X, 0.0, 1.16))])
    scene.frame_set(T("0.4"))
    eyes = (nar.matrix_world @ nar.pose.bones["LeftEye"].head + nar.matrix_world @ nar.pose.bones["RightEye"].head) / 2
    su.animate_camera(cams["eyes"], [(T("0.4"), tuple(eyes + Vector((0, 0.42, 0.0))), tuple(eyes))])
    for name in ("eyes",):
        cams[name].data.dof.use_dof = False
    ctx["marks"]["0.4/cricket"], ctx["marks"]["0.4/mouse"], ctx["marks"]["0.4/wind_gust"] = (s[0] for s in sounds)
