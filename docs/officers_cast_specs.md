# The three officers: specs for the character generator

The Visitors (shots 5.1–5.15, `stories/the_tell_tale_heart/preview_v4.py`) needs three police officers.
The scene runs now with **stand-ins**: the narrator re-dressed, told apart by height, hair colour, dark wool,
a top hat and a copper star. These specs are for making the real ones with the same generator as `OldMan`
and `Narrator`. They use the format of `assets/characters/*/params.json`, so they can go into
`_work\cast\<Name>.json`.

**Period:** Philadelphia, 1843. US police wore no uniforms until the 1850s, so these are plain clothes:
- dark wool frock coats, waistcoats and cravats;
- top hats;
- dark leather shoes.

`preview_v4.py` adds the copper star badge and the hat as props. If the generator can't make a frock coat, a
dark long-sleeved shirt and trousers work; the scene tints them.

## Hale: the senior officer (speaks first at the door)
50s, heavy-set, weathered, grey hair with grey side-whiskers. Calm, courteous, used to authority.

```json
{
  "sex": "male",
  "face": {"Face_Asian": 0.0, "Face_Black": 0.05, "Face_Caucasian": 1.3},
  "ethnicity": "Caucasian",
  "build": "heavy",
  "body": {"Body_Muscular": 0.25, "Body_Skinny": 0.0, "Body_Overweight": 0.45},
  "prop": {"leg": 1.0, "arm": 1.0, "torso": 1.03, "neck": 1.05, "head": 1.02, "shoulder": 1.04, "hips": 1.04,
           "hand": 1.02, "foot": 1.0},
  "height": 1.72,
  "facep": {"nose_proj": 0.002, "nose_len": 0.002, "nose_w": 0.002, "bridge": 0.001, "chin_fwd": 0.0,
            "chin_down": 0.002, "jaw_w": 0.003, "cheek_w": 0.002, "cheek_fwd": 0.0, "brow": 0.002, "lips": -0.001,
            "mouth_w": 0.001, "forehead": 0.0, "occiput": 0.0, "head_w": 0.001, "crown": 0.0, "ear_out": 0.001},
  "seed": 5101,
  "slot": null,
  "skin_eth": "Caucasian",
  "skin": {"value": 0.9, "sat": 1.05, "hue": 0.0},
  "eye_color": 2,
  "hair_color": "grey",
  "hair": "short",
  "beard": "sideburns",
  "clothes": {"outfit": "shirt_trousers", "pieces": ["md_shirt", "md_pants", "mh:shoes01"],
              "shirt": "dark_brown", "pants": "dark_brown", "tie": "black", "tint": "dark_brown", "tee": "white",
              "shoes": "black"}
}
```

## Brandt: the young officer ("Cold night for it, eh?")
Early 20s, tall and slim, clean-shaven, fair hair, an open, friendly face.

```json
{
  "sex": "male",
  "face": {"Face_Asian": 0.0, "Face_Black": 0.0, "Face_Caucasian": 1.4},
  "ethnicity": "Caucasian",
  "build": "slim",
  "body": {"Body_Muscular": 0.3, "Body_Skinny": 0.5, "Body_Overweight": 0.0},
  "prop": {"leg": 1.02, "arm": 1.0, "torso": 1.0, "neck": 1.0, "head": 0.99, "shoulder": 1.0, "hips": 0.98,
           "hand": 1.0, "foot": 1.0},
  "height": 1.80,
  "facep": {"nose_proj": 0.0, "nose_len": -0.001, "nose_w": -0.001, "bridge": 0.0, "chin_fwd": 0.001,
            "chin_down": 0.0, "jaw_w": 0.0, "cheek_w": -0.001, "cheek_fwd": 0.001, "brow": 0.0, "lips": 0.001,
            "mouth_w": 0.0, "forehead": 0.0, "occiput": 0.0, "head_w": -0.001, "crown": 0.0, "ear_out": 0.0},
  "seed": 5102,
  "slot": null,
  "skin_eth": "Caucasian",
  "skin": {"value": 1.0, "sat": 0.95, "hue": 0.0},
  "eye_color": 0,
  "hair_color": "blonde",
  "hair": "short",
  "beard": "none",
  "clothes": {"outfit": "shirt_trousers", "pieces": ["md_shirt", "md_pants", "mh:shoes01"],
              "shirt": "navy", "pants": "navy", "tie": "black", "tint": "navy", "tee": "white", "shoes": "black"}
}
```

## Mercer: the quiet officer ("Colder than a churchyard.")
40s, lean, a narrow face, black hair and a dark moustache. Says little and watches.

```json
{
  "sex": "male",
  "face": {"Face_Asian": 0.0, "Face_Black": 0.1, "Face_Caucasian": 1.2},
  "ethnicity": "Caucasian",
  "build": "lean",
  "body": {"Body_Muscular": 0.15, "Body_Skinny": 0.6, "Body_Overweight": 0.0},
  "prop": {"leg": 1.01, "arm": 1.01, "torso": 1.0, "neck": 1.02, "head": 1.0, "shoulder": 0.98, "hips": 0.97,
           "hand": 1.0, "foot": 1.0},
  "height": 1.78,
  "facep": {"nose_proj": 0.002, "nose_len": 0.002, "nose_w": -0.001, "bridge": 0.002, "chin_fwd": 0.001,
            "chin_down": 0.001, "jaw_w": -0.002, "cheek_w": -0.003, "cheek_fwd": -0.001, "brow": 0.002, "lips": -0.001,
            "mouth_w": -0.001, "forehead": 0.0, "occiput": 0.0, "head_w": -0.002, "crown": 0.0, "ear_out": 0.0},
  "seed": 5103,
  "slot": null,
  "skin_eth": "Caucasian",
  "skin": {"value": 0.94, "sat": 1.0, "hue": 0.0},
  "eye_color": 1,
  "hair_color": "black",
  "hair": "short",
  "beard": "moustache",
  "clothes": {"outfit": "shirt_trousers", "pieces": ["md_shirt", "md_pants", "mh:shoes01"],
              "shirt": "charcoal", "pants": "charcoal", "tie": "black", "tint": "charcoal", "tee": "white",
              "shoes": "black"}
}
```

Option names such as `"build"`, `"hair_color"`, `"beard"` and the colours follow what the existing two use.
If the generator doesn't know a value (`"sideburns"`, `"grey"`, `"navy"` …), use its nearest one.

## When they are made
1. Copy each output folder (`.blend`, `params.json`, `textures\`, `previews\`) to `assets/characters/Hale`,
   `Brandt` and `Mercer`.
2. In `stories/the_tell_tale_heart/cast3d.py`, set `character="Hale"` (and so on). Remove that officer's
   `height`, `hair_tint` and `brow_tint`; keep `fabrics` only if the clothes need tinting.
3. Rebuild the scene: `blender -b --factory-startup --python stories/the_tell_tale_heart/preview_v4.py -- build`.

Texture paths: `humans.build()` now finds a character's textures in its own `textures\` folder, even when
the `.blend` was saved with the paths of the machine that made it.
