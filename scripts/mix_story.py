"""
Mix a story's soundtrack: voices + sound effects + heartbeat + score, timed from timeline.json.

    .venv/bin/python -I scripts/mix_story.py stories/the_tell_tale_heart

Writes output/renders/<story>/soundtrack.wav (48 kHz stereo, loudness-normalised to -16 LUFS).
"""
import importlib.util
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sound_library import LOOPS, RATE, heart, loop, music, sfx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
VOICE_DB = -18.0       # RMS level every spoken line is brought to
MUSIC_GAIN = 0.4       # score sits well under the voice
VOICE = {"N": (1.0, 0.0), "NS": (1.0, 0.0), "OM": (0.95, -0.12), "O1": (0.9, -0.25), "O2": (0.9, 0.25),
         "O3": (0.9, 0.1)}                      # gain, pan for each speaker


def load_story(folder):
    spec = importlib.util.spec_from_file_location("film", folder / "film.py")
    film = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(film)
    return film


def read_wav(path):
    with wave.open(str(path)) as w:
        assert w.getframerate() == RATE, path
        data = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return data if w.getnchannels() == 1 else data[::2]


class Mix:
    def __init__(self, seconds):
        self.buf = np.zeros((int(seconds * RATE), 2), np.float32)

    def put(self, x, start, gain=1.0, pan=0.0):
        s = int(round(start * RATE))
        a, b = max(0, s), min(len(self.buf), s + len(x))
        if b <= a:
            return
        angle = (pan + 1) * np.pi / 4
        seg = x[a - s:b - s] * gain
        self.buf[a:b, 0] += seg * np.cos(angle)
        self.buf[a:b, 1] += seg * np.sin(angle)


def heartbeat_times(film, start_of):
    runs = []
    for s_id, s_off, bpm0, bpm1, e_id, e_off, muffled in film.HEARTBEATS:
        t0, t1 = start_of[s_id] + s_off, start_of[e_id] + e_off
        t, beats = t0, []
        while t < t1:
            beats.append(t)
            t += 60.0 / (bpm0 + (bpm1 - bpm0) * (t - t0) / max(t1 - t0, 1e-6))
        runs.append((beats, muffled, bpm1 > bpm0))
    return runs


def main(folder):
    film = load_story(folder)
    tl = json.loads((folder / "timeline.json").read_text())
    fps = tl["fps"]
    shots = {s["id"]: s for s in tl["shots"]}
    start_of = {sid: (s["start"] - 1) / fps for sid, s in shots.items()}
    mix = Mix(tl["seconds"] + 2)
    rng = np.random.default_rng(3)

    # score: continuous per cue, with short fades only where the cue changes
    cues = [(s["id"], s["music"] or "silence") for s in film.SHOTS]
    fade = int(0.5 * RATE)
    for i, (sid, cue) in enumerate(cues):
        seg = music(cue, start_of[sid], shots[sid]["seconds"]).copy()
        if i and cues[i - 1][1] != cue and len(seg) > fade:
            seg[:fade] *= np.linspace(0, 1, fade)
        if i + 1 < len(cues) and cues[i + 1][1] != cue and len(seg) > fade:
            seg[-fade:] *= np.linspace(1, 0, fade)
        mix.put(seg, start_of[sid], MUSIC_GAIN)

    # sound effects
    cache = {}
    for shot in film.SHOTS:
        sid, dur = shot["id"], shots[shot["id"]]["seconds"]
        for cue, offset, gain in shot["sfx"]:
            if gain <= 0:
                continue                                 # timing markers (heartbeat starts)
            at = offset if offset >= 0 else dur + offset
            if cue in LOOPS:
                x = loop(cue, max(0.1, dur - at), start_of[sid] + at)
            else:
                x = cache.setdefault(cue, sfx(cue))
            mix.put(x, start_of[sid] + at, gain * 0.8, pan=float(rng.uniform(-0.3, 0.3)))

    # heartbeats (the same beat times the picture uses for the dust on the floor)
    for beats, muffled, rising in heartbeat_times(film, start_of):
        beat = heart(muffled)
        for k, t in enumerate(beats):
            frac = k / max(len(beats) - 1, 1)
            gain = (0.35 + 0.75 * frac ** 1.5) if rising else (0.9 - 0.75 * frac)
            mix.put(beat, t, gain)

    # voices
    for shot in tl["shots"]:
        for line in shot["lines"]:
            gain, pan = VOICE[line["who"]]
            x = read_wav(ROOT / line["file"])
            x *= 10 ** (VOICE_DB / 20) / (np.sqrt(np.mean(x ** 2)) + 1e-9)     # every line at the same level
            mix.put(x, start_of[shot["id"]] + line["offset"], gain, pan)

    out_dir = ROOT / "output" / "renders" / folder.name
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / "soundtrack_raw.wav"
    data = mix.buf / max(1e-6, np.max(np.abs(mix.buf))) * 0.95
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((data * 32767).astype(np.int16).tobytes())
    final = out_dir / "soundtrack.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=14", "-ar", str(RATE), str(final)], check=True)
    raw.unlink()
    print(f"Soundtrack: {final} ({tl['seconds'] / 60:.2f} min)")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
