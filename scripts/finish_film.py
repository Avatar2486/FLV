"""
Join a film's rendered shots and add its soundtrack.

    .venv/bin/python -I scripts/finish_film.py stories/the_tell_tale_heart output/renders/tell_tale_heart/shots

Writes output/renders/<story>/<story>_master.mp4 (the rendered H.264 untouched + AAC 192k) and
<story>.mp4, a ~80 MB re-encode (900 kb/s) that fits GitHub's 100 MB file limit. Checks every shot is
present first.
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
master = out_dir / f"{story.name}_master.mp4"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(picture), "-i", str(out_dir / "soundtrack.wav"),
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                "-movflags", "+faststart", str(master)], check=True)
picture.unlink()
listing.unlink()
web = out_dir / f"{story.name}.mp4"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(master), "-c:v", "libx264", "-preset", "slow",
                "-b:v", "900k", "-maxrate", "1800k", "-bufsize", "3600k", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-b:a", "128k", "-movflags", "+faststart", str(web)], check=True)
for f in (master, web):
    print(f"Film: {f} ({f.stat().st_size / 1e6:.1f} MB)")
