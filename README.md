# FLV - AI Story Studio

AI-assisted 3D animated storytelling production system.

## Requirements

- Blender 5.3+ (same version on every machine where possible)
- Python (Blender's bundled Python runs all Blender scripts)
- Git

## Project structure

```
FLV/
├── blender/scenes/test_bedroom.blend   the bedroom project (open this in Blender)
├── scripts/
│   ├── create_test_scene.py   builds the bedroom and saves the .blend
│   ├── render_preview.py      540x960 PNG of any frame -> output/previews/
│   ├── render_video.py        1080x1920 H.264 MP4     -> output/renders/
│   ├── validate_scene.py      checks project + renders -> output/validation_report.md
│   ├── scene_utils.py         shared helpers: shapes, collections, lights, cameras, render, save
│   ├── material_library.py    every MAT_* material (colour, roughness ...)
│   ├── character_library.py   rigged walker, sleeper, walk/reach/breathe animation helpers
│   ├── asset_library.py       procedural builders: furniture, lamps, props, door, window ...
│   ├── download_assets.py     fetches the free CC0 Poly Haven set into assets/
│   ├── build_asset_library.py packs everything for Blender's Asset Browser
│   └── register_asset_library.py  adds assets/ to Blender as the "FLV" library (once per machine)
├── assets/
│   ├── FLV_Procedural_Assets.blend   47 FLV assets, drag-and-drop
│   ├── FLV_PolyHaven_Assets.blend    385 Poly Haven assets (built locally, not in Git)
│   ├── polyhaven_manifest.json       source, author and licence of every downloaded asset
│   ├── furniture/polyhaven/   props/polyhaven/   Poly Haven models (glTF, 1K textures)
│   ├── environments/hdri/     night-sky HDRIs
│   ├── textures/polyhaven/    floor, wall and fabric texture sets
│   └── characters/            (empty, for AI-generated characters)
├── stories/       story scripts and scene definitions
├── audio/         voiceovers and sound effects
└── output/        previews, renders and the validation report
```

## Commands

Run everything from the `FLV` folder. The commands are the same on macOS,
Windows and Linux as long as `blender` is on your PATH. On Windows, use the
full path instead, e.g.
`& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"`.

```bash
# 1. Build the bedroom (about 1 second). Saves blender/scenes/test_bedroom.blend
blender --background --factory-startup --python scripts/create_test_scene.py

# 2. Preview PNG, 540x960, frame 1 (a few seconds) -> output/previews/bedroom_main_preview.png
blender --background --factory-startup --python scripts/render_preview.py
#    other cameras -> bedroom_bed_preview.png / bedroom_window_preview.png
blender --background --factory-startup --python scripts/render_preview.py -- --camera CAMERA_Bed
blender --background --factory-startup --python scripts/render_preview.py -- --camera CAMERA_Window
#    any moment of the story, e.g. frame 300 (writing) -> bedroom_main_preview_f0300.png
blender --background --factory-startup --python scripts/render_preview.py -- --frame 300

# 3. The 17-second story video, 1080x1920, 24 fps, H.264 (about 27 min) -> output/renders/bedroom_main.mp4
blender --background --factory-startup --python scripts/render_video.py
#    through another camera -> output/renders/bedroom_bed.mp4
blender --background --factory-startup --python scripts/render_video.py -- --camera CAMERA_Bed

# 4. Check everything and write output/validation_report.md
blender --background --factory-startup --python scripts/validate_scene.py

# Open the project (macOS; on Windows/Linux use File > Open in Blender)
open blender/scenes/test_bedroom.blend
```

**Careful:** step 1 rebuilds the bedroom from scratch and replaces the
`.blend`, including changes you made by hand. Blender keeps the previous file
as `test_bedroom.blend1`. Once you start editing by hand, stop re-running step 1.
Rename the old file to get it back.

The render scripts never change the `.blend`. They render whatever you last
saved, so your edits in Blender show up in the next render.

## Editing the bedroom in Blender (no Python needed)

The file opens in the **Layout** workspace, showing the room in Material Preview.

### Getting around

| Do this | How |
|---|---|
| Orbit / pan / zoom | middle-mouse drag / Shift + middle-mouse / scroll (trackpad: two-finger drag, Shift+drag, pinch) |
| See the real night lighting | press **Z**, choose **Rendered**. Choose **Material Preview** again for bright, easy editing |
| Find an object | **Outliner** (top right): open `FLV_BEDROOM`, then a collection, then click a name |
| Frame the selected object | **View > Frame Selected** (numpad `.`) |

### Collections (Outliner)

| Collection | Contents |
|---|---|
| `ROOM` | floor, walls, skirting, wall panels, slats, painting, door, hidden helper ceiling |
| `BED` | frame, legs, headboard, mattress, sheet, blanket, fold, throw, pillows, cushions |
| `FURNITURE` | bedside tables, lamps, wardrobe, open closet, desk, chairs, side table, TV, rug, plant |
| `WINDOW` | frame, glass, divider, sill, curtains, rod, night sky, moon, trees outside |
| `PROPS` | books, alarm clock, water glass, picture frame, laptop, notebook, pencils, handwriting, vase |
| `CHARACTERS` | `CHAR_Walker` (rig, body, hand targets) and `CHAR_Sleeper` (head, arm, covers) |
| `LIGHTING` | every light, plus the `ATMOS_Haze` fog |
| `CAMERAS` | `CAMERA_Main`, `CAMERA_Bed`, `CAMERA_Window` |

Click the eye icon next to a collection to hide it while you work.

### Move, rotate, add or delete furniture

- Each piece of furniture has a **main part** that carries the rest:
  `BED_Frame`, `TABLE_Bedside_Left`, `LAMP_Base`, `WARDROBE_Body`, `CHAIR_Desk_Seat`,
  `DESK_Top`, `TV_Stand`, `CLOSET_Frame`, `DOOR_Frame` and so on.
  Click it, press **G** to move (**G** then **X** or **Y** to keep it on one axis), and
  **R Z** to turn it. Everything attached moves with it.
- Click a single part (a pillow, a drawer) to move only that part.
- To open the door, select `DOOR_Panel` and press **R Z**. It swings on its hinge.
- **Duplicate** a piece: right-click its main part in the Outliner, choose **Select
  Hierarchy**, then press **Shift+D** and move it.
- **Add** a new object or light: **Add** menu (Shift+A) in the viewport.
- **Delete**: select, press **X**.
- **Change a size**: select, then press **S** to scale, or type values in the **N** side panel.
- Bevels, cloth wrinkles and smoothness are live **modifiers** (wrench tab in
  Properties). Change their numbers or switch them off there.

### Change materials and colours

1. Select an object, open **Material Properties** (red sphere tab at the right).
2. Change **Base Color**, **Roughness** and so on.

Materials are shared: `MAT_Wall_Cream` is used by both walls, so changing it
recolours every wall. To change one object only, click the number next to the
material name to make it a separate copy. To apply a different existing material,
click the sphere icon left of the material name and choose one from the list.

### Change the lighting

Select a light in `LIGHTING`, open **Light Properties** (green bulb tab), and
change **Power** or **Color**.

| Light | Role |
|---|---|
| `LIGHT_LAMP_Bulb` | warm bedside lamp (moves with `LAMP_Base`) |
| `LIGHT_PENDANT_Bulb` | warm hanging lamp |
| `LIGHT_Moon` | blue moonlight through the window. Rotate it to move the light patches on the floor |
| `LIGHT_Moon_Window_Fill` | soft blue glow spilling in from the window |
| `LIGHT_Room_Ambient` | gentle fill so nothing goes completely black |

- **Fog / light beams**: select `ATMOS_Haze` in the Outliner, then in Material
  Properties change **Density** (0 = none, 0.03 = current, 0.08 = thick). It can't
  be clicked in the viewport, so it doesn't get in the way.
- **Background**: World Properties (red globe tab).
- `ROOM_Ceiling_ShadowOnly` is an invisible ceiling. Cameras don't see it, but it
  stops moonlight from coming in over the walls. Leave it in place.

### Cameras

- **Look through a camera**: select it in the Outliner, then **View > Cameras >
  Set Active Object as Camera** (Ctrl + numpad 0). The render uses the active camera.
- **Re-aim the active camera**: while looking through it, press **N**, open the
  **View** tab and tick **Lock Camera to View**. Navigate until it looks right,
  then untick it.
- **Camera animation**: each camera moves between a keyframe on the first and the
  last frame, with ease in and ease out. `CAMERA_Main` starts on the whole room and
  eases in on the desk. To change a start or end, go to that frame on the timeline,
  move or turn the camera, hover over the viewport, press **I** and choose
  **Location & Rotation**. Press **Alt+I** to remove a keyframe.
- **Video length**: set **End** on the timeline (24 frames = 1 second).

### The story and the characters

| Seconds | What happens |
|---|---|
| 0-1 | Wide view of the whole room. Someone sleeps in the bed; the walker stands by the door |
| 0.5-9 | The walker crosses the room, past the armchair and the foot of the bed, to the desk |
| 9-11 | Turns to the desk, leans in, picks up the pencil |
| 11-15 | Writes three lines in the notebook (the ink appears as they write) |
| 15-17 | Looks up at the window. The sleeper breathes slowly the whole time |

- **Pose the walker yourself**: click `CHAR_Walker_Rig` (the bones show through the
  body), press **Ctrl+Tab** for Pose Mode, click a bone, press **R** to rotate it,
  then **I** to keyframe it. Ctrl+Tab again to leave.
- **Move where a hand goes**: the hands follow the small spheres
  `CHAR_Walker_Hand_Target.L` / `.R`. Move one at a frame and press **I > Location**.
- **Change the route or timing**: edit `WALK_PATH`, `NOTEBOOK` and `PENCIL` near the
  top of `scripts/create_test_scene.py` and rebuild (this replaces the .blend).
- **Clothes and skin colours**: `MAT_Shirt`, `MAT_Pants`, `MAT_Skin`, `MAT_Hair`,
  `MAT_Pajama` in Material Properties.
- **Swap in a Mixamo or AI character later**: import it, then copy the walk with
  Mixamo's own animations, or rename its bones to the FLV names (`hips`, `spine`,
  `thigh.L` ...) to reuse `character_library.py`.

### Bring in AI-generated models (Meshy, Tripo, Mixamo)

1. Save the downloaded file into `assets/characters`, `assets/furniture` and so on.
2. Choose **File > Import > glTF / FBX / OBJ** and pick the file.
3. Rename it the FLV way (double-click the name in the Outliner, e.g.
   `CHAR_Girl`, `PROP_Candle`). Press **M** to move it into the right collection.

### Save and render from the UI

- **Save**: File > Save (Cmd+S / Ctrl+S).
- **Still image**: F12, then Image > Save As.
- **Video**: Render > Render Animation (Ctrl+F12) writes
  `output/renders/bedroom_main.mp4`, at 1080x1920, H.264, 17 s.

## Film: The Tell-Tale Heart (10 minutes)

A 10-minute horror short adapted from Edgar Allan Poe's *The Tell-Tale Heart* (1843, public
domain: free to adapt and monetise). Everything is in `stories/the_tell_tale_heart/`:

| File | What it is |
|---|---|
| `source_text.md` | Poe's original text, with source and licence |
| `film.py` | **The shot list** — 69 shots: narration (Poe's words), new lines (marked adapted), framing, movement, action, light, sound cues |
| `production_plan.md` | The readable plan, generated from `film.py`: why this story, structure, cast, visual and sound approach, adaptation notes, full shot list with timecodes |
| `timeline.json` | Shot start frames and lengths, sized to the recorded voices |
| `sets.py`, `build_film.py` | Builds the 1840s house sets, cast, props, lights and a camera per shot |

Make the film (from the `FLV` folder):

```bash
# 1. Voices (Piper) + timeline + production plan          ~20 s
.venv/bin/python -I scripts/story_tools.py stories/the_tell_tale_heart
# 2. Blender scene with every shot                          ~10 s -> blender/scenes/tell_tale_heart.blend
blender --background --factory-startup --python stories/the_tell_tale_heart/build_film.py
# 3. Render shot by shot (two workers in parallel)          ~5-6 h for 1080p
blender -b blender/scenes/tell_tale_heart.blend --python scripts/render_shots.py -- \
    --timeline stories/the_tell_tale_heart/timeline.json --out output/renders/tell_tale_heart/shots --worker 0 --workers 2
#    (run a second copy with --worker 1; re-render single shots with --only 3.5,3.13)
# 4. Soundtrack: voices + synthesised effects + heartbeat + score   ~20 s
.venv/bin/python -I scripts/mix_story.py stories/the_tell_tale_heart
# 5. Join the shots and add the soundtrack                ~10 min
.venv/bin/python -I scripts/finish_film.py stories/the_tell_tale_heart output/renders/tell_tale_heart/shots
```

Step 5 writes `output/renders/the_tell_tale_heart/the_tell_tale_heart.mp4` (the copy in git, re-encoded
to ~80 MB to fit GitHub's 100 MB limit) and `the_tell_tale_heart_master.mp4` (full render quality, local
only). Per-shot renders, logs and the soundtrack WAV are local only too (see `.gitignore`); the commands
above rebuild them.

Open `blender/scenes/tell_tale_heart.blend` to see every shot: the timeline markers switch
cameras, so scrubbing the timeline plays the film's edit.

## Asset library (drag and drop, 432 assets)

| Library | What's in it | Licence |
|---|---|---|
| FLV procedural (47) | rigged person, sleeping person, notebook, pencil, double and single bed, bedside table, wardrobe, open closet, bookshelf, desk, dining table, chair, armchair, sofa, side table, TV and stand, rug, coat rack, plant. Lights: table, floor, desk, pendant and ceiling lamps, candle, flashlight (all with real lights). Room parts: door, window, curtains, wall panels. Decor: painting, wall clock (stopped at 3:00), crime evidence board. Props: books, alarm clock, glass, picture frame, laptop, vase, mug, bottle, box, suitcase, bin, knife, sealed envelope | yours, generated by the scripts |
| Poly Haven models (205) | furniture, seating, tables, shelves, lamps, decor, electronics, appliances | CC0, free for commercial use, no credit needed |
| Poly Haven night skies (61) | HDRI Worlds for background and lighting | CC0 |
| Poly Haven materials (119) | floor, wall and fabric texture sets | CC0 |

After cloning on a new machine, run these once (this Mac is already set up):

```bash
blender --background --factory-startup --python scripts/build_asset_library.py   # ~20 s
blender --background --python scripts/register_asset_library.py                  # adds the "FLV" library
```

**Using it in Blender**

1. Turn any editor (the Timeline at the bottom works well) into an **Asset Browser** with
   the editor-type menu at its top-left corner.
2. Choose **FLV** in the library drop-down, then a catalog on the left, such as
   `FLV/Furniture`, `Poly Haven/Models/Seating` or `Poly Haven/Night Skies`.
3. Drag and drop:
   - **a model into the viewport**: it lands where you drop it. If it arrives as one
     uneditable "instance", untick **Instance** in the pop-up panel at the bottom-left.
   - **a material onto an object**: the object takes that material.
   - **a night sky into the viewport**: it becomes the World background and lighting.

**Getting more**

- Poly Haven: edit `SELECTION` in `scripts/download_assets.py`. Category examples:
  `industrial`, `containers`, `tools`, `food` for models; `indoor`, `urban` for HDRIs;
  `wood`, `brick` for textures. Run `python3 scripts/download_assets.py --list` to see
  the size, then run it without `--list` and rebuild the library. The Git repo is about
  700 MB now; keep it under about 1 GB.
- [Kenney](https://kenney.nl/assets/category:3D): CC0 stylized low-poly packs (Furniture
  Kit, Building Kit, City Kits) that match the FLV look. Downloads need a click on
  their site. Unzip into `assets/furniture/kenney/` and import.
- [Quaternius](https://quaternius.com): CC0 stylized characters and props.
- [Mixamo](https://www.mixamo.com): rigged characters and animations (free Adobe login).

## Claude Code + Blender (MCP for Blender)

[MCP for Blender](https://github.com/ahujasid/mcp-for-blender) (formerly `blender-mcp`,
MIT licence) lets Claude Code work inside a running Blender. It can look at the viewport
and renders, run Python live, import Poly Haven and Sketchfab assets, and generate models
with Meshy, Tripo or Hyper3D (you supply their API keys). `uv` is already installed.
To set it up, run from this folder:

```bash
uvx mcp-for-blender@2.3.1 install-addon                                    # copies the add-on into Blender
claude mcp add blender -e DISABLE_TELEMETRY=true -- uvx mcp-for-blender@2.3.1
```

Then in Blender go to **Edit > Preferences > Add-ons**, enable **MCP for Blender**. In the 3D
viewport, press **N**, open the **MCP for Blender** tab and click **Start MCP Server**.
Restart Claude Code; `claude mcp list` should show `blender`. If `install-addon` can't
find Blender, use **Add-ons > Install from Disk** with `addon.py` from the project page.

**Safety:** the add-on runs any Python it receives on local port 9876, with no password.
Save your work first, and only start the server while you use it. Set
`BLENDER_MCP_SAFE_MODE=1` to block file, network and program access when you don't need
them. The version is pinned to 2.3.1 so updates don't install unreviewed.

## Voice generation (Piper)

The Python virtual environment and the voice model aren't in Git. Set them up
once per machine:

```bash
python3 -m venv .venv
.venv/bin/pip install piper-tts                       # Windows: .venv\Scripts\pip
.venv/bin/python -m piper.download_voices en_US-lessac-medium --download-dir voices
echo "Your line here" | .venv/bin/piper -m voices/en_US-lessac-medium.onnx -f audio/voiceovers/line.wav
```

Check each voice's licence before commercial use. `en_US-lessac` comes from a
non-commercial dataset. `en_US-ljspeech-high` is public domain.

## Portability notes

- No absolute paths are stored. The `.blend` saves its video path relative to
  itself (`//../../output/renders/`). The scripts find the project folder from their
  own location.
- Scripts only use Blender's bundled Python, `pathlib` and `bpy`. They need no
  extra packages and run no shell commands.
- The engine name differs between Blender versions (4.2-4.x call Eevee
  `BLENDER_EEVEE_NEXT`; 5.x calls it `BLENDER_EEVEE`). `scene_utils.eevee_engine()`
  picks the right one.
