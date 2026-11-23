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
# The Visitors (preview_v4): the narrator's arc, and the officers' easy calm.
CHARM = {"mouthSmileLeft": 0.55, "mouthSmileRight": 0.5, "cheekSquintLeft": 0.3, "cheekSquintRight": 0.25,
         "eyeSquintLeft": 0.2, "eyeSquintRight": 0.2, "browInnerUp": 0.15}            # a real (Duchenne) smile
PLEASANT = {"mouthSmileLeft": 0.4, "mouthSmileRight": 0.4, "cheekSquintLeft": 0.2, "cheekSquintRight": 0.2,
            "eyeSquintLeft": 0.15, "eyeSquintRight": 0.15}
FORCED_SMILE = {"mouthSmileLeft": 0.35, "mouthSmileRight": 0.3, "mouthPressLeft": 0.3, "mouthPressRight": 0.3,
                "browInnerUp": 0.45, "eyeWideLeft": 0.3, "eyeWideRight": 0.3}     # lips only: no cheeks, worried brows
FURY = {"browDownLeft": 0.8, "browDownRight": 0.8, "noseSneerLeft": 0.5, "noseSneerRight": 0.5, "eyeWideLeft": 0.4,
        "eyeWideRight": 0.4, "mouthUpperUpLeft": 0.35, "mouthUpperUpRight": 0.35, "mouthStretchLeft": 0.3,
        "mouthStretchRight": 0.3, "jawOpen": 0.15}
HORROR = {"browInnerUp": 1.0, "browOuterUpLeft": 0.6, "browOuterUpRight": 0.6, "eyeWideLeft": 0.9,
          "eyeWideRight": 0.9, "mouthStretchLeft": 0.45, "mouthStretchRight": 0.45, "mouthFrownLeft": 0.3,
          "mouthFrownRight": 0.3, "jawOpen": 0.12}
NEUTRAL = {k: 0.0 for d in (FEAR, SLY, TENSE, CHARM, PLEASANT, FORCED_SMILE, FURY, HORROR) for k in d}

# The three officers (preview_v4). STAND-INS: the narrator re-dressed - told apart by height, hair and dark wool
# (1840s police wore no uniform: frock coats, top hats, a star badge; preview_v4 adds the hat and badge).
# When the generated officers arrive (docs/officers_cast_specs.md), set character="Hale" etc. and drop the tints.
HALE = dict(name="Hale", character="Narrator", height=1.72,                     # senior: grey
            hair_tint=(2.2, 3.0, 4.5), brow_tint=(2.2, 3.0, 4.5),
            fabrics={"shirt": ("caban", (0.1, 0.08, 0.065), 4), "trousers": ("poly_wool_herringbone", (0.16, 0.14, 0.12), 4)})
BRANDT = dict(name="Brandt", character="Narrator", height=1.80,                 # young: fair
              hair_tint=(2.6, 2.5, 2.0), brow_tint=(2.2, 2.1, 1.8),
              fabrics={"shirt": ("caban", (0.055, 0.065, 0.12), 4), "trousers": ("poly_wool_herringbone", (0.13, 0.13, 0.16), 4)})
MERCER = dict(name="Mercer", character="Narrator", height=1.78,                 # quiet: black hair
              hair_tint=(0.35, 0.35, 0.35), brow_tint=(0.4, 0.4, 0.4),
              fabrics={"shirt": ("caban", (0.07, 0.07, 0.075), 4), "trousers": ("poly_wool_herringbone", (0.12, 0.12, 0.13), 4)})
OFFICER_HEIGHTS = {s["name"]: s["height"] for s in (HALE, BRANDT, MERCER)}
