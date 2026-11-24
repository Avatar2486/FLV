"""
THE TELL-TALE HEART — 10-minute FLV adaptation of Edgar Allan Poe's story (1843, public domain).

The single source of truth for the film: every shot, its narration and dialogue,
sound cues, framing notes and whether it is ADAPTED (not in Poe's text).
Voice generation, the audio mix, the Blender build and the production plan all read this file.

Narration lines are Poe's words, verbatim (some passages are cut for time).
Lines marked adapted=True, and shots whose `adapted` note is filled in, are FLV additions.
Plain Python, no Blender needed.
"""

TITLE = "The Tell-Tale Heart"

PLAN_INTRO = """
**Source:** "The Tell-Tale Heart" by Edgar Allan Poe, first published in *The Pioneer*, January 1843
(text: *The Works of the Late Edgar Allan Poe*, 1850 — see `source_text.md`). **Public domain worldwide:**
free to adapt, narrate and monetise; no permission or fee needed.

**Why this story.** It is one of the most famous horror stories ever written and fits a 10-minute
Blender film almost perfectly: one house, one night, a tiny cast (narrator, old man, three officers),
and a structure built on suspense — seven nights of creeping, the eighth-night attack, the cover-up,
and the police visit where guilt (the heartbeat) breaks the narrator. It is driven by things Blender
does well: darkness, a single beam of light, slow camera moves, close-ups of an eye, floorboards and
a clock, and above all sound (the heartbeat, a ticking watch, the death-watch beetle, silence).
"""

PLAN_APPROACH = """
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
"""
FPS = 24
RESOLUTION = (1920, 1080)          # 16:9 master for long-form YouTube; key action kept centre-safe

# Who speaks, with which voice. Every voice here is licensed for commercial use.
# Recorded sound (scripts/mix_story.py --real): cue -> (file in audio/sfx/freesound, longest seconds used).
# Cues not listed keep their synthesised sound (death-watch beetles, clock strikes, voices).
REAL_SFX = {
    "bed_creak": ("floorboard_creak_506661.mp3", 1.7), "wind_gust": ("wind_chimney_26189.mp3", 4.5),
    "wind_loop": ("wind_chimney_872557.mp3", None), "mouse": ("mouse_scurry_638668.mp3", 2.2),
    "cricket": ("cricket_chirp_164485.mp3", 0.6), "knock3": ("knock_street_door_119833.mp3", 3.7),
    "steps_wood": ("stairs_footsteps_51149.mp3", 5.5), "steps_group": ("stairs_footsteps_210573.mp3", 6.0),
    "steps_heavy": ("stairs_footsteps_210573.mp3", 8.0), "door_open": ("door_creak_275471.mp3", 4.6),
    "door_creak_soft": ("door_latch_710510.mp3", 3.0), "chair_place": ("chair_scrape_485141.mp3", 2.0),
    "chair_scrape": ("chair_scrape_485144.mp3", 5.3), "bell_toll": ("church_bell_454855.mp3", 7.0),
    "bed_drag": ("bed_drag_735345.mp3", 2.6),
}
# Score: Chopin (Musopen, CC0) under the synthesised drones. cue -> file in audio/music/chopin
SCORE = {"drone_low": "nocturne_op48_no1.mp3", "drone_night": "nocturne_op27_no1.mp3",
         "drone_tension": "prelude_op28_no15.mp3", "drone_rise": "prelude_op28_no24.mp3"}

CAST = {
    "N":  {"name": "The Narrator (voice-over)", "model": "en_US-john-medium", "speaker": None,
           "length_scale": 0.97, "fx": "narration", "licence": "public domain (LibriVox reader)"},
    "NS": {"name": "The Narrator (on screen)", "model": "en_US-john-medium", "speaker": None,
           "length_scale": 1.0, "fx": "room", "licence": "public domain (LibriVox reader)"},
    "OM": {"name": "The Old Man", "model": "en_US-joe-medium", "speaker": None,
           "length_scale": 1.3, "fx": "old", "licence": "CC0"},
    "O1": {"name": "Officer Hale (senior)", "model": "en_US-libritts-high", "speaker": 90,
           "length_scale": 1.05, "fx": "room", "licence": "CC BY 4.0 — LibriTTS (Zen et al., 2019)"},
    "O2": {"name": "Officer Brandt (young)", "model": "en_US-bryce-medium", "speaker": None,
           "length_scale": 1.0, "fx": "room", "licence": "public domain"},
    "O3": {"name": "Officer Mercer (quiet)", "model": "en_US-norman-medium", "speaker": None,
           "length_scale": 1.1, "fx": "room", "licence": "public domain (LibriVox reader)"},
}

SEQUENCES = {
    0: "Prologue — Hearken",
    1: "The Eye",
    2: "Seven Nights",
    3: "The Eighth Night",
    4: "Concealment",
    5: "The Visitors",
    6: "Epilogue",
}


def shot(id, set, min, lines=(), sfx=(), music=None, frame="", move="", action="", light="",
         transition="cut", adapted=""):
    """One shot. lines = [(cast key, text) or (cast key, text, True) when the line is adapted].
    sfx = [(cue, seconds from the shot start, gain)]; negative seconds count back from the end."""
    return {"id": id, "seq": int(id.split(".")[0]) if id[0].isdigit() else 0, "set": set, "min": min,
            "lines": [l if len(l) == 3 else (*l, False) for l in lines], "sfx": list(sfx), "music": music,
            "frame": frame, "move": move, "action": action, "light": light, "transition": transition,
            "adapted": adapted}


SHOTS = [
    # ------------------------------------------------------------------ 0. PROLOGUE
    shot("0.1", "black", 3, sfx=[("heart_single", 1.2, 1.0)], music="silence",
         frame="Black", action="A single heartbeat in the dark.", transition="fade in"),
    shot("0.2", "chamber_floor", 7, [("N", "True!—nervous—very, very dreadfully nervous I had been and am;")],
         sfx=[("watch_tick_loop", 0, 0.35)], music="drone_low",
         frame="ECU floorboards, 100 mm macro, f/2", move="Slow push along a plank seam",
         action="Dust drifts through a thin ray of light over the boards.", light="Single cold ray, haze"),
    shot("0.3", "void", 10, [("N", "but why will you say that I am mad? The disease had sharpened my senses—not "
                                   "destroyed—not dulled them. Above all was the sense of hearing acute.")],
         music="drone_low", frame="MCU narrator, 50 mm, f/2.8", move="Slow dolly in",
         action="The narrator sits in a straight-backed chair in a black void and speaks to us.",
         light="Hard top light, deep falloff", adapted="Direct-to-camera framing device (the 'you' of the text)"),
    shot("0.4", "void", 7, [("N", "I heard all things in the heaven and in the earth. I heard many things in hell.")],
         sfx=[("cricket", 0.8, 0.5), ("mouse", 2.6, 0.6), ("wind_gust", 4.2, 0.5)], music="drone_low",
         frame="ECU eyes, 85 mm", move="Locked off", action="His eyes dart toward each sound, left, right, above.",
         light="Top light", adapted="Spatialised sounds show his 'acute hearing'"),
    shot("0.5", "void", 8, [("N", "How, then, am I mad? Hearken! and observe how healthily—how calmly I can tell "
                                   "you the whole story.")],
         music="drone_low", frame="MCU → CU, 50 mm", move="Push in to a close-up", action="A thin smile.",
         light="Top light", transition="smash cut to title"),
    shot("T", "title", 5, sfx=[("boom", 0.2, 1.0), ("heart_single", 0.25, 0.8)], music="silence",
         frame="Title card", action="THE TELL-TALE HEART — after Edgar Allan Poe", transition="fade out"),

    # ------------------------------------------------------------------ 1. THE EYE
    shot("1.1", "exterior", 5, sfx=[("wind_loop", 0, 0.6)], music="drone_low",
         frame="WS the narrow two-storey house at dusk, 35 mm", move="Crane down from roofline to the door",
         action="A street lamp flickers; one lit window upstairs.", light="Blue dusk, warm window",
         transition="dissolve", adapted="Establishing shot of the house"),
    shot("1.2", "kitchen", 6, [("N", "It is impossible to say how first the idea entered my brain; but once "
                                     "conceived, it haunted me day and night.")],
         sfx=[("cup_clink", 1.5, 0.5)], music="drone_low",
         frame="WS kitchen, 24 mm", move="Slow lateral dolly",
         action="Morning. The narrator prepares a breakfast tray with care.", light="Soft morning window light",
         adapted="Visualises 'I was never kinder to the old man'"),
    shot("1.3", "stairs", 5, [("N", "Object there was none. Passion there was none.")],
         sfx=[("steps_wood", 0.3, 0.6)], music="drone_low",
         frame="MS following, 35 mm", move="Steadicam follows him up the stairs",
         action="He carries the tray up to the old man's chamber.", light="Daylight through the stairwell"),
    shot("1.4", "chamber_day", 7, [("N", "I loved the old man. He had never wronged me. He had never given me "
                                         "insult.")],
         music="drone_low", frame="Two-shot, 35 mm", move="Gentle push",
         action="The old man sits up in bed and smiles as the tray is set down.",
         light="Daylight slits through the shutters"),
    shot("1.5", "chamber_day", 4, [("N", "For his gold I had no desire.")], sfx=[("coin", 0.6, 0.4)],
         music="drone_low", frame="Insert: the strongbox of coins, 85 mm", move="Rack focus box → narrator",
         action="The open chest gleams; the narrator does not look at it.", light="Daylight slit"),
    shot("1.6", "chamber_day", 5, [("N", "I think it was his eye! yes, it was this!")], music="drone_rise",
         frame="OTS narrator → old man, 85 mm", move="Rack focus to the old man's face",
         action="The old man turns his head toward the narrator.", light="Daylight slit"),
    shot("1.7", "eye", 7, [("N", "One of his eyes resembled that of a vulture—a pale blue eye, with a film over "
                                 "it.")],
         sfx=[("sting_low", 0.2, 0.7)], music="drone_rise", frame="ECU the vulture eye, 100 mm macro",
         move="Creeping push", action="The milky blue eye blinks, slowly.", light="Soft key, cold rim"),
    shot("1.8", "chamber_day", 4, [("N", "Whenever it fell upon me, my blood ran cold;")],
         sfx=[("cup_rattle", 0.4, 0.5)], music="drone_low", frame="CU narrator, 85 mm", move="Locked off",
         action="His teacup trembles on its saucer.", light="Daylight"),
    shot("1.9", "narrator_room", 9, [("N", "and so by degrees—very gradually—I made up my mind to take the life "
                                           "of the old man, and thus rid myself of the eye for ever.")],
         sfx=[("clock_tick_loop", 0, 0.4)], music="drone_low",
         frame="WS narrator at his window, 24 mm", move="Locked off time-lapse",
         action="Day becomes night around him as he sits perfectly still.", light="Day → dusk → candle",
         transition="dissolve to night", adapted="Time-lapse of his decision"),

    # ------------------------------------------------------------------ 2. SEVEN NIGHTS
    shot("2.1", "corridor", 10, [("N", "Now this is the point. You fancy me mad. Madmen know nothing. But you "
                                       "should have seen me. You should have seen how wisely I proceeded—with "
                                       "what caution—with what foresight!")],
         sfx=[("clock_tick_loop", 0, 0.5), ("door_creak_soft", 0.5, 0.4)], music="drone_night",
         frame="Low WS down the corridor, 24 mm", move="Slow dolly back as he advances",
         action="He leaves his room with a closed dark lantern; the long-case clock nears twelve.",
         light="Moonlight from the landing window, black corridor"),
    shot("2.2", "watch", 4, [("N", "I was never kinder to the old man than during the whole week before I killed "
                                   "him.")],
         sfx=[("watch_tick_loud", 0, 0.8)], music="drone_night",
         frame="Insert: pocket watch in his palm, 100 mm", move="Locked off",
         action="The minute hand reaches twelve.", light="Moon sliver on the glass"),
    shot("2.3", "door_latch", 5, [("N", "And every night, about midnight, I turned the latch of his door and "
                                        "opened it—oh, so gently!")],
         sfx=[("latch", 1.2, 0.8)], music="drone_night", frame="Macro: fingertips on the latch, 100 mm, f/2",
         move="Focus pull fingers → latch", action="The latch turns a millimetre at a time.",
         light="Moon edge light"),
    shot("2.4", "chamber_night", 9, [("N", "And then, when I had made an opening sufficient for my head, I put "
                                           "in a dark lantern, all closed, closed, so that no light shone out, and "
                                           "then I thrust in my head.")],
         sfx=[("door_creak_soft", 0.6, 0.5)], music="drone_night",
         frame="Reverse from the bed side, 35 mm", move="Locked off",
         action="The door opens a sliver; the lantern's dark shape eases in, then his head.",
         light="Almost black; faint moon around the shutters"),
    shot("2.5", "chamber_night", 13, [("N", "It took me an hour to place my whole head within the "
                                            "opening so far that I could see him as he lay upon his bed. Ha!—would "
                                            "a madman have been so wise as this?")],
         sfx=[("clock_tick_fast", 0, 0.35)], music="drone_night",
         frame="Profile CU of his head in the door gap, 85 mm", move="Locked off",
         action="His head creeps forward while the clock's hands sweep a whole hour behind him.",
         light="Moon rim", adapted="Clock time-lapse shows the hour"),
    shot("2.6", "lantern", 7, [("N", "And then, when my head was well in the room, I undid the lantern "
                                     "cautiously—oh, so cautiously—cautiously (for the hinges creaked)—")],
         sfx=[("hinge_tiny", 2.5, 0.7)], music="drone_night", frame="Macro: the lantern shutter, 100 mm",
         move="Slow push", action="A thumb eases the tin shutter open a crack.", light="Lantern glow leaks out"),
    shot("2.7", "chamber_night", 6, [("N", "I undid it just so much that a single thin ray fell upon the vulture "
                                           "eye.")],
         music="drone_night", frame="WS chamber, 24 mm", move="Lateral dolly following the beam",
         action="A thread of light crosses the dark room and lands on the old man's closed eye.",
         light="One hard beam in haze"),
    shot("2.8", "chamber_night", 16, [("N", "And this I did for seven long nights—every night just at midnight—but "
                                            "I found the eye always closed; and so it was impossible to do the "
                                            "work; for it was not the old man who vexed me, but his Evil Eye.")],
         sfx=[("clock_chime", 0.3, 0.4), ("clock_chime", 6.3, 0.35), ("clock_chime", 12.3, 0.3)],
         music="drone_night", frame="Repeated beam composition, 50 mm", move="Locked off, varied per night",
         action="Night II … Night VII: the same beam, the same closed eye; the narrator more gaunt each night.",
         light="Beam + moon", adapted="Night II–VII title cards"),
    shot("2.9", "chamber_day", 16, [("N", "And every morning, when the day broke, I went boldly into the "
                                          "chamber,"),
                                    ("NS", "Good morning, sir! Did you pass the night well?", True),
                                    ("OM", "Well enough, my boy. Well enough.", True),
                                    ("N", "He would have been a very profound old man, indeed, to "
                                          "suspect that every night, just at twelve, I looked in upon him while he "
                                          "slept.")],
         music="drone_low", frame="Two-shot, 35 mm handheld feel", move="Subtle handheld drift",
         action="Bright morning. The narrator throws open the shutters and greets the old man warmly.",
         light="Hard morning sun", transition="smash cut to black",
         adapted="Morning dialogue (the text reports it: 'calling him by name in a hearty tone')"),

    # ------------------------------------------------------------------ 3. THE EIGHTH NIGHT
    shot("3.1", "corridor", 8, [("N", "Upon the eighth night I was more than usually cautious in opening the "
                                      "door. A watch's minute hand moves more quickly than did mine.")],
         sfx=[("bell_toll", 0.2, 0.7), ("wind_loop", 0, 0.4)], music="drone_tension",
         frame="WS corridor, 24 mm, NIGHT VIII card", move="Very slow push", action="He waits at the door.",
         light="Moon, deeper shadows", adapted="Night VIII title card"),
    shot("3.2", "door_latch", 6, [("N", "Never before that night had I felt the extent of my own powers.")],
         sfx=[("watch_tick_loud", 0, 0.5)], music="drone_tension", frame="Macro: the door edge creeping, 85 mm",
         move="Locked off", action="The door edge moves slower than a watch hand.", light="Moon edge"),
    shot("3.3", "door_gap", 4, [("N", "I fairly chuckled at the idea; and perhaps he heard me;")],
         sfx=[("chuckle", 0.6, 0.5)], music="drone_tension", frame="CU narrator in the gap, 85 mm",
         move="Locked off", action="His shoulders shake with a stifled laugh.", light="Underglow from the lantern"),
    shot("3.4", "chamber_night", 4, [("N", "for he moved on the bed suddenly, as if startled.")],
         sfx=[("bed_creak", 0.2, 0.9)], music="drone_tension", frame="WS chamber, 24 mm", move="Locked off",
         action="The old man shifts in bed.", light="Pitch black, shutter outlines"),
    shot("3.5", "door_gap", 12, [("N", "Now you may think that I drew back—but no. His room was as black as pitch "
                                       "with the thick darkness, and so I knew that he could not see the opening of the "
                                       "door, and I kept pushing it on steadily, steadily.")],
         music="drone_tension", frame="CU narrator, 85 mm", move="Imperceptible push",
         action="He freezes — then keeps pushing.", light="Underglow"),
    shot("3.6", "lantern", 5, [("N", "I had my head in, and was about to open the lantern, when my thumb slipped "
                                     "upon the tin fastening,")],
         sfx=[("clink", -0.6, 1.0)], music="drone_tension", frame="Macro: thumb on the tin fastening, 100 mm",
         move="Locked off", action="The thumb slips — CLINK.", light="Lantern leak"),
    shot("3.7", "chamber_night", 4, [("N", "and the old man sprang up in the bed, crying out—"),
                                     ("OM", "Who's there?")],
         sfx=[("bed_creak", 1.4, 1.0)], music="silence", frame="WS, 24 mm", move="Snap push",
         action="The old man bolts upright in bed.", light="Silhouette against the shutters"),
    shot("3.8", "chamber_night", 16, [("N", "I kept quite still and said nothing. For a whole hour I did not move "
                                            "a muscle. He was still sitting up in the bed, listening;—just as I have done, night "
                                            "after night, hearkening to the death watches in the wall.")],
         sfx=[("deathwatch_loop", 0, 0.5)], music="silence",
         frame="High corner two-shot, 24 mm", move="Locked off",
         action="Both frozen. Moonlight crawls across the floor as the hour passes.",
         light="Moving moon patch", adapted="Moonlight time-lapse"),
    shot("3.9", "beetle", 3, sfx=[("deathwatch", 0.3, 1.0), ("deathwatch", 1.6, 0.9)], music="silence",
         frame="Macro: a death-watch beetle in the wall timber, 100 mm", move="Locked off",
         action="The beetle taps.", light="Raking moonlight", adapted="Visual of the 'death watches'"),
    shot("3.10", "chamber_night", 6, [("N", "Presently I heard a slight groan, and I knew it was the groan of "
                                            "mortal terror.")],
         sfx=[("groan", 0.3, 0.8)], music="drone_tension", frame="CU old man, 85 mm", move="Slow push",
         action="His lips tremble in the dark.", light="Faint moon on his face"),
    shot("3.11", "chamber_night", 12, [("N", "He had been saying to himself—"),
                                       ("OM", "It is nothing but the wind in the chimney—it is only a mouse "
                                              "crossing the floor—it is merely a cricket which has made a single "
                                              "chirp.")],
         sfx=[("wind_gust", 2.0, 0.6), ("mouse", 5.0, 0.7), ("cricket", 8.0, 0.6)], music="drone_tension",
         frame="Cutaways: chimney, floor, wall, 50 mm", move="Small pushes",
         action="Soot falls in the grate; a mouse crosses the boards; a cricket chirps.",
         light="Moon", adapted="Each 'supposition' shown"),
    shot("3.12", "chamber_night", 7, [("N", "All in vain; because Death, in approaching him, had stalked with his "
                                            "black shadow before him, and enveloped the victim.")],
         music="drone_tension", frame="WS wall above the bed, 24 mm", move="Slow tilt down",
         action="The narrator's shadow stretches, impossibly long, across the wall and over the old man.",
         light="Low lantern leak casting the shadow", adapted="Shadow-of-Death visual"),
    shot("3.13", "lantern", 9, [("N", "So I opened it—you cannot imagine how stealthily, stealthily—until, at "
                                      "length, a single dim ray, like the thread of the spider, shot from out the "
                                      "crevice and fell upon the vulture eye.")],
         music="drone_tension", frame="Macro: the crevice, then follow the ray, 100 → 50 mm",
         move="Track along the beam", action="The ray, fine as spider silk, crosses the room.",
         light="Thread-thin beam in haze"),
    shot("3.14", "eye", 4, [("N", "It was open—wide, wide open—and I grew furious as I gazed upon it.")],
         sfx=[("sting_high", 0.0, 1.0)], music="drone_tension", frame="ECU the eye, 100 mm", move="Snap zoom in",
         action="The vulture eye is wide open.", light="The beam on the eye"),
    shot("3.15", "door_gap", 14, [("N", "And now—have I not told you that what you mistake for madness is but "
                                        "over-acuteness of the senses?—there came to my ears a low, "
                                        "dull, quick sound, such as a watch makes when enveloped in cotton. It was the beating of the old man's heart.")],
         sfx=[("heart_start", 4.0, 0.0)], music="drone_tension", frame="CU narrator, 85 mm", move="Slow push",
         action="He tilts his head, listening. Insert: a watch wrapped in cotton.", light="Underglow"),
    shot("3.16", "chamber_night", 12, [("N", "It grew quicker and quicker, and louder and louder every instant. And now a new anxiety seized "
                                             "me—the sound would be heard by a neighbor! The old man's hour had "
                                             "come!")],
         music="drone_tension", frame="Cutting CU eye / CU narrator / lantern hand", move="Creeping Dutch tilt",
         action="Cuts quicken with the heartbeat.", light="Beam, moon", transition="hard cut on the yell"),
    shot("3.17", "chamber_night", 3, sfx=[("lantern_open", 0.0, 1.0), ("yell", 0.1, 0.9), ("shriek", 0.6, 0.9)],
         music="silence", frame="WS, 24 mm", move="Whip pan",
         action="He throws the lantern open — light floods the room — and leaps.", light="Lantern fully open"),
    shot("3.18", "chamber_night", 11, [("N", "In an instant I dragged him to the floor, and pulled the heavy bed "
                                             "over him. But, for many minutes, the heart beat on with a muffled sound.")],
         sfx=[("bed_drag", 0.5, 1.0), ("heart_muffled", 4.0, 0.0)], music="drone_low",
         frame="Top-down, 24 mm", move="Locked off",
         action="Only shadows and the heavy bed tipping over; the narrator straightens, smiling.",
         light="Lantern on the floor", adapted="Violence kept off-screen"),
    shot("3.19", "exterior", 3, sfx=[("wind_loop", 0, 0.5)], music="drone_low",
         frame="WS across the street, 50 mm", move="Locked off",
         action="A neighbour's window lights up; a curtain twitches.", light="Night street",
         adapted="The neighbour who heard the shriek"),
    shot("3.20", "chamber_night", 7, [("N", "At length it ceased. The old man was dead.")],
         music="silence", frame="Floor-level, 35 mm", move="Locked off",
         action="The heartbeat slows… and stops. Three seconds of silence.", light="Lantern on the floor"),
    shot("3.21", "chamber_night", 9, [("N", "There was no pulsation. He was stone dead. His eye would trouble me no "
                                            "more.")],
         music="drone_low", frame="CU his hand on the nightshirt, 85 mm", move="Locked off",
         action="A hand rests on the still chest.", light="Lantern"),

    # ------------------------------------------------------------------ 4. CONCEALMENT
    shot("4.1", "void", 8, [("N", "If still you think me mad, you will think so no longer when I describe the wise "
                                  "precautions I took for the concealment of the body.")],
         music="drone_low", frame="MCU narrator, 50 mm", move="Slow push", action="Back in the void, calm.",
         light="Top light", adapted="Framing device"),
    shot("4.2", "chamber_night", 6, [("N", "The night waned, and I worked hastily, but in silence.")],
         sfx=[("work_muffled", 0.5, 0.5)], music="drone_low", frame="WS the wall, 35 mm", move="Locked off",
         action="Only his huge shadow works on the wall; nothing else is shown.", light="Lantern on the floor",
         adapted="Dismemberment omitted (implied)"),
    shot("4.3", "chamber_floor", 8, [("N", "I then took up three planks from the flooring of the chamber, and "
                                           "deposited all between the scantlings.")],
         sfx=[("nail_squeal", 0.6, 0.9), ("nail_squeal", 2.8, 0.8), ("nail_squeal", 5.0, 0.8)],
         music="drone_low", frame="CU the floor, 50 mm", move="Slow crane up",
         action="Three planks lift away, revealing the dark joists.", light="Lantern"),
    shot("4.4", "chamber_floor", 8, [("N", "I then replaced the boards so cleverly, so cunningly, that no human "
                                           "eye—not even his—could have detected any thing wrong.")],
         sfx=[("hammer_muffled", 1.0, 0.6), ("hammer_muffled", 2.2, 0.6)], music="drone_low",
         frame="Top-down, 35 mm", move="Locked off", action="The planks settle back, seamless.", light="Lantern"),
    shot("4.5", "chamber_night", 9, [("N", "There was nothing to wash out—no blood-spot "
                                           "whatever. A tub had caught all—ha! ha!")],
         music="drone_low", frame="MS narrator, 50 mm", move="Locked off",
         action="He wipes his clean hands and laughs.", light="Lantern"),
    shot("4.6", "corridor", 8, [("N", "When I had made an end of these labors, it was four o'clock—still dark as "
                                      "midnight.")],
         sfx=[("clock_strike", 0.4, 0.8), ("clock_strike", 1.9, 0.8), ("clock_strike", 3.4, 0.8),
              ("clock_strike", 4.9, 0.8), ("knock3", -1.6, 1.0)], music="silence",
         frame="CU the long-case clock face, 50 mm", move="Locked off", action="The clock strikes four. Then: knocking.",
         light="Moon"),

    # ------------------------------------------------------------------ 5. THE VISITORS
    shot("5.1", "stairs", 8, [("N", "As the bell sounded the hour, there came a knocking at the street door. I went "
                                    "down to open it with a light heart—for what had I now to fear?")],
         sfx=[("steps_wood", 1.0, 0.6), ("knock3", 3.5, 0.7)], music="drone_low",
         frame="MS, 35 mm, steadicam leading", move="Backward steadicam down the stairs",
         action="He descends with a candle, almost lightly.", light="Candle"),
    shot("5.2", "entry", 12, [("N", "There entered three men, who introduced themselves, with perfect suavity, as "
                                    "officers of the police."),
                              ("O1", "Forgive the hour, sir. A neighbour heard a shriek in the night. We are bound to "
                                     "search the premises.", True)],
         sfx=[("door_open", 0.2, 0.8), ("wind_loop", 0, 0.5)], music="drone_low",
         frame="From the hall, 35 mm", move="Locked off",
         action="The street door opens on three officers with bull's-eye lanterns, breath fogging.",
         light="Their lanterns vs the street lamp",
         adapted="Officer dialogue paraphrases the text's report"),
    shot("5.3", "entry", 8, [("NS", "A shriek? My own, gentlemen—in a dream. The old man is away in the country. "
                                    "Come in, come in!", True)],
         music="drone_low", frame="CU narrator, 50 mm", move="Locked off", action="All smiles.",
         light="Candle + lanterns", adapted="'The shriek, I said, was my own in a dream…' as dialogue"),
    shot("5.4", "kitchen", 8, [("N", "I took my visitors all over the house. I bade them search—search well."),
                               ("NS", "Search well, gentlemen!", True)],
         sfx=[("steps_group", 0.5, 0.6)], music="drone_low", frame="WS, 24 mm", move="Pan with the lanterns",
         action="Lantern beams sweep the kitchen and hall.", light="Moving lantern beams"),
    shot("5.5", "chamber_dawn", 6, [("N", "I led them, at length, to his chamber. I showed them his treasures, "
                                          "secure, undisturbed.")],
         sfx=[("coin", 2.0, 0.5)], music="drone_low", frame="MS, 35 mm", move="Gentle push",
         action="He opens the strongbox; the officers nod.", light="Lanterns + candle"),
    shot("5.6", "chamber_dawn", 13, [("N", "I brought chairs into the room, "
                                           "and desired them here to rest from their fatigues, while I myself, in "
                                           "the wild audacity of my perfect triumph, placed my own seat upon the "
                                           "very spot beneath which reposed the corpse of the victim.")],
         sfx=[("chair_place", 1.5, 0.6), ("chair_place", 3.5, 0.6), ("chair_place", 9.0, 0.8)],
         music="drone_tension", frame="Floor-level, 24 mm", move="Locked off",
         action="His chair's legs settle exactly on the replaced planks.", light="Lanterns"),
    shot("5.7", "chamber_dawn", 12, [("N", "The officers were satisfied. My manner had convinced them. I was "
                                           "singularly at ease."),
                                     ("O2", "Cold night for it, eh?", True),
                                     ("O3", "Colder than a churchyard.", True),
                                     ("N", "They sat, and while I answered cheerily, they chatted of familiar "
                                           "things.")],
         sfx=[("laugh_group", -2.0, 0.4)], music="drone_low", frame="Wide four-shot, 24 mm", move="Slow arc",
         action="Warm, almost cosy: three officers and their host.", light="Warm lanterns",
         adapted="Small talk lines"),
    shot("5.8", "chamber_dawn", 10, [("N", "But, ere long, I felt myself getting pale and wished them gone. My head "
                                           "ached, and I fancied a ringing in my ears.")],
         sfx=[("ringing", 3.0, 0.4)], music="drone_tension", frame="CU narrator, 85 mm", move="Slow push",
         action="His smile slips.", light="Warm, draining"),
    shot("5.9", "chamber_floor", 7, [("N", "The ringing became more distinct—until, at length, I found that the "
                                           "noise was not within my ears.")],
         sfx=[("ringing", 0, 0.5), ("heart_return", 3.5, 0.0)], music="drone_tension",
         frame="Macro: the floorboard under his chair, 100 mm", move="Locked off",
         action="Dust on the plank seam jumps with each beat.", light="Lanterns", adapted="Dust-on-beat visual"),
    shot("5.10", "chamber_dawn", 13, [("N", "It was a low, dull, quick sound—much such a sound as a watch makes "
                                            "when enveloped in cotton. I gasped for breath—and yet the officers "
                                            "heard it not.")],
         music="drone_tension", frame="CU narrator ↔ officers, 50 mm", move="Handheld, growing",
         action="Sweat; the officers' faces blur and stretch.", light="Desaturating"),
    shot("5.11", "chamber_dawn", 12, [("N", "I arose and argued about trifles, in a high key and with violent "
                                            "gesticulations; but the noise steadily increased. I paced the floor to and fro with heavy strides—but the noise "
                                            "steadily increased.")],
         sfx=[("steps_heavy", 2.0, 0.7)], music="drone_tension", frame="MS, 35 mm", move="360° orbit",
         action="He paces; the camera circles him.", light="Desaturating"),
    shot("5.12", "chamber_dawn", 10, [("N", "Oh God! what could I do? I foamed—I raved—I swore! I swung the chair "
                                            "upon which I had been sitting, and grated it upon the boards, but the "
                                            "noise arose over all.")],
         sfx=[("chair_scrape", 5.0, 1.0)], music="drone_tension", frame="Top-down, 24 mm", move="Locked off",
         action="He swings the chair and grinds it across the planks.", light="Cold"),
    shot("5.13", "chamber_dawn", 12, [("N", "It grew louder—louder—louder! And still the men chatted pleasantly, "
                                            "and smiled. Was it possible they heard not? Almighty God!—no, no! They "
                                            "heard!—they suspected!—they knew!—they were making a mockery of my "
                                            "horror!")],
         sfx=[("laugh_group", 2.0, 0.5)], music="drone_tension", frame="CU officers, 35 mm wide-close",
         move="Slow dolly zoom", action="The officers smile on, pleasantly. One sips tea.", light="Cold, vignette"),
    shot("5.14", "chamber_dawn", 6, [("N", "I felt that I must scream or die!—and now—again!—hark! louder! louder! "
                                           "louder! louder!—")],
         music="drone_tension", frame="Rapid cuts on the beat", move="Shake on each beat",
         action="Eyes, smiles, the planks, his own eye.", light="Strobing", transition="hard cut"),
    shot("5.15", "chamber_dawn", 8, [("NS", "Villains! Dissemble no more! I admit the deed!—tear up the planks!—"
                                            "here, here!—it is the beating of his hideous heart!")],
         sfx=[("stomp", 2.5, 1.0)], music="silence", frame="MS → top-down, 50 mm", move="Push, then whip",
         action="He leaps up and stamps on the planks, pointing.", light="Cold", transition="smash cut to black"),

    # ------------------------------------------------------------------ 6. EPILOGUE
    shot("6.1", "black", 3, sfx=[("heart_single", 2.0, 0.9)], music="silence", frame="Black",
         action="Silence. Then one more heartbeat.", adapted="Final heartbeat"),
    shot("6.2", "void", 5, [("N", "Hearken.", True)], music="drone_low", frame="CU narrator, 85 mm",
         move="Locked off", action="Calm again, he whispers to us.", light="Top light",
         adapted="Closing callback to the opening"),
    shot("6.3", "credits", 9, music="drone_low", frame="Credits",
         action="Based on 'The Tell-Tale Heart' by Edgar Allan Poe (1843). Credits.", transition="fade out"),
]

# The heartbeat score: (shot id where it starts, seconds into that shot, start bpm, end bpm,
#                       shot id where it ends, seconds into that shot, muffled?)
HEARTBEATS = [
    ("3.15", 9.0, 62, 96, "3.17", 0.2, False),     # the old man's heart, rising to the attack
    ("3.18", 6.0, 90, 40, "3.20", 3.0, True),      # under the bed, slowing to nothing
    ("5.8", 2.0, 60, 150, "5.15", 6.0, True, "5.13"),     # the tell-tale heart under the planks
]
