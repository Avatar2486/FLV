# The Tell-Tale Heart, whole film (480p, eight parts): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The whole Tell-Tale Heart (69 shots, about 10 minutes) as one 480p film made of eight parts. Each
part's frames, sound and MP4 are kept in its own folder, and the parts are joined into one MP4 with a
`parts.json` index.

**Architecture:**
- One builder per part: the existing `preview_v2.py` (part 03), `preview_v3.py` (04) and `preview_v4.py`
  (06), plus a new `preview_v5.py` core with one act module per new part (00, 01, 02, 05, 07).
- A new `film_parts.py` holds the part registry and the film clock. It renders a part's frames (inside
  Blender), mixes the whole film's sound once (plain Python, numpy and ffmpeg) and slices it per part. It
  muxes each part's MP4 and joins the film (video streams copied, the film-wide sound laid once).

**Tech Stack:**
- Blender 5.3 (bpy, Eevee) on the Mac mini M4;
- numpy and ffmpeg (`.venv`);
- Chatterbox (`tools/chatterbox/.venv`), Wav2ARKit;
- 100STYLE and CMU BVH;
- `scripts/humans.py`, `scripts/sound_library.py`, `scripts/mix_story.py` helpers.

**Spec:** `docs/superpowers/specs/2026-11-24-tell-tale-heart-whole-film-design.md`

## Global Constraints

- **Output:** 854×480, 24 fps, H.264 + AAC.
- **480p only.** No 1080p.
- **Voices:** Chatterbox with Kokoro reference voices (`audio/voice_refs/`). The old 19-Nov voices are not used.
- **Motion:** only `assets/mocap/` (100STYLE, CMU).
- **Sound:**
  - recorded Freesound CC0 takes in `audio/sfx/freesound/`;
  - Chopin (Musopen CC0) in `audio/music/chopin/` via `film.SCORE`;
  - `sound_library` synthesis only where no recording exists.
- **No downloads** without first showing the user a URL / size / licence table.
- **Realism rules:**
  - human-like lips;
  - nothing moves unless a hand moves it;
  - no dolls (everyone on screen moves at least 0.5° in every 1 s);
  - no rigged-looking hands.
- **Folders:** `output/renders/the_tell_tale_heart_film/parts/<NN_name>/` holds `frames/480p/*.png`,
  `soundtrack.wav`, `part_480p.mp4`, `timeline.json` (v5 parts), `check.txt` and `stills/`. The joined film is
  `output/renders/the_tell_tale_heart_film/the_tell_tale_heart_480p.mp4`, with `parts.json` and
  `soundtrack_film.wav`. **Nothing in a part folder is deleted by joining.**
- **Credits maker line:** "An FLV film".
- **Git:**
  - work on branch `visitors-v4`;
  - commit after each task;
  - push by fast-forwarding `UAT` and pushing **UAT only**;
  - never commit `.blend`, frames, MP4s or WAV renders.
- **Blender commands** use `--python-exit-code 1`, so a failed assert fails the command.

## Review Focus

1. **Stale frames:** a part re-rendered after a fix must not keep old PNGs (Blender's render skips files that
   exist). `film_parts.render` clears the folder; the Task 1 self-check asserts the MP4's length equals the
   frame count / 24.
2. **Sound drifting at a join:** part starts in the film must be the exact sum of earlier frame counts / 24,
   and the joined film carries one film-wide sound track, not concatenated AAC streams. The Task 1
   self-check asserts the joined length to within 1 frame and that a line placed at a part's 1.0 s sounds at
   film time start + 1.0 s.
3. **A part changing length after a fix:** every later part's sound must move with it, without re-rendering
   pictures. The Task 1 self-check changes part A's frame count and asserts part B's slice start moves by the
   same amount.
4. **24 kHz Chatterbox lines in the 48 kHz mix** (`mix_story.read_wav` asserts 48 kHz). Lines are decoded
   with `read_audio`. The Task 1 self-check mixes a 24 kHz line and asserts its length in the mix.
5. **Continuity across parts:**
   - the strongbox lid shut except when a hand opens it;
   - the loose planks at rest except in 4.3–4.4;
   - the narrator's worn look rising through 2.8 and held in 3.x.

   Pinned by `continuity` assertions in the shared check (Task 4), run for parts 01, 02, 03, 04, 05 and 06.

---

### Task 1: `film_parts.py`, the part registry, film clock, render, mix, mux and join

**Files:**
- Create: `stories/the_tell_tale_heart/film_parts.py`
- Modify: `stories/the_tell_tale_heart/film.py` (the 5.x `HEARTBEATS` entry, see Step 3)

**Interfaces:**
- **Produces:**
  - `PARTS: list[dict]`: one per part, keys `key`, `title`, `shots`
    (list of shot ids), `blend` (Path), `timeline` (Path to the builder's timeline.json) and `voice_dir`
    (Path or None, for timelines whose line files are bare names, as v2 writes them). The order and shots
    are:
    - `00_prologue`: 0.1–0.5 and T;
    - `01_the_eye`: 1.1–1.9;
    - `02_seven_nights`: 2.1–2.9;
    - `03_eighth_night`: 3.1–3.10;
    - `04_the_attack`: 3.11–3.21;
    - `05_concealment`: 4.1–4.6;
    - `06_the_visitors`: 5.1–5.15;
    - `07_epilogue`: 6.1–6.3.
  - `FILM = ROOT / "output/renders/the_tell_tale_heart_film"`, `part_dir(key) -> Path`.
  - `part_timeline(key) -> dict`, normalised to:
    `{"fps": 24, "frames": int, "seconds": float, "shots": [{"id", "start", "seconds", "lines": [{"who", "file", "start", "seconds", "gain"}]}], "marks": {"<shot>/<cue>": seconds}}`.
    - `file` is project-relative.
    - `gain` is 1.0 for planned lines and 0.25 for chatter.
    - Chatter from v4's `"chatter"` list is folded into its shots' lines.
  - `film_clock() -> list[dict]`: `{"key", "start", "frames", "seconds", "nominal"}` in film order. A part
    without a timeline yet uses its shots' lengths from `stories/the_tell_tale_heart/timeline.json`, with
    `nominal: True`.
  - `write_index() -> Path`: writes `FILM/parts.json` (the clock, plus each shot's film start time).
  - `render(key) -> int`: runs inside Blender with that part's blend open and returns the frame count.
  - `mix() -> Path`: writes `FILM/soundtrack_film.wav`, then each part's `soundtrack.wav` slice.
  - `mux(key) -> Path`: writes `part_480p.mp4`.
  - `join() -> Path`: writes `the_tell_tale_heart_480p.mp4`.
- **CLI:**
  - `.venv/bin/python -I stories/the_tell_tale_heart/film_parts.py selfcheck|index|mix|mux <key>|join`
  - `blender -b <blend> --python-exit-code 1 --python stories/the_tell_tale_heart/film_parts.py -- render <key>`

- [ ] **Step 1: Write `selfcheck()` in `film_parts.py`.** It works on two synthetic parts in a temp folder.
  `FILM` and `PARTS` are overridable for the test, and there is a `frames` override.
  - Part "A" is 48 frames and part "B" is 72, each solid-colour PNGs at 854×480.
  - Each has one 24 kHz sine "line" (0.5 s) at part-time 1.0 s.
  - Assert `film_clock()` starts == [0.0, 2.0].
  - Assert slice lengths of 2.0 s and 3.0 s, to within 1/24 s.
  - Assert `mux` durations of 2.0 s and 3.0 s, and a `join` duration of 5.0 s, each to within 1/24 s
    (ffprobe).
  - Assert the mix's RMS in film time 3.0–3.5 s is more than 10× its RMS in 2.4–2.9 s (B's line lands at
    2.0 + 1.0).
  - Then set A to 60 frames: assert B's start == 2.5 and its line's loud window moves to 3.5 s.

- [ ] **Step 2: Run it.** Run: `.venv/bin/python -I stories/the_tell_tale_heart/film_parts.py selfcheck`.
  Expected: it fails (the functions don't exist yet).

- [ ] **Step 3: Implement.**
  - **The registry and `part_timeline`:**
    - v2 (part 03) line files are bare names, resolved through `voice_dir`.
    - v3 and v4 line files are project-relative.
    - `start` in all three builder timelines is seconds.
  - **`render`:**
    - 854×480 at 100%, PNG RGB, `eevee.taa_render_samples = 24`;
    - output `part_dir(key)/frames/480p/#####`;
    - `shutil.rmtree` that folder first;
    - frame range from the scene;
    - afterwards assert the PNG count == `frame_end - frame_start + 1`.
  - **`mix`:**
    - Reuse `mix_story`'s `Mix`, `read_audio`, `fitted` and `heartbeat_times`, and `sound_library`'s
      `music`, `sfx`, `heart`, `loop` and `LOOPS`, with `film.SCORE` and `film.REAL_SFX`.
    - The score plays per shot cue, continuous across shots that share a cue (as `mix_story.main` does).
    - Shot effects come from `film.SHOTS`. A part mark named `"<shot>/<cue>"` replaces that cue's offset.
      Marks with no matching cue play at gain 0.7.
    - Voices are brought to −18 dB RMS × `gain` using `mix_story.VOICE` pans.
    - Chatter in 5.10–5.13 is low-passed at 1.2 kHz and slowed 3% (resampled).
    - Heartbeats come from `film.HEARTBEATS`, with an optional 8th field: a shot id from which a muffled
      run plays clear.
    - Loudness is normalised as in `mix_story` (`loudnorm=I=-16:TP=-1.5:LRA=14`).
  - **`mux`:**
    `ffmpeg -framerate 24 -start_number <frame_start> -i frames/480p/%05d.png -i soundtrack.wav -c:v libx264 -pix_fmt yuv420p -crf 20 -c:a aac -b:a 192k -shortest`.
  - **`join`:** the concat demuxer over the part MP4s' video (`-map 0:v -c:v copy`) plus
    `soundtrack_film.wav` encoded as AAC; then `write_index()`.
  - **`film.HEARTBEATS`:** replace the `('5.9', 3.5, 60, 150, '5.15', 7.0, False)` entry with
    `('5.8', 2.0, 60, 150, '5.15', 6.0, True, '5.13')`, the run the Visitors picture already uses (muffled,
    clear from 5.13).

- [ ] **Step 4: Run the self-check.** Run the Step 2 command. Expected: `film_parts selfcheck OK` with the
  measured numbers.

- [ ] **Step 5: Commit.** `git add stories/the_tell_tale_heart/film_parts.py stories/the_tell_tale_heart/film.py`,
  then commit with the message "film_parts: part registry, film clock, render, film-wide mix, mux and join".

### Task 2: Part 06, The Visitors: the breakdown (5.11–5.15)

**Files:**
- Modify: `stories/the_tell_tale_heart/preview_v4.py`: new `_act_breakdown`, appended to `ACTS`; `beat_times`
  reads `film.HEARTBEATS`; the mark rename.
- Modify: `scripts/humans.py`:
  - `HAND_SHAPES["point"]`: index (5, 5, 3), the other fingers as `"fist"`, thumb (30, 30, 20),
    `THUMB_ACROSS["point"] = 20`;
  - `GESTURES["point"]`: dir (0.6, −0.8, 0.0), elbow 160, palm "down", fingers "point", dip 0.03;
  - palm `"down"` = (0, 0, −1).

**Interfaces:**
- **Consumes:** `film_parts.film_clock` (not needed yet), `film.HEARTBEATS` (Task 1 format).
- **Produces:**
  - v4 timeline marks renamed to `"<shot>/<cue>"`: `"5.1/knock3"`, plus `"5.12/chair_scrape"`,
    `"5.15/stomp"` and `"5.6/chair_place"`, all written by `build()`.
  - A new helper `_stand_up(ctx, rig, r0, r1, stand)`: sit to stand, feet kept by leg IK.
    `ctx["stand"]` holds the narrator's frame-1 rotations, recorded in `build()` after `relax_arms`.
  - `_walk` gains `clips=None`, passed to `v3._mocap_gait`.

- [ ] **Step 1: Write the failing test.** The humans self-check gets `assert 140 <= elbow` for a forced
  `"point"` stroke. Then add the 5.11–5.15 contacts to `check`: both hands on the chair rail from the grab in
  5.12 to the release in 5.15, registered in `ctx["held"]`. The chair is a held prop for those frames.
- [ ] **Step 2: Run the checks and confirm they fail.**
  - Run: `blender -b --factory-startup --python-exit-code 1 --python scripts/humans.py -- --selfcheck`.
    Expected: the point check fails (unknown kind).
  - Run `preview_v4.py -- build`, then `check 5.11,5.12,5.13,5.14,5.15`. Expected: it fails (frozen, lips).
- [ ] **Step 3: Implement `_act_breakdown`** (per the v4 spec, `…/2026-11-23-visitors-officers-scene-design.md`,
  shots 5.11–5.15). The pinned values:
  - **5.11:**
    - He rises over t 0.3–1.5 (`_stand_up`).
    - He argues during the chatter c10 and c11 with `energy=0.9`.
    - He paces with `clips=(("Angry_FW", 240), ("Rushed_FW", 240))` along
      (−1.0, −0.55) → (−1.75, −0.6) → (−1.75, 0.75) → (−1.7, −0.45) → (−1.25, 0.15), ending at heading 76.8.
    - Face `TENSE`, then `FURY` by c11.
    - The orbit camera circles his smoothed head at radius 1.4 and height 1.6, clamped inside
      x/y ±2.3/±2.1.
  - **5.12:**
    - Both hands on the rail at chair-local (±0.14, 0.37, 1.06).
    - He stands at chair-local (0, 0.62, 0).
    - The chair, seat heading 76.8:
      - lifts 0.18 m;
      - swings to heading 136.8 over 1.5–2.8 s;
      - comes back to 76.8 and lands with a bang at 3.6 s (mark `5.12/chair_scrape` at 4.0 s);
      - is ground back and forth ±0.2 m, 3 times, over 4.0–8.5 s. His body moves half that.
    - His fingers are reset to identity and gripped at 0.55, as in 5.6.
  - **5.13:**
    - He grips the rail; face `HORROR`; a body tremor layer at 7–9 Hz, 0.8°.
    - Mercer sips over 9.0–12.5 s (the cup to his mouth and back; the cup carried by `_carry` to the
      film's end).
    - Hale chuckles at 2.0 s.
    - The `officers` camera dolly-zooms from (−0.4, −0.05, 1.25) at 35 mm to (−0.75, 0.02, 1.25) at 52 mm.
  - **5.14:**
    - Cuts on every second beat from `beat_times`, cycling `eye_n`, `smile_h`, `macro`, `smile_b`,
      `eye_n`, `smile_m`, `macro`, added to `ctx["extra_cuts"]`.
    - `delta_rotation_euler` jolts of ±1.2° on each beat.
    - `eye_n` is placed 0.25 m in front of his head at T("5.14").
    - `_dust` runs for 5.14.
  - **5.15:**
    - He lets go of the rail at 0.3 s.
    - Forced gestures: `"chop"` at 0.43, `"fist"` at 3.34, `"point"` at 4.66.
    - Stamps of the right leg (hip 45°, knee 70°, up in 0.18 s, down in 0.07 s) land at 6.1 s and 6.6 s.
      Mark `5.15/stomp` at the first.
    - The officers `startle(legs=False)` at 0.55 s, then `_stand_up` over 1.2–2.6 s.
    - Face `FURY`; lips on the NS line.
    - The `ms15` camera pushes from (0.4, −1.3, 1.5) toward his head by 5.8 s, whip-pans to the planks
      (−0.8, 0, 0) at 6.0–6.2 s, and back up by 7.2 s.
- [ ] **Step 4: Build and check.**
  - Run `build`, then `check` on all 15 shots. Expected: `V4 check OK (animated)`.
  - Run the self-check. Expected: all OK.
- [ ] **Step 5: Look at the stills.** Run `stills 5.11@3,5.11@12,5.12@2,5.12@6,5.13@10,5.14@3,5.15@1,5.15@6.2`.
  Expected: no clipping, no floating, faces as listed.
- [ ] **Step 6: Commit.** Commit with the message "Visitors: the breakdown, 5.11-5.15". Push UAT.

### Task 3: Part 06 render, the first film-wide mix, its MP4 to the user

**Files:**
- Modify: `stories/the_tell_tale_heart/film_parts.py` (only if the real part shows a bug)

**Interfaces:**
- **Consumes:** Task 1's `render`, `mix` and `mux`; Task 2's blend and timeline.

- [ ] **Step 1: Render.** Run
  `blender -b blender/scenes/tell_tale_heart_v4_visitors.blend --python-exit-code 1 --python stories/the_tell_tale_heart/film_parts.py -- render 06_the_visitors`.
  Expected: the frame count printed equals the scene's frame range (about 4,300).
- [ ] **Step 2: Mix and mux.** Run `film_parts.py mix`, then `mux 06_the_visitors`. Expected: `part_480p.mp4`,
  with its length equal to frames / 24 to within 1 frame (printed).
- [ ] **Step 3: Check the sync and look at the result.** Check sync on the lip frames of `5.2_1_O1` (Hale's
  first word against his jaw opening, within 2 frames). Make a 1 fps contact sheet and look for black frames,
  frozen people and props off their hands.
- [ ] **Step 4: Commit and hand over.** Commit. Give the user `parts/06_the_visitors/part_480p.mp4`.

### Task 4: The shared check, and the `preview_v5.py` core

**Files:**
- Modify: `stories/the_tell_tale_heart/preview_v4.py`: split `check()` into
  - `_check_inside(scene, rigs, obstacles, chairs, hands, frames)`,
  - `_check_held(scene, rigs, held, f0, f1)`,
  - `_check_feet(scene, rigs, f0, f1)`,
  - `_check_lips(scene, spoken, f0, f1)`,
  - `_check_frozen(scene, rigs, f0, f1)`,
  - `_check_locked(scene, rigs, f0, f1, step)`,
  - `_check_continuity(scene, f0, f1)`.

  Each returns `(fails: list[str], notes: list[str])`. `check()` composes them with unchanged output.
- Create: `stories/the_tell_tale_heart/preview_v5.py`. It holds:
  - the paths;
  - `PART_MODULES`, from part key to an act module;
  - `timeline(part)`;
  - `build(part)`;
  - `check(part)`, `stills(part, shots)`, `voices(part)`.
- Create: `stories/the_tell_tale_heart/preview_v5/lines.json`, the lines of parts 00, 01, 02, 05, 07 and 04,
  built from `film.SHOTS` lines. It also holds 3.2's narration, written to
  `audio/voiceovers/the_tell_tale_heart_v2/3.2_N.wav` (v2's naming) for Task 10.
- Create: `stories/the_tell_tale_heart/parts/__init__.py`.

**Interfaces:**
- **Produces:**
  - Each act module in `stories/the_tell_tale_heart/parts/` exposes:
    - `SHOTS: list[tuple[str, list[tuple[str, str]], float]]`: shot id, `[(line key, who)]`, minimum seconds;
    - `CAMERAS: dict[str, tuple[at, look, lens]]`;
    - `CUTS: list[tuple[shot, sec, camera]]`;
    - `LIGHTS: dict[shot, dict[light, energy]]`;
    - `SETS: list[str]`, names of `sets.py` builders;
    - `CAST: list[str]`, from "Narrator" and "OldMan";
    - `act(ctx) -> None`.
  - `preview_v5.build(part)` writes:
    - `blender/scenes/tell_tale_heart_v5_<key>.blend`;
    - `FILM/parts/<key>/timeline.json`, in v4's format plus `"marks"`.
  - Voice files go to `audio/voiceovers/the_tell_tale_heart_v5/<shot>_<k>_<who>.wav`.
  - Each line's `ref`:
    - N and NS: `audio/voice_refs/narrator.wav`;
    - OM: `old_man.wav`.

  `exaggeration`: 0.5 for N, 0.6 for NS and OM. `cfg`: 0.5.
  - `_check_continuity` asserts, at each sampled frame:
    - the strongbox lid is shut unless its shot is 1.5 or 5.5;
    - the loose planks are at z −0.025 unless the shot is 4.3 or 4.4;
    - the narrator's `worn` custom property never drops from one sampled frame to the next.

- [ ] **Step 1: Write the failing test.** Add `preview_v5.py -- selfcheck`. It builds a minimal test part
  (one 3 s void shot with the narrator saying one existing line). It asserts:
  - the blend saves;
  - the timeline is 3.0–3.6 s;
  - `check` passes (lips, not frozen).
- [ ] **Step 2: Run it.** Run `blender -b --factory-startup --python-exit-code 1 --python stories/the_tell_tale_heart/preview_v5.py -- selfcheck`.
  Expected: it fails (the module doesn't exist).
- [ ] **Step 3: Implement.**
  - Do the split in v4, keeping v4's output identical. Re-run `check 5.1,…,5.10` and expect the same
    notes and OK.
  - Write the v5 core, which imports `preview_v4 as v4` and `preview_v3 as v3` for `_converse`, `_walk`,
    `_contact`, `_at`, `_hold`, `_stand_up` and `_carry`.
  - Generate the voices:
    `tools/chatterbox/.venv/bin/python -I scripts/chatterbox_lines.py stories/the_tell_tale_heart/preview_v5/lines.json`.
- [ ] **Step 4: Run the self-check and the v4 check.** Expected: both OK, and every line in `lines.json` has
  its WAV.
- [ ] **Step 5: Commit.** Commit with the message "preview_v5 core and the shared check; voices for parts 00,
  01, 02, 04, 05, 07".

### Tasks 5–9: The new parts

**Order of work (the spec's):** Tasks 5, 6 and 7 (parts 00, 01, 02), then Task 10 (03), then Task 11 (04),
then Tasks 8 and 9 (05, 07), then Task 12.

Each new part follows the same steps, with that part's own checks (listed per task):

- [ ] **Step 1:** Write the part's act module with its `SHOTS`, `CAMERAS`, `CUTS`, `LIGHTS`, `SETS` and
  `CAST`, plus an `act` stub. Add the part-specific checks listed below to `preview_v5.check`.
- [ ] **Step 2:** Run `build <key>`, then `check <key>`. Expected: it fails (frozen, lips, the part's own
  checks).
- [ ] **Step 3:** Implement `act` per the spec's "What each new part shows" and the production plan's frame,
  move and light columns.
- [ ] **Step 4:** Run `build`, then `check`. Expected: OK. Then run `stills`, make a contact sheet of every
  shot and look at it.
- [ ] **Step 5:** Run `film_parts render <key>`, then `mix`, then `mux <key>`. Make a 1 fps contact sheet and
  look at it.
- [ ] **Step 6:** Commit, push UAT, and give the user the part's MP4 path.

**Task 5: 00 Prologue** (`parts/p00_prologue.py`)
- **0.1:** Black, then a fade in at the end of 0.1.
- **0.2:** A 100 mm macro along the seam at (−0.6, 0.0, 0.0) in the chamber; dust motes drifting in one cold
  ray through haze.
- **0.3–0.5:** The void.
  - The narrator in `VO_Chair`; a hard top light.
  - `_converse` with `energy=0.4` for direct-address gestures.
  - 0.4: eye targets left, right and up, at the cricket, mouse and wind cue times.
  - 0.5: a smile (`SLY`, mouthSmile 0.3).
- **T:** The title text, fading out over its last 1.0 s.
- **Checks:** lips on the 0.2–0.5 lines; not frozen.

**Task 6: 01 The Eye** (`parts/p01_the_eye.py`)
- **1.1:** The street at dusk, a crane down. The gas lamp flicker is a light-energy noise on the lamp.
- **1.2:** Each tray item is placed by a hand (`_contact` plus `_carry`): teapot, cup and saucer, toast, egg
  cup.
- **1.3:** The stair ascent: 5.1's step-over-step run upward, both hands on the tray (two contacts).
- **1.4:** The old man sits up (`rise_in_bed`) and smiles (`PLEASANT`). The tray is set down by the
  narrator's hands on the bed table or the old man's lap.
- **1.5:** The strongbox lid opened by the old man's hand before the shot (shown open; allowed between
  shots). A rack focus.
- **1.6:** Over the shoulder, his head turns (`eyes` plus head yaw).
- **1.7:** An ECU of the old man's left eye with the film-eye cataract of 3.14; a slow blink.
- **1.8:** A CU of the narrator. The cup trembles on its saucer in his own hand: a hand tremor layer of
  6–8 Hz, 0.6°, with the cup `_carry`d.
- **1.9:** The narrator's room as a time-lapse. Light keys run day → dusk → candle over 10 s; he sits
  (`_sit`), breathing and blinking.
- **Part checks:** contacts on the tray, the cup and the saucer; held props drift under 1 cm; the
  continuity lid exception in 1.5.

**Task 7: 02 Seven Nights** (`parts/p02_seven_nights.py`)
- **2.1:** The corridor. He carries the closed lantern (`hang`). The long-case clock hands are keyed to
  11:56 → 11:58.
- **2.2:** The `watch_macro` set restyled to the spec: open face, white enamel, Roman numerals, blued hands,
  50 mm. The minute hand reaches 12; it is in his palm (contact).
- **2.3:** A macro of his fingertips turning the chamber door's own latch (contact). The latch moves only
  with the fingers.
- **2.4–2.5:** The door opened a sliver by his hand. The lantern eases in, then his head, at 1 cm/s. The
  clock behind sweeps an hour (keyed hands).
- **2.6–2.7:** The thumb cracks the shutter open: v3's 3.13 thumb and shutter keys, re-used; the thread of
  light on the closed eye.
- **2.8:** Six nights, about 2.4 s each, with "Night II" … "Night VII" text cards.
  - `worn` rises 0.1 per night, to 0.6: darker under the eyes (a face-shape or material darkening),
    skin desaturation, eyelids heavier (blink baseline 0.15 × worn).
- **2.9:**
  - Morning; his hands throw open the shutters (contacts on each shutter leaf).
  - The NS and OM lines, with gestures and lips.
  - The old man sitting up, listening and nodding.
- **Part checks:** contacts on the watch, the latch, the door and the shutters; `worn` monotonic (the
  continuity check); clock hands moving only by their keys.

**Task 8: 05 Concealment** (`parts/p05_concealment.py`)
- **4.1:** The void, calm (`_converse`, `energy=0.3`).
- **4.2:** The lantern on the floor throwing his shadow on the wall. Only the shadow is in frame: he works
  (CMU `113_*` kneeling-work clip or the v3 kneel layer) between the lamp and the wall.
- **4.3:** His hands lift the three `CH_Plank_Loose_*` one by one (contact on each); they rise and are set
  aside; the joists below (`CH_Scantlings`).
- **4.4:** Top-down: his hands set them back; they end at z −0.025.
- **4.5:** An MS; he wipes his hands (a rubbing layer: both hands in contact at the palms) and laughs
  (`chuckle`, plus a voiced laugh synthesised in the mix, mark `4.5/laugh_group`).
- **4.6:** A CU of the long-case clock face at 4:00. Four strikes (marks `4.6/clock_strike` ×4, from the
  production plan's cue list), then the knock (mark `4.6/knock3`).
- **Part checks:** each plank moves only while a hand holds it (held-prop drift under 1 cm); the planks at
  rest after 4.4 (continuity).

**Task 9: 07 Epilogue** (`parts/p07_epilogue.py`)
- **6.1:** Black, one heartbeat.
- **6.2:** The void, a CU; he whispers "Hearken." (lips; the Chatterbox line at exaggeration 0.3).
- **6.3:** The credits, fading out over their last 1.5 s. The text, in this order:
  - "Based on 'The Tell-Tale Heart' by Edgar Allan Poe (1843)";
  - "An FLV film";
  - the credit lines marked **credit** in `assets/THIRD_PARTY.md`;
  - "Motion: The 100STYLE Dataset – Ian Mason (CC BY 4.0); CMU Graphics Lab Motion Capture Database";
  - "Music: Frédéric Chopin, recordings from Musopen (CC0)";
  - "Sound: Freesound (CC0)";
  - "Voices: Chatterbox (Resemble AI, MIT)";
  - "Lip sync: Wav2ARKit".
- **Checks:** lips on 6.2; the credits' text objects exist and are in the camera's view.

### Task 10: Part 03, The Eighth Night (rebuilt with today's toolkit, plus 3.2 and 3.9)

**Files:**
- Modify: `stories/the_tell_tale_heart/preview_v2.py`:
  - add shots 3.2 and 3.9 to `SHOTS`, with lines from `film.SHOTS`;
  - add the voice for 3.2 (`3.2_N.wav`, generated in Task 4); 3.9 has no line;
  - add the commands `check` and `stills`, composed from Task 4's checks;
  - set `OUT` to `FILM/parts/03_eighth_night`.
- Modify: `stories/the_tell_tale_heart/film_parts.py` (part 03's `timeline` path).

- [ ] **Step 1:** Add `check`. Run `build` and `check` with the current toolkit. Expected: FAIL. List every
  failure; these are the regressions to fix.
- [ ] **Step 2:** Fix each failure at its root cause. Re-run until `check` is OK.
- [ ] **Step 3:** Add 3.2 and 3.9:
  - **3.2:** an 85 mm macro of the door edge. His palm pushes the door at 0.5°/s (contact).
  - **3.9:** `sets.beetle_macro`, the beetle's taps on the "deathwatch" marks.

  Then `build` and `check` (OK), `stills`, and look at them.
- [ ] **Step 4:** Run `film_parts render 03_eighth_night`, then `mix`, then `mux`. Look at the contact sheet.
  Commit, push UAT, give the user the MP4.

### Task 11: Part 04, The Attack (Chatterbox voices, plus 3.19)

**Files:**
- Modify: `stories/the_tell_tale_heart/preview_v3.py`:
  - `VO` set to `audio/voiceovers/the_tell_tale_heart_v5`;
  - lines from `preview_v5/lines.json` (part 04's entries);
  - add 3.19;
  - add `check` and `stills` from Task 4's checks;
  - set `OUT` to `FILM/parts/04_the_attack`.

- [ ] **Step 1:** Add `check`. Run `build` and `check`. Expected: FAIL. List the failures.
- [ ] **Step 2:** Fix them at the root. `check` is OK.
- [ ] **Step 3:** Add 3.19: the street at night. A neighbour's window across the street lights up (a candle
  carried into view, its light keyed with the hand), then a curtain twitches, moved by a visible hand
  (contact). Then `build` and `check` (OK), `stills`.
- [ ] **Step 4:** Render, `mix`, `mux`, the contact sheet. Commit, push UAT, give the user the MP4.

### Task 12: The film: final mix, join, notes, hand over

**Files:**
- Create: `docs/tell_tale_heart_film_notes.md`. It covers:
  - the parts table: path, length, film start;
  - how to fix one part: rebuild, render, `mix`, `mux`, `join`;
  - the measured `check` numbers per part;
  - what is still open (the stand-in officers' faces, the credits maker name, licences to check before
    sharing).
- Modify: `docs/tell_tale_heart_v2_notes.md`, the "Where things are" row for the film.

- [ ] **Step 1:** Run `film_parts.py mix`, then `mux` for every part, then `join`. Expected:
  - the film's length = the sum of the parts' frames / 24, to within 1 frame;
  - `parts.json` lists 8 parts and 69 shots.
- [ ] **Step 2:** Make a 1 fps contact sheet of the whole film and look at every join. Check sync at one
  spoken line in each part (lip frames against the voice, within 2 frames).
- [ ] **Step 3:** Write the notes. Commit, push UAT, give the user the film path and the parts index.
