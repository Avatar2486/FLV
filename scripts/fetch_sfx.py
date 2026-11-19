"""
Fetch real recorded sound effects from Freesound, CC0 (public domain) only.

    .venv/bin/python -I scripts/fetch_sfx.py

Needs a free Freesound API key in .env as FREESOUND_API_KEY=... (https://freesound.org/apiv2/apply).
For each cue it saves the best-matching CC0 sounds as high-quality MP3 previews (no OAuth needed) to
audio/sfx/freesound/, and records id, author, licence and link in audio/sfx/freesound/manifest.json.
Re-running skips sounds already saved.
"""
import http.client
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audio" / "sfx" / "freesound"
HEADERS = {"User-Agent": "FLV-SFXFetcher/1.0"}
PER_CUE = 3                      # candidates per cue, to choose from by ear

CUES = {   # cue: (searches tried in order until one finds CC0 sounds, min seconds, max seconds)
    "deathwatch_beetle": (["deathwatch beetle", "beetle tapping", "insect ticking", "tapping wood slow"], 1, 60),
    "wind_chimney": (["wind chimney", "wind howling", "wind interior"], 5, 180),
    "mouse_scurry": (["mouse scurry", "mouse running", "rodent scratching", "mouse"], 0.5, 30),
    "cricket_chirp": (["single cricket chirp", "cricket chirp"], 0.2, 10),
    "door_creak": (["old wooden door creak", "door creak"], 1, 15),
    "door_latch": (["old door latch", "wooden door latch", "door latch"], 0.2, 5),
    "lantern_shutter": (["metal latch click", "metal hinge click", "tin click"], 0.1, 3),
    "floorboard_creak": (["wooden floorboard creak", "floor creak"], 0.5, 10),
    "floorboard_pry": (["prying wood plank", "nail pull wood", "crowbar wood", "wood plank remove"], 1, 20),
    "bed_drag": (["heavy furniture drag", "furniture drag wooden floor", "drag heavy wood"], 1, 20),
    "clock_strike": (["grandfather clock chime", "clock chime strike", "clock bell strike"], 2, 40),
    "knock_street_door": (["knocking heavy wooden door", "knocking door"], 1, 10),
    "stairs_footsteps": (["footsteps wooden stairs", "footsteps stairs"], 2, 30),
    "chair_scrape": (["wooden chair scrape floor", "chair scrape"], 0.5, 6),
    "rain_window": (["rain on window glass", "rain window", "rain on glass", "rain"], 10, 240),
    "room_tone_night": (["quiet room tone night", "room tone quiet"], 10, 240),
    "street_night": (["night street ambience quiet", "night ambience town", "night ambience"], 10, 240),
    "dog_distant": (["distant dog bark night", "dog barking distant"], 2, 30),
    "horse_hooves": (["horse hooves cobblestone", "horse hooves street", "horse hooves"], 3, 60),
    "carriage_wheels": (["horse carriage wheels", "horse carriage", "cart wheels wooden"], 3, 60),
    "church_bell": (["church bell toll", "church bell"], 3, 60),
    "watchman_rattle": (["wooden ratchet rattle", "ratchet rattle", "wooden rattle"], 0.5, 10),
    "iron_gate": (["iron gate creak", "metal gate creak"], 1, 10),
    "shutter_bang": (["wooden shutter bang wind", "shutter bang", "wooden shutter"], 0.5, 10),
}


def api_key():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("FREESOUND_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("Put FREESOUND_API_KEY=... in .env (free key: https://freesound.org/apiv2/apply)")


def get(url):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as r:
                return r.read()
        except (OSError, http.client.HTTPException):     # dropped connections, 502s: wait and retry
            if attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))


def search(key, words, lo, hi):
    query = urllib.parse.urlencode({
        "query": words, "filter": f'license:"Creative Commons 0" duration:[{lo} TO {hi}]',
        "sort": "score", "page_size": PER_CUE, "token": key,
        "fields": "id,name,username,license,duration,url,previews"})
    return json.loads(get(f"https://freesound.org/apiv2/search/text/?{query}"))["results"]


def main():
    key = api_key()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for cue, (searches, lo, hi) in CUES.items():
        results = next((r for words in searches if (r := search(key, words, lo, hi))), [])
        if not results:
            print(f"none  {cue}")
        for s in results:
            assert "publicdomain/zero" in s["license"], s        # CC0 only, whatever the filter returned
            file = OUT / f"{cue}_{s['id']}.mp3"
            if not file.exists():
                file.write_bytes(get(s["previews"]["preview-hq-mp3"]))
            manifest[file.name] = {"cue": cue, "freesound_id": s["id"], "name": s["name"], "author": s["username"],
                                   "license": "CC0-1.0", "source": s["url"], "seconds": round(s["duration"], 2)}
            print(f"have  {file.name}  ({s['name']} by {s['username']})")
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))     # after every cue
    print(f"{len(manifest)} sounds -> {manifest_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
