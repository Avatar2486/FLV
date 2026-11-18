"""
FLV story tools: voices and timing for a story folder that contains film.py.

    .venv/bin/python -I scripts/story_tools.py stories/the_tell_tale_heart

1. Generates every spoken line with Piper (voices/ folder), cleans it up with ffmpeg
   (EQ, room tone, ageing for the old man) and stores 48 kHz WAVs in
   audio/voiceovers/<story>/. Lines are cached by content, so re-running only
   generates what changed.
2. Writes <story>/timeline.json: each shot's start frame and length, sized so its
   lines fit with natural pauses, plus where each line starts.
Runs with the project's .venv Python (Piper lives there), not inside Blender.
"""
import hashlib
import importlib.util
import json
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAD, GAP, TAIL = 0.5, 0.4, 0.8          # seconds of air before, between and after lines

FX = {   # ffmpeg filters per delivery style
    "narration": "highpass=f=70,lowpass=f=9000,acompressor=threshold=-22dB:ratio=3:attack=5:release=120,"
                 "aecho=0.8:0.3:23:0.12",
    "room": "highpass=f=90,lowpass=f=7500,aecho=0.8:0.55:35|61:0.22|0.12",
    "old": "highpass=f=80,asetrate=22050*0.93,aresample=22050,atempo=1.0753,vibrato=f=6.5:d=0.22,"
           "lowpass=f=6000,aecho=0.8:0.55:35|61:0.22|0.12",
}


def load_story(folder):
    spec = importlib.util.spec_from_file_location("film", Path(folder) / "film.py")
    film = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(film)
    return film


def speakable(text):
    """Punctuation Piper reads cleanly: dashes and brackets become pauses."""
    for a, b in (("—", ", "), ("(", ", "), (")", ", "), (";", ","), ("!—", "! "), ("?—", "? ")):
        text = text.replace(a, b)
    return " ".join(text.replace(" ,", ",").replace(",,", ",").split())


def wav_seconds(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def make_voices(film, out_dir):
    from piper import PiperVoice, SynthesisConfig     # only needed here
    voices, lines = {}, []
    out_dir.mkdir(parents=True, exist_ok=True)
    for shot in film.SHOTS:
        for i, (who, text, adapted) in enumerate(shot["lines"]):
            cast = film.CAST[who]
            key = hashlib.sha1(f"{who}|{text}|{cast}".encode()).hexdigest()[:10]
            final = out_dir / f"{shot['id']}_{i}_{who}_{key}.wav"
            if not final.exists():
                model = cast["model"]
                if model not in voices:
                    voices[model] = PiperVoice.load(str(ROOT / "voices" / f"{model}.onnx"))
                raw = final.with_suffix(".raw.wav")
                with wave.open(str(raw), "wb") as w:
                    voices[model].synthesize_wav(speakable(text), w, syn_config=SynthesisConfig(
                        speaker_id=cast["speaker"], length_scale=cast["length_scale"],
                        noise_scale=0.6, noise_w_scale=0.75))
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-af",
                                FX[cast["fx"]] + ",aresample=48000", "-ac", "1", str(final)], check=True)
                raw.unlink()
            lines.append({"shot": shot["id"], "index": i, "who": who, "adapted": adapted, "text": text,
                          "file": final.relative_to(ROOT).as_posix(), "seconds": round(wav_seconds(final), 3)})
    return lines


def build_timeline(film, lines):
    fps, frame, shots = film.FPS, 1, []
    by_shot = {}
    for line in lines:
        by_shot.setdefault(line["shot"], []).append(line)
    for shot in film.SHOTS:
        spoken = by_shot.get(shot["id"], [])
        t, starts = LEAD, []
        for line in spoken:
            starts.append(round(t, 3))
            t += line["seconds"] + GAP
        needed = (t - GAP + TAIL) if spoken else 0
        seconds = max(shot["min"], needed)
        frames = round(seconds * fps)
        shots.append({"id": shot["id"], "start": frame, "frames": frames, "seconds": frames / fps,
                      "lines": [dict(l, offset=s) for l, s in zip(spoken, starts)]})
        frame += frames
    return {"fps": fps, "frame_end": frame - 1, "seconds": (frame - 1) / fps, "shots": shots}


if __name__ == "__main__":
    folder = Path(sys.argv[1]).resolve()
    film = load_story(folder)
    lines = make_voices(film, ROOT / "audio" / "voiceovers" / folder.name)
    timeline = build_timeline(film, lines)
    (folder / "timeline.json").write_text(json.dumps(timeline, indent=1))
    spoken = sum(l["seconds"] for l in lines)
    print(f"{len(lines)} lines, {spoken / 60:.1f} min of speech; film {timeline['seconds'] / 60:.2f} min "
          f"({timeline['frame_end']} frames) -> {folder.name}/timeline.json")
