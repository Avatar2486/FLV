# FLV bedroom validation report

2026-11-18 18:25 | Blender 5.3.0

| Check | Result | Detail |
|---|---|---|
| Blend file exists | PASS | blender/scenes/test_bedroom.blend |
| Blend file reopens | PASS | 143 objects, 56 materials |
| Collections FLV_BEDROOM > ROOM, BED, FURNITURE, WINDOW, PROPS, LIGHTING, CAMERAS | PASS | all present |
| Key objects exist | PASS | 15 found |
| No generic names (Cube.001 ...) | PASS | none |
| Every object sits in a scene collection | PASS | none |
| Every mesh has a material | PASS | 135 meshes |
| Materials named MAT_* | PASS | 56 materials |
| CAMERA_Main is the active camera | PASS | CAMERA_Main |
| Timeline 1-120 at 24 fps (5 s) | PASS | frames 1-120 at 24 fps |
| CAMERA_Main animated smoothly | PASS | keys at [1, 120], Bezier ease |
| CAMERA_Bed animated smoothly | PASS | keys at [1, 120], Bezier ease |
| CAMERA_Window animated smoothly | PASS | keys at [1, 120], Bezier ease |
| Eevee at 1080x1920 with AgX | PASS | BLENDER_EEVEE, 1080x1920, AgX |
| Saved output is H.264 MP4 | PASS | //../../output/renders/bedroom_main.mp4 |
| Output path is relative to the .blend | PASS | //../../output/renders/bedroom_main.mp4 |
| No absolute file paths stored | PASS | none |
| Preview PNG is 540x960 and has an image in it | PASS | output/previews/bedroom_main_preview.png: 540x960, 583 KB, contrast 1.00 |
| Video MP4 is 1080x1920 and 5 s long | PASS | output/renders/bedroom_main.mp4: 1080x1920, 120 frames at 24 fps = 5.00 s, 1.7 MB |
