"""
Install the MakeHuman asset packs in assets/makehuman_packs/ into MPFB (Blender's MakeHuman add-on),
the same as MPFB's "Load pack from zip file" button. Safe to re-run.

    blender -b --python scripts/install_makehuman_packs.py
"""
from pathlib import Path

import bpy

PACKS = Path(__file__).resolve().parent.parent / "assets" / "makehuman_packs"

for pack in sorted(PACKS.glob("*.zip")):
    bpy.ops.mpfb.load_pack(filepath=str(pack))
    print(f"installed {pack.name}")

from bl_ext.blender_org.mpfb.services import LocationService  # noqa: E402  (exists once MPFB is enabled)

data = Path(LocationService.get_user_data())
for kind in ("skins", "eyes", "eyebrows", "eyelashes", "hair", "clothes", "expressions", "poses"):
    folder = data / kind
    count = sum(1 for p in folder.iterdir() if p.is_dir()) if folder.is_dir() else 0
    print(f"{kind:10} {count:4} assets in MPFB")
