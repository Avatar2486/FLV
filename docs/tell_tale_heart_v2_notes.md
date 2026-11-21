# Tell-Tale Heart v2: what we researched, built and struggled with

This is the project log for the "human-like" rebuild: what was chosen, what was researched, which
problems came up and how each was found and fixed, and what is still open. The detailed research, with
numbers and every source, is in [`realism_research.md`](realism_research.md). Asset licences and credit
lines are in [`../assets/THIRD_PARTY.md`](../assets/THIRD_PARTY.md).

## Where things are

| What | Where |
|---|---|
| Latest preview film, shots 3.1–3.10 ("the eighth night"), 52.5 s, 1080p | `output/renders/the_tell_tale_heart_v2_preview/the_tell_tale_heart_v2_preview.mp4` |
| Samples to choose from (voices, characters, motion, sound, street) | `output/samples/` (the README there explains each) |
| Character and motion toolkit | `scripts/humans.py` (self-check: `blender -b --factory-startup --python scripts/humans.py -- --selfcheck`) |
| Preview scene builder, render and mix | `stories/the_tell_tale_heart/preview_v2.py` |
| Voices: batch generator, reference voices, generated lines | `scripts/chatterbox_lines.py`, `audio/voice_refs/`, `audio/voiceovers/the_tell_tale_heart_v2/` |
| Sets: chamber, corridor, 1843 street | `stories/the_tell_tale_heart/sets.py` |
| Character looks: old man, narrator, expressions | `stories/the_tell_tale_heart/cast3d.py` |
| Gait measurements | `scripts/gait_stats.py`, `output/samples/motion/gait_measured.json` |
| Downloads: models, packs, mocap, voices, music | `scripts/download_film_kit.sh` (re-runnable), `scripts/fetch_100style.py`, `scripts/fetch_sfx.py` |

Kept local, not in git: rendered PNG frames, MakeHuman zips, the Kokoro and Wav2ARKit models, the
Chatterbox environment (`tools/`) and the Freesound key in `.env`.

## What was chosen

| Area | Choice |
|---|---|
| Characters | **Our own generated characters** (`assets/characters/`, since 2026-11-21): rigged, scanned skin textures, 47 ARKit-named face shapes built on their own mesh; Poly Haven fabrics on the clothes. (Before: MPFB / MakeHuman.) |
| Voices | **C, Chatterbox** (MIT). Each character's reference voice is a synthetic Kokoro voice, so no real person's voice is cloned. |
| Motion | **B, 100STYLE** motion capture (CC BY 4.0), with CMU clips (free) for creeping and other actions |
| Sound | **B**, recorded CC0 Freesound effects, with Chopin (Musopen, CC0) under the drones |
| Lip sync | Wav2ARKit (Apache-2.0), which turns speech audio into the 52 face shapes; it replaced Rhubarb, which looked "not human-like" |

**Your rules:**
- Lips move like real speech.
- **Nothing moves on its own:** a hand is on every prop that moves.
- Show URLs, sizes and licences before downloading anything.

## How a shot is made
1. **Characters:** `humans.build()` appends each of our characters from `assets/characters/` with skin,
   eyes, hair, clothes and the face shapes. Skin under the clothes was removed when it was generated, so it
   can't poke through.
2. **Body motion:**
   - Motion capture is retargeted onto the rig (`retarget`).
   - The feet are locked to the floor where they're planted (`plant_feet`).
   - Hand-built layers go on top: breathing, sway, startle, rising from bed, chuckle, leaning in.
3. **Hands and props:**
   - Arm IK (`reach`) puts hands on doors, rings and mattresses.
   - `grip` curls the fingers.
   - `hang` hangs carried things from the hand. A prop only moves when a hand moves it.
4. **Face:**
   - Wav2ARKit lips follow the voice.
   - Gaze, blinks and saccades follow the "Eyes Alive" statistics.
   - Expressions are keyed per beat.
5. **Voices:** Chatterbox lines are generated in one batch from a JSON list, then get the film's voice
   effects at the mix.
6. **Render:** Eevee at 1920×1080, 48 samples, about 4–7 s per frame on the M4. Cameras switch on
   timeline markers.
7. **Mix:** room tone, Chopin and recorded effects are placed on the frames where the action happens,
   then loudness-normalised (−16 LUFS).

## What we researched
Each item is applied in `scripts/humans.py`. Numbers and sources are in `realism_research.md`.

| Topic | Key findings we used |
|---|---|
| **Lips** | Jaw and lips are separate actions (JALI). Neighbouring sounds blend. Lips close fully on m, b and p. The face leads the sound by about a frame. The mouth rests closed. |
| **Eyes** | Saccade sizes follow P(A) = 15.7·e^(−A/6.9). Duration is 25 ms + 2.4 ms per degree. Speakers look at listeners 3.1 ± 3.2 s at a time; listeners 7.9 ± 1.6 s. Gaze shifts over 15° bring the head along. |
| **Blinks** | Close in about 80 ms and reopen in about 150 ms. Some are partial. They cluster at speech pauses and with big gaze shifts. |
| **Breathing** | Inhale 40%, exhale 45%, rest 15%. A quick in-breath comes before each phrase. Rates by style: calm 13, old 17, anxious 22, panic 32 and sleep 12 breaths per minute. |
| **Idle body** | Slow postural sway, never fully still. |
| **Startle** | A head-to-toe wave (Brown 1991). Blink at 20–40 ms, then the neck, shoulders, arms and legs in turn, up to 395 ms. |
| **Creeping and tiptoeing** | Measured 20 real recordings. Sneaking is slower, with shorter steps, knees bent 2–3× more, a 25–50° lean, both feet down up to 68% of the time and pauses up to 26%. Tiptoeing raises the heels about 13°. |
| **Footskate** | Lock contacts, use two-bone leg IK and blend over 3 frames (Kovar et al.). Sliding fell from 3–7 to 1–2 cm/s. |
| **Rising from bed** (older adults) | The head lifts first. One elbow props and both arms push. The trunk curls only 37° (young people 63°). The knees draw up late, to about 75° (Watanabe 2019; Cordo 2003). A short "register" beat comes before the move. |
| **Laughing** | "Ha" pulses about 75 ms long, about 210 ms apart (about 5 Hz). 4–12 pulses per breath, all on one out-breath. About half of laughs are silent. Cheeks raised plus lip corners up (AU6 + AU12). A stifled laugh keeps the mouth shut. Animators break a laugh into small-small-big. |
| **Hands** | The palm on MPFB hands faces −Z. Pronation and supination happen in the forearm, not the wrist. Wrist bends are kept near 15°. Carried things hang plumb and swing like a pendulum. |
| **Moonlight and grain** | A large soft area light causes traced-shadow speckle in Eevee. The fix is a small source with jittered shadows. |
| **The 1843 street** | Philadelphia row houses: red brick, white marble steps, shutters, brick sidewalks with stone curbs, wet cobbles, gas lamps. Built in three depth layers, warm gaslight against cold moonlight, readable silhouettes, and sound for what isn't shown. |
| **Models and data** | We checked free, commercially usable options. Chosen: MPFB, 100STYLE, CMU, Chatterbox, Kokoro, Wav2ARKit, Freesound CC0, Musopen. Rejected for licence reasons: Free3D and BlendSwap (personal use), Mixamo (login, can't share), F5-TTS, XTTS, Fish S2 and VibeVoice (non-commercial), LAFAN1 and Bandai Namco (non-commercial), BBC sounds (non-commercial). |

## What we struggled with, and how each was fixed
Most fixes were checked by measurement rather than by eye: mesh overlap tests (BVH), the depth of
skin inside surfaces, joint angles and raycasts. Those checks were one-off scripts and are not in the
repo; the arm, retarget and feet checks are in `humans.py --selfcheck`.

### Downloads and tools
| Problem | Cause | Fix |
|---|---|---|
| The safety check blocked the big download twice | Automated downloads of many files | You ran `scripts/download_film_kit.sh` yourself. Never worked around. |
| The 100STYLE download kept dropping at 159 MB | The Zenodo connection resets | Read only the needed files from the zip, using HTTP range requests (`fetch_100style.py`) |
| Re-running the kit failed with "No installable packages" | The add-on was already installed | Skip add-ons that are already present |
| Chatterbox couldn't add its watermark and crashed | setuptools 84 has no `pkg_resources` | Pinned `setuptools<81` in its own environment |
| Freesound: incomplete reads, then 502 errors site-wide, narrow searches with no results, the manifest lost on a crash | A Freesound outage, and over-specific queries | Retries with back-off, fallback queries, manifest saved after each cue |
| Chatterbox WAVs wouldn't open in Blender's Python | They were 32-bit float WAVs | Saved as 16-bit PCM |
| Shell surprises | zsh doesn't split `$VAR`; ffmpeg ate stdin in loops; this ffmpeg has no `drawtext` | Explicit arguments, `-nostdin`, no text overlays |
| Blender 5 API surprises | Actions have no `.fcurves` (layered actions); `matrix_world` is stale after moving until `view_layer.update()` | A helper that walks layers and channel bags; an update before reading |

### Faces and lips
| Problem | Cause | Fix |
|---|---|---|
| Lips grimaced with clenched teeth | The jaw opened too little against the lip raisers | `SPEECH_GAIN` rebalances them (jaw ×2.4) |
| The mouth hung open at rest | MakeHuman's neutral mouth is slightly open | A resting lip seal (`mouthShrugLower` 0.3) that gives way as the mouth opens |
| Rhubarb lips weren't human-like | Fixed mouth shapes | Replaced with Wav2ARKit; its resting offset is removed, and it is gated by voice activity |
| The chuckle looked mechanical, and his tense face vanished afterwards | An even 4.5 Hz shake, the face keyed every 3 frames, and it ended by zeroing the shapes | Rebuilt from laughter research; it settles back to the given expression |
| His face was too dark to read in 3.3 | The half-open door shadowed the gap light | Moonlight now comes through the same slot the camera looks through |

### Body layers and motion capture
| Problem | Cause | Fix |
|---|---|---|
| Breathing piled up (the neck drifted 62 mm) | Each layer read poses already changed by earlier frames | Read the base pose for every frame first, then key |
| Rotations went the wrong way (hands swung backward) | Applied about rest-pose axes | Applied in the posed orientation |
| Some bones ignored the layers | They were in Euler mode | `build()` sets all bones to quaternions |
| Startle directions were wrong, with too much head dip | Sign errors | Signs fixed and measured (shoulders +14 mm); neck 10°→6°, head 4°→2° |
| Retargeted root motion exploded | Divided by CMU's root rest height, which is about 0 | Scaled by the leg-length ratio |
| The self-check reported 360° errors | q and −q are the same rotation | Compare with min(angle, 360° − angle) |
| `plant_feet` did nothing, then straightened the legs | A stale `matrix_world`; locking the ankle | Update first; move the body and lock the ball of the foot |
| 100STYLE clips included turnarounds | The window was taken from the start of the clip | `straight_stretch()` picks the straightest window |
| The creep walked sideways | A sign error in the facing direction | `(y, −x)` |
| `reach()` never returned the arm to where it started | Same as the layer bug: it read poses after keying | Read first; the self-check measures 0.000° after release |
| The old man's toes poked through the blanket during the startle | The startle's 4° hip flex lifted the feet | `startle(legs=False)` for someone in bed |
| The old man sat up like a jack-knife | One hip hinge in 0.45 s | `rise_in_bed()` from the research: head first, elbow prop, arm push, knees up late |

### Clothes and skin
| Problem | Cause | Fix |
|---|---|---|
| Fabrics looked green | The texture's own colour | Desaturate, then tint |
| A spot on the calf | The sock top showing through the trousers | Masking from inner to outer garments (the first try, masking every garment against every other, cut holes) |
| A dark hole inside the collar | The pack's own delete group, and ours, hid neck skin at the collar opening | Skin within 6 cm of any garment opening stays visible |
| A shirt cuff flipped out into a flap | The wrist took the hand's whole twist | The forearm takes 3/4 of it (as in real arms) |

### Props, hands and the set: nothing may clip or float
| Problem | Cause | Fix |
|---|---|---|
| The old man, pillow and blanket floated about 20 cm above the mattress | An old comment said the mattress was at 0.62 m; a raycast found 0.44 m | Everything moved onto the real mattress (`sets.py`) |
| His feet were inside the footboard | The rig was placed at y 0.27; the footboard is at 0.21–0.30 | Moved up the bed |
| The blanket floated, was lumpy, poked or terraced | It was a flat box, then over-dilated | Shaped over his legs with raycasts and smoothing; tucked in at the foot; follows his legs with shape keys |
| The narrator's face and shoulder were inside the wall or jamb (4–6 cm) | He stood 6 cm too far toward the jamb | Square in the doorway, leaning in only as far as the door has opened |
| The lantern and his hand went through the closed door; his hand was inside the door handle | They were placed where the closed door is | The lantern is held low behind the door; his palm pushes the door at chest height |
| All hands faced the wrong way | `hand_frame()` assumed the palm faces +Z; MPFB's faces −Z | Fixed once in `hand_frame()`; measured on both hands of both characters |
| His fingertips sank 4–5 cm into the door | The rig's fingers curve toward the palm | Hand tilted 12°, wrist 4.8 cm out; measured 1–4 mm off |
| His hand looked pressed on "glass" by the door edge in 3.6 | It stayed on the door after the push | It leaves the door and cradles the lantern from below |
| The lantern tipped sideways | It was bolted to the hand | `hang()`: plumb by the ring's top wire, pendulum swing |
| The left wrist bent 56°, crumpling the cuff | A fixed hand direction against a raised forearm | `reach(wrist=…)`: the hand follows the forearm, bent 15° |
| The right hand went through the lantern; the lantern went into his thigh, then his belly | Fingers pointed into it; hold positions were too close; the path to the lantern crossed it | Re-placed, routed beside and below; measured: fingers on metal 2–10 mm, nothing else touching |
| The close-up in 3.3 couldn't see his face | The door hid it | Computed the viewing window (123–151° around his head); camera at about 140° |

### Light and rendering
| Problem | Cause | Fix |
|---|---|---|
| Fine grain on every moonlit surface, which was the old "haze speckle" | A 1.2 m area light's traced soft shadows in Eevee. Didn't help: more samples (160), more shadow rays or steps, finer shadow maps, hiding the haze, raytracing off; jitter on the big light gave blocky tiles. | A 0.15 m moon light with jittered shadows; fills cast no shadows |
| Three render workers were slower than one | 16 GB RAM: 5.4 GB of swap in use | One worker, about 4–7 s per frame; the full preview takes about 2¼ hours |
| Could other machines help? | Eevee needs a decent graphics chip | Lenovo IdeaPad S145 (Radeon Vega 3/8): much slower, and frames from two different chips can flicker. Oracle free ARM server: no graphics chip at all. The M4 Mac is the best machine here. |

### Our own slips (caught and fixed)
- A too-wide text replacement in `humans.py` deleted `hold()`, `chuckle()` and `tremble()`. Found right
  away by listing the functions, and restored from git.
- Two measurement mistakes would have given wrong answers:
  - reading vertex groups by index on a masked (evaluated) mesh, whose indices no longer match
  - a depth formula that called a point under the lantern's base "inside"

  Both were caught by cross-checking, and fixed before any decision relied on them.
- An early grain test changed a setting that did nothing: samples alone could never fix it.

## Characters replaced with ours (2026-11-21)
The MPFB / MakeHuman old man and narrator were replaced by two characters from our own generator, made
from cast specs (fixed choices instead of random ones). What changed in the code:

| Where | Change |
|---|---|
| `scripts/humans.py` `build()` | Appends `assets/characters/<character>/<character>.blend` instead of building with MPFB; no MPFB add-on or MakeHuman packs needed. Bones renamed to the toolkit's names (`Spine` -> `LowerBack` ...); hands re-rolled so `hand_frame()` and `grip()` keep their meaning (palm on -Z, +X curls); `film_eye`, fabrics and tints as before |
| `grip()` | Our hands have five fingers with three joints each (MPFB had one chain): about 80 degrees per finger at curl 1 |
| `_key_eyes()` | Eyeballs turn on the `LeftEye` / `RightEye` bones by the exact angle; `eyeLookUp/Down` shapes move the lids with them |
| `lip_sync()` | Same Wav2ARKit path (now also finds a Windows `.venv`); when the model isn't installed it falls back to `_speech_envelope()`: jaw from loudness, rounded or spread lips from the spectrum. Coarser (no m/b/p closures) |
| `SPEECH_GAIN`, `REST_SEAL` | Our jaw is a real hinge and our neutral mouth is closed: jaw gain 2.4 -> 1.3, rest seal 0.3 -> 0 |
| `cast3d.py` | Specs now name a character folder; the old man's brows and stubble are tinted grey so they don't glow in moonlight |
| `preview_v2.py` | The thumb that slips on the lantern catch is `RightHandThumb1` |
| Self-check | `humans.py --selfcheck` also loads both characters: bone and vertex-group names, finger curl toward the palm, gaze direction, and a ray test that a closed eyelid covers the eye |

Found on the way: the generator's palm test (the bow of the fingers) pointed at the back of the hand on
this basemesh, which would have curled fingers backward. The palm side is now taken from the thumb, which
sits a few cm off the knuckle plane on the palm side (checked with a render of a curled hand).

## Still open and known limits
- **The old man's nightshirt** is generated from the body and smoothed, so it is close-fitting rather than
  a loose gown. Most of it is under the blanket; a loose gown would need a cloth simulation.
- **Lips without Wav2ARKit** (any machine without `voices/wav2arkit/` and the `.venv`): the fallback follows
  loudness and brightness of the voice, not phonemes. Rebuild on a machine with the model for real lips.
- **The blanket** only follows his legs. It doesn't slide down when he sits up, which needs cloth
  simulation.
- **Shutter-slat moonlight** draws crisp stripes on the bed. It is plausible, but could be softened.
- **Grips** were measured on the MPFB hands (fingers 2–10 mm into what they touch). Our five-finger hands
  hold the lantern ring and cradle its base in the renders, but the contacts have not been re-measured.
- **The door push** keeps his wrist bent back about 89°. It is mostly hidden by the door, but stiff.
- **The corridor moon** (`co_moon`, a 0.8 × 1.3 m area light) is still large, so it may speckle like the
  chamber did. Fix it in the rebuild.
- **Render time:** about 2¼ hours per minute of film on the M4. Re-render only the shots that change; use
  720p drafts for checking motion.
- **Waiting on you:**
  - Motion choice A, B or C for the night visits (`output/samples/motion/`).
  - Feedback on this preview.
  - Then the full rebuild: all 69 shots with these characters, mocap, Chatterbox voices, recorded
    sound, the street, the body layers, props moved only by hands, and the earlier glitch fixes.

## How to rebuild the preview
```
tools/chatterbox/.venv/bin/python -I scripts/chatterbox_lines.py stories/the_tell_tale_heart/preview_v2/lines.json
blender -b --factory-startup --python stories/the_tell_tale_heart/preview_v2.py -- build   # about 1 minute
blender -b blender/scenes/tell_tale_heart_v2_preview.blend --python stories/the_tell_tale_heart/preview_v2.py -- render 1 1
.venv/bin/python -I stories/the_tell_tale_heart/preview_v2.py soundtrack         # optional: check the mix early
.venv/bin/python -I stories/the_tell_tale_heart/preview_v2.py mix                # soundtrack + final MP4
```
Rendering skips frames that already exist. Delete
`output/renders/the_tell_tale_heart_v2_preview/frames/` to render everything again.
