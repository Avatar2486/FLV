"""
Add FLV/assets to Blender as the "FLV" asset library. Run once per machine:

    blender --background --python scripts/register_asset_library.py

(No --factory-startup here: this edits and saves your own Blender preferences.)
Afterwards the Asset Browser in any project lists every FLV and Poly Haven asset.
"""
from pathlib import Path

import bpy

assets = str(Path(__file__).resolve().parent.parent / "assets")
libraries = bpy.context.preferences.filepaths.asset_libraries
library = next((lib for lib in libraries if lib.name == "FLV"), None) or libraries.new(name="FLV")
library.path = assets
library.import_method = "APPEND"           # dropped assets become your own editable copies
bpy.ops.wm.save_userpref()
print(f'Asset library "FLV" -> {assets}')
