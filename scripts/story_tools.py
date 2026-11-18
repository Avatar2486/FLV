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
LEAD, GAP, TAIL = 0.4, 0.35, 0.6          # seconds of air before, between and after lines

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


def tc(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def write_plan(film, timeline, folder):
    """production_plan.md: the human-readable plan, generated from film.py + timeline.json."""
    shots = {s["id"]: s for s in timeline["shots"]}
    by_seq = {}
    for shot in film.SHOTS:
        by_seq.setdefault(shot["seq"], []).append(shot)
    L = [f"# {film.TITLE} — production plan", "",
         getattr(film, "PLAN_INTRO", "").strip(), "",
         f"**Runtime:** {tc(timeline['seconds'])} · **Shots:** {len(film.SHOTS)} · **Format:** "
         f"{film.RESOLUTION[0]}x{film.RESOLUTION[1]}, {film.FPS} fps, H.264 + AAC", "",
         "## Structure", "", "| Sequence | Starts | Length |", "|---|---|---|"]
    for seq, items in by_seq.items():
        a = (shots[items[0]["id"]]["start"] - 1) / film.FPS
        n = sum(shots[s["id"]]["seconds"] for s in items)
        L.append(f"| {seq}. {film.SEQUENCES[seq]} | {tc(a)} | {n:.0f} s |")
    L += ["", "## Cast and voices", "", "| Role | Voice | Licence |", "|---|---|---|"]
    L += [f"| {c['name']} | Piper `{c['model']}`{' speaker ' + str(c['speaker']) if c['speaker'] is not None else ''}"
          f" | {c['licence']} |" for c in film.CAST.values()]
    L += ["", getattr(film, "PLAN_APPROACH", "").strip(), "", "## Adaptation notes", "",
          "Narration is Poe's text, verbatim, with passages cut for time. These are FLV additions:", ""]
    for shot in film.SHOTS:
        if shot["adapted"]:
            L.append(f"- **{shot['id']}** — {shot['adapted']}")
        for who, text, adapted in shot["lines"]:
            if adapted:
                L.append(f"- **{shot['id']}** — new line for {film.CAST[who]['name']}: “{text}”")
    L += ["", "## Shot list", "",
          "| # | In | Dur | Framing / lens | Movement | Action | Light | Sound | Words | Out |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for shot in film.SHOTS:
        t = shots[shot["id"]]
        words = " / ".join(f"{w}: {x[:60]}{'…' if len(x) > 60 else ''}" for w, x, _ in shot["lines"]) or "—"
        sound = ", ".join(c for c, _, g in shot["sfx"] if g > 0) or "—"
        mark = " ⓐ" if shot["adapted"] else ""
        L.append(f"| {shot['id']}{mark} | {tc((t['start'] - 1) / film.FPS)} | {t['seconds']:.1f}s | {shot['frame']} | "
                 f"{shot['move'] or '—'} | {shot['action'] or '—'} | {shot['light'] or '—'} | "
                 f"{sound}; score: {shot['music'] or '—'} | {words.replace('|', '/')} | {shot['transition']} |")
    L += ["", "ⓐ = shot contains adapted (non-Poe) material. Speakers: N narration, NS narrator on screen, "
              "OM old man, O1–O3 officers."]
    (folder / "production_plan.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    folder = Path(sys.argv[1]).resolve()
    film = load_story(folder)
    lines = make_voices(film, ROOT / "audio" / "voiceovers" / folder.name)
    timeline = build_timeline(film, lines)
    (folder / "timeline.json").write_text(json.dumps(timeline, indent=1))
    write_plan(film, timeline, folder)
    spoken = sum(l["seconds"] for l in lines)
    print(f"{len(lines)} lines, {spoken / 60:.1f} min of speech; film {timeline['seconds'] / 60:.2f} min "
          f"({timeline['frame_end']} frames) -> {folder.name}/timeline.json")
