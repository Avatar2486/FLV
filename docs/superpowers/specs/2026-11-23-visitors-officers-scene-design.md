# The Visitors (shots 5.1–5.15): three officers, a 480p draft — design

## Intent

Make the Visitors sequence of *The Tell-Tale Heart* (production plan shots 5.1–5.15, about 2:52) as a
480p draft with sound, so the user can see how the officers' scene plays before anything goes to 1080p.

The user's bar: **when people talk they gesture; nobody stands still like a doll; every emotion and
detail is there.** This is the scene where the narrator's calm cracks, so it lives on faces, hands and
bodies more than any other part of the film.

## Goals

- All 15 shots, 5.1 to 5.15, cut together with voices, effects, score and the returning heartbeat, as
  `output/renders/the_tell_tale_heart_v4_visitors/draft_480p.mp4`.
- Four people on screen who are always alive:
  - The speaker gestures in time with the speech.
  - Listeners react: they nod, glance at the speaker, shift their weight, sip, laugh.
  - Everyone breathes, sways, blinks and moves their eyes.
- The narrator's emotional arc reads from his face and body alone (table below).
- The film's two rules hold:
  - Lips move like real speech, from the voice.
  - No prop moves unless a hand moves it: door, candle, lanterns, hats, chairs, teacup.
- A reusable gesture toolkit in `scripts/humans.py`, so later scenes (the prologue, the morning
  dialogue) get gestures for free.

## Non-goals

- 1080p. This is a draft for judging action and acting.
- The final officer characters. Stand-ins are used now (see Officers).
- Cloth simulation for coats, loudness normalisation, and a full collision pass. Contact is measured
  where it matters, as in v3.
- Any other sequence, or the v2/v3 re-renders.

## Anti-goals (a failure even if it renders)

- **Doll-like stillness.** Any character frozen for more than about 1 s while on screen.
- **Mechanical motion.** The same gesture repeated identically, gestures on a fixed rhythm, or
  everyone moving at once.
- **Lips without sound, or speech without lips.**
- **Clipping or floating.** Hands through bodies, chairs or each other; a hat floating off a head.
- **A prop moving on its own.**

## Constraints

- **Platform:** Blender 5.3 on the Mac mini M4 (Eevee).
  - 480p drafts render with Blender's own encoder, as `preview_v3.draft()` does.
  - The first 480p frames will be timed and an estimate given before the full run. Rough guess: 1.5–3 h
    for about 4,100 frames.
- **Motion data:** the CMU library is already on disk (`assets/mocap/library/cmu`, 2,548 BVH; free for
  any use). 100STYLE covers walks. **Nothing new is downloaded.** If something turns out to be
  missing, the URL/size/licence table goes to the user first.
- **Voices:**
  - Chatterbox (the user's pick), with Kokoro-made reference voices, so no real person is cloned.
  - Wav2ARKit lips. Both are installed on this Mac.
- **The character generator** that made OldMan and Narrator is on the teammate's Windows PC, not here.
- **Licences:** the speech-to-gesture AI models (DiffuseStyleGesture and others) learn from BEAT and
  ZEGGS data, which the user believes are non-commercial. The film is meant to be monetised, so they
  are out.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| **A (chosen)** | **Motion-capture gesture pieces, timed to the speech.** Cut gesture units out of CMU's conversation, quarrel, shrug and laugh clips, then place each so its stroke lands on a stressed syllable | Real human movement, free licence, no download. Needs a stress detector and a layering step on top of the existing pose |
| B | Hand-keyed gesture library (about 15 poses: palm-up offer, point, wave-off …) with the same timing rule | Full control, but hand-keyed arms look mechanical: exactly the doll feeling the user rejected |
| C | AI speech-to-gesture model | Automatic, but non-commercial training data, a large download, and a different skeleton |

The user handed over the how ("do the work"). A is the builder's call, stated to the user before this
document.

## Research brief (production design and acting)

### Period: Philadelphia, 1843
- **No police uniforms yet.** US forces adopted uniforms from 1854. New York's 1845 force wore an
  eight-pointed copper star on ordinary clothes.
  ([nypdhistory.com](https://nypdhistory.com/staves/),
  [Wikipedia](https://en.wikipedia.org/wiki/Police_uniforms_in_the_United_States).)
  So the officers wear dark wool frock coats, waistcoats, cravats and top hats, with a copper star
  badge. Philadelphia's own badge is not documented, so the star is creative licence.
- **Bull's-eye lanterns**, as in the production plan.
- **Breath fogs at the door.** It is 4 a.m. in a cold street.
- **Hats come off indoors** (period manners). Hale removes his while he speaks at the door. In the
  chamber the hats rest on their knees or on the floor by the chairs.

### Exterior through the street door (5.2)
- The entry set's street stub: cobbles, a gas lamp, night sky, wind.
- Behind it, the v2 1843 street set (red brick, white marble steps, shutters), so the doorway frames a
  real street in depth. Their lanterns are against the street lamp.

### Light
- 5.1: candle only.
- 5.2: lanterns against the gas lamp.
- 5.4: lantern beams sweep the kitchen and hall.
- In the chamber, the officers' lanterns make the brightest scene in the film: warm and cosy in 5.7,
  draining and desaturating from 5.8 to cold in 5.12–5.15.

### Gesture timing (co-speech gesture research)
- **Phases.** A gesture has optional preparation, a stroke, holds and retraction; only the stroke is
  required (Kendon; McNeill).
- **Timing.** The stroke comes before or on the stressed syllable, never after it. It overlaps the
  pitch accent in 80–90% of cases.
  ([Frontiers 2018](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2018.01514/full);
  [PMC review](https://pmc.ncbi.nlm.nih.gov/articles/PMC6137092);
  [Neff, gesture synthesis](https://www.cs.ucdavis.edu/~neff/papers/HandGestureSynthesisForConversationalCharacters_PREPRINT.pdf).)
- **Holds.** Holds stretch a gesture to fit the phrase. Hands go back to rest only at real pauses.
- **Head.** The head moves with pitch and loudness ("visual prosody", Munhall et al. 2004). Speakers
  make small head nods on stressed syllables.
- **Emotion changes the size and speed of gestures.**
  - Calm: small, below the chest, soft.
  - Angry or agitated: large, fast, high and expansive (Wallbott 1998). Poe asks for this outright:
    "violent gesticulations".
- **Listeners** nod at the ends of the speaker's phrases, look at the speaker (and away now and then),
  and shift posture. This part is the builder's call, tuned by eye.

## What gets built

| Piece | Where |
|---|---|
| Scene builder, `build` / `draft` / `render` as in v3 | `stories/the_tell_tale_heart/preview_v4.py` |
| Scene | `blender/scenes/tell_tale_heart_v4_visitors.blend` |
| Voice lines (Chatterbox) | `stories/the_tell_tale_heart/preview_v4/lines.json` → `audio/voiceovers/the_tell_tale_heart_v4/` |
| Two new officer reference voices (Kokoro, offline) | `audio/voice_refs/officer_brandt.wav`, `officer_mercer.wav` (Hale keeps `officer.wav`) |
| Gesture toolkit plus its self-check | `scripts/humans.py` |
| Stand-in officers, and the swap to the real ones later | `stories/the_tell_tale_heart/cast3d.py` |
| Officer specs for the teammate | `docs/officers_cast_specs.md` |
| Notes, in the style of the v3 notes | `docs/tell_tale_heart_v4_visitors_notes.md` |

`preview_v4.py` reuses `preview_v3`'s helpers (the mocap gait, world-space foot planting, the soundtrack
mixer, `draft()`) by importing them, not by copying them.

### Gesture toolkit (`scripts/humans.py`)
- **`stress_times(wav)`.** Stressed-syllable times from the voice, using peaks of loudness and pitch (no
  transcript needed). Wav2ARKit's input path already loads the audio.
- **Gesture bank.**
  - Cut from these CMU clips: 18_08/19_08 (explain), 18_10/19_10 and 80_48 (quarrel, arguing), 111_25,
    113_16 and 141_21 (shrug), 13_14 (laugh).
  - Each unit is split at wrist-speed peaks into preparation, stroke and retraction, and stored as
    upper-body rotations (spine, neck, shoulders, arms, hands) relative to the clip's own rest pose.
  - Each unit is tagged calm or agitated.
- **`gestures(rig, wav, start, energy, hands=("Left","Right"))`.**
  - Picks units without repeating one back to back.
  - Lands each stroke 0–0.15 s before a stressed syllable, and holds to fill the phrase.
  - Retracts to rest only at pauses longer than about 0.5 s.
  - Scales amplitude and speed by `energy`, and adds small head nods on the strokes.
  - Layered on top of whatever the body is doing, standing or seated, the way the breathing and sway
    layers are.
  - A hand that is holding something is left out of `hands`.
- **`listen(rig, start, end, speaker, phrase_ends)`.** Gaze to the speaker's head with glances away,
  nods at phrase ends, slow weight shifts.
- **Self-check** (`--selfcheck`). A synthetic stressed beat must get a stroke within the window. No
  unit may be used twice in a row. A held hand must stay still.

### Officers
- **Now: stand-ins.**
  - Three copies of the Narrator character, told apart by:
    - Height: Hale 1.72 m and heavier-set by scale, Brandt 1.80 m, Mercer 1.78 m.
    - Hair tint: grey, fair, black.
    - Dark coat-coloured fabric tints instead of the white shirt.
    - A top hat prop on the head bone, and a copper star on the chest.
  - Their faces match the narrator's. That is a known limit of stand-ins, accepted for this draft.
- **Later: the real officers.** `docs/officers_cast_specs.md` gives the teammate three specs in the same
  format as `assets/characters/*/params.json`:
  - **Hale** (senior): 50s, heavy-set, grey side-whiskers, weathered.
  - **Brandt** (young): early 20s, clean-shaven, fair, open face.
  - **Mercer** (quiet): 40s, lean, dark moustache, narrow face.
  - The spec also asks for a frock coat, waistcoat and top hat if the generator can make them.
  - When the folders land in `assets/characters/`, each stand-in becomes the real one by changing one
    line in `cast3d.py`, then rebuild.

### Voices and the officers' chatter
- **Planned lines** (Chatterbox):
  - The narration: N.
  - The narrator on screen (NS): 5.3, 5.4, 5.15.
  - The officers: O1 in 5.2, O2 and O3 in 5.7.
- **Chatter under the narration.** Poe: "they chatted of familiar things"; "the men chatted pleasantly,
  and smiled".
  - About 12 short small-talk lines are written for 5.7–5.13 in 1840s English (the cold, the hour, the
    watch house, a fire across the river).
  - They are voiced and mixed quietly under the narration: audible as murmur, clear only in the gaps.
    Their lips and gestures follow these lines.
  - From 5.10 the chatter gets muffled and stretched as the heartbeat takes over.
- **Lips:** Wav2ARKit for every on-screen line, the chatter included.

### The shots (timings follow the voice lengths, as v3's `timeline()` does; the plan's lengths are the minimum)

| Shot | Action and acting | Camera |
|---|---|---|
| 5.1 | He comes down the stairs with a candle, almost lightly. A knock. Light-hearted face. The candle is carried by the hand | Backward steadicam, MS |
| 5.2 | His hand opens the street door. Three officers stand in the cold, lanterns lit, breath fogging. Hale lifts his hat and speaks (gestures with his free hand). The other two look past the narrator into the house | From the hall |
| 5.3 | "A shriek? My own, gentlemen…": all charm. A dismissive wave on "dream", an open welcoming arm on "come in" | CU |
| 5.4 | Their lantern beams sweep the kitchen and hall. He leads: "Search well, gentlemen!", with an inviting sweep of the arm | Pan with the lanterns |
| 5.5 | His hands open the strongbox lid. The officers lean in and nod | MS, gentle push |
| 5.6 | He carries his chair in and sets its legs exactly on the loose planks. The others are already seated, and the officers settle | Floor level |
| 5.7 | The warm, cosy four-shot. Officers chat (chatter lines plus "Cold night for it, eh?" / "Colder than a churchyard."). Gestures, a laugh, nods. He answers cheerily, relaxed and expansive | Slow arc |
| 5.8 | His smile slips. He goes pale (skin desaturates). A hand to his temple. Listening at nothing | CU, slow push |
| 5.9 | Dust on the plank seam under his chair jumps with each heartbeat (from the approved shot list) | Macro |
| 5.10 | Sweat, shallow fast breathing. The officers keep chatting and gesturing, unconcerned. He forces a smile at them | Handheld CU, growing |
| 5.11 | He rises and argues about trifles in a high key with violent gesticulations (agitated gesture bank), then paces with heavy strides (CMU 143_29, 17_01) | 360° orbit |
| 5.12 | He grabs the chair with both hands, swings it and grinds it across the planks (hands on the chair throughout). The officers glance and carry on | Top-down |
| 5.13 | The officers smile on pleasantly. One sips tea (cup carried by his hand). His horror builds: eyes wide, head shaking | CU officers, dolly zoom |
| 5.14 | Rapid cuts on the beat: eyes, smiles, the planks, his own eye | Shake on each beat |
| 5.15 | He leaps up, stamps on the planks, points: "Villains! … here, here!" The officers start to their feet (startle) | Push, then whip |

### The narrator's arc

| Shots | State | Face | Body |
|---|---|---|---|
| 5.1–5.7 | Light, suave, in control | `SLY` and smiles; relaxed brows | Open, expansive; calm gestures |
| 5.8–5.9 | The ringing begins | Smile fades; brows draw in | Stillness creeping in; anxious breathing |
| 5.10 | Gasping, hiding it | Forced smile, wide eyes, sweat | Panic breathing, fidgeting hands |
| 5.11–5.12 | Raving | `TENSE` into fury | Agitated gestures, pacing, chair swing |
| 5.13–5.14 | Horror, paranoia | `FEAR` with brows up | Trembling (`tremble()`) |
| 5.15 | Confession | Fury, mouth wide | Stamp, point |

**The officers** stay easy and pleasant throughout: smiles, small calm gestures, a laugh. Only at
5.15 do they startle.

### Sound
- **Effects:**
  - Already recorded in `audio/sfx/freesound`: stair footsteps, the street-door knock, the door latch
    and creak, chair scrape, floorboard creak, street night, the watchman's rattle (outside in 5.2).
  - Not recorded yet: a stamp, coins, a chair set down, group footsteps, a teacup, group laughter, the
    ringing. These use the film's synthesised versions (`scripts/sound_library.py`, as in v1) for the
    draft. Fetching recorded ones later is a download, so the URL table goes to the user first.
- **Score:** drones.
- **Heartbeat:** returns muffled ("a watch enveloped in cotton") at 5.8 and climbs from 60 to 150 bpm to
  5.15, using the same `HEARTBEATS` mechanism as v3. The dust jumps in 5.9 are on these beats.

### How it is checked before handing over
1. The `humans.py` self-check passes, gesture checks included.
2. A **10-second 480p test of 5.7** (the four-shot, the most gestures) is rendered first and shown to the
   user, before the full draft.
3. Measured contact where it can fail:
   - hands against the bodies, chairs and lantern nearby (BVH overlap);
   - planted feet (cm/s);
   - hats on heads;
   - the cup and chair on the hand.
4. A contact sheet of one frame per shot is looked at before the full draft.
5. Then the full draft. Its run time and any remaining problems go into the notes as "Still open".

## Calls the builder makes
- Exact gesture units, energies, chatter wording, chair and lantern placement in the chamber.
- Where the tea tray comes from (set on the washstand between 5.6 and 5.7).
- In-camera versions of the 5.10 "faces blur and stretch" and 5.14 strobe: defocus, dolly zoom, shake,
  light flicker. There is no compositing pass in the draft.
- How the stand-ins are told apart (within the description above).
