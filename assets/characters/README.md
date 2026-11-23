# Characters

Our own generated characters, loaded into scenes by `scripts/humans.py` (`humans.build(spec)`), cast in
`stories/the_tell_tale_heart/cast3d.py`. They replace the MPFB / MakeHuman people the films used before.

| Folder | Who | Look |
|---|---|---|
| `OldMan/` | the old man | slim, 1.68 m, gaunt face, pale blotchy aged skin, silver hair, white stubble, grey-blue eyes (the film makes his left eye milky), long-sleeved nightshirt, barefoot |
| `Narrator/` | the narrator | average build, 1.76 m, brown hair, brown eyes, white shirt, high-waisted trousers, leather shoes |

Each folder: `<Name>.blend` (rig + meshes; its textures live in `textures/`, and `humans.build()` points the materials there even when the .blend was saved with another machine's paths), `params.json` (every choice
used to make it) and `previews/` (`face.png`, `q34.png`, `expressions.png`: neutral, blink, speaking, smile,
fear, gaze).

## What is in a character

- **Body**: one skinned mesh (skin hidden under clothes is already removed, so nothing pokes through),
  2K skin colour, normal and roughness maps.
- **Rig**: 54 bones with Mixamo names (`mixamorig:Hips` ...), A pose, max 4 bones per vertex, plus
  `LeftEye` / `RightEye`. `humans.build()` renames them for the toolkit (`Spine` -> `LowerBack`,
  `Spine1` -> `Spine`, `Spine2` -> `Spine1`, `Neck` -> `Neck1`, prefix dropped) and re-rolls the hands
  (palm on the hand bone's -Z, +X curls a finger).
- **Face**: 47 shape keys with ARKit names, built on the character's own mesh: `eyeBlink`, `eyeWide`,
  `eyeSquint`, `eyeLookUp/Down` (lids follow the gaze), `browInnerUp`, `browOuterUp`, `browDown`,
  `cheekSquint`, `cheekPuff`, `noseSneer`, `jawOpen` (a real hinge rotation, lower teeth and tongue follow),
  `jawForward/Left/Right`, `mouthClose`, `mouthFunnel`, `mouthPucker`, `mouthSmile`, `mouthFrown`,
  `mouthStretch`, `mouthDimple`, `mouthPress`, `mouthShrugLower/Upper`, `mouthLowerDown`, `mouthUpperUp`,
  `mouthRollLower/Upper`, `mouthLeft/Right` (Left/Right = the character's own side). Eyebrows, lashes and
  beard carry the same keys so they move with the skin. Eyeballs turn on their eye bones.
- **Meshes in a scene**: `<name>.body`, `.eyes`, `.mouth` (teeth, gums, tongue), `.hair`, `.brows`,
  `.lashes`, `.beard`, and one per garment (`.nightshirt`, `.shirt`, `.trousers`, `.shoes`).

## Making them again, or more

They come from the character generator in `Downloads\Compressed\Generated_Characters` (not in this repo),
from a cast spec (fixed choices instead of random ones): `_work\cast\OldMan.json`, `_work\cast\Narrator.json`.

```
blender -b -Y --factory-startup "<FlipBox>\Male Custom Basemesh\Male_Custom_Basemesh.blend" ^
    --python _work\scripts\make_char.py -- <Generated_Characters> 0 4242 male - clothes _work\cast\OldMan.json
```

Copy the output folder (`.blend`, `params.json`, `textures\`, `previews\`) here, then rebuild the scene.
To use another generated character, copy its folder here and point a spec at it:
`dict(name="Someone", character="<folder>")`.

## Licence

Built from the FlipBox basemesh and its scanned skin textures, Facial Hair Toolkit beard cards, a Marvelous
Designer shirt and trousers, MakeHuman CC0 shoes and Poly Haven CC0 fabrics. See `../THIRD_PARTY.md`:
check the commercial items' terms before publishing these files.
