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
    # Preserve the existing 46-word starter deck at its original ids for progress compatibility.
    for line in (HERE / "data/words.txt").read_text("utf-8").splitlines():
        if not line.strip() or line.startswith("#"):continue
        parts=line.split("|")
        if len(parts)!=4:raise RuntimeError(f"Invalid core word row: {line}")
        uy,zh,latin,topic=[x.strip() for x in parts]
        if uy in seen or topic not in TOPIC_NAMES:raise RuntimeError("Duplicate/invalid core word")
        seen.add(uy)
        dataset.append({"uy":uy,"zh":zh,"latin":latin,"topic":topic,
                        "status":"source-compared","source":"公开词汇表交叉参考；尚非母语者逐词终审"})
    safe_count=len(dataset)
    candidates=HERE/"data/word_bank_2000.json"
    if not candidates.is_file():raise RuntimeError("Missing dictionary-backed 2000-word candidate index; do not silently build a smaller release")
    backing=json.loads(candidates.read_text(encoding="utf-8"))
    for row in backing:
        uy=row.get("uy","").strip()
        zh=row.get("zh","").strip()
        topic=row.get("topic","daily")
        if uy in seen or not uy or not zh or topic not in TOPIC_NAMES:continue
        seen.add(uy)
        dataset.append({"uy":uy,"zh":zh,"latin":"","topic":topic,
                        "status":"unreviewed",
                        "source":row.get("source","公开维汉词典"),
                        "imla_id":row.get("imla_id",""),
                        "spelling_dictionary":row.get("spelling_dictionary",""),
                        "category":row.get("category",""),
                        "frequency":row.get("freq",0)})
        if len(dataset)==2000:break
    if len(dataset)!=2000 or safe_count < 40:
        raise RuntimeError(f"Expected 2000 candidates with >=40 source-compared starter words; got {len(dataset)} / {safe_count}")
    # Important: the 1954 candidates are for SEARCH/REVIEW ONLY. They are not learning
    # answers; cross-checking spelling does not validate Chinese sense accuracy.
    import hashlib
    actual_safe={x["uy"] for x in dataset if x["status"]=="source-compared"}
    if len(actual_safe)!=safe_count:raise RuntimeError("Starter word duplication")
    idx_note = f"2,000 entry reference index; {safe_count} source-compared words enabled for study"
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
    for i,row in enumerate(dataset):
        uy,zh,latin,topic=row["uy"],row["zh"],row["latin"],row["topic"]
        safe=row["status"]=="source-compared"
        wid=f"uy{i+1:05d}" if safe else "uw"+hashlib.sha256(uy.encode("utf-8")).hexdigest()[:16]
        lvl=0 if safe and i<32 else 1 if safe else 2
        exposed_zh=zh if safe else f"候选义项·待复核：{zh}"
        # 32 is an intentionally separate local QA eligibility bit. It is not audio.
        qa_flag=32 if safe else 0
        index_rows.append([wid,uy,exposed_zh,latin,lvl,topics.index(topic),qa_flag])
        entries.append({
            "id":wid,"w":uy,"uk":latin,"us":"",
            "senses":[{"pos":"词语","zh":exposed_zh,"en":""}],
            "ex":[],"col":[],"fam":[],"syn":[],"ant":[],
            "tip":("拉丁转写："+latin+"。已通过多份公开词表对照，但未完成母语终审。" if safe
                   else "此词仅供资料检索：词形对应2009/2011审校词目，中文候选释义未经人工复核。请勿直接背诵。"),
            "cefr":"A1" if lvl==0 else "A2" if lvl==1 else "B1",
            "topic":topic,"m":qa_flag,
            "note":("基础词·多来源对照；" if safe else
                     "候选词·默认不进入任何背诵测验；")+
                   "来源："+row.get("source","")+
                   (("；正字词目ID："+row.get("imla_id","")) if not safe else ""),
        })
    idx.update({"id":"uyghur-atlas-starter-v1","name":"维语词光 · 2000词分级审校库",
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

    # The original FSRS implementation is unchanged; only source-eligibility
    # filtering is added. A dictionary entry is NOT a verified memorization item.
    patch("src/store/session.ts",
          'if (w.cefr < from || p.cards[w.id] || out.includes(w.id)) continue;',
          'if (!(w.media & 32) || w.cefr < from || p.cards[w.id] || out.includes(w.id)) continue;')
    patch("src/store/session.ts",
          'const due = dueIds(p).filter((id) => atlas.byId.has(id));',
          'const due = dueIds(p).filter((id) => !!(atlas.byId.get(id)?.media & 32));')
    patch("src/pages/Practice.tsx",
          'atlas.words.filter((w) => w.cefr >= startLevel).slice(0, 400).map((w) => w.id)',
          'atlas.words.filter((w) => w.cefr >= startLevel && !!(w.media & 32)).slice(0, 400).map((w) => w.id)')
    # Insert a plain-language notice without replacing original page layout.
    patch("src/pages/Today.tsx",
          '<header className="greet">',
          '<div style={{padding:"12px 16px",marginBottom:16,borderRadius:12,background:"var(--surface, #f5f0e5)",fontSize:13,lineHeight:1.6}} role="note">词库已有 2,000 条可搜索的词目，但其中约 1,954 条中文释义仍在审校，暂不参与背诵测验。系统仅安排多来源交叉参考的基础词进入每日复习，避免把候选译义当作标准答案。</div>\n      <header className="greet">')

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
    # All original IELTS/media marketing claims are wrong in an audio-free Uyghur build.
    # Keep the About page layout but replace claims with the actual adapted scope.
    about_file = ROOT / "src/pages/About.tsx"
    about = about_file.read_text("utf-8")
    for old, new in [
        ("一词一画，点亮雅思。", "维语词光 · 用词汇点亮星图。"),
        ("词光把雅思阅读 8000 词整理成 {atlas.count.toLocaleString()} 个词条。每个词一幅原创插画，一句日常例句，一句雅思例句，配英美发音、常用搭配和易混提示。学会一个，就在你的星图上点亮一颗星。",
         "本版基于原版 Word Atlas 开源代码改造，目前收录 {atlas.count.toLocaleString()} 条维语词目，尚未经语言专家全面终审。其中多来源核对的基础词可以参加背诵，其他词条暂供查词审校，不能当作最终译义。暂无真实维语音频、逐词插画和审校例句。"),
        ("它免费、开源、无需注册。代码用 MIT，词库用 CC BY 4.0，谁都可以拿去用。",
         "程序保留原版 MIT 代码许可；原版素材与内容许可证另行适用。学习进度存于本机浏览器。"),
        ("每个词都有一幅画，画的就是第一句例句里发生的事。",
         "按照维文、中文释义和转写提示学习，不把英语插画误认成维语词义。"),
        ("选义、看图补句、听音辨词、拼写，从认得走到会写。",
         "先认出词义，再进行维语拼写；无可靠维语音源时不开启听音题。"),
        ("释义、例句、搭配和提示由大语言模型按统一的词典规范重新撰写；插画由图像模型按统一画风逐词绘制；发音和朗读由 ElevenLabs 合成（英音 Alice，美音 Sarah）。所有内容都经过结构和一致性的自动校验，但没有逐条人工审校。看到错的地方，欢迎在 GitHub 提 Issue，或者直接改数据提 PR。",
         "此版本的维语词汇是从公开资料交叉参考的候选词中选取，尚未完成维吾尔语母语专家逐词终审，因此请结合可靠词典复核。没有使用英文配音充当维语配音，也未编造例句。"),
        ("词光不是官方雅思词表，也不承诺提分。它只想把背单词这件事，做得好看一点、扎实一点。",
         "此版本不代表高校辅导员招聘官方词汇要求。现有候选词库不是2,000条全部专业审定的背诵题库；未经核对的释义不参与自动测验。"),
        ("data/word-atlas.json", "data/words.txt"),
        ("和 <code>.csv</code> 是完整词库；<code>public/atlas</code> 里是网页用的分块数据、插画和音频。拿去做 Anki 牌组、背词小程序、浏览器插件，或者 AI 应用的评测集，署名即可。",
         "是维语候选词列表；网页构建时自动生成 <code>public/atlas</code> 词库索引与词条。请保留上游项目与内容来源的版权信息。"),
    ]:
        if old not in about:
            raise RuntimeError(f"Upstream About page changed: {old[:25]}")
        about = about.replace(old,new)
    about_file.write_text(about,"utf-8")
    patch("src/config.ts", "https://github.com/designfuchen/word-atlas",
          "https://github.com/laijihong123-lgtm/uyghur-word-atlas")
    # Retain the About section's explicit original-project attribution.
    # Do not rewrite it automatically as if the Uyghur content were already certified.
    html = ROOT / "index.html"
    s = html.read_text("utf-8").replace("词光 Word Atlas","维语词光 Uyghur Atlas").replace(
        "雅思","维语")
    s = re.sub(r'(<meta name="description" content=")[^"]*',
               lambda m: m.group(1)+"2,000条维语候选词可查询；仅多来源对照词进入学习。基于 Word Atlas 开源代码，无英语假发音。",s)
    s = re.sub(r'(<meta property="og:description" content=")[^"]*',
               lambda m: m.group(1)+"维语词光：基于开源 Word Atlas 改造的维语学习实验版本。",s)
    s = s.replace("https://0xlei.tech/words/brand/og-card.jpg",
                  "/uyghur-word-atlas/brand/og-card.jpg")
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
        "There are 2,000 searchable candidate entries. Only the first 46 source-compared words are enabled for study. All dictionary-only Chinese senses are NOT language-expert validated.\n"
        "Real Uyghur pronunciation is NOT provided.\n","utf-8")
    print(f"Adaptation complete: {len(entries)} Uyghur entries, {safe_count} study-eligible, "
          "no English TTS/listening, original UI/FSRS/WebGL files retained.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.exit(f"Port error: {exc}")
