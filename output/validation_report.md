# FLV bedroom validation report

2026-11-18 19:37 | Blender 5.3.0

| Check | Result | Detail |
|---|---|---|
| Blend file exists | PASS | blender/scenes/test_bedroom.blend |
| Blend file reopens | PASS | 159 objects, 67 materials |
| Collections FLV_BEDROOM > ROOM, BED, FURNITURE, WINDOW, PROPS, CHARACTERS, LIGHTING, CAMERAS | PASS | all present |
| Key objects exist | PASS | 21 found |
| No generic names (Cube.001 ...) | PASS | none |
| Every object sits in a scene collection | PASS | none |
| Every mesh has a material | PASS | 148 meshes |
| Materials named MAT_* | PASS | 67 materials |
| CAMERA_Main is the active camera | PASS | CAMERA_Main |
| Timeline starts at frame 1, 24 fps, whole seconds | PASS | frames 1-408 = 17 s |
| CAMERA_Main animated smoothly | PASS | keys at [1, 408], Bezier ease |
| CAMERA_Bed animated smoothly | PASS | keys at [1, 408], Bezier ease |
| CAMERA_Window animated smoothly | PASS | keys at [1, 408], Bezier ease |
| Walker animated (walk, pick up pencil, write) | PASS | 159 keyed frames, last at 383 |
| Sleeper breathes (looping) | PASS | covers rise and fall |
| Eevee at 1080x1920 with AgX | PASS | BLENDER_EEVEE, 1080x1920, AgX |
| Saved output is H.264 MP4 | PASS | //../../output/renders/bedroom_main.mp4 |
| Output path is relative to the .blend | PASS | //../../output/renders/bedroom_main.mp4 |
| No absolute file paths stored | PASS | none |
| Preview PNG is 540x960 and has an image in it | PASS | output/previews/bedroom_main_preview.png: 540x960, 538 KB, contrast 1.00 |
| Video MP4 is 1080x1920 and 17 s long | PASS | output/renders/bedroom_main.mp4: 1080x1920, 408 frames at 24 fps = 17.00 s, 5.6 MB |
