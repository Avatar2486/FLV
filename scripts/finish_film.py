"""
Join a film's rendered shots and add its soundtrack.

    .venv/bin/python -I scripts/finish_film.py stories/the_tell_tale_heart output/renders/tell_tale_heart/shots

Writes output/renders/<story>/<story>.mp4 (H.264 + AAC 192k). Checks every shot is present first.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
story, shots_dir = (ROOT / a for a in sys.argv[1:3])
shots = json.loads((story / "timeline.json").read_text())["shots"]
files = [shots_dir / f"{i:03d}_{s['id']}.mp4" for i, s in enumerate(shots)]
missing = [f.name for f in files if not f.exists() or f.stat().st_size == 0]
if missing:
    sys.exit(f"Missing shots: {missing}")
out_dir = ROOT / "output" / "renders" / story.name
listing = out_dir / "shots.txt"
listing.write_text("".join(f"file '{f}'\n" for f in files))
picture = out_dir / "picture.mp4"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                "-c", "copy", str(picture)], check=True)
final = out_dir / f"{story.name}.mp4"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(picture), "-i", str(out_dir / "soundtrack.wav"),
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                "-movflags", "+faststart", str(final)], check=True)
picture.unlink()
listing.unlink()
print(f"Film: {final} ({final.stat().st_size / 1e6:.1f} MB)")
