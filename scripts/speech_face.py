"""
Speech -> face: run Wav2ARKit (Apache-2.0; wav2vec2 + LAM Audio2Expression, learned from real faces) on a
voice line and write the 52 ARKit face-unit weights per frame as JSON. scripts/humans.py lip_sync() calls it.

    .venv/bin/python -I scripts/speech_face.py line.wav out.json

Model files: voices/wav2arkit/ (scripts/download_film_kit.sh). Output: {"fps": 30, "names": [...52],
"frames": [[52 weights], ...], "voice": [0-1 per frame]}, weights 0-1.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort

MODEL = Path(__file__).resolve().parent.parent / "voices" / "wav2arkit"


def speech_to_face(wav):
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(wav), "-f", "f32le", "-ac", "1", "-ar", "16000",
                          "-"], capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.float32)[None, :].copy()
    config = json.loads((MODEL / "config.json").read_text())
    session = ort.InferenceSession(str(MODEL / config["onnx"]["model_file"]), providers=["CPUExecutionProvider"])
    weights = session.run(None, {config["input_spec"]["name"]: audio})[0][0]
    fps = config["output_fps"]
    # voice activity per frame (0-1): loudness from -50 dB (silence) to -32 dB (speech), so pauses close the mouth
    hop = 16000 // fps
    rms = [np.sqrt(np.mean(audio[0, i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(len(weights))]
    db = 20 * np.log10(np.array(rms) / (max(rms) + 1e-12))
    voice = np.clip((db + 50) / 18, 0, 1)
    voice = np.convolve(voice, np.ones(3) / 3, mode="same")          # ~100 ms smoothing
    return {"fps": fps, "names": config["blendshape_names"], "frames": np.clip(weights, 0, 1).round(4).tolist(),
            "voice": voice.round(3).tolist()}


if __name__ == "__main__":
    result = speech_to_face(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(result))
    jaw = [f[result["names"].index("jawOpen")] for f in result["frames"]]
    print(f"{len(result['frames'])} frames at {result['fps']} fps; jawOpen max {max(jaw):.2f} mean {np.mean(jaw):.2f}")
