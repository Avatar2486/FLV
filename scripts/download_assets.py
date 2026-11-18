"""
Download free CC0 assets from Poly Haven (https://polyhaven.com) into assets/.

    python3 scripts/download_assets.py           # download the FLV selection
    python3 scripts/download_assets.py --list    # only show what would be downloaded

Poly Haven assets are CC0 (public domain): free for any use, including commercial,
with no credit required. Their API is free for commercial use too; it only asks every
client to send its own User-Agent.

Re-running only fetches files that are missing. assets/polyhaven_manifest.json records
where every asset came from. Plain Python 3, no extra packages.
"""
import argparse
import hashlib
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

API = "https://api.polyhaven.com"
HEADERS = {"User-Agent": "FLV-AssetFetcher/1.0"}
ASSETS = Path(__file__).resolve().parent.parent / "assets"
RESOLUTION = "1k"            # small and fast; Poly Haven also has 2k/4k/8k for close-ups
MAX_ASSET_MB = 6             # skip unusually heavy models so the Git repo stays small

# Which assets to fetch: any asset in one of these categories is included.
SELECTION = {
    "models": {"furniture", "seating", "table", "shelves", "lighting", "decorative",
               "electronics", "appliances"},
    "hdris": {"night"},
    "textures": {"indoor", "fabric"},
}
FURNITURE = {"furniture", "seating", "table", "shelves"}      # other models go to assets/props
TEXTURE_MAPS = ("Diffuse", "nor_gl", "Rough")                  # colour, normal (OpenGL), roughness


def get_json(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def plan(kind, asset_id, info):
    """Return (folder, [(relative path, url, size, md5), ...]) for one asset."""
    files = get_json(f"{API}/files/{asset_id}")
    if kind == "models":
        group = "furniture" if FURNITURE & set(info["categories"]) else "props"
        folder = ASSETS / group / "polyhaven" / asset_id
        main = files.get("gltf", {}).get(RESOLUTION, {}).get("gltf")
        if not main:                                           # a few models have no glTF
            return folder, []
        entries = [(Path(main["url"]).name, main["url"], main["size"], main["md5"])]
        entries += [(rel, f["url"], f["size"], f["md5"]) for rel, f in main.get("include", {}).items()]
    elif kind == "hdris":
        folder = ASSETS / "environments" / "hdri"
        f = files["hdri"][RESOLUTION]["hdr"]
        entries = [(Path(f["url"]).name, f["url"], f["size"], f["md5"])]
    else:
        folder = ASSETS / "textures" / "polyhaven" / asset_id
        entries = []
        for name in TEXTURE_MAPS:
            f = files.get(name, {}).get(RESOLUTION, {}).get("jpg")
            if f:
                entries.append((Path(f["url"]).name, f["url"], f["size"], f["md5"]))
    return folder, entries


def download(folder, entry):
    rel, url, size, md5 = entry
    target = folder / rel
    if target.is_file() and target.stat().st_size == size:
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = response.read()
            if hashlib.md5(data).hexdigest() != md5:
                raise IOError(f"checksum mismatch for {url}")
            target.write_bytes(data)
            return size
        except (OSError, IOError) as error:
            if attempt == 2:
                raise
            print(f"  retry {url}: {error}")
            time.sleep(2 + attempt * 3)


def main():
    parser = argparse.ArgumentParser(description="Download CC0 assets from Poly Haven")
    parser.add_argument("--list", action="store_true", help="only list the selection and its size")
    args = parser.parse_args()

    manifest, jobs, total = {}, [], 0
    for kind, categories in SELECTION.items():
        catalogue = get_json(f"{API}/assets?type={kind}")
        chosen = sorted(i for i, info in catalogue.items() if categories & set(info["categories"]))
        with ThreadPoolExecutor(4) as pool:                 # look up file lists, a few at a time
            plans = list(pool.map(lambda i: plan(kind, i, catalogue[i]), chosen))
        kind_bytes = 0
        for asset_id, (folder, entries) in zip(chosen, plans):
            size = sum(e[2] for e in entries)
            if not entries or size > MAX_ASSET_MB * 1e6:
                continue
            info = catalogue[asset_id]
            manifest[asset_id] = {
                "name": info["name"], "type": kind, "categories": info["categories"],
                "authors": sorted(info.get("authors", {})), "license": "CC0-1.0",
                "source": f"https://polyhaven.com/a/{asset_id}",
                "files": [(folder / e[0]).relative_to(ASSETS).as_posix() for e in entries],
            }
            jobs += [(folder, e) for e in entries]
            kind_bytes += size
        count = sum(1 for m in manifest.values() if m["type"] == kind)
        print(f"{kind:9} {count:4} assets  {kind_bytes / 1e6:7.1f} MB")
        total += kind_bytes
    print(f"{'total':9} {len(manifest):4} assets  {total / 1e6:7.1f} MB at {RESOLUTION}")
    if args.list:
        return

    with ThreadPoolExecutor(4) as pool:
        fetched = sum(pool.map(lambda job: download(*job), jobs))
    (ASSETS / "polyhaven_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(f"Downloaded {fetched / 1e6:.1f} MB new; manifest: assets/polyhaven_manifest.json")


if __name__ == "__main__":
    main()
