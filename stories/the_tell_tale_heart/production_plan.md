# The Tell-Tale Heart — production plan

**Source:** "The Tell-Tale Heart" by Edgar Allan Poe, first published in *The Pioneer*, January 1843
(text: *The Works of the Late Edgar Allan Poe*, 1850 — see `source_text.md`). **Public domain worldwide:**
free to adapt, narrate and monetise; no permission or fee needed.

**Why this story.** It is one of the most famous horror stories ever written and fits a 10-minute
Blender film almost perfectly: one house, one night, a tiny cast (narrator, old man, three officers),
and a structure built on suspense — seven nights of creeping, the eighth-night attack, the cover-up,
and the police visit where guilt (the heartbeat) breaks the narrator. It is driven by things Blender
does well: darkness, a single beam of light, slow camera moves, close-ups of an eye, floorboards and
a clock, and above all sound (the heartbeat, a ticking watch, the death-watch beetle, silence).

**Runtime:** 10:13.38 · **Shots:** 69 · **Format:** 1920x1080, 24 fps, H.264 + AAC

## Structure

| Sequence | Starts | Length |
|---|---|---|
| 0. Prologue — Hearken | 0:00.00 | 41 s |
| 1. The Eye | 0:40.75 | 57 s |
| 2. Seven Nights | 1:37.46 | 103 s |
| 3. The Eighth Night | 3:20.29 | 176 s |
| 4. Concealment | 6:16.58 | 48 s |
| 5. The Visitors | 7:04.46 | 172 s |
| 6. Epilogue | 9:56.38 | 17 s |

## Cast and voices

| Role | Voice | Licence |
|---|---|---|
| The Narrator (voice-over) | Piper `en_US-john-medium` | public domain (LibriVox reader) |
| The Narrator (on screen) | Piper `en_US-john-medium` | public domain (LibriVox reader) |
| The Old Man | Piper `en_US-joe-medium` | CC0 |
| Officer Hale (senior) | Piper `en_US-libritts-high` speaker 90 | CC BY 4.0 — LibriTTS (Zen et al., 2019) |
| Officer Brandt (young) | Piper `en_US-bryce-medium` | public domain |
| Officer Mercer (quiet) | Piper `en_US-norman-medium` | public domain (LibriVox reader) |

## Visual approach

- **Look:** stylised "puppet theatre" characters in a realistic 1840s house; low-key lighting, haze,
  one warm practical (the dark lantern) against cold moonlight. The brightest scene — the officers'
  lanterns — is where the narrator falls apart.
- **Camera grammar:** locked-off and slow dolly moves while he is in control; macro inserts (latch,
  watch, eye, beetle, floor) for his "acute senses"; rising Dutch angles, handheld shake and faster
  cutting in time with the heartbeat in both climaxes; top-down shots for the violence (kept
  off-screen) and the cover-up; direct address to camera in a black void as a framing device.
- **Sets:** chamber (hero set: loose planks, shuttered window, real doorway), corridor with
  long-case clock, entry hall and stairs, kitchen, narrator's room, street exterior, black void,
  macro sets (eye at 10x scale, pocket watch, beetle).

## Sound approach

- Voices: Piper TTS (commercially licensed voices), EQ and room tone per scene.
- Every effect and the score are synthesised from scratch (no licences needed): heartbeat
  (clean and "watch wrapped in cotton" versions), watch and clock ticks, bells, creaks, wind, the
  death-watch beetle, knocks, scrapes and a drone score that only fades where the cue changes.
- The heartbeat is one score shared by picture and sound: it accelerates 62 → 96 bpm before the
  attack, slows to silence under the bed, and returns 60 → 150 bpm during the police visit — the
  dust on the floorboard jumps on the same beats.

## Adaptation notes

Narration is Poe's text, verbatim, with passages cut for time. These are FLV additions:

- **0.3** — Direct-to-camera framing device (the 'you' of the text)
- **0.4** — Spatialised sounds show his 'acute hearing'
- **1.1** — Establishing shot of the house
- **1.2** — Visualises 'I was never kinder to the old man'
- **1.9** — Time-lapse of his decision
- **2.5** — Clock time-lapse shows the hour
- **2.8** — Night II–VII title cards
- **2.9** — Morning dialogue (the text reports it: 'calling him by name in a hearty tone')
- **2.9** — new line for The Narrator (on screen): “Good morning, sir! Did you pass the night well?”
- **2.9** — new line for The Old Man: “Well enough, my boy. Well enough.”
- **3.1** — Night VIII title card
- **3.8** — Moonlight time-lapse
- **3.9** — Visual of the 'death watches'
- **3.11** — Each 'supposition' shown
- **3.12** — Shadow-of-Death visual
- **3.18** — Violence kept off-screen
- **3.19** — The neighbour who heard the shriek
- **4.1** — Framing device
- **4.2** — Dismemberment omitted (implied)
- **5.2** — Officer dialogue paraphrases the text's report
- **5.2** — new line for Officer Hale (senior): “Forgive the hour, sir. A neighbour heard a shriek in the night. We are bound to search the premises.”
- **5.3** — 'The shriek, I said, was my own in a dream…' as dialogue
- **5.3** — new line for The Narrator (on screen): “A shriek? My own, gentlemen—in a dream. The old man is away in the country. Come in, come in!”
- **5.4** — new line for The Narrator (on screen): “Search well, gentlemen!”
- **5.7** — Small talk lines
- **5.7** — new line for Officer Brandt (young): “Cold night for it, eh?”
- **5.7** — new line for Officer Mercer (quiet): “Colder than a churchyard.”
- **5.9** — Dust-on-beat visual
- **6.1** — Final heartbeat
- **6.2** — Closing callback to the opening
- **6.2** — new line for The Narrator (voice-over): “Hearken.”

## Shot list

| # | In | Dur | Framing / lens | Movement | Action | Light | Sound | Words | Out |
|---|---|---|---|---|---|---|---|---|---|
| 0.1 | 0:00.00 | 3.0s | Black | — | A single heartbeat in the dark. | — | heart_single; score: silence | — | fade in |
| 0.2 | 0:03.00 | 7.0s | ECU floorboards, 100 mm macro, f/2 | Slow push along a plank seam | Dust drifts through a thin ray of light over the boards. | Single cold ray, haze | watch_tick_loop; score: drone_low | N: True!—nervous—very, very dreadfully nervous I had been and a… | cut |
| 0.3 ⓐ | 0:10.00 | 10.1s | MCU narrator, 50 mm, f/2.8 | Slow dolly in | The narrator sits in a straight-backed chair in a black void and speaks to us. | Hard top light, deep falloff | —; score: drone_low | N: but why will you say that I am mad? The disease had sharpene… | cut |
| 0.4 ⓐ | 0:20.12 | 7.0s | ECU eyes, 85 mm | Locked off | His eyes dart toward each sound, left, right, above. | Top light | cricket, mouse, wind_gust; score: drone_low | N: I heard all things in the heaven and in the earth. I heard m… | cut |
| 0.5 | 0:27.12 | 8.6s | MCU → CU, 50 mm | Push in to a close-up | A thin smile. | Top light | —; score: drone_low | N: How, then, am I mad? Hearken! and observe how healthily—how … | smash cut to title |
| T | 0:35.75 | 5.0s | Title card | — | THE TELL-TALE HEART — after Edgar Allan Poe | — | boom, heart_single; score: silence | — | fade out |
| 1.1 ⓐ | 0:40.75 | 5.0s | WS the narrow two-storey house at dusk, 35 mm | Crane down from roofline to the door | A street lamp flickers; one lit window upstairs. | Blue dusk, warm window | wind_loop; score: drone_low | — | dissolve |
| 1.2 ⓐ | 0:45.75 | 8.8s | WS kitchen, 24 mm | Slow lateral dolly | Morning. The narrator prepares a breakfast tray with care. | Soft morning window light | cup_clink; score: drone_low | N: It is impossible to say how first the idea entered my brain;… | cut |
| 1.3 | 0:54.54 | 5.0s | MS following, 35 mm | Steadicam follows him up the stairs | He carries the tray up to the old man's chamber. | Daylight through the stairwell | steps_wood; score: drone_low | N: Object there was none. Passion there was none. | cut |
| 1.4 | 0:59.54 | 7.0s | Two-shot, 35 mm | Gentle push | The old man sits up in bed and smiles as the tray is set down. | Daylight slits through the shutters | —; score: drone_low | N: I loved the old man. He had never wronged me. He had never g… | cut |
| 1.5 | 1:06.54 | 4.0s | Insert: the strongbox of coins, 85 mm | Rack focus box → narrator | The open chest gleams; the narrator does not look at it. | Daylight slit | coin; score: drone_low | N: For his gold I had no desire. | cut |
| 1.6 | 1:10.54 | 5.0s | OTS narrator → old man, 85 mm | Rack focus to the old man's face | The old man turns his head toward the narrator. | Daylight slit | —; score: drone_rise | N: I think it was his eye! yes, it was this! | cut |
| 1.7 | 1:15.54 | 7.0s | ECU the vulture eye, 100 mm macro | Creeping push | The milky blue eye blinks, slowly. | Soft key, cold rim | sting_low; score: drone_rise | N: One of his eyes resembled that of a vulture—a pale blue eye,… | cut |
| 1.8 | 1:22.54 | 4.5s | CU narrator, 85 mm | Locked off | His teacup trembles on its saucer. | Daylight | cup_rattle; score: drone_low | N: Whenever it fell upon me, my blood ran cold; | cut |
| 1.9 ⓐ | 1:27.00 | 10.5s | WS narrator at his window, 24 mm | Locked off time-lapse | Day becomes night around him as he sits perfectly still. | Day → dusk → candle | clock_tick_loop; score: drone_low | N: and so by degrees—very gradually—I made up my mind to take t… | dissolve to night |
| 2.1 | 1:37.46 | 11.7s | Low WS down the corridor, 24 mm | Slow dolly back as he advances | He leaves his room with a closed dark lantern; the long-case clock nears twelve. | Moonlight from the landing window, black corridor | clock_tick_loop, door_creak_soft; score: drone_night | N: Now this is the point. You fancy me mad. Madmen know nothing… | cut |
| 2.2 | 1:49.12 | 5.3s | Insert: pocket watch in his palm, 100 mm | Locked off | The minute hand reaches twelve. | Moon sliver on the glass | watch_tick_loud; score: drone_night | N: I was never kinder to the old man than during the whole week… | cut |
| 2.3 | 1:54.46 | 7.2s | Macro: fingertips on the latch, 100 mm, f/2 | Focus pull fingers → latch | The latch turns a millimetre at a time. | Moon edge light | latch; score: drone_night | N: And every night, about midnight, I turned the latch of his d… | cut |
| 2.4 | 2:01.67 | 10.2s | Reverse from the bed side, 35 mm | Locked off | The door opens a sliver; the lantern's dark shape eases in, then his head. | Almost black; faint moon around the shutters | door_creak_soft; score: drone_night | N: And then, when I had made an opening sufficient for my head,… | cut |
| 2.5 ⓐ | 2:11.92 | 13.0s | Profile CU of his head in the door gap, 85 mm | Locked off | His head creeps forward while the clock's hands sweep a whole hour behind him. | Moon rim | clock_tick_fast; score: drone_night | N: It took me an hour to place my whole head within the opening… | cut |
| 2.6 | 2:24.92 | 10.4s | Macro: the lantern shutter, 100 mm | Slow push | A thumb eases the tin shutter open a crack. | Lantern glow leaks out | hinge_tiny; score: drone_night | N: And then, when my head was well in the room, I undid the lan… | cut |
| 2.7 | 2:35.33 | 6.0s | WS chamber, 24 mm | Lateral dolly following the beam | A thread of light crosses the dark room and lands on the old man's closed eye. | One hard beam in haze | —; score: drone_night | N: I undid it just so much that a single thin ray fell upon the… | cut |
| 2.8 ⓐ | 2:41.33 | 16.0s | Repeated beam composition, 50 mm | Locked off, varied per night | Night II … Night VII: the same beam, the same closed eye; the narrator more gaunt each night. | Beam + moon | clock_chime, clock_chime, clock_chime; score: drone_night | N: And this I did for seven long nights—every night just at mid… | cut |
| 2.9 ⓐ | 2:57.33 | 23.0s | Two-shot, 35 mm handheld feel | Subtle handheld drift | Bright morning. The narrator throws open the shutters and greets the old man warmly. | Hard morning sun | —; score: drone_low | N: And every morning, when the day broke, I went boldly into th… / NS: Good morning, sir! Did you pass the night well? / OM: Well enough, my boy. Well enough. / N: He would have been a very profound old man, indeed, to suspe… | smash cut to black |
| 3.1 ⓐ | 3:20.29 | 8.4s | WS corridor, 24 mm, NIGHT VIII card | Very slow push | He waits at the door. | Moon, deeper shadows | bell_toll, wind_loop; score: drone_tension | N: Upon the eighth night I was more than usually cautious in op… | cut |
| 3.2 | 3:28.67 | 6.0s | Macro: the door edge creeping, 85 mm | Locked off | The door edge moves slower than a watch hand. | Moon edge | watch_tick_loud; score: drone_tension | N: Never before that night had I felt the extent of my own powe… | cut |
| 3.3 | 3:34.67 | 4.2s | CU narrator in the gap, 85 mm | Locked off | His shoulders shake with a stifled laugh. | Underglow from the lantern | chuckle; score: drone_tension | N: I fairly chuckled at the idea; and perhaps he heard me; | cut |
| 3.4 | 3:38.83 | 4.6s | WS chamber, 24 mm | Locked off | The old man shifts in bed. | Pitch black, shutter outlines | bed_creak; score: drone_tension | N: for he moved on the bed suddenly, as if startled. | cut |
| 3.5 | 3:43.46 | 14.7s | CU narrator, 85 mm | Imperceptible push | He freezes — then keeps pushing. | Underglow | —; score: drone_tension | N: Now you may think that I drew back—but no. His room was as b… | cut |
| 3.6 | 3:58.12 | 7.0s | Macro: thumb on the tin fastening, 100 mm | Locked off | The thumb slips — CLINK. | Lantern leak | clink; score: drone_tension | N: I had my head in, and was about to open the lantern, when my… | cut |
| 3.7 | 4:05.17 | 5.8s | WS, 24 mm | Snap push | The old man bolts upright in bed. | Silhouette against the shutters | bed_creak; score: silence | N: and the old man sprang up in the bed, crying out— / OM: Who's there? | cut |
| 3.8 ⓐ | 4:10.96 | 16.0s | High corner two-shot, 24 mm | Locked off | Both frozen. Moonlight crawls across the floor as the hour passes. | Moving moon patch | deathwatch_loop; score: silence | N: I kept quite still and said nothing. For a whole hour I did … | cut |
| 3.9 ⓐ | 4:26.96 | 3.0s | Macro: a death-watch beetle in the wall timber, 100 mm | Locked off | The beetle taps. | Raking moonlight | deathwatch, deathwatch; score: silence | — | cut |
| 3.10 | 4:29.96 | 6.0s | CU old man, 85 mm | Slow push | His lips tremble in the dark. | Faint moon on his face | groan; score: drone_tension | N: Presently I heard a slight groan, and I knew it was the groa… | cut |
| 3.11 ⓐ | 4:35.96 | 12.1s | Cutaways: chimney, floor, wall, 50 mm | Small pushes | Soot falls in the grate; a mouse crosses the boards; a cricket chirps. | Moon | wind_gust, mouse, cricket; score: drone_tension | N: He had been saying to himself— / OM: It is nothing but the wind in the chimney—it is only a mouse… | cut |
| 3.12 ⓐ | 4:48.04 | 7.7s | WS wall above the bed, 24 mm | Slow tilt down | The narrator's shadow stretches, impossibly long, across the wall and over the old man. | Low lantern leak casting the shadow | —; score: drone_tension | N: All in vain; because Death, in approaching him, had stalked … | cut |
| 3.13 | 4:55.71 | 12.5s | Macro: the crevice, then follow the ray, 100 → 50 mm | Track along the beam | The ray, fine as spider silk, crosses the room. | Thread-thin beam in haze | —; score: drone_tension | N: So I opened it—you cannot imagine how stealthily, stealthily… | cut |
| 3.14 | 5:08.25 | 6.2s | ECU the eye, 100 mm | Snap zoom in | The vulture eye is wide open. | The beam on the eye | sting_high; score: drone_tension | N: It was open—wide, wide open—and I grew furious as I gazed up… | cut |
| 3.15 | 5:14.42 | 17.2s | CU narrator, 85 mm | Slow push | He tilts his head, listening. Insert: a watch wrapped in cotton. | Underglow | —; score: drone_tension | N: And now—have I not told you that what you mistake for madnes… | cut |
| 3.16 | 5:31.58 | 12.0s | Cutting CU eye / CU narrator / lantern hand | Creeping Dutch tilt | Cuts quicken with the heartbeat. | Beam, moon | —; score: drone_tension | N: It grew quicker and quicker, and louder and louder every ins… | hard cut on the yell |
| 3.17 | 5:43.58 | 3.0s | WS, 24 mm | Whip pan | He throws the lantern open — light floods the room — and leaps. | Lantern fully open | lantern_open, yell, shriek; score: silence | — | cut |
| 3.18 ⓐ | 5:46.58 | 11.0s | Top-down, 24 mm | Locked off | Only shadows and the heavy bed tipping over; the narrator straightens, smiling. | Lantern on the floor | bed_drag; score: drone_low | N: In an instant I dragged him to the floor, and pulled the hea… | cut |
| 3.19 ⓐ | 5:57.58 | 3.0s | WS across the street, 50 mm | Locked off | A neighbour's window lights up; a curtain twitches. | Night street | wind_loop; score: drone_low | — | cut |
| 3.20 | 6:00.58 | 7.0s | Floor-level, 35 mm | Locked off | The heartbeat slows… and stops. Three seconds of silence. | Lantern on the floor | —; score: silence | N: At length it ceased. The old man was dead. | cut |
| 3.21 | 6:07.58 | 9.0s | CU his hand on the nightshirt, 85 mm | Locked off | A hand rests on the still chest. | Lantern | —; score: drone_low | N: There was no pulsation. He was stone dead. His eye would tro… | cut |
| 4.1 ⓐ | 6:16.58 | 8.7s | MCU narrator, 50 mm | Slow push | Back in the void, calm. | Top light | —; score: drone_low | N: If still you think me mad, you will think so no longer when … | cut |
| 4.2 ⓐ | 6:25.29 | 6.0s | WS the wall, 35 mm | Locked off | Only his huge shadow works on the wall; nothing else is shown. | Lantern on the floor | work_muffled; score: drone_low | N: The night waned, and I worked hastily, but in silence. | cut |
| 4.3 | 6:31.29 | 8.0s | CU the floor, 50 mm | Slow crane up | Three planks lift away, revealing the dark joists. | Lantern | nail_squeal, nail_squeal, nail_squeal; score: drone_low | N: I then took up three planks from the flooring of the chamber… | cut |
| 4.4 | 6:39.29 | 8.2s | Top-down, 35 mm | Locked off | The planks settle back, seamless. | Lantern | hammer_muffled, hammer_muffled; score: drone_low | N: I then replaced the boards so cleverly, so cunningly, that n… | cut |
| 4.5 | 6:47.46 | 9.0s | MS narrator, 50 mm | Locked off | He wipes his clean hands and laughs. | Lantern | —; score: drone_low | N: There was nothing to wash out—no blood-spot whatever. A tub … | cut |
| 4.6 | 6:56.46 | 8.0s | CU the long-case clock face, 50 mm | Locked off | The clock strikes four. Then: knocking. | Moon | clock_strike, clock_strike, clock_strike, clock_strike, knock3; score: silence | N: When I had made an end of these labors, it was four o'clock—… | cut |
| 5.1 | 7:04.46 | 8.6s | MS, 35 mm, steadicam leading | Backward steadicam down the stairs | He descends with a candle, almost lightly. | Candle | steps_wood, knock3; score: drone_low | N: As the bell sounded the hour, there came a knocking at the s… | cut |
| 5.2 ⓐ | 7:13.04 | 13.2s | From the hall, 35 mm | Locked off | The street door opens on three officers with bull's-eye lanterns, breath fogging. | Their lanterns vs the street lamp | door_open, wind_loop; score: drone_low | N: There entered three men, who introduced themselves, with per… / O1: Forgive the hour, sir. A neighbour heard a shriek in the nig… | cut |
| 5.3 ⓐ | 7:26.25 | 8.8s | CU narrator, 50 mm | Locked off | All smiles. | Candle + lanterns | —; score: drone_low | NS: A shriek? My own, gentlemen—in a dream. The old man is away … | cut |
| 5.4 | 7:35.04 | 8.0s | WS, 24 mm | Pan with the lanterns | Lantern beams sweep the kitchen and hall. | Moving lantern beams | steps_group; score: drone_low | N: I took my visitors all over the house. I bade them search—se… / NS: Search well, gentlemen! | cut |
| 5.5 | 7:43.04 | 8.2s | MS, 35 mm | Gentle push | He opens the strongbox; the officers nod. | Lanterns + candle | coin; score: drone_low | N: I led them, at length, to his chamber. I showed them his tre… | cut |
| 5.6 | 7:51.29 | 16.2s | Floor-level, 24 mm | Locked off | His chair's legs settle exactly on the replaced planks. | Lanterns | chair_place, chair_place, chair_place; score: drone_tension | N: I brought chairs into the room, and desired them here to res… | cut |
| 5.7 ⓐ | 8:07.54 | 16.3s | Wide four-shot, 24 mm | Slow arc | Warm, almost cosy: three officers and their host. | Warm lanterns | laugh_group; score: drone_low | N: The officers were satisfied. My manner had convinced them. I… / O2: Cold night for it, eh? / O3: Colder than a churchyard. / N: They sat, and while I answered cheerily, they chatted of fam… | cut |
| 5.8 | 8:23.83 | 10.0s | CU narrator, 85 mm | Slow push | His smile slips. | Warm, draining | ringing; score: drone_tension | N: But, ere long, I felt myself getting pale and wished them go… | cut |
| 5.9 ⓐ | 8:33.83 | 7.0s | Macro: the floorboard under his chair, 100 mm | Locked off | Dust on the plank seam jumps with each beat. | Lanterns | ringing; score: drone_tension | N: The ringing became more distinct—until, at length, I found t… | cut |
| 5.10 | 8:40.83 | 13.0s | CU narrator ↔ officers, 50 mm | Handheld, growing | Sweat; the officers' faces blur and stretch. | Desaturating | —; score: drone_tension | N: It was a low, dull, quick sound—much such a sound as a watch… | cut |
| 5.11 | 8:53.83 | 14.8s | MS, 35 mm | 360° orbit | He paces; the camera circles him. | Desaturating | steps_heavy; score: drone_tension | N: I arose and argued about trifles, in a high key and with vio… | cut |
| 5.12 | 9:08.62 | 13.5s | Top-down, 24 mm | Locked off | He swings the chair and grinds it across the planks. | Cold | chair_scrape; score: drone_tension | N: Oh God! what could I do? I foamed—I raved—I swore! I swung t… | cut |
| 5.13 | 9:22.12 | 17.0s | CU officers, 35 mm wide-close | Slow dolly zoom | The officers smile on, pleasantly. One sips tea. | Cold, vignette | laugh_group; score: drone_tension | N: It grew louder—louder—louder! And still the men chatted plea… | cut |
| 5.14 | 9:39.08 | 8.1s | Rapid cuts on the beat | Shake on each beat | Eyes, smiles, the planks, his own eye. | Strobing | —; score: drone_tension | N: I felt that I must scream or die!—and now—again!—hark! loude… | hard cut |
| 5.15 | 9:47.21 | 9.2s | MS → top-down, 50 mm | Push, then whip | He leaps up and stamps on the planks, pointing. | Cold | stomp; score: silence | NS: Villains! Dissemble no more! I admit the deed!—tear up the p… | smash cut to black |
| 6.1 ⓐ | 9:56.38 | 3.0s | Black | — | Silence. Then one more heartbeat. | — | heart_single; score: silence | — | cut |
| 6.2 ⓐ | 9:59.38 | 5.0s | CU narrator, 85 mm | Locked off | Calm again, he whispers to us. | Top light | —; score: drone_low | N: Hearken. | cut |
| 6.3 | 10:04.38 | 9.0s | Credits | — | Based on 'The Tell-Tale Heart' by Edgar Allan Poe (1843). Credits. | — | —; score: drone_low | — | fade out |

ⓐ = shot contains adapted (non-Poe) material. Speakers: N narration, NS narrator on screen, OM old man, O1–O3 officers.
