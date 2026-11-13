#!/usr/bin/env python3
"""Prepare, synthesize and verify sentence-level Uyghur audio for Word Atlas.

The public app stays static. This script attaches content-addressed MP3 paths to
each card example, each reading-room example and each reading sentence. Identical
Uyghur sentences share one file. Existing FSRS data and 1813 word recordings
remain untouched.

Commands: prepare (attach paths and patch UI), needs (exit 0 when cached),
generate (run MMS on missing sentences), verify (fail on missing/invalid audio).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("upstream/public/atlas")
CACHE = Path(".cache/uyghur-sentence-audio")
DEST = ROOT/"audio"/"examples"
MANIFEST = ROOT/"sentence-audio-manifest.json"
MODEL = "facebook/mms-tts-uig-script_arabic"
LICENSE = "CC BY-NC 4.0"
MIN_MP3 = 900


def load(path: Path):
    return json.loads(path.read_text("utf-8"))


def save(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), "utf-8")


def audio_name(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:32] + ".mp3"


def collect_and_attach():
    entries_paths = sorted((ROOT/"entries").glob("*.json"), key=lambda p: int(p.stem))
    if not entries_paths:
        raise RuntimeError("Missing dictionary entry chunks")
    by_id = {}
    texts = {}
    cards = 0
    links = 0
    for p in entries_paths:
        chunk = load(p)
        for e in chunk:
            if not e["ex"]:
                raise RuntimeError("Example missing for " + e["id"])
            cards += 1
            by_id[e["id"]] = e
            for ex in e["ex"]:
                sentence = ex["en"].strip()
                if not sentence or len(sentence) > 500 or not re.search(r"[\u0600-\u06ff]", sentence):
                    raise RuntimeError("Invalid Uyghur sentence: " + repr(sentence))
                name = audio_name(sentence)
                ex["audio"] = "audio/examples/" + name
                texts[name] = sentence
                links += 1
        save(p, chunk)

    if len(by_id) != 1813 or cards != 1813 or links < 1813:
        raise RuntimeError(f"Incorrect coverage {cards} cards, {links} sentences")

    examples_path = ROOT/"examples.json"
    examples = load(examples_path)
    if len(examples) != links:
        raise RuntimeError("Mismatch between card examples and example library")
    for item in examples:
        e = by_id[item["wordId"]]
        match = next((x for x in e["ex"] if x["en"] == item["ug"]), None)
        if not match:
            raise RuntimeError("Orphan example library item: "+item["id"])
        item["audio"] = match["audio"]
    save(examples_path, examples)

    reading_path = ROOT/"reading.json"
    stories = load(reading_path)
    read_count = 0
    for story in stories:
        for line in story["lines"]:
            sentence = line["ug"].strip()
            if not sentence:
                raise RuntimeError("Empty reader sentence")
            name = audio_name(sentence)
            line["audio"] = "audio/examples/" + name
            texts[name] = sentence
            read_count += 1
    save(reading_path, stories)

    idx_path = ROOT/"index.json"
    idx = load(idx_path)
    if idx.get("count") != 1813 or idx.get("id") != "uyghur-textbook-reviewed-20261113":
        raise RuntimeError("Unexpected study deck; do not change progress namespace")
    idx["sentenceVoiced"] = links
    idx["uniqueSentenceAudio"] = len(texts)
    save(idx_path, idx)

    manifest = {
        "model": MODEL,
        "license": LICENSE,
        "machine_synthesized": True,
        "human_reviewed": False,
        "wordCards": cards,
        "exampleLinks": links,
        "readerLines": read_count,
        "uniqueAudios": len(texts),
        "files": texts,
    }
    save(MANIFEST, manifest)
    return manifest


def patch(path: str, old: str, new: str):
    f = Path("upstream")/path
    src = f.read_text("utf-8")
    if old not in src:
        raise RuntimeError("Source patch anchor not found: "+path+" / "+old[:90])
    f.write_text(src.replace(old, new), "utf-8")


def patch_ui():
    patch("src/atlas/types.ts",
          "  uly?: string;\n  source?: string;\n}",
          "  uly?: string;\n  source?: string;\n  audio?: string;\n}")
    patch("src/ui/EntryView.tsx",
          "url={exUrls[i] ?? null} text={x.en}",
          'url={x.audio ? import.meta.env.BASE_URL + "atlas/" + x.audio : (exUrls[i] ?? null)} text={x.en}')
    patch("src/pages/StudyRoom.tsx",
          'import { isMastered } from "../store/srs";',
          'import { isMastered } from "../store/srs";\nimport { Speak } from "../ui/Speak";')
    patch("src/pages/StudyRoom.tsx",
          "type ReadingLine = { ug: string; zh: string; uly: string; refs: string[] };",
          "type ReadingLine = { ug: string; zh: string; uly: string; refs: string[]; audio?: string };")
    patch("src/pages/StudyRoom.tsx",
          "type ExampleItem = { id: string; wordId: string; word: string; ug: string; uly: string; zh: string; source?: string };",
          "type ExampleItem = { id: string; wordId: string; word: string; ug: string; uly: string; zh: string; source?: string; audio?: string };")
    patch("src/pages/StudyRoom.tsx",
          '<div className="uy-reader-linehead"><small>第 {i + 1} 句</small><button aria-label="收藏这一句"',
          '<div className="uy-reader-linehead"><small>第 {i + 1} 句</small><div className="uy-room-line-actions"><Speak url={line.audio ? import.meta.env.BASE_URL + "atlas/" + line.audio : null} text={line.ug} size="sm" /><button aria-label="收藏这一句"')
    patch("src/pages/StudyRoom.tsx",
          '{exampleBookmarks.has("story:" + activeStory.id + ":" + i) ? <BookmarkCheck size={17}/> : <Bookmark size={17}/>}</button></div>',
          '{exampleBookmarks.has("story:" + activeStory.id + ":" + i) ? <BookmarkCheck size={17}/> : <Bookmark size={17}/>}</button></div></div>')
    patch("src/pages/StudyRoom.tsx",
          'ug: line.ug, uly: line.uly, zh: line.zh,',
          'ug: line.ug, uly: line.uly, zh: line.zh, audio: line.audio,')
    patch("src/pages/StudyRoom.tsx",
          '<div className="uy-reader-linehead">{x.wordId ?',
          '<div className="uy-reader-linehead">{x.wordId ?')
    patch("src/pages/StudyRoom.tsx",
          '<button className="uy-room-save" aria-label={exampleBookmarks.has(x.id) ? "取消收藏例句" : "收藏例句"}',
          '<div className="uy-room-line-actions"><Speak url={x.audio ? import.meta.env.BASE_URL + "atlas/" + x.audio : null} text={x.ug} size="sm" /><button className="uy-room-save" aria-label={exampleBookmarks.has(x.id) ? "取消收藏例句" : "收藏例句"}')
    patch("src/pages/StudyRoom.tsx",
          '{exampleBookmarks.has(x.id) ? <BookmarkCheck size={18}/> : <Bookmark size={18}/>}</button>',
          '{exampleBookmarks.has(x.id) ? <BookmarkCheck size={18}/> : <Bookmark size={18}/>}</button></div>')
    # port_uyghur.py already disables the original English device-voice fallback.
    css = Path("upstream/src/styles/app.css")
    css.write_text(css.read_text("utf-8")+"""
/* Small sentence audio controls, preserving mobile reading layout. */
.uy-room-line-actions{display:flex;align-items:center;gap:9px}
.uy-room-line-actions .speak{flex:0 0 auto}
.ex-en[lang="ug"]{direction:rtl;text-align:right;line-height:1.9}
.ex-uly{font-size:13px;color:var(--ink-3);margin:6px 0 0;direction:ltr;text-align:left}
""", "utf-8")


def ready(path: Path):
    return path.is_file() and path.stat().st_size > MIN_MP3


def counts(manifest):
    names = manifest["files"]
    missing = [n for n in names if not ready(CACHE/n) and not ready(DEST/n)]
    return len(names), len(missing), missing


def needs(manifest):
    total, absent, _ = counts(manifest)
    print(f"SENTENCE_AUDIO_CACHE {total-absent}/{total}; missing={absent}", flush=True)
    return absent == 0


def normalized_spoken(sentence):
    # Native Uyghur letters preserved; replace punctuation with common TTS
    # separators and avoid feeding quotation punctuation to tokenizer.
    text = sentence.replace("؟", "?").replace("،", ",").replace("؛", ";")
    text = text.replace("«", "").replace("»", "").replace("“", "").replace("”", "")
    return re.sub(r"\s+", " ", text).strip()


def speech_chunks(sentence):
    text = normalized_spoken(sentence)
    # MMS is a short-utterance model. Split exceptionally long generated
    # textbook compounds at token boundaries rather than passing 500 chars.
    if len(text) <= 110:
        return [text]
    tokens = text.split(" ")
    chunks, current = [], ""
    for token in tokens:
        if current and len(current)+1+len(token)>90:
            chunks.append(current)
            current = token
        else:
            current = f"{current} {token}".strip()
    if current:
        chunks.append(current)
    return chunks


def generate(manifest):
    import numpy as np
    import torch
    from transformers import AutoTokenizer, VitsModel

    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = VitsModel.from_pretrained(MODEL)
    model.eval()
    CACHE.mkdir(parents=True, exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)
    texts = manifest["files"]
    errors = []
    created = 0
    for name, sentence in texts.items():
        if ready(CACHE/name) or ready(DEST/name):
            continue
        target = CACHE/name
        tmp = target.with_suffix(".part.mp3")
        try:
            waves = []
            for phrase in speech_chunks(sentence):
                inputs = tokenizer(phrase, return_tensors="pt")
                with torch.inference_mode():
                    wave = model(**inputs).waveform.squeeze().detach().cpu().numpy()
                if wave.size < 800 or not np.isfinite(wave).all():
                    raise ValueError("Empty or nonfinite waveform")
                waves.append(wave)
                waves.append(np.zeros(int(model.config.sampling_rate*.13), dtype=np.float32))
            output = np.concatenate(waves)
            pcm = (np.clip(output, -1, 1)*32767).astype("<i2").tobytes()
            subprocess.run(
                ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                 "-y", "-f", "s16le", "-ar", str(model.config.sampling_rate),
                 "-ac", "1", "-i", "pipe:0", "-codec:a", "libmp3lame",
                 "-b:a", "48k", str(tmp)],
                input=pcm, check=True, timeout=90,
            )
            if not ready(tmp):
                raise ValueError("MP3 file is missing or too small")
            tmp.replace(target)
            created += 1
            if created % 25 == 0:
                print(f"UYGHUR_EXAMPLE_TTS_PROGRESS {created} / {len(texts)}", flush=True)
        except Exception as exc:
            tmp.unlink(missing_ok=True)
            errors.append((name, str(exc)))
            print(f"UYGHUR_EXAMPLE_TTS_ERROR {name} {str(exc)}", flush=True)
    if errors:
        raise RuntimeError(f"Failed to generate {len(errors)} sentence recordings: {errors[:10]}")
    print("UYGHUR_EXAMPLE_AUDIO_GENERATED", created, "unique sentences",flush=True)


def verify(manifest):
    cache = CACHE
    dest = DEST
    dest.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in manifest["files"]:
        output = dest/name
        if not ready(output):
            prior = cache/name
            if not ready(prior):
                raise RuntimeError("Missing sentence audio: " + name)
            # Hardlinks avoid extra workspace disk usage.
            try:
                os.link(prior, output)
            except OSError:
                shutil.copyfile(prior, output)
        if not ready(output):
            raise RuntimeError("Corrupt sentence audio: " + name)
        paths.append(output)
    # Check a representative spread of decoded audio, not only file sizes.
    for i in sorted(set([0,len(paths)//4,len(paths)//2,len(paths)*3//4,len(paths)-1])):
        p = paths[i]
        result = subprocess.check_output(
            ["ffprobe","-v","error","-show_entries","stream=codec_name",
             "-of","default=noprint_wrappers=1:nokey=1",str(p)],
            text=True, timeout=20
        ).strip()
        if "mp3" not in result:
            raise RuntimeError("Audio decode check failed: "+str(p))
    print(f"ALL_EXAMPLE_AUDIO_VERIFIED {manifest['exampleLinks']} example links, "
          f"{manifest['readerLines']} reading lines, {len(paths)} distinct MP3s",flush=True)


def main():
    command = sys.argv[1] if len(sys.argv)>1 else "prepare"
    if command == "prepare":
        manifest = collect_and_attach()
        patch_ui()
        print(f"EXAMPLE_AUDIO_METADATA_READY {manifest['exampleLinks']} card examples, "
              f"{manifest['readerLines']} reader lines; {manifest['uniqueAudios']} unique recordings",
              flush=True)
    elif command in {"needs","generate","verify"}:
        manifest = load(MANIFEST)
        if command == "needs":
            sys.exit(0 if needs(manifest) else 1)
        if command == "generate":
            generate(manifest)
        if command == "verify":
            verify(manifest)
    else:
        raise SystemExit("Expected prepare, needs, generate or verify")


if __name__ == "__main__":
    main()
