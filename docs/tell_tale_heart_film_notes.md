# The Tell-Tale Heart — the whole film (480p, in eight parts)

The film is 625.7 s (10 min 26 s) at 854×480, 24 fps. It is built and rendered as eight parts, each in its own
folder, then joined. The parts are kept so that one can be fixed and re-rendered without touching the others.

- The film: `output/renders/the_tell_tale_heart_film/the_tell_tale_heart_480p.mp4`
- Where every shot falls in film time: `output/renders/the_tell_tale_heart_film/parts.json`
- The film-wide soundtrack (sliced per part): `output/renders/the_tell_tale_heart_film/soundtrack_film.wav`

## The parts

| Part | Shots | Starts at | Length | Folder (`output/renders/the_tell_tale_heart_film/parts/…`) | Builder |
|---|---|---|---|---|---|
| 00 Prologue | 0.1–0.5, T | 0:00.0 | 42.0 s | `00_prologue/` | `parts/p00_prologue.py` (preview_v5) |
| 01 The Eye | 1.1–1.9 | 0:42.0 | 58.5 s | `01_the_eye/` | `parts/p01_the_eye.py` (preview_v5) |
| 02 Seven Nights | 2.1–2.9 | 1:40.5 | 107.0 s | `02_seven_nights/` | `parts/p02_seven_nights.py` (preview_v5) |
| 03 The Eighth Night | 3.1–3.10 | 3:27.5 | 61.8 s | `03_eighth_night/` | `preview_v2.py` |
| 04 The Attack | 3.11–3.21 | 4:29.2 | 108.6 s | `04_the_attack/` | `preview_v3.py` |
| 05 Concealment | 4.1–4.6 | 6:17.9 | 51.2 s | `05_concealment/` | `parts/p05_concealment.py` (preview_v5) |
| 06 The Visitors | 5.1–5.15 | 7:09.1 | 179.6 s | `06_the_visitors/` | `preview_v4.py` |
| 07 Epilogue | 6.1–6.3 | 10:08.7 | 17.0 s | `07_epilogue/` | `parts/p07_epilogue.py` (preview_v5) |

Each part folder holds `part_480p.mp4` (its picture with its slice of the film's sound), `frames/480p/` (the
rendered frames), `timeline.json` (its shots, lines and sound marks), `check.txt` (the measured checks),
`stills/` and `render.log`.

## Fixing one part

To report a problem, name the part and the time in it (or the film time; `parts.json` maps one to the other).
The fix for part `NN_name`, where `B` is the Blender binary:

1. Change its builder (the table above), then rebuild and check it:
   - v5 parts: `B -b --python-exit-code 1 --python stories/the_tell_tale_heart/preview_v5.py -- build NN_name`,
     then `B -b blender/scenes/tell_tale_heart_v5_NN_name.blend --python-exit-code 1 --python
     stories/the_tell_tale_heart/preview_v5.py -- check NN_name` (and `stills NN_name 1.2@3,…` to look).
   - 03: `preview_v2.py -- build`, then `check`; 04: `preview_v3.py`; 06: `preview_v4.py` (same commands).
2. Render it: `.venv/bin/python -I stories/the_tell_tale_heart/film_parts.py renders NN_name`. One GPU render at a
   time; a render that hangs is restarted from its last frame. `NN_name:2005-2748` re-renders only those frames.
3. If its length changed, re-run the mix: `film_parts.py mix` (all parts' sound, sliced again). Then
   `film_parts.py mux NN_name` (and every later part, if the length changed), then `film_parts.py join`.

## What each part's check measured (last run)

Every part passes the shared checks (`preview_v4.run_checks`): hands inside other people or chairs, held props
drifting from the hand, planted feet sliding, seated arms locked straight, lips on lines spoken on screen,
continuity (the strongbox lid, the loose planks, the narrator's worn look) and nobody frozen on camera.
Part 06 also checks that nothing in the room comes between the 5.11 orbit camera and his head.

| Part | Held props: worst drift | Lips: smallest jaw opening on a spoken line |
|---|---|---|
| 00 | — (no held props) | 0.24 |
| 01 | 0.0 cm (teapot, cup, tray, saucer) | — (no lines on screen) |
| 02 | 0.0 cm (watch, door, shutters) | 0.16 |
| 03 | 0.0 cm (his palm on the door) | 0.20 |
| 04 | 0.0 cm (3.19: the neighbour's candle) | 0.16 |
| 05 | 0.0 cm (the three planks) | 0.24 |
| 06 | 0.8 cm | 0.10 |
| 07 | — | 0.16 |

Two exceptions are written into the checks. In the haul (3.18) a grip may sink 2.5 cm into a person (cloth and
flesh under a fist; the worst measured is 2.0 cm). And the dead old man is not expected to move.

## Still open

- The officers and the 3.19 neighbour are stand-ins built on the narrator's body (their own faces are not made).
- The credits' maker line reads "An FLV film"; change it in `parts/p07_epilogue.py` if you want a name there.
- Licences to check before the film is shared or monetised: the commercial character basemesh, the facial-hair
  presets and the clothing project (`assets/THIRD_PARTY.md`, marked "check").
- The cricket, mouse and wind in 0.4 are not panned to where his eyes go.
