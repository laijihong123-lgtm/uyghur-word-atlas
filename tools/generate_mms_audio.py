#!/usr/bin/env python3
"""Create genuine Uyghur TTS for reviewed textbook learning cards.

Non-commercial educational pilot. The model is the Uyghur Arabic-script MMS
voice by Meta (CC BY-NC 4.0); it is never an English TTS fallback.
Run after tools/port_uyghur.py and before building the site.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import numpy as np
import torch
from transformers import AutoTokenizer, VitsModel

ROOT = Path("upstream/public/atlas")
MODEL = "facebook/mms-tts-uig-script_arabic"
LIMIT = int(os.getenv("UYGHUR_TTS_LIMIT", "60"))



def persist_audio_flags(index: dict, index_path: Path, enabled: set[str]) -> None:
    for row in index["words"]:
        if row[0] in enabled:
            row[6] |= 2
    index["voiced"] = len(enabled)
    index_path.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), "utf-8")
    for path in sorted((ROOT / "entries").glob("*.json"), key=lambda f: int(f.stem)):
        entries = json.loads(path.read_text("utf-8"))
        for entry in entries:
            if entry["id"] in enabled:
                entry["m"] |= 2
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), "utf-8")
    
    
def main() -> None:
    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = VitsModel.from_pretrained(MODEL)
    model.eval()

    index_path = ROOT / "index.json"
    index = json.loads(index_path.read_text("utf-8"))
    audio_dir = ROOT / "audio" / "uk"
    audio_dir.mkdir(parents=True, exist_ok=True)
    enabled: set[str] = set()
    errors: list[tuple[str, str]] = []

    for item in index["words"][:LIMIT]:
        word_id, word = item[:2]
        # A terminal hyphen denotes a verb stem, not a sound.
        spoken = re.sub(r"\s*-\s*", " ", word).strip()
        if not spoken or not re.search(r"[\u0600-\u06ff]", spoken):
            continue
        try:
            inputs = tokenizer(spoken, return_tensors="pt")
            with torch.inference_mode():
                output = model(**inputs).waveform.squeeze().detach().cpu().numpy()
            if not np.isfinite(output).all() or output.size < 2000:
                raise ValueError("Empty or nonfinite waveform")
            pcm = (np.clip(output, -1, 1) * 32767).astype("<i2").tobytes()
            dest = audio_dir / f"{word_id}.mp3"
            subprocess.run(
                ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                 "-y", "-f", "s16le", "-ar", str(model.config.sampling_rate),
                 "-ac", "1", "-i", "pipe:0", "-codec:a", "libmp3lame",
                 "-b:a", "48k", str(dest)],
                input=pcm, check=True, timeout=40
            )
            if dest.stat().st_size < 1000:
                raise ValueError("MP3 is too small")
            enabled.add(word_id)
            if len(enabled) % 60 == 0:
                persist_audio_flags(index, index_path, enabled)
            print(f"TTS_OK {len(enabled)} {word_id} {word}", flush=True)
        except Exception as exc:
            errors.append((word_id, str(exc)))
            print(f"TTS_SKIPPED {word_id} {exc}", flush=True)

    persist_audio_flags(index, index_path, enabled)

    report = {
        "model": MODEL,
        "license": "CC BY-NC 4.0",
        "machine_synthesized": True,
        "requested": min(LIMIT, index["count"]),
        "created": len(enabled),
        "skipped": errors,
    }
    (ROOT / "uyghur-tts-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), "utf-8"
    )
    if not enabled:
        raise RuntimeError("MMS Uyghur produced no validated MP3 audio")
    print(f"Uyghur TTS pilot: {len(enabled)}/{min(LIMIT,index['count'])} recordings", flush=True)


if __name__ == "__main__":
    main()
