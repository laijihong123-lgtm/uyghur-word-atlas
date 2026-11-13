#!/usr/bin/env python3
"""Reattach validated, previously generated Uyghur MP3 audio after rebuilding the word index.

Reuses the last successful public GitHub Pages site artifact only if ALL 1813
original word IDs have non-empty MP3s. The original vocabulary and TTS
generator are unchanged; stable IDs are the provenance link.
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path

ROOT=Path("upstream/public/atlas")
SOURCES=[
    Path("previous-website/atlas/audio/uk"),
    Path("previous-website/upstream/dist/atlas/audio/uk"),
]
def main()->None:
    index_path=ROOT/"index.json"
    index=json.loads(index_path.read_text("utf-8"))
    assert index["count"]==1813 and len(index["words"])==1813
    source=next((p for p in SOURCES if p.is_dir()),None)
    if source is None:
        raise RuntimeError("No previous Uyghur audio artifact found")
    output=ROOT/"audio"/"uk"
    output.mkdir(parents=True,exist_ok=True)
    copied=0
    for row in index["words"]:
        word_id=row[0]
        previous=source/(word_id+".mp3")
        if not previous.is_file() or previous.stat().st_size<=1000:
            raise RuntimeError(f"Missing previous valid-size MP3 for {word_id}")
        shutil.copyfile(previous,output/(word_id+".mp3"))
        row[6] |= 2
        copied+=1
    index["voiced"]=copied
    index_path.write_text(json.dumps(index,ensure_ascii=False,separators=(",",":")),"utf-8")
    for path in sorted((ROOT/"entries").glob("*.json"),key=lambda p:int(p.stem)):
        entries=json.loads(path.read_text("utf-8"))
        for entry in entries:
            if not (output/(entry["id"]+".mp3")).is_file():
                raise RuntimeError("Unmapped entry MP3: "+entry["id"])
            entry["m"] |= 2
        path.write_text(json.dumps(entries,ensure_ascii=False,indent=2),"utf-8")
    report={"model":"facebook/mms-tts-uig-script_arabic","license":"CC BY-NC 4.0",
            "machine_synthesized":True,"reused_from_successful_pages_run":43483055237,
            "requested":1813,"created":copied,"skipped":[]}
    (ROOT/"uyghur-tts-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf-8")
    print("REUSED_PREVIOUS_VERIFIED_UYGHUR_MP3",copied,flush=True)

if __name__=="__main__":
    main()
