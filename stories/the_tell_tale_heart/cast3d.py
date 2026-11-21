"""
The Tell-Tale Heart: the cast, our own generated characters (assets/characters/<Name>), loaded by scripts/humans.py.
Both were made by the Generated_Characters pipeline from a cast spec (fixed choices instead of random ones):
  OldMan   - slim, 1.68 m, gaunt face, pale and blotchy aged skin, silver hair, white stubble, grey-blue eyes,
             a long-sleeved nightshirt, barefoot
  Narrator - average build, 1.76 m, brown hair, brown eyes, white shirt, high-waisted trousers, leather shoes
Fabrics are Poly Haven textures (assets/textures/polyhaven), greyed then tinted: (texture, tint, scale).
"""

OLD_MAN = dict(name="OldMan", character="OldMan",
               film_eye="left",                       # "a pale blue eye, with a film over it"
               brow_tint=(0.6, 0.6, 0.6), beard_tint=(0.55, 0.55, 0.55),   # grey, not glowing white, in moonlight
               fabrics={"nightshirt": ("rough_linen", (1.2, 1.15, 1.02), 5)})          # linen nightshirt

NARRATOR = dict(name="Narrator", character="Narrator",
                fabrics={"trousers": ("poly_wool_herringbone", (0.32, 0.29, 0.26), 4),
                         "shirt": ("stretch_poplin", (1.25, 1.2, 1.1), 4)})

# Expressions as ARKit face-unit weights (scripts/humans.py: face()).
FEAR = {"browInnerUp": 0.85, "browOuterUpLeft": 0.4, "browOuterUpRight": 0.4, "eyeWideLeft": 0.6,
        "eyeWideRight": 0.6, "mouthStretchLeft": 0.25, "mouthStretchRight": 0.25}
SLY = {"browDownLeft": 0.35, "browDownRight": 0.35, "eyeSquintLeft": 0.3, "eyeSquintRight": 0.3,
       "mouthSmileLeft": 0.45, "mouthSmileRight": 0.35, "cheekSquintLeft": 0.2}
TENSE = {"browDownLeft": 0.45, "browDownRight": 0.45, "eyeWideLeft": 0.25, "eyeWideRight": 0.25,
         "mouthPressLeft": 0.3, "mouthPressRight": 0.3, "noseSneerLeft": 0.15}
NEUTRAL = {k: 0.0 for d in (FEAR, SLY, TENSE) for k in d}
