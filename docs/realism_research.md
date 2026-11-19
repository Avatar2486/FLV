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
