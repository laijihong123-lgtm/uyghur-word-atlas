#!/usr/bin/env python3
"""Layer authentic-style beginner readings onto the existing Uyghur Word Atlas."""
from __future__ import annotations
import json
import shutil
from pathlib import Path
from port_uyghur import to_uly

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE / "upstream"

def change(rel, old, new):
    file = ROOT / rel
    text = file.read_text("utf-8")
    if old not in text:
        raise RuntimeError("Integration anchor changed in " + rel + ": " + old[:100])
    file.write_text(text.replace(old, new), "utf-8")

def main():
    index_path = ROOT / "public/atlas/index.json"
    idx = json.loads(index_path.read_text("utf-8"))
    if idx.get("count") != 1813 or idx.get("id") != "uyghur-textbook-reviewed-20261113":
        raise RuntimeError("Expected reviewed textbook word cards")
    folder = ROOT / "public/atlas/entries"
    chunks = [(p, json.loads(p.read_text("utf-8"))) for p in sorted(folder.glob("*.json"), key=lambda p:int(p.stem))]
    entries = [e for _, chunk in chunks for e in chunk]
    if len(entries) != 1813 or any(e["ex"] for e in entries):
        raise RuntimeError("Not the original no-example Uyghur deck")
    lookup = {e["w"]:e for e in entries}
    data = json.loads((HERE/"data/reading.json").read_text("utf-8"))
    if data.get("version") != 1:
        raise RuntimeError("Unknown reader schema")
    def enrich(line):
        uy, zh = line["ug"].strip(), line["zh"].strip()
        if not uy or not zh:
            raise RuntimeError("Empty reading text or translation")
        refs = []
        for term in dict.fromkeys(line["targets"]):
            e = lookup.get(term)
            if e is None:
                continue
            refs.append(e["id"])
            if len(e["ex"]) < 2 and not any(x["en"] == uy for x in e["ex"]):
                e["ex"].append({"en":uy, "zh":zh, "uly":to_uly(uy)})
        return {"ug":uy,"zh":zh,"uly":to_uly(uy),"refs":refs}
    readings = [{
        "id":s["id"], "title":s["title"], "titleZh":s["titleZh"],
        "level":s["level"], "description":s["description"],
        "lines":[enrich(line) for line in s["lines"]],
        "questions":s["questions"],
    } for s in data["stories"]]
    for line in data["extra"]:
        enrich(line)
    examples = [
        {"id":e["id"]+":"+str(i),"wordId":e["id"],"word":e["w"],"ug":x["en"],"uly":x["uly"],"zh":x["zh"]}
        for e in entries for i,x in enumerate(e["ex"])
    ]
    if len(readings) < 6 or len(examples) < 45:
        raise RuntimeError("Missing readings or too few mapped examples: "+str(len(examples)))
    for p, chunk in chunks:
        p.write_text(json.dumps(chunk, ensure_ascii=False, indent=2), "utf-8")
    idx["examples"] = len(examples)
    index_path.write_text(json.dumps(idx, ensure_ascii=False, separators=(",",":")), "utf-8")
    public = ROOT / "public/atlas"
    (public/"reading.json").write_text(json.dumps(readings, ensure_ascii=False, separators=(",",":")), "utf-8")
    (public/"examples.json").write_text(json.dumps(examples, ensure_ascii=False, separators=(",",":")), "utf-8")
    shutil.copyfile(HERE/"tools/StudyRoom.tsx", ROOT/"src/pages/StudyRoom.tsx")
    css = ROOT/"src/styles/app.css"
    css.write_text(css.read_text("utf-8")+"\n"+(HERE/"tools/reading.css").read_text("utf-8"), "utf-8")

    change("src/lib/router.ts", '  | { page: "learn" }', '  | { page: "library" }\n  | { page: "learn" }')
    change("src/lib/router.ts", '  else if (seg[0] === "learn") route = { page: "learn" };',
           '  else if (seg[0] === "library") route = { page: "library" };\n  else if (seg[0] === "learn") route = { page: "learn" };')
    change("src/App.tsx",
           'import { BookOpen, ChevronLeft, ChevronRight, Compass, Github, Keyboard, Moon, Search, Sun, User } from "lucide-react";',
           'import { BookMarked, BookOpen, ChevronLeft, ChevronRight, Compass, Github, Keyboard, Moon, Search, Sun, User } from "lucide-react";')
    change("src/App.tsx", 'import { AtlasPage } from "./pages/Atlas";',
           'import { AtlasPage } from "./pages/Atlas";\nimport { StudyRoom } from "./pages/StudyRoom";')
    change("src/App.tsx", '  { page: "atlas", label: "图鉴", icon: BookOpen },',
           '  { page: "atlas", label: "图鉴", icon: BookOpen },\n  { page: "library", label: "书房", icon: BookMarked },')
    change("src/App.tsx", '        {route.page === "atlas" && <AtlasPage route={route} />}',
           '        {route.page === "atlas" && <AtlasPage route={route} />}\n        {route.page === "library" && <StudyRoom />}')
    change("src/atlas/types.ts", 'export interface Example {\n  en: string;\n  zh: string;\n}',
           'export interface Example {\n  en: string;\n  zh: string;\n  uly?: string;\n}')
    change("src/store/store.ts", '  bookmarks: string[];\n  days: Record<string, DayStat>;',
           '  bookmarks: string[];\n  exampleBookmarks: string[];\n  readingDone: string[];\n  days: Record<string, DayStat>;')
    change("src/store/store.ts", '  bookmarks: [],\n  days: {},',
           '  bookmarks: [],\n  exampleBookmarks: [],\n  readingDone: [],\n  days: {},')
    change("src/store/store.ts",
           '  if (Array.isArray(v.bookmarks)) out.bookmarks = v.bookmarks.filter((x): x is string => typeof x === "string").slice(0, 20000);',
           '  if (Array.isArray(v.bookmarks)) out.bookmarks = v.bookmarks.filter((x): x is string => typeof x === "string").slice(0, 20000);\n'
           '  if (Array.isArray(v.exampleBookmarks)) out.exampleBookmarks = v.exampleBookmarks.filter((x): x is string => typeof x === "string").slice(0, 20000);\n'
           '  if (Array.isArray(v.readingDone)) out.readingDone = v.readingDone.filter((x): x is string => typeof x === "string").slice(0, 1000);')
    change("src/store/store.ts", '/* ---------- backup ---------- */',
           'export function toggleExampleBookmark(id: string) {\n'
           '  store.progress((p) => ({\n'
           '    ...p,\n'
           '    exampleBookmarks: p.exampleBookmarks.includes(id)\n'
           '      ? p.exampleBookmarks.filter((x) => x !== id)\n'
           '      : [id, ...p.exampleBookmarks],\n'
           '  }));\n}\n\n/* ---------- backup ---------- */')
    change("src/ui/EntryView.tsx",
           'import { toggleBookmark, useStore } from "../store/store";',
           'import { toggleBookmark, toggleExampleBookmark, useStore } from "../store/store";')
    change("src/ui/EntryView.tsx",
           '  const saved = useStore((s) => s.progress.bookmarks.includes(entry.id));',
           '  const saved = useStore((s) => s.progress.bookmarks.includes(entry.id));\n'
           '  const savedExamples = useStore((s) => s.progress.exampleBookmarks);')
    change("src/ui/EntryView.tsx", '"维语语境" : "日常"', '"补充例句" : "日常"')
    change("src/ui/EntryView.tsx", '<p className="ex-en" lang="en">', '<p className="ex-en" lang="ug" dir="rtl">')
    change("src/ui/EntryView.tsx", '                  <p className="ex-zh">{x.zh}</p>',
           '                  {x.uly && <p className="ex-uly" dir="ltr">{x.uly}</p>}\n'
           '                  <p className="ex-zh">{x.zh}</p>\n'
           '                  <button type="button" className="uy-room-save" onClick={() => toggleExampleBookmark(entry.id + ":" + i)}\n'
           '                    aria-pressed={savedExamples.includes(entry.id + ":" + i)} aria-label={savedExamples.includes(entry.id + ":" + i) ? "取消收藏例句" : "收藏例句"}>\n'
           '                    {savedExamples.includes(entry.id + ":" + i) ? "♥ 已收藏" : "♡ 收藏例句"}\n'
           '                  </button>')
    print("READING_ROOM_READY",len(readings),"stories",sum(len(x["lines"]) for x in readings),"sentences",len(examples),"word-linked examples", flush=True)

if __name__ == "__main__":
    main()
