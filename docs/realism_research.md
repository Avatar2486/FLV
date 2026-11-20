# How real people move: the research behind FLV's characters

Each finding below is used in `scripts/humans.py`. Numbers are from the cited studies unless marked
as measured on our MPFB characters.

## Lips and jaw: `lip_sync()`
- **Two separate actions.** Speech is mostly lip work with a little jaw; jaw and lips are independent
  (JALI, Edwards et al., SIGGRAPH 2016).
- **Coarticulation.** Neighbouring sounds blend into each other.
- **Closures.** m, b and p need a full lip closure, which viewers notice even when brief.
- **Timing.** The face shapes a sound slightly before it is heard.
- **How we apply it:**
  - The Wav2ARKit model (learned from real faces) drives the 52 ARKit face units from the voice.
  - Gains rebalance the jaw against the lip raisers for MPFB.
  - The face leads the sound by one frame.
  - The model's resting offset is removed, and the mouth closes wherever the voice is silent.
  - A resting lip seal (`mouthShrugLower` 0.3) gives way as the mouth opens.

## Eyes: `eyes()`
"Eyes Alive" (Lee, Badler & Badler, SIGGRAPH 2002), eye-tracked at 30 fps:
- **Saccade size:** P(A) ≈ 15.7·e^(−A/6.9). 90% are under 15°. The average is 15.6° when talking and
  13.8° when listening.
- **Direction:**

  | Direction | 0° | 45° | 90° | 135° | 180° | 225° | 270° | 315° |
  |---|---|---|---|---|---|---|---|---|
  | Share | 15.5% | 6.5% | 17.7% | 7.4% | 16.8% | 7.9% | 20.4% | 7.8% |

  Up/down and left/right are each about twice as common as diagonals.
- **Duration:** D = D0 + d·A, with D0 = 20–30 ms and d = 2–2.7 ms/deg. We use 25 ms + 2.4 ms/deg.
- **Spells:**

  | Mode | Looking at the listener | Looking away |
  |---|---|---|
  | Talking | 3.1 ± 3.2 s | 0.93 ± 0.8 s |
  | Listening | 7.9 ± 1.6 s | 0.43 ± 0.24 s |

  Speakers look at listeners about 41% of the time; listeners look at speakers about 75%.
- **Head:** natural saccades rarely exceed about 15°, so bigger gaze shifts bring the head. The eyes lead,
  the head follows, and the eyes counter-rotate as the head arrives (the vestibulo-ocular reflex). In our
  model the head takes 65% of the shift beyond 15°.
- **Eyelids:** the upper lid follows the eye when looking down. Gaze and blinks are coupled
  (Deng, Lewis & Neumann, IEEE CG&A 2005).
- **Blinks:**
  - Blinks are often partial, and closing is faster than reopening.
  - Blinking rises when speaking and falls when listening hard (PLoS ONE 2021; Trends in Hearing 2025).
  - Blinks cluster at speech pauses (Holtze et al. 2021).
  - Our rates: about 24/min talking, 12/min listening, 7/min afraid (blinking suppressed).
  - Large saccades carry a blink 60% of the time, and speech pauses 50% of the time.
  - Shape: closes in about 80 ms, reopens in about 150 ms; 15% of blinks are partial.
- **Measured on our MPFB eyes:** at full weight, `eyeLookOut` turns the eye about 38°, `eyeLookIn` about
  39°, up about 18° and down about 27°. Each eye can be driven separately, so near targets converge.

## Breathing: `breathe()`
- **Rhythm:** the inhale is slower than the exhale (animation practice). We use inhale 40%, exhale 45%,
  rest 15%.
- **Layering:** belly, chest, shoulders and head move slightly out of step. Shoulders and neck lag the
  chest by 2 frames, and the neck counter-rotates to keep the head level.
- **Speech:** a still torso between utterances reads as "holding breath". The most natural agents break
  their breathing rhythm only for a quick in-breath before speaking (PaolaChat study). We breathe in for
  0.35 s before each phrase and speak on a long out-breath.
- **Styles:**

  | Style | Breaths per minute | Chest | Shoulders |
  |---|---|---|---|
  | Calm | 13 | 1.0° | 0.5° |
  | Old | 17 | 0.8° | 0.9° |
  | Anxious | 22 | 1.6° | 1.4° |
  | Panic | 32 | 2.2° | 2.6° (rides high in chest and shoulders) |
  | Held | — | — | — |

## Body: `sway()`, `startle()`, mocap
- **Idle motion.** People are never still: postural sway, breathing and blinking are always present.
  A still body under a moving face reads as eerie, and natural postural oscillation makes viewers read
  emotion more strongly (Treal et al., Scientific Reports 2021). `sway()` adds slow, never-repeating drift
  (0.07–0.35 Hz, under 1°) to the lower back and neck.
- **Startle (Brown et al., Brain 1991):** a cranio-caudal wave. Each body part's onset:

  | Part | Onset |
  |---|---|
  | Blink | 20–40 ms |
  | Head | 60–120 ms |
  | Neck | 75–121 ms |
  | Shoulders | 100–121 ms |
  | Arms | 125–195 ms |
  | Legs | 145–395 ms |

  The flexion pattern: eyes close, neck and trunk flex, shoulders rise, arms abduct, elbows flex.
  `startle()` snaps in within 80 ms and settles over about 0.35 s.
- **Locomotion and actions** come from real motion capture, never hand-keyed walk cycles:
  - CMU: 2,435 clips, free for commercial use.
  - 100STYLE: 100 walking styles, CC BY 4.0.
  - Both are retargeted by `retarget()`; the library is fetched by `scripts/download_film_kit.sh`.
- **Props never move on their own.** A character's hand is on any object that moves.
- **No learned motion model is used.** The ones found (AMASS-, BEAT- and Bandai Namco-trained) carry
  non-commercial licences.

## Creeping and tiptoeing: `retarget()` + `plant_feet()`
**Field technique.** Trackers' "fox walk":
- Place the outer edge of the ball of the foot first, then roll inward onto the ball with the heel still up.
- Feel the ground before committing weight, keeping the knees bent to absorb each step.
- Slow pace and pauses.
- Some teach heel-first instead (Princeton nature-observation notes; *How to Walk Like a Fox*).

**Measured from real recordings** (`scripts/gait_stats.py` on the motion library; lengths in leg lengths):

| Clip | Speed | Cadence (steps/min) | Step | Knee bend in stance | Foot pitch in stance | Trunk lean | Both feet down | Paused |
|---|---|---|---|---|---|---|---|---|
| 100STYLE Neutral (baseline) | 0.81 | 90 | 0.54 | 14° | 31° | 4° | 22% | 2% |
| 100STYLE Tiptoe | 0.77 | 104 | 0.45 | 21° | 44° | 4° | 30% | 2% |
| 100STYLE OnToesCrouched | 0.64 | 96 | 0.40 | 46° | 44° | 24° | 35% | 2% |
| 100STYLE Crouched | 0.76 | 99 | 0.46 | 37° | 32° | 25° | 25% | 2% |
| 100STYLE InTheDark | 0.58 | 102 | 0.34 | 18° | 30° | 4° | 36% | 2% |
| CMU 77_29 creeping walk | 0.78 | 86 | 0.55 | 46° | 25° | 32° | 43% | 6% |
| CMU 77_34 creep and pause | 0.53 | 70 | 0.45 | 45° | 23° | 33° | 68% | 26% |
| CMU 91_18 careful walk, looking around | 0.46 | 69 | 0.40 | 25° | 16° | 4° | 19% | 14% |

How sneaking differs from walking:
- Slower and shorter steps.
- Knees bent two to three times more.
- A forward lean of 25–50° when crouched.
- Much longer with both feet down (weight tested before it is committed, up to 68%).
- Frequent pauses (up to 26% of the time).
- Tiptoeing adds quick, small steps with the heels about 13° higher.

**Footskate cleanup.**
- **The problem:** retargeted feet slid 3–7 cm/s while planted.
- **The method:** `plant_feet()` detects contacts on the ball of the foot (the pivot in these gaits), lowers or raises the whole body once so planted feet meet the floor, locks each contact to its average spot, solves two-bone leg IK (knee direction and foot angle kept), and blends over 3 frames, as Kovar et al. 2002 advise.
- **The result:** sliding falls to about 1–2 cm/s (mostly the blend frames), knee bend is kept, and no foot goes through the floor.

## Hands, props and the bed: `reach()`, `grip()`, `hold()`, `bedsheet()`
- **Nothing moves by itself.** Every moving prop has a hand on it.
  - `reach()` is two-bone arm IK: the wrist follows a target point (on the door, the lantern ring, the
    mattress), easing in and out over a few frames. The hand's angle can change per frame, so the palm
    stays flat on a turning door. `reach()` reads the arm's own motion before keying, so after release
    the arm returns exactly to where it was. The self-check measures this: 0.000° after release.
  - `hold()` puts a prop in a hand, so it moves only when that hand moves. When the narrator flinches at
    his own slip, the lantern jerks with his hand.
  - `grip()` curls the fingers round a handle. A negative curl straightens them for a flat hand.
- **Measured on the MPFB hands:**
  - +X on the finger bones curls them.
  - The palm is on the hand's −Z (curling moves the fingertips toward −Z, on both hands of both
    characters). `hand_frame()` had this backwards at first, so the hands lay palm-up.
- **Touching, not passing through.** Each contact is checked by mesh overlap (BVH) against the door,
  frame and walls every 30 frames, and by the hand's depth relative to the door face.
- **The door:**
  - His right palm pushes flat on the door's corridor face at chest height, away from the handle (gripping
    the handle looked wrong).
  - The rig's fingers curve toward the palm, so the hand is tilted 12° off the door with the wrist 4.8 cm
    out. Measured: the palm rests 1–4 mm off the surface, and nothing goes inside.
  - The door opens only while his hand pushes it, and stops when the hand stops.
- **Staging in the doorway:**
  - The wall is 0.15 m thick and the opening is 0.9 m wide.
  - He stands square in the opening, so his head and shoulders never enter the wall or jamb. Before, his
    face and shoulder were 4–6 cm into the jamb.
  - He leans in only as far as the opening door allows: his head is "in" once the door is fully open.
  - His face can be seen from the room only through the slot between the jamb and the door's edge, 123–151°
    around from his head. The close-up camera sits at about 140°.
- **The lantern:**
  - Held low at his side behind the door until his head is in, then raised into the gap.
  - It hangs from its top ring, palm down, fingers through the ring. At the "tin fastening" his thumb
    slips (a 28° thumb jerk), then the startle follows.
- **The bed:**
  - The mattress top is at z 0.44, from a raycast. The old note said 0.62, so the pillow, blanket and
    sleeper had floated about 0.2 m above it.
  - He lies on the mattress, his head on the pillow with the neck slightly bent.
- **Sleep:**
  - Slow, shallow breathing: 12 per minute, almost no shoulder movement.
  - A small body-only jerk when he "moved on the bed suddenly"; his eyes stay shut.
- **The blanket** is shaped over the sleeper's legs and feet:
  - Its heights are cast onto the leg geometry only, so the hands rest on top and he can sit up out of it.
  - It is spread and smoothed the way cloth spans gaps, so the feet make tents.
  - It is tucked in at the foot and hangs down both long sides.
  - It follows his legs (shape keys every 2 frames), so it rises only when his knees draw up under it.
- **A stifled chuckle** pulses the shoulders and chest at about 4.5 per second, close to the roughly
  210 ms spacing of laugh notes (Provine 1996), with the lips pressed into a smile.

## Waking in fright and rising from bed: `startle()` + `rise_in_bed()`
**How people sit up from lying.**
- *The order (Cordo et al. 2003):* the sit-up is serial. The neck and upper trunk flex first, then the
  lumbar trunk lifts, then the pelvis rotates. The head lifts first, and the body comes up in a wave
  toward the hips.
- *How older adults do it:* Watanabe et al. (2019) compared older adults (65–74) rising from lying to
  sitting with young adults.

  | Measure | Older adults | Young adults |
  |---|---|---|
  | Trunk flexion | 37° | 63° |
  | Elbow flexion | 92° | 84° |
  | Shoulder extension | 31–33° | 17–22° |
  | Hip flexion | 80° | 56° |
  | Knee flexion | 74–78° | 55–60° |

  Older adults curl the trunk much less and "often selected the push up": an elbow props and both arms
  push. Head and neck rotation come before the trunk. Neck flexion peaks at about 26% of the movement,
  trunk flexion at about 54%, and the knees at 67–82%.
- *Startle:* the startle comes first (Brown et al. 1991, above). Animators stage a fright as notice →
  register → react: a short beat before the big move (AnimSchool).

**How we apply it, for the old man at "the old man sprang up in the bed":**

| When | What happens |
|---|---|
| 0 s | The startle: his eyes snap open with a blink; neck, shoulders and arms flex. His legs stay still under the blanket. |
| +0.3 s | A beat to register the sound. |
| Rise, 1.1 s (startled, so fast) | The head lifts first (neck flexion peaks at 26%). He turns about 9° toward the door and props on his right elbow; the right hand, then the left, goes to the mattress beside his hips and pushes. The trunk curls to 37° at 54%, then straightens to about 15° as the hips lift him to sitting. The head comes upright. The knees draw up late (hip about 20°, knee about 40° under the blanket, which rises with them). |
| End | A small settle. His hands stay planted behind him as he sits listening, and his eyes and head turn to the door. |

## Light and grain (Eevee, Blender 5.3)
- **The speckle came from the moon light's size.** Fine grain on every moonlit surface came from the
  shadows of the large (1.2 × 1.4 m) area light.
- **What didn't help:**
  - More samples (160)
  - More shadow rays or steps
  - A finer shadow map
  - Hiding the haze
  - Turning raytracing off
  - Jitter on the big light, which gave blocky shadow tiles instead
- **The fix:** a small moon light (0.15 m; the real moon is a small, sharp source) with jittered
  shadows, overblur 0. Fill lights cast no shadows. The film's old "haze speckle" glitch was this.

## Sources
- [JALI (Edwards et al. 2016)](https://www.dgp.toronto.edu/~elf/jali.html)
- [Lip-sync theory (Flawless)](https://kb.flawlessai.com/lip-sync-theory)
- [Wav2ARKit model card](https://hug-proxy.pages.dev/myned-ai/wav2arkit_cpu)
- [Eyes Alive (Lee, Badler & Badler 2002)](https://repository.upenn.edu/hms/51)
- [Ruhland et al. 2015, eye gaze review](https://diglib.eg.org:443/xmlui/handle/10.1111/cgf12603)
- [Deng et al. 2005, eye motion and blinks](https://graphics.cs.uh.edu/wp-content/uploads/papers/2005/CGA_eyemotion.pdf)
- [Blinking while speaking and listening (2021)](https://doaj.org/article/360238ef0e524934a56d072810e322ee)
- [Eye-blink patterns and attention to speech (Holtze et al.)](https://offis.de/offis/publikation/eye-blink-patterns-reflect-attention-to-continuous-speech.html)
- [Listening and blinking (Concordia, 2025)](https://www.sciencedaily.com/releases/2025/12/251222043239.htm)
- [Modelling 3D human breathing (MPI)](https://al.is.mpg.de/research_projects/modeling-3d-human-breathing)
- [Breathing in agents (PaolaChat)](https://unpaywall.org/10.1007%2F978-3-319-91581-4_26)
- [Animation breathing timing (AnimSchool)](https://blog.animschool.edu/tag/animated-breathing/)
- [Postural oscillations and empathy (Treal et al. 2021)](https://www.nature.com/articles/s41598-021-91710-5.pdf)
- [Idle animation believability (2025)](https://arxiv.org/pdf/2509.05023)
- [Startle response](https://Www.Wikipedia.org/wiki/Startle)
- Provine, R. R. (1996), "Laughter", *American Scientist* 84(1): laugh notes about 75 ms long, every 210 ms
- [Watanabe et al. 2019, supine to sitting in young and elderly (J Phys Ther Sci 31:102)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6348188/)
- [Cordo et al. 2003, the sit-up: complex kinematics (J Electromyogr Kinesiol 13:239)](https://pubmed.ncbi.nlm.nih.gov/12706604/)
- [AnimSchool: staging a reaction](https://blog.animschool.edu/tag/staging/)
- [Fox walk / nature observation (Princeton)](https://swh.princeton.edu/~oa/nature/naturobs.pdf)
- [How to Walk Like a Fox](https://www.chelseagreen.com/2021/how-to-walk-like-a-fox-and-see-in-the-dark)
- [Stealthy walking mechanics (cats)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2583958/)
- [Toe-walking biomechanics (Frontiers 2022)](https://www.frontiersin.org/articles/10.3389/fbioe.2022.810560/full)
- [Footskate cleanup (Kovar et al.)](https://research.cs.wisc.edu/graphics/Gallery/kovar.vol/Cleanup)
- [Skeleton-Aware Networks: contact locking](https://arxiv.org/pdf/2005.05732)
- [UnderPressure: foot contact](https://arxiv.org/pdf/2208.04598)
- [Sneak walk animation (Animation Mentor)](https://www.animationmentor.com/blog/tutorial-animating-sneak-walk-cycle-with-personality/)
