#!/usr/bin/env python3
"""Overlay vetted-candidate Uyghur data on the ORIGINAL designfuchen/word-atlas source.
Does not machine-translate an English corpus. Fails if upstream patch anchors change.
The 46 starter entries are preliminary references, NOT native-speaker certified.
"""
from __future__ import annotations
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE / "upstream"
TOPIC_NAMES = ["education","work","technology","science","environment","health","society",
               "government","economy","media","arts","travel","city","nature",
               "daily","emotion","thinking","sport","history"]

def patch(path: str, before: str, after: str):
    file = ROOT / path
    s = file.read_text(encoding="utf-8")
    if before not in s:
        raise RuntimeError(f"Upstream file changed; safe patch stopped: {path}: {before[:75]}")
    file.write_text(s.replace(before, after), encoding="utf-8")

def main():
    if not (ROOT / "src/store/session.ts").exists():
        raise RuntimeError("Expected actual Word Atlas source in upstream/")
    pkg = json.loads((ROOT / "package.json").read_text("utf-8"))
    if pkg.get("name") != "word-atlas":
        raise RuntimeError("Not the original Word Atlas source.")

    dataset = []
    seen = set()
    for line in (HERE / "data/words.txt").read_text("utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) != 4:
            raise RuntimeError(f"Malformed vocabulary row: {line}")
        uy, zh, latin, topic = [x.strip() for x in parts]
        if not (uy and zh and latin and topic in TOPIC_NAMES):
            raise RuntimeError(f"Invalid word row: {line}")
        if not re.search("[\u0600-\u06ff]", uy) or uy in seen:
            raise RuntimeError(f"Invalid/duplicate Uyghur form: {uy}")
        seen.add(uy)
        dataset.append((uy,zh,latin,topic))
    if len(dataset) < 10:
        raise RuntimeError("Too few eligible words, refusing to build.")
    atlas_dir = ROOT / "public/atlas"
    index_file = atlas_dir / "index.json"
    idx = json.loads(index_file.read_text("utf-8"))
    if not isinstance(idx.get("words"), list) or not isinstance(idx.get("topics"), list):
        raise RuntimeError("Upstream index format changed.")
    topics = [x[0] for x in idx["topics"]]

    # Remove all English word entry chunks; do not accidentally serve English words.
    for name in ("entries", "img", "thumb", "audio"):
        dest = atlas_dir / name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
    entries_dir = atlas_dir / "entries"
    entries_dir.mkdir(parents=True, exist_ok=True)
    index_rows = []
    entries = []
    for i, (uy, zh, latin, topic) in enumerate(dataset):
        wid = f"uy{i+1:05d}"
        lvl = 0 if i < 32 else 1
        index_rows.append([wid, uy, zh, latin, lvl, topics.index(topic), 0])
        entries.append({
            "id":wid, "w":uy, "uk":latin, "us":"",
            "senses":[{"pos":"词语","zh":zh,"en":""}],
            "ex":[], "col":[], "fam":[], "syn":[], "ant":[],
            "tip":"拉丁字母转写提示："+latin+"（不是录音或国际音标）",
            "cefr":"A1" if lvl == 0 else "A2",
            "topic":topic, "m":0,
            "note":"公开资料交叉参考的初筛词；未经母语专家逐项终审。"
        })
    idx.update({"id":"uyghur-atlas-starter-v1","name":"维语词光 · 初筛词库",
                "count":len(index_rows),"examples":0,"illustrated":0,
                "voiced":0,"chunk":100,"words":index_rows})
    index_file.write_text(json.dumps(idx,ensure_ascii=False,separators=(",",":")),"utf-8")
    for n in range(0, len(entries), 100):
        (entries_dir / f"{n//100}.json").write_text(
            json.dumps(entries[n:n+100],ensure_ascii=False,indent=2),"utf-8")

    # Disable all unverified pronunciation, INCLUDING the original English TTS fallback.
    audio_path = ROOT / "src/lib/audio.ts"
    audio = audio_path.read_text("utf-8")
    fallback = '  if (!("speechSynthesis" in window)) return "unsupported" as const;'
    if fallback not in audio:
        raise RuntimeError("Cannot safely disable English TTS fallback.")
    audio = audio[:audio.index(fallback)] + '  return "unsupported" as const;\n}\n'
    audio = audio.replace(
        'async function speak(url: string | null | undefined, text: string, accent: "uk" | "us", rate: number)',
        'async function speak(url: string | null | undefined, _text: string, _accent: "uk" | "us", rate: number)')
    audio_path.write_text(audio,"utf-8")

    # Keep original FSRS scheduler; adjust question selection only when no media exists.
    file = ROOT / "src/store/session.ts"
    s = file.read_text("utf-8")
    match = re.search(
        r"function quizKind\(ref: WordRef, p: Progress, s: Settings, salt: number\): QuizKind \{.*?\n\}",
        s,re.S)
    if not match:
        raise RuntimeError("Quiz mode selector was changed upstream.")
    newkind = """function quizKind(ref: WordRef, p: Progress, s: Settings, salt: number): QuizKind {
  const c = p.cards[ref.id];
  const roll = hashSeed(ref.id + salt) % 100;
  // No image or Uyghur voice; retain meaning choice and optionally spelling.
  return s.spell && !!c && (c.s >= 4 || roll < 35) ? "spell" : "meaning";
}"""
    s = s[:match.start()] + newkind + s[match.end():]
    s = s.replace('import { MEDIA } from "../atlas/types";\n','')
    retry = ('        const ref = atlas.byId.get(step.id)!;\n'
             '        const kind: QuizKind = step.kind === "meaning" ? (ref.media & MEDIA.img ? "picture" : "listen") : "meaning";')
    if retry not in s:
        raise RuntimeError("Question retry logic changed upstream.")
    s = s.replace(retry,
        '        const ref = atlas.byId.get(step.id)!;\n'
        '        const kind: QuizKind = step.kind === "meaning" && settings.spell ? "spell" : "meaning";')
    file.write_text(s,"utf-8")

    # No 'listen' or picture/cloze cards with absent Uyghur recordings / examples.
    patch("src/pages/Practice.tsx",
          'import { Headphones, Keyboard, RotateCcw, Type } from "lucide-react";',
          'import { RotateCcw, Type } from "lucide-react";')
    patch("src/pages/Practice.tsx",
          '  ["sentence", "例句", "照着抄写，练出手感", Keyboard],\n'
          '  ["dictation", "听写", "只听声音，写下整句", Headphones],',
          '  // Sentence typing and dictation require audited examples and real Uyghur voice.')
    patch("src/pages/Practice.tsx",
          '["word", "单词", "看图写出单词", Type]',
          '["word", "单词", "根据中文提示写出维语词", Type]')
    patch("src/pages/Practice.tsx",
          'className="typing-input"', 'className="typing-input" lang="ug" dir="rtl"')

    # Preserve visual component; without audio only show text transliteration.
    patch("src/ui/Speak.tsx", '  return (\n    <button',
          '  if (!url) return label ? <span className="speak-label">{label}</span> : null;\n  return (\n    <button')
    patch("src/ui/EntryView.tsx", 'accent === "uk" ? "英" : "美"', '"转写"')
    patch("src/ui/EntryView.tsx",
          'className="headword" lang="en"', 'className="headword" lang="ug" dir="rtl"')
    patch("src/pages/Learn.tsx",
          'className="headword" lang="en"', 'className="headword" lang="ug" dir="rtl"')

    # Small targeted branding changes, leaving original React UI, WebGL, and FSRS untouched.
    for file in list((ROOT / "src").rglob("*.tsx")):
        s = file.read_text("utf-8")
        if file.name == "About.tsx": # keep original acknowledgements/license text
            continue
        s = s.replace("词光 Word Atlas","维语词光 Uyghur Atlas").replace(
            "一词一画，点亮雅思", "一词一画，学习维语").replace(
            "雅思词汇","维语词汇").replace("雅思", "维语")
        file.write_text(s, "utf-8")
    html = ROOT / "index.html"
    s = html.read_text("utf-8").replace("词光 Word Atlas","维语词光 Uyghur Atlas").replace(
        "雅思","维语")
    css = """<style id="uyghur-rtl">
      .headword,.prompt-word .headword,.typing-text{direction:rtl;unicode-bidi:plaintext;
          font-family:"Geeza Pro","Noto Naskh Arabic","Noto Sans Arabic",serif}
      .typing-input[lang="ug"]{direction:rtl;unicode-bidi:plaintext}
      .uyghur-translit{direction:ltr}
      </style>"""
    if "</head>" not in s:
        raise RuntimeError("Upstream HTML shell changed.")
    html.write_text(s.replace("</head>",css+"\n</head>"),"utf-8")
    for name in ("manifest.json","manifest.webmanifest"):
        f = ROOT/"public"/name
        if f.exists():
            f.write_text(f.read_text("utf-8").replace("词光","维语词光").replace(
                "Word Atlas","Uyghur Atlas"),"utf-8")

    (ROOT/"UYGHUR_PORT_NOTICE.md").write_text(
        "# Uyghur Atlas – source and content notice\n\n"
        "Based on designfuchen/word-atlas, code MIT licensed.\n"
        "Original project: https://github.com/designfuchen/word-atlas\n"
        "Original source/illustrations have separate licensing terms.\n"
        "This build excludes English word audio and original English illustrations.\n"
        "The vocabulary is preliminary cross-source material, NOT fully expert-proofread.\n"
        "Real Uyghur pronunciation is NOT provided.\n","utf-8")
    print(f"Adaptation complete: {len(entries)} preliminary Uyghur words, "
          "no English TTS/listening, original UI/FSRS/WebGL files retained.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.exit(f"Port error: {exc}")
