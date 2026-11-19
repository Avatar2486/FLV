"""
Speak a batch of lines with Chatterbox (MIT; Resemble AI), loading the model once.
Runs in Chatterbox's own environment (scripts/download_film_kit.sh):

    tools/chatterbox/.venv/bin/python -I scripts/chatterbox_lines.py lines.json

lines.json: [{"text": ..., "ref": "audio/voice_refs/narrator.wav", "exaggeration": 0.5, "cfg": 0.5,
              "out": "audio/voiceovers/<story>/<id>.wav"}, ...]. Paths are relative to the project.
The reference clips in audio/voice_refs/ are Kokoro voices (synthetic), so no real person's voice is copied.
Lines whose output already exists are skipped.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main(spec):
    lines = [l for l in json.loads(Path(spec).read_text()) if not (ROOT / l["out"]).exists()]
    if not lines:
        print("all lines already spoken")
        return
    import torch
    import torchaudio
    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device="mps" if torch.backends.mps.is_available() else "cpu")
    for line in lines:
        wav = model.generate(line["text"], audio_prompt_path=str(ROOT / line["ref"]),
                             exaggeration=line.get("exaggeration", 0.5), cfg_weight=line.get("cfg", 0.5))
        out = ROOT / line["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        torchaudio.save(str(out), wav, model.sr, encoding="PCM_S", bits_per_sample=16)   # plain 16-bit WAV
        print(f"spoke {out.name}: {wav.shape[-1] / model.sr:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1])
