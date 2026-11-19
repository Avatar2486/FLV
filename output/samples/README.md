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

## 3. Motion: `motion/`
The narrator creeping, with real motion capture retargeted onto him:
- **A:** CMU "careful creeping": crouched, arms forward, sneaking.
- **B:** 100STYLE "Tiptoe": upright, light steps.
- **`compare_A_left_B_right.mp4`:** both side by side.

**Your choice:** A or B for the night visits (the other can still be used elsewhere).

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

Sources and licences: `assets/THIRD_PARTY.md`.
