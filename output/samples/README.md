# Tell-Tale Heart v2: samples to choose from

Short tests of the new characters, motion, voices, sound and street, made before the full rebuild.
Each one asks for a choice, listed under **Your choice**.

## 1. Voices: `voices/`
- **`voices_compare.mp3`:** four lines, each spoken by three engines with the same text and effects:
  - A = Piper (the current film)
  - B = Kokoro
  - C = Chatterbox, which has an emotion control
- **Lines:**
  1. The narrator, calm
  2. The narrator, hysterical ("Villains! Dissemble no more!")
  3. The old man
  4. The officer
- Each take is also saved separately, for example `2_narrator_hysterical_C_chatterbox.mp3`.
- **`kokoro_male_voices.mp3`:** all 12 Kokoro male voices on the narrator's first line, each announced by name.

**Your choice:** A, B or C for each character, and a Kokoro voice name if you prefer one for a character.

## 2. Characters: `characters/`
Built with MPFB (MakeHuman):
- **The old man:** about 77 years old, frail, in a linen nightshirt, with grey hair, one grey eye and the
  pale, filmed "vulture eye".
- **The narrator:** gaunt, about 30, in an untucked shirt and wool trousers.

Files:
- Stills of both faces, front and three-quarter, and of both full bodies.
- **`talking_test.mp4`:** the old man frightened ("It is nothing but the wind in the chimney…") and the
  narrator going from tense to a sly smile ("True! nervous…"), both in the chosen Chatterbox voices.
- **Lip sync, new version:** made by a model learned from real talking faces (Wav2ARKit), so:
  - the jaw opens only a little and the lips do most of the work
  - sounds blend into each other, and the lips close fully on m, b and p
  - the face moves a frame before the sound, as real lips do
  - the mouth rests closed in pauses
  - expressions, blinks and small head movements play underneath the speech

- **Living body (new):** see `docs/realism_research.md` for the research behind each part.
  - **Eyes:** the "Eyes Alive" gaze statistics for talking or listening, with the eyes leading and the head
    following big shifts.
  - **Blinks:** quick to close and slower to open, some partial, gathering at speech pauses.
  - **Breathing:** an in-breath before each phrase, with the phrase spoken on the out-breath.
  - **Sway:** slow postural sway, so the body is never frozen.
- **`reaction_test.mp4` (new):** the old man listening in the dark hears the latch:
  - a startle that runs head to toe: blink, neck, shoulders, arms
  - a held breath, eyes darting with the head following toward the door
  - panic breathing, then "Who's there?"

**Your choice:** keep these looks, or tell me what to change (age, build, hair, clothes, face).

## 3. Motion: `motion/` (version 2: researched creeping and tiptoeing)
The research is in `docs/realism_research.md`. It combines the trackers' "fox walk" with 20 real
recordings I measured, and shows that people sneaking:
- walk slower, with shorter steps
- bend their knees two to three times more and lean forward
- keep both feet down much longer, testing the floor before committing their weight
- pause often
- when tiptoeing, take quick small steps with the heels lifted

The feet are now locked to the floor where they're planted, which fixes the sliding and floating in the
first version. Planted-foot sliding fell from 3–7 cm/s to about 1–2 cm/s, with the knee bend kept.

The narrator creeps toward the door, holding his breath, tense, eyes on the floor ahead, with the lamp
carried in front:
- **`A_creep_and_pause.mp4`:** CMU "creep and pause": knees bent 46°, leaning, pausing 16% of the time.
- **`B_on_toes_crouched.mp4`:** 100STYLE "on toes, crouched": a low tiptoe, knees bent 48°.
- **`C_tiptoe.mp4`:** 100STYLE "tiptoe": upright, light, quick steps.
- **`compare_A_left_B_middle_C_right.mp4`:** all three side by side.

The numbers measured on each clip are in `gait_measured.json`.

**Your choice:** A, B or C for the night visits (or a mix: for example A to cross the room, B at the bed).

## 4. Sound: `sound/`
The same film footage with two soundtracks:
- **A:** the current synthesised sound.
- **B:** recorded CC0 sound effects from Freesound, with Chopin (Musopen, CC0) under the drones.

Scenes:
- **`night_3.7-3.11`:** bed creak, death-watch beetles, the groan, chimney wind, the mouse, the cricket.
- **`4am_4.6-5.2`:** the clock strikes four, the knocking, footsteps, the street door.

**Your choice:** A or B, and anything that sounds wrong.

## 5. The street: `street/`
The new 1843 street outside the house at 4 a.m.:
- red-brick row houses with shutters and six-over-six sash windows
- white marble steps with iron rails
- brick sidewalks with stone curbs, and wet cobbles with puddles
- cast-iron gas lamps
- a bare tree, a church steeple in the mist, moonlit clouds

Files:
- Three stills: down the street, the old man's house, and the door.
- **`street_push_in.mp4`:** a 5-second move toward the door, with night ambience, a distant dog and wind.

**Your choice:** keep this look, or tell me what to change.

## 6. Everything together: "the eighth night" (film shots 3.1–3.10), about 53 s
**File:** `output/renders/the_tell_tale_heart_v2_preview/the_tell_tale_heart_v2_preview.mp4`

The new pipeline in a real scene from the film:
- MPFB characters
- Chatterbox voices
- lips driven by the voice
- eyes, blinks, breathing and sway
- recorded sound and Chopin's Prelude No. 15

**What happens:**

| Shot | Action |
|---|---|
| 3.1 | The narrator's right palm, flat on the door at chest height and away from the handle, pushes it open slowly and steadily. It moves only while his hand is on it. |
| 3.3 | Seen through the slot between the jamb and the door's edge, he chuckles silently: shoulders shaking, lips pressed into a smile. |
| 3.4 | The sleeping old man jerks in bed; his eyes stay shut. |
| 3.5 | Close on the narrator, holding his breath. |
| 3.5–3.6 | He leans in only as far as the door has opened; his head is in once it is fully open. He raises the lantern, held by its ring, into the gap. His thumb slips on the catch (*clink*) and he flinches; the lantern jerks with his hand. |
| 3.7 | The old man wakes in fright: eyes snap open, a startle, a beat to register. Then he rises the way older people do: head first, he props on his right elbow toward the door, pushes up with both hands, and draws his knees up under the blanket. He cries "Who's there?" |
| 3.8 | Both are frozen, listening. |
| 3.10 | The old man's trembling lips, then the groan. |

**Also new:**
- The blanket is shaped over the sleeping man: his feet make tents, it is tucked in at the foot, and
  his hands rest on top.
- No clipping: the narrator, his hands and the lantern stay clear of the door, frame and walls. Every
  30th frame is checked by mesh overlap, and the palm on the door is measured 1–4 mm off its surface.
  The bed things now sit on the real mattress; they had floated about 20 cm above it.
- The speckled grain all over the earlier renders is fixed. It came from the moon light's soft shadows;
  the moon is now a small, sharp light.

**Your choice:** whether this is the right direction for the full rebuild, and anything that looks or
sounds wrong (timing, faces, hands, light, voices).

Sources and licences: `assets/THIRD_PARTY.md`.
