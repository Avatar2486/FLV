"""
The Tell-Tale Heart as one film made of eight parts. Each part is built by its own scene builder (preview_v2/v3/v4
for parts 03, 04, 06; preview_v5 for the rest); this file knows the parts, lays their timelines end to end (the
film clock), renders a part's 480p frames into its own folder, mixes the whole film's sound once (so the score
and the heartbeat run on across the joins), cuts each part's slice of it, muxes each part's MP4 and joins them.
Nothing in a part's folder is deleted by joining: fix one part, re-render it, mix, mux it, join.

    .venv/bin/python -I stories/the_tell_tale_heart/film_parts.py selfcheck | index | mix | mux <key> | join
    blender -b <part blend> --python-exit-code 1 --python stories/the_tell_tale_heart/film_parts.py -- render <key>
"""
import json
import math
import shutil
import subprocess
import time
import sys
import tempfile
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(HERE)]

FPS = 24
FILM = ROOT / "output" / "renders" / "the_tell_tale_heart_film"
V1_TIMELINE = HERE / "timeline.json"            # the 19-Nov film's shot lengths: a part not built yet uses these
RENDERS, SCENES, VOICES = ROOT / "output" / "renders", ROOT / "blender" / "scenes", ROOT / "audio" / "voiceovers"


def _ids(seq, n):
    return [f"{seq}.{i}" for i in range(1, n + 1)]


def _v5(key, title, shots):
    return dict(key=key, title=title, shots=shots, blend=SCENES / f"tell_tale_heart_v5_{key}.blend",
                timeline=FILM / "parts" / key / "timeline.json", voice_dir=None)


PARTS = [
    _v5("00_prologue", "Prologue", _ids(0, 5) + ["T"]),
    _v5("01_the_eye", "The Eye", _ids(1, 9)),
    _v5("02_seven_nights", "Seven Nights", _ids(2, 9)),
    dict(key="03_eighth_night", title="The Eighth Night", shots=_ids(3, 10),
         blend=SCENES / "tell_tale_heart_v2_preview.blend",
         timeline=FILM / "parts" / "03_eighth_night" / "timeline.json",
         voice_dir=VOICES / "the_tell_tale_heart_v2"),
    dict(key="04_the_attack", title="The Attack", shots=[f"3.{i}" for i in range(11, 22)],
         blend=SCENES / "tell_tale_heart_v3_attack.blend",
         timeline=FILM / "parts" / "04_the_attack" / "timeline.json", voice_dir=None),
    _v5("05_concealment", "Concealment", _ids(4, 6)),
    dict(key="06_the_visitors", title="The Visitors", shots=_ids(5, 15),
         blend=SCENES / "tell_tale_heart_v4_visitors.blend",
         timeline=RENDERS / "the_tell_tale_heart_v4_visitors" / "timeline.json", voice_dir=None),
    _v5("07_epilogue", "Epilogue", _ids(6, 3)),
]


def _part(key):
    return next(p for p in PARTS if p["key"] == key)


def part_dir(key):
    return FILM / "parts" / key


def _project_path(file, voice_dir):
    """A timeline's line file as a usable path: absolute, project-relative, or a bare name in voice_dir."""
    p = Path(file)
    if p.is_absolute():
        return p
    if voice_dir is not None and len(p.parts) == 1:
        return Path(voice_dir) / p
    return ROOT / p


def part_timeline(key):
    """The part's builder timeline, normalised: lines with project paths and a gain (chatter 0.25, folded into
    the shot it falls in), marks keyed "<shot>/<cue>" (bare marks, an older builder's, are dropped)."""
    part = _part(key)
    tl = json.loads(Path(part["timeline"]).read_text())
    seconds = tl.get("seconds") or sum(s["seconds"] for s in tl["shots"])
    shots = []
    for s in tl["shots"]:
        lines = [dict(who=l["who"], file=str(_project_path(l["file"], part["voice_dir"])), start=l["start"],
                      seconds=l["seconds"], gain=1.0, chatter=False) for l in s.get("lines", [])]
        shots.append(dict(id=s["id"], start=s["start"], seconds=s["seconds"], lines=lines))
    for c in tl.get("chatter", []):
        home = next((s for s in shots if s["start"] <= c["start"] < s["start"] + s["seconds"]), shots[-1])
        home["lines"].append(dict(who=c["who"], file=str(_project_path(c["file"], part["voice_dir"])),
                                  start=c["start"], seconds=c["seconds"], gain=0.25, chatter=True))
    marks = {k: v for k, v in tl.get("marks", {}).items() if "/" in k}
    return dict(fps=FPS, frames=int(tl.get("frames") or round(seconds * FPS)), seconds=seconds, shots=shots,
                marks=marks)


def film_clock():
    """The parts laid end to end: [{key, start, frames, seconds, nominal, shots: [(id, part start, seconds)]}].
    A part with no timeline yet stands in with its shots' lengths from the 19-Nov film (nominal)."""
    v1 = {s["id"]: s for s in json.loads(V1_TIMELINE.read_text())["shots"]} if V1_TIMELINE.exists() else {}
    clock, frames_before = [], 0
    for part in PARTS:
        if Path(part["timeline"]).exists():
            tl = part_timeline(part["key"])
            frames, nominal = tl["frames"], False
            shots = [(s["id"], s["start"], s["seconds"]) for s in tl["shots"]]
        else:
            frames, nominal, shots, t = 0, True, [], 0.0
            for sid in part["shots"]:
                n = v1[sid]["frames"] if sid in v1 else 0
                shots.append((sid, t, n / FPS))
                frames, t = frames + n, t + n / FPS
        clock.append(dict(key=part["key"], title=part["title"], start=frames_before / FPS, frames=frames,
                          seconds=frames / FPS, nominal=nominal, shots=shots))
        frames_before += frames
    return clock


def write_index():
    """FILM/parts.json: each part's start and length in the film, its MP4, and each shot's film start."""
    clock = film_clock()
    parts = [dict(key=c["key"], title=c["title"], start=round(c["start"], 3), seconds=round(c["seconds"], 3),
                  frames=c["frames"], nominal=c["nominal"], mp4=str(part_dir(c["key"]) / "part_480p.mp4"),
                  shots=[dict(id=sid, part_start=round(t, 3), film_start=round(c["start"] + t, 3), seconds=round(d, 3))
                         for sid, t, d in c["shots"]]) for c in clock]
    FILM.mkdir(parents=True, exist_ok=True)
    out = FILM / "parts.json"
    out.write_text(json.dumps(dict(fps=FPS, seconds=round(sum(c["seconds"] for c in clock), 3), parts=parts),
                              indent=1))
    return out


# ----------------------------------------------------------------------------------------------- picture
def render(key, resume=None, until=None):
    """Inside Blender, with the part's scene open: every frame at 854x480 into the part's frames/480p folder,
    emptied first (Blender's render keeps frames it finds: a re-rendered part must not show old ones). `resume`
    (a frame) keeps the frames before it and renders on from there - after a render that hung part-way; `until`
    stops there (re-rendering one fixed stretch: the other frames are kept)."""
    import bpy
    scene = bpy.context.scene
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = 854, 480, 100
    r.image_settings.file_format, r.image_settings.color_mode = "PNG", "RGB"
    scene.eevee.taa_render_samples = 24
    out = part_dir(key) / "frames" / "480p"
    if resume is None:
        shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    for f in range(resume or scene.frame_start, (until or scene.frame_end) + 1):
        scene.frame_set(f)
        r.filepath = str(out / f"{f:05d}.png")
        bpy.ops.render.render(write_still=True)
    count = len(list(out.glob("*.png")))
    assert count == scene.frame_end - scene.frame_start + 1, f"{count} frames for {scene.frame_start}..{scene.frame_end}"
    print(f"film_parts render {key}: {count} frames -> {out}")
    return count


BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"


def renders(keys, stall=600):
    """Outside Blender: render the parts in turn, one GPU job at a time. A key "06_the_visitors:260" resumes at
    frame 260. A render with no new frame for `stall` s (Eevee can hang in a Metal readback) is killed and
    resumed from its last frame, which is rendered again (it may have been cut off mid-write)."""
    for spec in keys:
        key, _, at = spec.partition(":")                  # "key:from" or "key:from-to"
        part = next(p for p in PARTS if p["key"] == key)
        out, log = part_dir(key) / "frames" / "480p", part_dir(key) / "render.log"
        resume, _, until = at.partition("-")
        resume, until = (int(resume) if resume else None), (int(until) if until else None)
        while True:
            cmd = [BLENDER, "-b", str(part["blend"]), "--python-exit-code", "1", "--python", __file__, "--",
                   "render", key] + ([str(resume)] if resume else []) + ([str(until)] if until else [])
            with open(log, "a") as fh:
                proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT)
            seen, last, hung = -1, time.time(), False
            while proc.poll() is None:
                time.sleep(15)
                n = len(list(out.glob("*.png"))) if out.exists() else 0
                if n != seen:
                    seen, last = n, time.time()
                elif time.time() - last > stall:
                    proc.kill()
                    proc.wait()
                    hung = True
            if not hung:
                if proc.returncode:
                    raise RuntimeError(f"render {key} failed ({proc.returncode}): see {log}")
                print(f"film_parts renders: {key} done")
                break
            resume = max(int(f.stem) for f in out.glob("*.png"))
            print(f"film_parts renders: {key} hung; resuming at {resume}", flush=True)


def _media_seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def mux(key):
    """The part's frames and its slice of the film's sound -> part_480p.mp4 (H.264 + AAC), its length checked."""
    d = part_dir(key)
    frames = sorted((d / "frames" / "480p").glob("*.png"))
    assert frames, f"no frames for {key}: render it first"
    first = int(frames[0].stem)
    out = d / "part_480p.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-start_number", str(first),
                    "-i", str(d / "frames" / "480p" / "%05d.png"), "-i", str(d / "soundtrack.wav"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", str(out)], check=True)
    got = _media_seconds(out)
    assert abs(got - len(frames) / FPS) < 1.5 / FPS, f"{key}: MP4 {got:.3f} s for {len(frames)} frames"
    return out


def join():
    """The parts' pictures end to end (copied, not re-encoded) under the film's one soundtrack ->
    the_tell_tale_heart_480p.mp4; then parts.json. The parts' folders are left as they are."""
    clock = film_clock()
    missing = [c["key"] for c in clock if not (part_dir(c["key"]) / "part_480p.mp4").exists()]
    assert not missing, f"parts with no MP4 yet: {missing}"
    listing = FILM / "parts_concat.txt"
    listing.write_text("".join(f"file '{part_dir(c['key']) / 'part_480p.mp4'}'\n" for c in clock))
    out = FILM / "the_tell_tale_heart_480p.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-i", str(FILM / "soundtrack_film.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    total = sum(c["frames"] for c in clock) / FPS
    got = _media_seconds(out)
    assert abs(got - total) < 1.5 / FPS, f"film {got:.3f} s, parts add up to {total:.3f} s"
    write_index()
    return out


# ----------------------------------------------------------------------------------------------- sound
def _wav_seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def _wav_rate(path):
    with wave.open(str(path)) as w:
        return w.getframerate()


def _read_wav(path):
    """A 16-bit WAV as float32, mono (the channels averaged)."""
    import numpy as np
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()).mean(axis=1)


def _write_wav(path, stereo, rate):
    import numpy as np
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(stereo, -1, 1) * 32767).astype(np.int16).tobytes())


def _muffle(x, rate):
    """Chatter heard through the heartbeat (5.10-5.13): low-passed at 1.2 kHz and slowed 3%."""
    import numpy as np
    spec = np.fft.rfft(x)
    spec[np.fft.rfftfreq(len(x), 1 / rate) > 1200] = 0
    x = np.fft.irfft(spec, len(x)).astype(np.float32)
    return np.interp(np.arange(0, len(x), 1 / 1.03), np.arange(len(x)), x).astype(np.float32)


def mix():
    """The whole film's sound on the film clock, mixed once: the score (film.SCORE, continuous across shots that
    share a cue), each shot's effects (film.SHOTS; a part mark "<shot>/<cue>" sets that cue's time, other marks
    play too), the heartbeat runs (film.HEARTBEATS; an 8th field names the shot from which a muffled run plays
    clear), and every voice at -18 dB RMS x its gain. Loudness-normalised, written to FILM/soundtrack_film.wav,
    then cut into each part's soundtrack.wav."""
    import numpy as np
    import film
    from mix_story import VOICE, Mix, fitted, read_audio
    from sound_library import LOOPS, RATE, heart, loop, music, sfx
    clock = film_clock()
    total = sum(c["seconds"] for c in clock)
    m = Mix(total + 1.0)
    shots = {s["id"]: s for s in film.SHOTS}
    starts = {sid: c["start"] + t for c in clock for sid, t, _ in c["shots"]}
    lengths = {sid: d for c in clock for sid, _, d in c["shots"]}
    real = {c["key"]: part_timeline(c["key"]) for c in clock if not c["nominal"]}
    recordings = {}

    def recording(name):
        if name not in recordings:
            recordings[name] = read_audio(ROOT / "audio" / "sfx" / "freesound" / name)
        return recordings[name]

    def cue_sound(name, at, seconds_left):
        if name.endswith(".mp3"):
            return fitted(recording(name), min(len(recording(name)) / RATE, 8.0))
        if name in film.REAL_SFX:
            file, longest = film.REAL_SFX[name]
            x = recording(file)
            span = max(0.1, seconds_left) if name in LOOPS else min(longest or 1e9, len(x) / RATE)
            return fitted(x if name not in LOOPS else np.roll(x, -int(at * RATE) % len(x)), span)
        if name in LOOPS:
            return loop(name, max(0.1, seconds_left), at)
        return sfx(name)
    # score
    order = [sid for c in clock for sid, _, _ in c["shots"]]
    run_start, fade, pianos = {}, int(0.5 * RATE), {}
    for i, sid in enumerate(order):
        cue = (shots.get(sid) or {}).get("music") or "silence"
        if i == 0 or ((shots.get(order[i - 1]) or {}).get("music") or "silence") != cue:
            run_start[cue] = starts[sid]
        seg = music(cue, starts[sid], lengths[sid]).copy()
        if cue in film.SCORE and len(seg):
            if cue not in pianos:
                pianos[cue] = read_audio(ROOT / "audio" / "music" / "chopin" / film.SCORE[cue])
            piano = pianos[cue]
            a = int((starts[sid] - run_start[cue]) * RATE) % len(piano)
            piece = np.roll(piano, -a)[:len(seg)]
            seg = seg * 0.45 + np.pad(piece, (0, len(seg) - len(piece))) * (0.32 / 0.4)
        nxt = (shots.get(order[i + 1]) or {}).get("music") if i + 1 < len(order) else None
        if i and len(seg) > fade and ((shots.get(order[i - 1]) or {}).get("music") or "silence") != cue:
            seg[:fade] *= np.linspace(0, 1, fade)
        if len(seg) > fade and (nxt or "silence") != cue:
            seg[-fade:] *= np.linspace(1, 0, fade)
        m.put(seg, starts[sid], 0.4)
    # effects: the shot list's cues, timed by the part's marks where it has them; then the other marks
    for c in clock:
        marks = real[c["key"]]["marks"] if c["key"] in real else {}
        used = set()
        for sid, t, d in c["shots"]:
            for name, offset, gain in (shots.get(sid) or {}).get("sfx", []):
                if gain <= 0:
                    continue
                at = offset if offset >= 0 else d + offset
                if f"{sid}/{name}" in marks:                # the mark is when that cue happens: once
                    if f"{sid}/{name}" in used:
                        continue
                    at = marks[f"{sid}/{name}"] - t
                    used.add(f"{sid}/{name}")
                m.put(cue_sound(name, starts[sid] + at, d - at), starts[sid] + at, gain * 0.8)
        for mark, at in marks.items():
            if mark not in used:
                cue = mark.split("/", 1)[1].split("#")[0]   # "5.15/stomp#2": the same cue again
                m.put(cue_sound(cue, c["start"] + at, 4.0), c["start"] + at, 0.7)
    # heartbeats
    for run in film.HEARTBEATS:
        sid, off, b0, b1, eid, eoff, muffled = run[:7]
        clear_from = starts.get(run[7]) if len(run) > 7 else None
        if sid not in starts or eid not in starts:
            continue
        t0, t1 = starts[sid] + off, starts[eid] + eoff
        t, beats = t0, []
        while t < t1:
            beats.append(t)
            t += 60.0 / (b0 + (b1 - b0) * (t - t0) / max(t1 - t0, 1e-6))
        for k, t in enumerate(beats):
            frac = k / max(len(beats) - 1, 1)
            soft = muffled and (clear_from is None or t < clear_from)
            if b1 < b0:
                gain = 0.9 - 0.75 * frac                    # slowing to silence
            else:
                gain = 0.3 + 0.5 * frac if soft else 0.35 + 0.75 * frac ** 1.5    # rising
            m.put(heart(soft), t, gain)
    # voices
    for c in clock:
        if c["key"] not in real:
            continue
        for s in real[c["key"]]["shots"]:
            for line in s["lines"]:
                x = read_audio(line["file"])
                x = x * (10 ** (-18 / 20) / (np.sqrt(np.mean(x ** 2)) + 1e-9))
                if line["chatter"] and any(starts.get(f"5.{n}", 1e9) <= c["start"] + line["start"] <
                                           starts.get(f"5.{n}", 1e9) + lengths.get(f"5.{n}", 0) for n in (10, 11, 12, 13)):
                    x = _muffle(x, RATE)
                gain, pan = VOICE.get(line["who"], (1.0, 0.0))
                m.put(x, c["start"] + line["start"], gain * line["gain"], pan)
    FILM.mkdir(parents=True, exist_ok=True)
    raw = FILM / "soundtrack_film_raw.wav"
    data = m.buf / max(1e-6, float(np.max(np.abs(m.buf)))) * 0.95
    _write_wav(raw, data, RATE)
    final = FILM / "soundtrack_film.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-af", "loudnorm=I=-16:TP=-1.5:LRA=14",
                    "-ar", str(RATE), "-c:a", "pcm_s16le", str(final)], check=True)
    raw.unlink()
    with wave.open(str(final)) as w:
        rate, chans = w.getframerate(), w.getnchannels()
        full = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, chans)
    for c in clock:
        a, b = int(round(c["start"] * rate)), int(round((c["start"] + c["seconds"]) * rate))
        piece = full[a:b]
        if len(piece) < b - a:
            piece = np.vstack([piece, np.zeros((b - a - len(piece), chans), np.int16)])
        d = part_dir(c["key"])
        d.mkdir(parents=True, exist_ok=True)
        with wave.open(str(d / "soundtrack.wav"), "wb") as w:
            w.setnchannels(chans)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(piece.tobytes())
    print(f"film_parts mix: {total:.1f} s ({total / 60:.2f} min) -> {final}; "
          f"{sum(1 for c in clock if c['nominal'])} parts still nominal")
    return final


def selfcheck():
    """Two synthetic parts (48 and 72 frames, one 24 kHz line each at part-time 1.0 s): the film clock, the
    mix's slices, the parts' MP4s and the joined film all line up, to within a frame; a line lands at its part's
    start + 1.0 s in the film; when part A grows to 60 frames, B and its line move with it."""
    global FILM, PARTS
    import numpy as np
    keep = FILM, PARTS
    tmp = Path(tempfile.mkdtemp(prefix="film_parts_check_"))
    try:
        FILM = tmp / "film"

        def make_part(key, frames, colour):
            d = part_dir(key)
            (d / "frames" / "480p").mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={colour}:s=854x480:r=24",
                            "-frames:v", str(frames), "-start_number", "1", str(d / "frames" / "480p" / "%05d.png")],
                           check=True)
            line = tmp / f"{key}_line.wav"
            t = np.arange(int(0.5 * 24000)) / 24000
            with wave.open(str(line), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes((0.4 * np.sin(2 * np.pi * 220 * t) * 32767).astype(np.int16).tobytes())
            tl = tmp / f"{key}_timeline.json"
            tl.write_text(json.dumps({"fps": 24, "frames": frames, "seconds": frames / 24, "shots": [
                {"id": f"{key}1", "start": 0.0, "seconds": frames / 24,
                 "lines": [{"who": "N", "file": str(line), "start": 1.0, "seconds": 0.5}]}]}))
            return dict(key=key, title=key, shots=[f"{key}1"], blend=None, timeline=tl, voice_dir=None)
        PARTS = [make_part("A", 48, "red"), make_part("B", 72, "blue")]
        clock = film_clock()
        assert [c["start"] for c in clock] == [0.0, 2.0], clock
        mix()
        lengths = [_wav_seconds(part_dir(k) / "soundtrack.wav") for k in ("A", "B")]
        assert abs(lengths[0] - 2.0) < 1 / 24 and abs(lengths[1] - 3.0) < 1 / 24, lengths
        film = _read_wav(FILM / "soundtrack_film.wav")
        rate = _wav_rate(FILM / "soundtrack_film.wav")

        def rms(a, b):
            x = film[int(a * rate):int(b * rate)]
            return float(np.sqrt(np.mean(x ** 2)) + 1e-12)
        assert rms(3.0, 3.5) > 10 * rms(2.4, 2.9), (rms(3.0, 3.5), rms(2.4, 2.9))
        durations = [_media_seconds(mux(k)) for k in ("A", "B")]
        assert abs(durations[0] - 2.0) < 1 / 24 and abs(durations[1] - 3.0) < 1 / 24, durations
        joined = _media_seconds(join())
        assert abs(joined - 5.0) < 1 / 24, joined
        index = json.loads((FILM / "parts.json").read_text())
        assert [p["key"] for p in index["parts"]] == ["A", "B"] and index["parts"][1]["start"] == 2.0, index
        # part A is fixed and grows to 60 frames: B moves, and its line with it (no picture re-render)
        spec = json.loads(Path(PARTS[0]["timeline"]).read_text())
        spec.update(frames=60, seconds=2.5)
        spec["shots"][0]["seconds"] = 2.5
        Path(PARTS[0]["timeline"]).write_text(json.dumps(spec))
        assert film_clock()[1]["start"] == 2.5, film_clock()
        mix()
        film = _read_wav(FILM / "soundtrack_film.wav")
        assert rms(3.5, 4.0) > 10 * rms(2.9, 3.4), (rms(3.5, 4.0), rms(2.9, 3.4))
        print(f"film_parts selfcheck OK: starts {[c['start'] for c in clock]} -> B at 2.5 after A grew; slices "
              f"{[round(x, 3) for x in lengths]} s; MP4s {[round(x, 3) for x in durations]} s; joined {joined:.3f} s")
    finally:
        FILM, PARTS = keep
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    {"selfcheck": selfcheck, "index": lambda: print(write_index()), "mix": lambda: print(mix()),
     "mux": lambda: print(mux(args[1])), "join": lambda: print(join()),
     "render": lambda: print(render(args[1], *(int(a) for a in args[2:4]))),
     "renders": lambda: renders(args[1:])}[args[0]]()
