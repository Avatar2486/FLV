# The Tell-Tale Heart, the whole film (about 10 minutes, 480p): design

## Intent
The user wants the whole film, from the first heartbeat to the credits. It is about 10 minutes long, all in
the new realistic style that 3.1–3.21 and 5.1–5.10 already use. It is built in **parts**, and each part lives
in its own folder with its own video. The parts are then joined into one film, and **none of them are
deleted**. The user watches the film, names a part and a moment ("part 02 at 0:41: the latch moves on its
own"), and only that part is fixed, re-rendered and re-joined.

They chose:
- to build every missing part in the new style before joining. The alternative was stitching in the old
  19-Nov version for now;
- **480p only.** No 1080p pass;
- **one builder per part**, joined at the end (approach 1 below).

## Goals
- All 69 shots of the film's shot list (`film.py`, `production_plan.md`) in the new style. This includes
  the shots the earlier parts skipped: 3.2 (the door edge creeping), 3.9 (the death-watch beetle) and 3.19
  (the neighbour's window).
- Eight parts, each with:
  - a scene builder;
  - its voices (Chatterbox);
  - lips (Wav2ARKit);
  - living bodies (gaze, blinks, breath, sway, gestures with speech, listeners' nods);
  - measured checks;
  - a 480p MP4 with sound.
- One joined 480p film with a parts index, so any moment in the film maps to a part and a time in it.
- Picture and sound in sync. The score and the heartbeat flow across the joins.

## Non-goals
- 1080p.
- The real officer characters. The stand-ins stay until the teammate's models arrive (`docs/officers_cast_specs.md`).
- New downloads. Anything missing gets the URL / size / licence table first.
- Rewriting Poe or the shot list. The adaptation in `production_plan.md` stands.

## Anti-goals (a failure even if it renders)
- A doll: anyone on screen frozen for a second.
- A prop that moves with no hand on it, or a hand that misses what it touches (a "ghost hand").
- Rigged-looking hands:
  - straight locked arms;
  - fanned fingers;
  - a flat or upright thumb;
  - a hand frozen at a world angle.
- Lips that don't move with the voice.
- Clipping (hands in bodies or furniture), feet sliding or floating.
- Black frames, stale frames from an earlier render, or a part whose video doesn't match its build.
- A visible jump in style or continuity between parts:
  - the chamber's furniture, the door's hardware, the lantern, the strongbox, costumes;
  - the time of night.

## Constraints
- **Platform:** Blender 5.3 on the Mac mini M4, Eevee.
- **Output:** 854×480, 24 fps, H.264 + AAC. ffmpeg is on this Mac (used to join).
- **Voices:** Chatterbox with Kokoro reference voices (`audio/voice_refs/`).
  - The attack's new-style voices (3.11–3.21) were made on the other machine and are not here, so they
    are generated again.
  - The old 19-Nov voices are not used.
- **Motion:** 100STYLE and CMU clips already in `assets/mocap/`; the toolkit in `scripts/humans.py`.
- **Sound:**
  - the recorded Freesound CC0 takes in `audio/sfx/freesound/`;
  - Chopin (Musopen CC0) in `audio/music/chopin/` through `film.SCORE`;
  - synthesised cues from `scripts/sound_library.py` only where no recording exists.
- **Rules carried from earlier parts:**
  - human-like lips;
  - nothing moves unless a hand moves it;
  - research before planning;
  - show URLs before any download.
- **Git:** commit after each part; push to **UAT only**.

## Approaches
1. **One builder and scene per part, joined at the end (chosen).**
   - This is how 3.1–3.10 (`preview_v2.py`), the attack (`preview_v3.py`) and the Visitors
     (`preview_v4.py`) are made.
   - A fix touches one part: rebuild, re-render and re-join that part only.
   - The cost: each part repeats some setup (sets, cast).
2. **One scene for the whole film.**
   - Continuity is automatic.
   - But every fix rebuilds 10 minutes (about an hour), and one bug blocks everything.
3. **Upgrade the old `build_film.py`.** It is built around the old characters and voices, so it is more work
   than 1 with the same problem as 2.

The user picked 1.

## The parts

| Part | Shots | Builder | State today |
|---|---|---|---|
| 00 Prologue | 0.1–0.5, T | new | not built |
| 01 The Eye | 1.1–1.9 | new | not built |
| 02 Seven Nights | 2.1–2.9 | new | not built |
| 03 The Eighth Night | 3.1–3.10 | `preview_v2.py` | built and rendered (1080p, 20 Nov); **3.2 and 3.9 missing** |
| 04 The Attack | 3.11–3.21 | `preview_v3.py` | built; **3.19 missing**; voices missing on this Mac |
| 05 Concealment | 4.1–4.6 | new | not built |
| 06 The Visitors | 5.1–5.15 | `preview_v4.py` | 5.1–5.10 built and checked; **5.11–5.15 to animate** |
| 07 Epilogue | 6.1–6.3 | new | not built |

**Builder for the new parts (the builder's call):** `preview_v5.py`, one file with a part argument for
00, 01, 02, 05 and 07. The alternative is one file per part, like v2–v4. These parts share sets and patterns
(the void, the chamber at night), so one file avoids repeating them.

### Folders
Nothing in a part's folder is deleted when the film is joined.

```
output/renders/the_tell_tale_heart_film/
  parts/
    00_prologue/      part_480p.mp4, frames/480p/*.png, soundtrack.wav, timeline.json, check.txt, stills/
    01_the_eye/       ...
    ...
    07_epilogue/      ...
  the_tell_tale_heart_480p.mp4     the joined film
  parts.json                       each part's start and length in the film, its shots and their start times
  soundtrack_film.wav              the whole film's sound, mixed once
```

### Fades at the joins
A fade the shot list puts at a part's edge (0.1's fade in, the title's fade out, the credits' fade out) is
rendered inside that part's own frames. Joining is then a plain cut with no re-encode of the pictures, and
each part's video looks the same alone as it does in the film.

### Sound across the joins
- The film is mixed once, on the film's own clock: every part's timeline is laid end to end.
- Each part's MP4 carries its slice of that mix, so the Chopin and the heartbeat play on through the joins.
- If a part changes length, only the sound is re-mixed and the later parts re-muxed (minutes). Their
  pictures are not re-rendered.

## What each new part shows
The shots are as in `production_plan.md` (frame, move, light, transition). Where they need it, the
research and the builder's reading are below.

**00 Prologue**
- **0.1** Black, one heartbeat.
- **0.2** A macro along a plank seam, dust drifting in a single cold ray through haze.
- **0.3–0.5** The narrator in a straight-backed chair in a black void, speaking to us.
  - Hard top light, deep falloff.
  - Lips and eyes alive, small gestures (direct address).
  - In 0.4 his eyes dart toward each sound (cricket left, mouse right, wind above). The sounds are placed
    in the stereo field to match.
  - 0.5 ends on a thin smile.
- **T** Title card.

**01 The Eye**
- **1.1** The 1843 street at dusk, a crane down from the roofline to the door. A gas lamp flickers.
  Philadelphia's gas street lamps date from 1836.
- **1.2** The kitchen in the morning. He prepares a breakfast tray with care: teapot, cup and saucer, toast or
  bread and butter, a boiled egg. These are 1850s middle-class breakfast staples (foodtimeline's 1853 bill of
  fare).
  - The kitchen keeps its set; 1840s kitchens were moving from the open hearth to cast-iron stoves.
  - Each item is placed by a hand.
- **1.3** He carries the tray up the stairs: the stair walk of 5.1 run upward, both hands on the tray.
- **1.4** The old man sits up in bed, the day chamber lit through the shutter slits, and smiles as the tray is
  set down.
- **1.5** An insert of the open strongbox, rack focus to the narrator.
- **1.6** Over the narrator's shoulder, the old man turns his head toward him.
- **1.7** An ECU of the vulture eye: the old man's own eye with the cataract film used in 3.14, blinking slowly.
- **1.8** A CU of the narrator. His teacup trembles on its saucer, in his own hand.
- **1.9** The narrator's room as a time-lapse, day to night. He sits still but alive: breathing, blinking, the
  light changing around him.

**02 Seven Nights**
- **2.1** The corridor at midnight. He leaves his room with the closed dark lantern; the long-case clock is near
  twelve.
- **2.2** A pocket watch in his palm. 1840s style: open face, key wind, white enamel dial, Roman numerals,
  blued steel hands, about 45–55 mm.
- **2.3** Fingertips on the chamber door's latch. The hardware must match the door in parts 03, 04 and 06.
  For reference, thumb latches and rim locks were both in use around 1840.
- **2.4–2.5** The door opens a sliver; the lantern's dark shape eases in, then his head, creeping forward while
  the clock behind sweeps a whole hour.
- **2.6–2.7** His thumb eases the shutter a crack; a thread of light crosses to the old man's closed eye. This
  is the same rig as 3.13.
- **2.8** Night II to Night VII. The same composition each night, with "Night II" … "Night VII" cards. He looks
  more worn each night: darker under the eyes, paler, heavier lids.
  - These are the cues raters gave sleep-deprived faces (Sundelin et al. 2013). A larger 2019 study did not
    reproduce them, so they stay subtle.
- **2.9** A bright morning. He throws open the shutters and greets the old man: "Good morning, sir! Did you
  pass the night well?" — "Well enough, my boy. Well enough."

**05 Concealment**
- **4.1** The void, calm.
- **4.2** Only his huge shadow works on the wall, from the lantern on the floor.
- **4.3** His hands lift three planks away, revealing the dark joists.
- **4.4** Top-down: his hands set them back, seamless.
- **4.5** He wipes his clean hands and laughs.
- **4.6** The long-case clock strikes four; then the knocking. Part 06 begins on that knock.

**07 Epilogue**
- **6.1** Black, silence, one more heartbeat.
- **6.2** The void, a CU. He whispers "Hearken."
- **6.3** Credits:
  - based on Poe (1843);
  - the credit lines required in `assets/THIRD_PARTY.md` (100STYLE "Ian Mason", the CC-BY items marked
    **credit**, and so on).

**Added to 03:**
- **3.2** A macro of the door edge creeping.
- **3.9** The death-watch beetle in the wall timber (`sets.beetle_macro`).

**Added to 04:**
- **3.19** The neighbour's window across the street lights up; a curtain twitches. A hand moves it.

## Continuity (one film)
- **Characters:** the same cast and costumes across all parts.
- **The narrator's worn look:** grows over 2.8 and stays into 3.x, at the 2.8 Night VII level.
- **The chamber:**
  - bed, shutters, strongbox, door and loose planks are identical everywhere;
  - the lid is shut except when a hand opens it;
  - the planks show no seam after 4.4.
- **The door's latch hardware** in 2.3 is the one parts 03, 04 and 06 already show.
- **The light by time of day:** day (1.x, 2.9) and night (2.x, 3.x, 4.x, 5.x), both from the existing light rigs.
- **The toolkit:** parts 03 and 04 are rebuilt with the current toolkit, which has the hand, gesture and lip
  fixes. Their own checks plus the new ones (contacts, locked arms) must pass, so they match the newer parts.

## Checks, per part
1. The `humans.py` self-check.
2. The part's own `check`:
   - hands inside people or furniture;
   - held props drifting from the hand;
   - contacts measured at build time (2 cm);
   - planted feet sliding;
   - lips moving on every spoken line;
   - nobody frozen on camera;
   - seated arms locked straight.
3. Stills, a contact sheet of every shot, looked at before rendering.
4. The render starts from cleared frames. The MP4's length is checked against the timeline.
5. A contact sheet of the finished MP4 at one frame a second, looked at before handing over.

## Order of work
1. **06 The Visitors.** Already in progress: 5.11–5.15, then its sound.
2. **00, 01, 02.**
3. **03 and 04.** Rebuild with the current toolkit; add 3.2, 3.9 and 3.19; generate the attack's voices.
4. **05, 07.**
5. **The film-wide mix and the join.**

Each part is handed to the user (its MP4 path) as it is finished. The joined film comes once all eight exist,
and is re-joined after any fix.

## Left to the builder
- Blocking, camera paths and the timing inside each shot.
- The tray's exact contents.
- How the time-lapses are staged.
- The credits' layout and the order of the credit lines. The maker's name reads "An FLV film" for now (the
  user didn't give one; it is one line to change).
- The exact lengths: the shot list's are minimums, and each part's timeline comes from its voices, as in v2–v4.

## Sources
- [Food Timeline, 1853 middle-class bills of fare](https://foodtimeline.org/foodpioneer.html)
- [Cliveden (Germantown) kitchen: hearth, later range](https://savingplaces.org/one-house-two-kitchens-clivedens-unique-history-lesson)
- [The cook stove replacing the hearth, 1830s–1860s](https://www.oldhouseonline.com/kitchens-and-baths-articles/kitchen-appliances/history-of-the-kitchen-stove/)
- [1840s key-wind pocket watches: enamel dials, Roman numerals, blued hands](https://www.1stdibs.com/jewelry/watches/pocket-watches/period/1840s)
- [Thumb latches and rim/mortise locks in early American houses (Maryland, Curator's Choice)](https://apps.jefpat.maryland.gov/curatorschoice/CCIssues/..\pdfs\2013-11.pdf)
- [Sundelin et al. 2013, cues of fatigue](https://pubmed.ncbi.nlm.nih.gov/23997369/); [Holding et al. 2019, not replicated](https://pubmed.ncbi.nlm.nih.gov/31006920/)
- [Philadelphia's first gas street lamps, 1836](https://blog.phillyhistory.org/?p=9111)
