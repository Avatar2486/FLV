# The Visitors (5.1–5.15) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A 480p draft with sound of the Visitors sequence (shots 5.1–5.15). Three officers and the
narrator gesture with speech, react while listening, and act the narrator's breakdown.

**Architecture:**
- A new scene builder, `preview_v4.py`, follows `preview_v3.py`'s build / draft / render pattern and
  imports v3's generic helpers. Those helpers get small keyword parameters, so v4 can pass its own
  shots, clips and output folder.
- Co-speech gesture and listening layers go into `scripts/humans.py`. They are made from CMU gesture
  units, timed so each stroke lands on a stressed syllable detected in the voice.
- Measured checks run inside Blender: the self-check, plus a `check` command in `preview_v4.py`.

**Tech Stack:** Blender 5.3 (bpy, Eevee, built-in encoder), numpy, CMU and 100STYLE BVH, Chatterbox
plus Kokoro (`tools/chatterbox/.venv`, `.venv`), Wav2ARKit.

**Spec:** `docs/superpowers/specs/2026-11-23-visitors-officers-scene-design.md`

## Global Constraints

- Blender 5.3 on the Mac M4.
- **The draft:** 854×480, 24 fps, H.264 + AAC, written to
  `output/renders/the_tell_tale_heart_v4_visitors/draft_480p.mp4`. Frames go in `frames/480p/`
  (git-ignored).
- **No downloads.** Motion comes only from `assets/mocap/library/cmu`, `assets/mocap/cmu` and
  `assets/mocap/100style`. Anything missing: show the user a table of URL, size and licence first.
- **Voices:** Chatterbox with Kokoro reference voices, 16-bit PCM WAV.
- **Lips:** Wav2ARKit for every on-screen line. The build fails if the loudness fallback would be used.
- **Props:** nothing moves unless a hand moves it (door, candle, lanterns, hats, chairs, strongbox lid,
  teacup). A change between shots is allowed.
- **Gesture timing:** the stroke lands 0–0.15 s before the stressed syllable, never after it. Hands go
  back to rest only at pauses longer than 0.5 s. No unit is used twice in a row.
- **No doll:** every on-screen character moves in every 1 s window, by at least 0.5° summed over the
  spine, neck, head and arm bones.
- **Branch:** `visitors-v4`, not UAT. Commit after each task.
- **Names:**
  - `stories/the_tell_tale_heart/preview_v4.py`
  - `blender/scenes/tell_tale_heart_v4_visitors.blend`
  - `stories/the_tell_tale_heart/preview_v4/lines.json`
  - `audio/voiceovers/the_tell_tale_heart_v4/<shot>_<who>[_<n>].wav`

## Review Focus

1. **A gesture moves a hand that is holding something** (a lantern, the cup, a hat, the candle). That
   hand must stay put and the prop must stay in it. Pinned by the Task 2 held-hand assertion, and by
   Task 5's `check` measuring the distance from each prop to its hand.
2. **Seated gestures drive hands into thighs, the chair or a neighbour.** Pinned by Task 5's
   `check`: hand-to-body overlap for every pair of characters, every 4th frame.
3. **Chatter talks over an on-screen line, or two officers talk at once.** Pinned by Task 4's
   timeline assertion.
4. **A character holds still for more than a second while waiting for a cue.** Pinned by the
   stillness check (Task 5 `check`).
5. **A stand-in's height scale breaks the foot planting or root motion,** leaving feet floating or in
   the floor. Pinned by Task 3's foot-height assertion and the planted-foot slide in `check`.

---

### Task 1: Let v4 reuse v3's helpers

**Files:**
- Modify: `stories/the_tell_tale_heart/preview_v3.py`: `timeline()` (line 65), `_mocap_gait()`
  (line 835), `render()` (line 1510), `draft()` (line 1529)

**Interfaces:**
- Produces:
  - `timeline(shots=None, voice_fn=None) -> dict`
  - `_mocap_gait(humans, rig, track, first, last, hands_busy, fps=FPS, clips=GAIT_CLIPS)`
  - `render(part, parts, folder="frames", size=None, out=None)`
  - `draft(out=None, mix=None, blend_name="V3")`
  - Each `None` means v3's own value: `SHOTS`, `voice`, `OUT`, `soundtrack`.

- [ ] **Step 1: Write the check.** Load preview_v3 in Blender, call `timeline()`, and assert that each
  shot's `id`, `start` and `seconds` equal the committed
  `output/renders/the_tell_tale_heart_v3_attack/timeline.json` (tolerance 0.001 s).

  ```
  blender -b --factory-startup --python-expr "import sys,json; sys.path.insert(0,'stories/the_tell_tale_heart'); import preview_v3 as v; a=v.timeline()['shots']; b=json.load(open('output/renders/the_tell_tale_heart_v3_attack/timeline.json'))['shots']; assert [(s['id'],round(s['start'],3),round(s['seconds'],3)) for s in a]==[(s['id'],round(s['start'],3),round(s['seconds'],3)) for s in b]; print('V3 TIMELINE SAME')"
  ```
- [ ] **Step 2: Run it on the unmodified file.** Expected: `V3 TIMELINE SAME`. This is the baseline. If
  it fails, the voices differ from the teammate's: record which shots, then compare against this run's
  output instead.
- [ ] **Step 3: Add the keyword parameters.** Behaviour must not change when they are omitted.
  `draft()` uses `out` for frames and MP4, `mix(out_wav)` for the soundtrack, and `blend_name` in its
  log lines.
- [ ] **Step 4: Re-run Step 1.** Expected: `V3 TIMELINE SAME`. Also run
  `python3 -m py_compile stories/the_tell_tale_heart/preview_v3.py`, which must pass.
- [ ] **Step 5: Commit**

  ```
  git checkout -b visitors-v4
  git add stories/the_tell_tale_heart/preview_v3.py
  git commit
  ```
  Message: "v3 helpers take shots, clips and output folder (for v4)".

### Task 2: Stressed syllables and gestures (`scripts/humans.py`)

**Files:**
- Modify: `scripts/humans.py`
  - `_layer()` (line 474) gains `local=False`. When it is `True`, `offsets(frame)` returns
    `{bone: Quaternion}`, applied as `q_base @ delta` in bone-local space.
  - Add `stress_times`, `gesture_bank`, `gestures`, `listen`, `_selfcheck_gestures`.
  - The `__main__` self-check also calls `_selfcheck_gestures()`.

**Interfaces:**
- Produces:
  - `stress_times(wav) -> list[float]`: seconds from the start of the WAV.
  - `gesture_bank(rig, clips=GESTURE_CLIPS) -> list[dict]`. Each unit has `id`, `clip`, `energy`
    ("calm"/"agitated"), `stroke` (sample index), `n` (samples), and
    `rot: {bone: list[Quaternion]}` (deltas from the clip's rest).
  - `gestures(rig, wav, start_frame, energy=0.5, hands=("Left", "Right"), bank=None, seed=1) -> list[int]`:
    the stroke frames.
  - `listen(rig, start, end, speaker_rig, phrase_ends=(), seed=1)`.
  - `GESTURE_CLIPS`:
    - calm: `18_08`, `19_08`
    - agitated: `18_10`, `19_10`, `80_48`
    - shrug (calm): `111_25`, `113_16`, `141_21`
    - laugh (calm): `13_14`
    - All from `assets/mocap/library/cmu/<id>.bvh`.

- [ ] **Step 1: Write the failing self-check, `_selfcheck_gestures()`.**
  1. Write a 3 s, 16 kHz, 16-bit WAV to `bpy.app.tempdir`: a quiet 160 Hz hum, plus three 120 ms bursts
     at 0.6 s, 1.5 s and 2.4 s with +18 dB loudness and +60 Hz pitch. Assert that `stress_times`
     returns exactly 3 values, each within 0.05 s of a burst.
  2. Build `Narrator`, then `relax_arms`. Run `gestures(rig, wav, 1, hands=("Right",))`. Assert:
     - every stroke frame f satisfies `burst*24 - 0.15*24 - 1 <= f <= burst*24 + 1`;
     - no unit id repeats back to back (the function records its choices in `rig["gesture_log"]`);
     - every `Left*` arm bone's quaternion at frames 1–72 equals its value before the call (tolerance
       1e-4).
  3. Run `listen(rig2, 1, 72, rig, phrase_ends=[36])` on a second Narrator. Assert a head pitch change
     of at least 3° within frames 36–48.
- [ ] **Step 2: Run it.** Command: `blender -b --factory-startup --python scripts/humans.py -- --selfcheck`.
  Expected: FAIL with `NameError: stress_times`.
- [ ] **Step 3: Implement `stress_times(wav)`.**
  - 10 ms hops. Compute loudness (RMS dB) and pitch (autocorrelation, 70–300 Hz, voiced frames only).
  - Score = z(loudness) + 0.5·z(pitch rise over 50 ms).
  - Stresses are score peaks above 1.0, at least 0.25 s apart, inside voiced spans.
- [ ] **Step 4: Implement `gesture_bank(rig, clips)`.**
  - Bake each clip with `retarget()` onto `rig` at frames 50000+, read the upper-body bones' local
    quaternions per frame, then delete those keys.
  - Rest pose = the mean quaternion over the clip's lowest-motion second.
  - Split into units at wrist-speed minima. Keep units 0.6–2.5 s long whose peak wrist speed is above
    0.4 m/s. The stroke is the peak-speed sample.
  - Bones: `Spine1, Neck1, Head, {Left,Right}{Shoulder,Arm,ForeArm,Hand}`.
- [ ] **Step 5: Implement `gestures()`.**
  - For each stress from `stress_times`, in order, pick a unit of the matching energy (`energy >= 0.6`
    means agitated), randomly, never the previous id.
  - Place its stroke 1–3 frames before the stress.
  - Scale its deltas by `0.5 + energy` (slerp from identity), and its playback speed by
    `0.8 + 0.4·energy`.
  - When the next stress comes before the unit's retraction, hold the stroke pose until the next
    preparation. Retract only across pauses longer than 0.5 s.
  - Add a head nod (pitch 2–4°) on each stroke. Apply everything through `_layer(local=True)`, only on
    the bones of the given `hands`, plus spine, neck and head.
- [ ] **Step 6: Implement `listen()`.**
  - Gaze and head turn toward `speaker_rig`'s head, using the existing `eyes()` with mode
    `"listening"`.
  - A nod of 3–6° pitch over about 0.5 s at each phrase end, 70% of the time.
  - A weight shift (hips roll 1–2°) every 4–8 s.
- [ ] **Step 7: Re-run the self-check.** Expected: the existing lines, plus `humans gestures OK: 3
  stresses, strokes on time, held hand still, listener nods`.
- [ ] **Step 8: Commit** `scripts/humans.py`. Message: "Co-speech gestures and listening, timed to
  stressed syllables".

### Task 3: Stand-in officers and the teammate's specs

**Files:**
- Modify: `stories/the_tell_tale_heart/cast3d.py`
  - Add `HALE`, `BRANDT`, `MERCER` (stand-ins on `character="Narrator"`).
  - Add a `height` key for each, plus `OFFICER_HEIGHTS`.
  - Add expressions `PLEASANT`, `CHARM`, `FORCED_SMILE`, `FURY`, `HORROR`.
- Modify: `scripts/humans.py`: `build()` reads `spec.get("height")` and scales the rig uniformly to
  match it.
- Create: `docs/officers_cast_specs.md`

**Interfaces:**
- Consumes: `humans.build(spec)`.
- Produces:
  - `cast3d.HALE / BRANDT / MERCER` (dicts).
  - `preview_v4.top_hat(coll, rig) -> Object` and `preview_v4.star_badge(coll, rig) -> Object`, both
    parented to bones (written in Task 5's file, but tested here through a small build).

- [ ] **Step 1: Write the check (fails at first).** Build the three stand-ins plus the Narrator in an
  empty scene. Assert:
  - head-top heights are within 1 cm of 1.72 / 1.80 / 1.78 / 1.76 m;
  - all object names are unique;
  - each foot is within 1 cm of the floor in rest pose;
  - each hat's lowest point is 0–2 cm above the hair (downward raycast at 5 points);
  - each badge is 0–1 cm off the chest surface.
- [ ] **Step 2: Run it.** Expected: FAIL (`KeyError`/`AttributeError` on `HALE`).
- [ ] **Step 3: Implement the stand-ins.**
  - **Hale:** grey hair tint (0.55); dark brown wool (`poly_wool_herringbone`, tint (0.18, 0.15, 0.13));
    1.72 m.
  - **Brandt:** fair hair (1.3, 1.15, 0.8); navy wool (0.12, 0.14, 0.2); 1.80 m.
  - **Mercer:** black hair (0.35); charcoal (0.14, 0.14, 0.15); 1.78 m.
  - Shirts are tinted the coat colour, so they read as coats from a distance.
  - Write the expressions as ARKit weights, in the style of `FEAR` and `SLY`.
- [ ] **Step 4: Implement the props.**
  - `top_hat`: crown radius 0.085 m, height 0.16 m, brim radius 0.15 m, black felt material, parented
    to `Head` and fitted to the hair by raycast.
  - `star_badge`: 8-point copper star, 4 cm, on the left chest, parented to `Spine1`.
- [ ] **Step 5: Write `docs/officers_cast_specs.md`.**
  - Three specs in the exact JSON shape of `assets/characters/Narrator/params.json`.
  - **Hale:** 50s, `build` heavy, `Body_Overweight` 0.45, grey hair, `beard` "sideburns".
  - **Brandt:** early 20s, `Body_Skinny` 0.5, fair hair, no beard.
  - **Mercer:** 40s, lean, black hair, `beard` "moustache".
  - Ask for frock coat, waistcoat, cravat and top hat pieces if the generator has them.
  - Say that the swap is one line each in `cast3d.py` (`character="Hale"` …).
- [ ] **Step 6: Re-run the check.** Expected: `stand-ins OK` with the four heights printed.
- [ ] **Step 7: Commit**: `cast3d.py`, `humans.py`, `docs/officers_cast_specs.md`.

### Task 4: Voices, chatter and the timeline

**Files:**
- Create: `audio/voice_refs/officer_brandt.wav`, `audio/voice_refs/officer_mercer.wav`. Make them with
  a one-off `.venv/bin/python -I -c` call to `kokoro_onnx.Kokoro("voices/kokoro/kokoro-v1.0.onnx",
  "voices/kokoro/voices-v1.0.bin")`: two male voices distinct from each other and from the existing
  refs, 8–10 s of neutral text, 16-bit PCM. Record the voice ids in the notes (Task 9).
- Create: `stories/the_tell_tale_heart/preview_v4/lines.json`
- Create: `stories/the_tell_tale_heart/preview_v4.py`: module constants and `timeline()` only, for now.

**Interfaces:**
- Consumes: `preview_v3.timeline(shots, voice_fn)` (Task 1).
- Produces, in `preview_v4`:
  - `SHOTS`: list of `(id, [(line_key, who)], minimum_s)`.
  - `CHATTER`: list of `(shot_id, offset_s, line_key, who)`.
  - `timeline() -> dict`: v3's shape plus `"chatter": [{"file", "who", "line", "start", "seconds"}]`.
    It is written to `OUT/timeline.json`.

- [ ] **Step 1: Write the timeline assertion** (a `check_timeline()` in `preview_v4`):
  - no chatter line overlaps an `NS`/`O1`/`O2`/`O3` line (50 ms tolerance);
  - no two chatter lines overlap;
  - every chatter line lies inside shots 5.7–5.13;
  - total length is at least 170 s.
- [ ] **Step 2: Run it.** Command: `blender -b --factory-startup --python stories/the_tell_tale_heart/preview_v4.py -- timeline`.
  Expected: FAIL (no lines yet).
- [ ] **Step 3: Write `lines.json`.**
  - The planned lines, verbatim from `stories/the_tell_tale_heart/timeline.json` shots 5.1–5.15:
    - `N` → `narrator.wav`, exaggeration 0.5
    - `NS` → `narrator.wav`, 0.6; 5.15 at 0.9
    - `O1` → `officer.wav`, 0.5
    - `O2` → `officer_brandt.wav`, 0.6
    - `O3` → `officer_mercer.wav`, 0.4
  - 12 chatter lines, 4–9 words each, in 1840s idiom:
    - Topics: the cold, the hour, the watch-house, a fire across the Schuylkill, a lame horse, supper
      waiting.
    - Spread across O1, O2 and O3; the narrator answers twice (`NS`, cheerily) in 5.7.
    - Keys: `5.7_O2_c1` and so on.
- [ ] **Step 4: Generate the voices.** Run
  `tools/chatterbox/.venv/bin/python -I scripts/chatterbox_lines.py stories/the_tell_tale_heart/preview_v4/lines.json`.
  Expected: every `out` file exists. Check each with `wave.open`: 16-bit, longer than 0.5 s.
- [ ] **Step 5: Fill in `SHOTS` and `CHATTER`.** Shot minimums come from the production plan. Chatter
  offsets go in the narration's gaps. Re-run Step 2. Expected: `V4 timeline OK: <n> s, 12 chatter
  lines`.
- [ ] **Step 6: Play the voices to the user.** Make a quick listen (Hale, Brandt and Mercer, one line
  each, joined in a WAV under `output/samples/voices/`) and say where it is. Not a blocking gate.
- [ ] **Step 7: Commit**: the refs, `lines.json`, the voices, `preview_v4.py`.

### Task 5: The scene, cameras, and the `check` command

**Files:**
- Modify: `stories/the_tell_tale_heart/preview_v4.py`
  - Add `build()`: sets via `sets.entry`, `sets.kitchen`, `sets.chamber` and `sets.street`, with the
    street placed beyond the entry door.
  - Characters via `humans.build`; lanterns via `sets.dark_lantern`; `top_hat`, `star_badge`.
  - Chairs: Poly Haven `dining_chair_02`. Tea tray and cup via `lib.mug`.
  - A camera per shot, bound to timeline markers as in v3. Camera moves:
    - 5.1: backward steadicam
    - 5.10: handheld noise plus defocus pulses
    - 5.11: 360° orbit
    - 5.13: dolly zoom, 35→24 mm while dollying in
    - 5.14: cuts plus a shake on each beat
    - 5.15: push, then a whip pan
  - Lights per the spec's light plan, keyed over time: warm in 5.7, draining from 5.8, cold from 5.12.
  - At the start of `build`, assert that `voices/wav2arkit/config.json` and `.venv` exist, so lips
    never fall back to loudness.
  - `check()`: measured checks, printed with numbers, asserted at the thresholds below.
  - `stills()`: one 480p frame from the middle of each shot, saved to `OUT/stills/`.

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces:
  - Commands `build | check | stills | test57 | draft`.
  - Rig names `Narrator, Hale, Brandt, Mercer`.
  - Props `V4_Candle, V4_Lantern_{Hale,Brandt,Mercer}, V4_Hat_*, V4_Chair_{Narrator,Hale,Brandt,Mercer}, V4_Cup`.

- [ ] **Step 1: Write `check()`** with these thresholds:
  - hand-to-other-body overlap = 0 (BVH overlap of each rig's hand vertices against the other bodies),
    every 4th frame;
  - each held prop keeps a constant offset from its hand (within 1 cm) while held;
  - planted feet slide under 2 cm/s;
  - the stillness rule from Global Constraints, for each character in each shot where they are on
    camera;
  - hats keep a constant transform relative to the head, except when a hand is holding them.
- [ ] **Step 2: Build with no animation, then run `check` and `stills`.** Expected: `check` passes
  (nothing moves yet, so stillness is skipped while there are no keys). Look at the 15 stills: framing
  matches the shot list, and each set reads.
- [ ] **Step 3: Commit**: `preview_v4.py`, plus the scene `.blend` (git, about 50 MB, as v3's is).

### Task 6: The chamber chat (5.6–5.10) and the 5.7 test for the user

**Files:**
- Modify: `stories/the_tell_tale_heart/preview_v4.py`: `_act_chamber(tl)`.

**Interfaces:**
- Consumes: `humans.gestures`, `listen`, `lip_sync`, `eyes`, `blinks`, `breathe`, `sway`, `reach`,
  `grip`, `hang`; v3 `_mocap_gait(clips=…)`.

- [ ] **Step 1: Animate 5.6.**
  - The narrator walks in carrying his chair: two-hand `reach` to the chair's back rail, with the chair
    following the hands.
  - He sets it with its legs on `CH_Plank_Loose_*` and sits. The sit comes from CMU `113_15`, the seated
    hold from `114_05`.
  - The officers are already seated (between-shot change), hats on their knees, under one hand each.
- [ ] **Step 2: Animate 5.7–5.10.**
  - Every voiced line, chatter included, gets `lip_sync`.
  - `gestures(energy=0.35)` for the officers, using the free hand only.
  - `listen()` for everyone who isn't speaking; `breathe` and `sway` throughout.
  - A laugh unit plus a `PLEASANT` face on one officer at a chatter punchline.
  - The narrator's arc faces: `CHARM`, then fading at 5.8, then `FORCED_SMILE` at 5.10.
  - 5.8: a hand to his temple; the skin desaturates (keyed material).
  - 5.10: sweat shine (roughness down), panic `breathe`.
  - 5.9: dust motes on the seam jump on the heartbeat (`_beat`-style pulse from `HEARTBEATS`).
- [ ] **Step 3: Run `check`.** Expected: all pass for frames in 5.6–5.10.
- [ ] **Step 4: Render the test.** `test57` renders 10 s of 5.7 at 480p with its own soundtrack slice
  to `OUT/test_5.7_480p.mp4`. Show it to the user and get feedback on the gestures before going on.
  This is a gate.
- [ ] **Step 5: Commit.**

### Task 7: The arrival and the search (5.1–5.5)

- [ ] **Step 1: Animate 5.1.**
  - A stair descent from CMU `113_19` / `114_07` (the down segment), with the hips' height following the
    set's 0.214 m steps. The feet are framed out in the medium shot; this is recorded as Still open.
  - The candle hangs from his right hand (`hang`).
  - A `CHARM` face.
- [ ] **Step 2: Animate 5.2.**
  - His left hand opens `EN_DOOR_Panel` (`reach` plus the door following the hand, as in v3's door).
  - The officers stand outside with their lanterns (`hang`).
  - Breath fog: small emissive wisps at their mouths on exhales, from the `breathe` phase.
  - Hale's free hand lifts his hat off (`reach` to the brim, the hat following the hand) while he says
    his line with `gestures`.
  - The other two `listen`, then glance past the narrator.
- [ ] **Step 3: Animate 5.3–5.5.**
  - 5.3: NS with `gestures(energy=0.5)`. The design calls for a wave-off on "dream" and an open arm on
    "come in"; if no bank unit lands there, key the one stroke by hand.
  - 5.4: they walk with lanterns (`_mocap_gait`); the beams sweep from the lantern hands; the
    narrator's "Search well" arm sweep.
  - 5.5: his hand lifts the strongbox lid; the officers lean in and nod (`listen`).
- [ ] **Step 4: Run `check`** on 5.1–5.5. Expected: all pass.
- [ ] **Step 5: Commit.**

### Task 8: The breakdown (5.11–5.15)

- [ ] **Step 1: Animate 5.11.**
  - He rises (CMU `113_15`, the stand segment) and argues with `gestures(energy=0.9)`, which uses the
    agitated units.
  - He paces with heavy strides: `_mocap_gait(clips=(("Angry_FW", 240), ("Rushed_FW", 240)))` along a
    there-and-back track.
  - Faces go from `TENSE` to `FURY`.
- [ ] **Step 2: Animate 5.12.** Both hands `reach` the chair's back. The chair follows the hands through
  a swing arc, then grinds along the planks (scrape mark in the timeline). The officers glance at him
  and carry on chatting.
- [ ] **Step 3: Animate 5.13–5.14.**
  - The officers are `PLEASANT`. Mercer lifts the cup (`reach`, then the cup follows), sips, and puts it
    back.
  - The narrator is `HORROR`, with `tremble()`.
  - 5.14: the cut points and shake keys go on the heartbeat times from `HEARTBEATS` (the cameras come
    from Task 5).
- [ ] **Step 4: Animate 5.15.**
  - He leaps up and stamps: a keyed stamp layer with a heel strike on a beat.
  - He points at the planks: a right-arm `reach` toward the planks.
  - `FURY`, with lips on the NS line.
  - The officers startle (`startle(legs=False)` while seated, then rise).
- [ ] **Step 5: Run `check`** on 5.11–5.15. Expected: all pass.
- [ ] **Step 6: Commit.**

### Task 9: The soundtrack, the full draft, and the notes

**Files:**
- Modify: `stories/the_tell_tale_heart/preview_v4.py`: `soundtrack(out_wav)`.
- Create: `docs/tell_tale_heart_v4_visitors_notes.md` (same structure as the v3 notes).
- Modify: `docs/tell_tale_heart_v2_notes.md` ("Where things are" row).

- [ ] **Step 1: Write `soundtrack()`.**
  - Voices at −18 dB RMS. Chatter 12 dB under, low-passed and slowed 3% from 5.10 on.
  - Recorded effects: `stairs_footsteps`, `knock_street_door`, `door_latch`, `door_creak`,
    `chair_scrape`, `floorboard_creak`, `street_night`, `watchman_rattle`.
  - Synthesised from `sound_library.sfx` for the cues with no recording: stomp, coin, chair_place,
    steps_group, cup_clink, laugh_group, ringing.
  - Score from `film.SHOTS` cues.
  - `HEARTBEATS = [("5.8", 2.0, 60, 150, "5.15", 6.0, True)]`. It is unmuffled from 5.13.
- [ ] **Step 2: Check before the draft.** Run `stills` and `check` on the whole scene. Look at the 15
  stills. Expected: `check` passes, and no frozen, clipping or floating thing shows in the stills.
- [ ] **Step 3: Run the draft.** Command:
  `blender -b blender/scenes/tell_tale_heart_v4_visitors.blend --python stories/the_tell_tale_heart/preview_v4.py -- draft`.
  Time the first 50 frames and tell the user the estimate. Expected: `draft_480p.mp4` about 2:52,
  with picture and sound in sync. Check this with the lip frames of one officer line.
- [ ] **Step 4: Write the notes.**
  - What was built.
  - Measured numbers from `check`.
  - Which Kokoro voice ids were used.
  - Still open: the stand-in faces, the stair feet, any thresholds that only just passed.
- [ ] **Step 5: Commit and hand over.** Commit the code, notes and timeline (the MP4 is git-ignored as
  `draft_*`). Give the user the MP4 path.
