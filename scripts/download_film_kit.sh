#!/bin/bash
# Downloads the free tools and data for realistic characters, motion, voices, sound and music (~5 GB).
# Every source, licence and credit line is listed in assets/THIRD_PARTY.md.
# Safe to re-run: files that are already there are skipped.
#     bash scripts/download_film_kit.sh
set -euo pipefail
cd "$(dirname "$0")/.."
B=/Applications/Blender.app/Contents/MacOS/Blender
MH=https://files.makehumancommunity.org/asset_packs
get() {   # get <url> <file>
    [ -s "$2" ] && { echo "have  $2"; return; }
    mkdir -p "$(dirname "$2")"
    echo "get   $2  <-  $1"
    curl -fL -C - --retry 5 --retry-all-errors -o "$2.part" "$1" && mv "$2.part" "$2"   # -C -: resume a cut-off download
}

# 1. Blender add-ons from extensions.blender.org: MPFB 2 (GPL-3), Sapling Tree Gen (GPL-2+)
EXT="$HOME/Library/Application Support/Blender/5.3/extensions/blender_org"
for x in mpfb sapling_tree_gen; do
    if [ -d "$EXT/$x" ]; then echo "have  Blender add-on $x"; else "$B" --online-mode -c extension install "$x" --sync --enable; fi
done

# 2. MakeHuman asset packs: CC0 unless the name says cc-by/ccby (credited in THIRD_PARTY.md)
for f in makehuman_system_assets/makehuman_system_assets_cc0 system_eye_materials01/system_eye_materials01_cc0 \
         system_hair_materials01/system_hair_materials01_cc0 system_clothes_materials01/system_clothes_materials01_cc0 \
         skins02/skins02_cc0 eyebrows01/eyebrows01_cc0 eyelashes01/eyelashes01_cc0 suits01/suits01_cc0 \
         pants01/pants01_cc0 clothes_materials01/clothes_materials01_cc0 gloves01/gloves01_cc0 \
         hats03/hats03_cc-by shoes03/shoes03_ccby suits03/suits03_cc-by shirts02/shirts02_ccby; do
    get "$MH/$f.zip" "assets/makehuman_packs/${f#*/}.zip"
done
for f in faceunits01 visemes01; do      # ARKit face units and visemes (expressions, lip sync)
    get "https://files2.makehumancommunity.org/functional/$f.zip" "assets/makehuman_packs/$f.zip"
done
"$B" -b --python scripts/install_makehuman_packs.py 2>&1 | grep -E "installed|assets in MPFB"   # load them into MPFB

# 3. Rhubarb Lip Sync 1.14 (MIT): mouth shapes from speech
get https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.14.0/Rhubarb-Lip-Sync-1.14.0-macOS.zip \
    tools/rhubarb/Rhubarb-Lip-Sync-1.14.0-macOS.zip
unzip -q -n tools/rhubarb/Rhubarb-Lip-Sync-1.14.0-macOS.zip -d tools/rhubarb

# 4. Voices. Kokoro v1.0 (Apache 2.0) in the project venv; Chatterbox (MIT) in its own venv (it pins torch 2.6)
get https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx voices/kokoro/kokoro-v1.0.onnx
get https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin voices/kokoro/voices-v1.0.bin
.venv/bin/pip install --quiet kokoro-onnx
[ -x tools/chatterbox/.venv/bin/python ] || /opt/homebrew/bin/python3.12 -m venv tools/chatterbox/.venv
tools/chatterbox/.venv/bin/pip install --quiet chatterbox-tts "setuptools<81"   # its watermarker needs pkg_resources

# 5. Motion capture. CMU (BVH by B. Hahne, "free for use in research and commercial projects")
for c in 08_04 16_33 82_08 77_05 77_14 77_29 77_34 91_32 79_73 17_01 13_05 86_15 111_09 111_06 18_08 18_10 13_14 81_08 22_03; do
    get "https://raw.githubusercontent.com/sfd158/cmu-mocap/master/data/$(printf %03d $((10#${c%_*})))/$c.bvh" "assets/mocap/cmu/$c.bvh"
done
# 100STYLE (CC BY 4.0, Ian Mason): only the 28 clips we use, read out of the 1.5 GB zip by range requests
python3 -I scripts/fetch_100style.py

# 6. Period music: Chopin, recorded by Musopen and released CC0 (archive.org/details/musopen-chopin)
CH=https://archive.org/download/musopen-chopin
get "$CH/Nocturne%20Op.%2048%20no.%201%20in%20C%20minor.mp3" audio/music/chopin/nocturne_op48_no1.mp3
get "$CH/Nocturne%20Op.%2027%20no.%201%20in%20C%20sharp%20minor.mp3" audio/music/chopin/nocturne_op27_no1.mp3
get "$CH/Prelude%20Op.%2028%20no.%2015.mp3" audio/music/chopin/prelude_op28_no15.mp3
get "$CH/Prelude%20Op.%2028%20no.%2024.mp3" audio/music/chopin/prelude_op28_no24.mp3
get "$CH/Prelude%20Op.%2028%20no.%206.mp3" audio/music/chopin/prelude_op28_no6.mp3

# 7. Poly Haven (CC0): the existing selection plus the named props and 1843 street assets
python3 scripts/download_assets.py

# 8. Freesound (CC0 only), when you have put FREESOUND_API_KEY=... in .env
if grep -q '^FREESOUND_API_KEY=.' .env 2>/dev/null; then .venv/bin/python -I scripts/fetch_sfx.py; else
    echo "skip  Freesound sounds: no FREESOUND_API_KEY in .env (see README, Downloads)"; fi

echo "Done."
