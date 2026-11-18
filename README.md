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
│   ├── render_preview.py      540x960 PNG of frame 1  -> output/previews/
│   ├── render_video.py        1080x1920 H.264 MP4     -> output/renders/
│   ├── validate_scene.py      checks project + renders -> output/validation_report.md
│   ├── scene_utils.py         shared helpers: shapes, collections, lights, cameras, render, save
│   ├── material_library.py    every MAT_* material (colour, roughness ...)
│   └── asset_library.py       furniture, props, walls, door, window builders
├── assets/        characters, environments, furniture, props, textures (AI models go here)
├── stories/       story scripts and scene definitions
├── audio/         voiceovers and sound effects
└── output/        previews and renders (not committed)
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

# 3. Five-second vertical video, 1080x1920, 24 fps, H.264 -> output/renders/bedroom_main.mp4
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
| `PROPS` | books, alarm clock, water glass, picture frame, laptop, vase |
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
- **Camera animation**: each camera drifts slowly between keyframes at frame 1
  and frame 120, with ease in and ease out. To change the start or end, go to
  that frame on the timeline, move the camera, hover over the viewport, press
  **I** and choose **Location**. Press **Alt+I** to remove a keyframe.
- **Video length**: set **End** on the timeline (24 frames = 1 second).

### Bring in AI-generated models (Meshy, Tripo, Mixamo)

1. Save the downloaded file into `assets/characters`, `assets/furniture` and so on.
2. Choose **File > Import > glTF / FBX / OBJ** and pick the file.
3. Rename it the FLV way (double-click the name in the Outliner, e.g.
   `CHAR_Girl`, `PROP_Candle`). Press **M** to move it into the right collection.

### Save and render from the UI

- **Save**: File > Save (Cmd+S / Ctrl+S).
- **Still image**: F12, then Image > Save As.
- **Video**: Render > Render Animation (Ctrl+F12) writes
  `output/renders/bedroom_main.mp4`, at 1080x1920, H.264, 5 s.

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
