"""
The Tell-Tale Heart: realistic (MPFB / MakeHuman) characters, built by scripts/humans.py.
Ages are MakeHuman sliders (0.5 = 25 years, 1.0 = 90). Fabrics are Poly Haven textures, greyed then tinted.
"""

OLD_MAN = dict(name="OldMan", age=0.97, weight=0.22, muscle=0.2, height=0.42, proportions=0.4,
               skin="old_caucasian_male", hair="short02", hair_material="bogdan666_short_02_gray",
               eyebrows="eyebrow001", eyes=("grey", "lightblue"),
               film_eye="left",                       # "a pale blue eye, with a film over it"
               clothes=[("maciekg_wizard_robe", "rough_linen", (1.2, 1.15, 1.02))])      # linen nightshirt

NARRATOR = dict(name="Narrator", age=0.6, weight=0.25, muscle=0.4, height=0.55, proportions=0.6,
                skin="middleage_caucasian_male", hair="short02", hair_material="bogdan666_short_02_brown",
                hair_tint=(0.32, 0.24, 0.2), eyebrows="eyebrow001", brow_tint=(0.35, 0.28, 0.24),
                eyes=("brownlight", "brownlight"),
                clothes=[("shoes01", None, None),                                      # inner to outer
                         ("toigo_wool_pants", "poly_wool_herringbone", (0.32, 0.29, 0.26)),
                         ("elvs_male_shirt_untucked_bd1", "stretch_poplin", (1.25, 1.2, 1.1))])

# Expressions as ARKit face-unit weights (scripts/humans.py: face()).
FEAR = {"browInnerUp": 0.85, "browOuterUpLeft": 0.4, "browOuterUpRight": 0.4, "eyeWideLeft": 0.6,
        "eyeWideRight": 0.6, "mouthStretchLeft": 0.25, "mouthStretchRight": 0.25}
SLY = {"browDownLeft": 0.35, "browDownRight": 0.35, "eyeSquintLeft": 0.3, "eyeSquintRight": 0.3,
       "mouthSmileLeft": 0.45, "mouthSmileRight": 0.35, "cheekSquintLeft": 0.2}
TENSE = {"browDownLeft": 0.45, "browDownRight": 0.45, "eyeWideLeft": 0.25, "eyeWideRight": 0.25,
         "mouthPressLeft": 0.3, "mouthPressRight": 0.3, "noseSneerLeft": 0.15}
NEUTRAL = {k: 0.0 for d in (FEAR, SLY, TENSE) for k in d}
