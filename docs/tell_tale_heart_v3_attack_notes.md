# Tell-Tale Heart v3 preview: "the attack" (shots 3.11–3.21)

The story picks up where the v2 preview ("the eighth night", 3.1–3.10) stops: the old man sitting up in
bed, listening; the narrator's head in the door. This part holds the hardest scene in the film: two
people in physical contact, a body moved by hands, and a heavy bed pulled over him, with the project's
rules of no clipping and nothing moving unless a hand moves it.

| What | Where |
|---|---|
| Scene builder, 480p draft (with sound, no ffmpeg), 1080p render | `stories/the_tell_tale_heart/preview_v3.py` |
| Scene | `blender/scenes/tell_tale_heart_v3_attack.blend` |
| Timeline (shot starts, line times, action marks) | `output/renders/the_tell_tale_heart_v3_attack/timeline.json` |
| Lines for v2-style (Chatterbox) voices | `stories/the_tell_tale_heart/preview_v3/lines.json` |
| Toolkit change: `reach()` follows a moving body | `scripts/humans.py` |

```
blender -b --factory-startup --python stories/the_tell_tale_heart/preview_v3.py -- build      # ~1.5 min
blender -b blender/scenes/tell_tale_heart_v3_attack.blend --python stories/the_tell_tale_heart/preview_v3.py -- draft
    # 480p frames + soundtrack + MP4 -> output/renders/the_tell_tale_heart_v3_attack/draft_480p.mp4 (~75 min, RTX 3050)
blender -b blender/scenes/tell_tale_heart_v3_attack.blend --python stories/the_tell_tale_heart/preview_v3.py -- render 1 2
    # 1080p frames, share 1 of 2 (run share 2 in a second Blender)
```

## The shots (98 s)

| Shot | What happens | Camera |
|---|---|---|
| 3.11 | The old man talks himself out of it ("only the wind… a mouse… a cricket"), lips from the voice; a mouse crosses the floor | MS of him; floor insert |
| 3.12 | The narrator's palm eases the door wider; let go, it swings on and stands open. His shadow, thrown by a light low behind him, falls across the wall over the bed | WS of the wall, tilting down |
| 3.13 | His thumb opens the lantern's shutter a crack; a thread of light crosses the haze to the eye | macro on the crevice; tracking along the ray |
| 3.14 | The vulture eye, wide open, in the light | ECU, snap zoom |
| 3.15–3.16 | He hears the heart; head tilted, then fury; cuts quicken with the beat, a creeping Dutch tilt | CU narrator / eye / lantern hand |
| 3.17 | He flings the shutter open (light floods the room), drops the lantern (it falls, rocks and stands on the floor), yells and runs in; the old man shrieks | WS from the north-west corner, whip pan to the bed |
| 3.18 | He seizes him at the shoulders, shoves him down flat, hauls him off the bed to the floor; the old man grabs at his forearms, then fights on the floor; the narrator goes to the foot of the bed, takes the feather-bed's corner and drags it off the frame over him; kneels and presses down while the heart beats on, muffled | top-down, locked off |
| 3.20 | The heart slows and stops; his bare feet stick out from under the feather-bed | floor level |
| 3.21 | The feather-bed is back on the frame (between the shots); the narrator's hand on the still chest | CU from the bed side |

3.19 (a neighbour's window, the street set) is left out of this preview.

## Choices

- **"The heavy bed" is the feather-bed.** In Poe's English a bed is the mattress; a heavy feather-bed
  smothers him. The gothic bed's frame can't cover a man lying beside it whichever way it tips (measured
  on the set), and the feather-bed reads clearly from above. The bed model is one mesh; its bedding (a
  draped piece with hanging sides) is split off as `V3_Featherbed`, and its two pillows as their own
  objects, which stay on the frame and settle onto what is left under them when the feather-bed is pulled
  from under them. A straw tick and side boards are added underneath, as 1840s beds had.
- **Voices** are the first Piper takes, the only recordings of these lines; the narrator therefore
  sounds different from the v2 preview. `preview_v3/lines.json` makes the Chatterbox versions; the build
  uses them as soon as they exist.
- **The soundtrack is mixed inside Blender** (numpy; Blender's own decoder for the MP3s), from the
  film's sound cues, recorded Freesound takes, the synthesised score and the heartbeat runs, plus this
  scene's actions (the lantern landing, the body hitting the floor, the feather-bed dragged, the floor
  creaking as he kneels). No ffmpeg needed. No loudness normalisation yet.

## What was hard, and how each was found and fixed

| Problem | Cause | Fix |
|---|---|---|
| Hands could not stay on someone moving | `reach()` read the body's position once, at the call | It reads it per frame (characters that don't move behave exactly as before; self-check passes) |
| Two people holding each other | Each one's hands follow the other's body | The narrator's hands follow the old man's shoulders (which his arms don't move); then the old man's hands follow the narrator's forearms |
| Walking, running, kneeling for our rigs | Mocap clips can't be blended between segments here | A procedural gait layered on a path (stride and cadence from speed, backward steps reverse the cycle, arms swing only when free) and a kneel layer; sign conventions measured first |
| The blanket swung like a wing while he kicked | It was attached to his thigh | It has its own shape keys: flat once his legs leave, then lifted and draped with the feather-bed it lies on |
| His raised arms went through the feather-bed | They were still up as it came over | Arms come down as the feather-bed is pulled |
| The feather-bed has to lie on a body | It is a rigid model | Shape keys: "pulled" (near side lifted toward his hands), "draped" and "pressed" (below) |
| In the first draft the feather-bed and blanket hovered over him like card: seen from his feet (3.20), his legs showed under them, with a flat strip on the floor | "Draped" floated the top a fixed ~19 cm over the body and dropped the sides in a wall onto a flat brim; the model is a single sheet of 981 points | The sides fall open; the top lies a soft ~9 cm over a bridged height field (a thick quilt feels the body, not the nose), thinning to edges that lie on what is really there (his shins, the floor) and close down over his legs at the foot end; soft folds where it lies flat; subdivided in the render from the cut to 3.18. The blanket lies on it, its sides part folded under. "Pressed" flattens it under the narrator's knees and shins as he kneels |
| The old man's hands stuck up through the feather-bed in 3.20 | His grab at the narrator's forearms ended 6 frames after its last goal, before `reach()`'s 8-frame let-go finished, so his arms stayed a third raised for good (hands 22 cm above his hips) | The grab runs long enough to let go fully; his hands lie at his sides |
| The narrator's hands pressed on air once the feather-bed lay low (18 cm up) | Kneeling upright his arms can't reach it | He leans in from the hips while pressing, as in 3.21; palms sunk a little into it. In 3.21 (his hand had been resting on the old man's raised forearm) he leans a little further, to the chest |
| The narrator's close-up spun round through 3.16 (by 66 s the camera was in his ear) | The creeping Dutch tilt read the camera's rotation back from its own last key and rolled it again, every 6 frames | Each key is built from the aim plus that frame's roll. The close-up also follows his (smoothed) head, with room in front of his face and the focus on it; the eye insert follows the eye |
| The thread of light never reached the eye | Traced: the barely open shutter swept over the light, and the door stood in the beam | The light sits just in front of the lens; the door swings fully open. A sweep of door angles showed the beam clears only past 90 degrees: the door is hinged on the east jamb, not the west as first assumed |
| The beam didn't show in the haze | Volume tiles (8 px) were coarser than the beam | 4 px tiles, a brighter beam; it is also re-aimed at the eye as his head moves |
| The door hid him in the wide shot | Seen from the east, the open door covers the doorway | The wide shot is from the north-west corner |
| His hand could not reach the chest in 3.21 | Kneeling upright, his shoulder was ~0.35 m too high | He leans in from the hips (thighs held) and lays the hand low on the near side of the chest |
| The close-up of the hand showed his own sleeve | The camera was on his side | Moved to the bed side |

## Still open

- **Contact is measured only where it was a problem**: the narrator's palms over the feather-bed (3–4 cm
  wrist-to-top while pressing, the palm on it; ~2 cm higher for a moment as he pants just after the
  heart stops) and on the chest in 3.21 (on it); his knees clear the old man's hand by 20 cm; the old
  man's hands at hip height under it. There is no full collision pass like v2's.
- **The gait is procedural**: the feet slide a little, most visible from above in 3.18.
- **The feather-bed** shows a brief crease while it changes from "pulled" to "draped", and it is a shape,
  not cloth: it does not move when he twitches under it, so his twitches are kept small (his bare feet,
  out from under it, show them). Two pillows sink 1–2.5 cm into its near edge where it still lies on the
  bed.
- **The eye insert (3.14, 3.16)** has a hard black shadow line down the cheek from the eye (a shadow of the
  brow in the thread of light); not chased.
- **The shadow on the wall (3.12)** is broad rather than a crisp silhouette.
- **The 3.21 close-up** was framed for the hand on his forearm; with the hand now lower, on the chest, it
  sits at the bottom edge of the frame, partly cut off. The camera should come down a little.
- **The 3.11 grate insert** was dropped (the soot didn't read in the dark).
- **Lips** use the loudness fallback on this machine (Wav2ARKit isn't installed here).
- Only a 480p draft exists; the 1080p render is not done.
