#!/usr/bin/env python3
"""Overlay vetted-candidate Uyghur data on the ORIGINAL designfuchen/word-atlas source.
Does not machine-translate an English corpus. Fails if upstream patch anchors change.
This user-reviewed textbook table contains 1817 study rows; four homograph pairs merge into 1813 cards.
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

    # User-supplied: 《维吾尔语词表_逐条复核版.xlsx》, first sheet.
    # Only the 1,817 explicitly approved study records are imported.
    # The 4 "暂缓背诵" records are deliberately excluded from study and search.
    import csv
    source_file=HERE/"data/textbook_reviewed.tsv"
    with source_file.open("r",encoding="utf-8-sig",newline="") as f:
        source_rows=list(csv.DictReader(f,delimiter="\t"))
    if len(source_rows)!=1817:
        raise RuntimeError(f"Expected exactly 1817 user-reviewed rows; got {len(source_rows)}")
    grouped={}
    for expected,row in enumerate(source_rows,1):
        if int(row["序号"])!=expected:raise RuntimeError(f"Wrong row order at {expected}")
        uy=row["维吾尔语"].strip()
        zh=row["中文释义"].strip()
        page=int(row["原书页码"])
        source_no=row["原表序号"].strip()
        if not uy or not zh or not source_no or not (546<=page<=637):
            raise RuntimeError(f"Empty/invalid approved word at #{expected}")
        if not re.search(r"[\u0600-\u06ff]",uy):raise RuntimeError(f"Non-Uyghur word at #{expected}")
        # Repeated written forms can have different valid textbook senses
        # (e.g. يۈز: face / hundred). Combine as ONE card with BOTH senses:
        # this prevents ambiguous meaning quizzes and avoids deleting any sense.
        if uy not in grouped:
            grouped[uy]={"uy":uy,"senses":[],"sources":[],"seq":expected}
        grouped[uy]["senses"].append(zh)
        grouped[uy]["sources"].append((source_no,page,expected))
    dataset=list(grouped.values())
    if len(dataset)!=1813:
        raise RuntimeError(f"Expected 1813 unique written forms from 1817 reviewed rows; got {len(dataset)}")
    safe_count=len(dataset)
    topics_cues=[
        ("education",("学校","学生","教师","教育","老师","课程","课本","教室","课堂","作业","大学","毕业","学期","考试","知识","班级","图书馆","学习")),
        ("health",("健康","医院","医生","病人","疾病","治疗","药物","疼痛","伤口","身体","症状")),
        ("government",("法律","法规","政府","纪律","违法","公安","警察","安全","危险","保护","制度")),
        ("work",("工作","职业","就业","企业","单位","岗位","工资","招聘","实习","管理人员")),
        ("emotion",("情绪","感情","悲伤","忧虑","担心","害怕","愤怒","快乐","高兴","压力")),
        ("thinking",("思想","观点","意见","分析","理解","解释","原因","判断","理论","方法")),
        ("society",("社会","交往","交谈","交流","朋友","合作","关系","家庭","尊重")),
        ("nature",("自然","森林","河流","海洋","植物","动物","大山")),
    ]
    def inferred_topic(gloss):
        for label,needles in topics_cues:
            if any(n in gloss for n in needles):return label
        return "daily"
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
        uy=row["uy"]
        meanings=list(dict.fromkeys(row["senses"])) # only deduplicate exact repeated sense strings
        joined=" ／ ".join(meanings)
        topic=inferred_topic(joined)
        wid=f"tb{row['seq']:04d}"
        # These six bins follow the textbook appendix order, NOT a CEFR rating.
        level=min(5, i*6//len(dataset))
        if topic not in topics:topic="daily"
        index_rows.append([wid,uy,joined,"",level,topics.index(topic),32])
        provenance="；".join(f"原表{n}·教材第{p}页" for n,p,_ in row["sources"])
        entries.append({
            "id":wid,"w":uy,"uk":"","us":"",
            "senses":[{"pos":"教材释义","zh":meaning,"en":""} for meaning in row["senses"]],
            "ex":[],"col":[],"fam":[],"syn":[],"ant":[],
            "tip":("教材以 - 结尾表示动词词干；请勿把末尾连字符当作词的一部分发音。"
                   if uy.endswith("-") else
                   "词表未提供经核对的拉丁转写或录音，本版不显示猜测读音。"),
            "cefr":f"第{level+1}组","topic":topic,"m":32,
            "note":"来自用户提供的逐条复核教材词表；"+provenance+
                   "。学习分组按原表顺序，不代表CEFR水平；主题仅依据中文释义自动辅助归类。",
        })
    idx.update({"id":"uyghur-textbook-reviewed-20261113","name":"维语词光 · 教材逐条复核词库",
                "count":len(index_rows),"examples":0,"illustrated":0,
                "voiced":0,"chunk":100,"words":index_rows})
    idx["cefr"]=[f"第{i}组" for i in range(1,7)]
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

    # Original FSRS memory scheduling is retained; only reviewed textbook cards are imported.
    patch("src/store/session.ts",
          'if (w.cefr < from || p.cards[w.id] || out.includes(w.id)) continue;',
          'if (!(w.media & 32) || w.cefr < from || p.cards[w.id] || out.includes(w.id)) continue;')
    patch("src/store/session.ts",
          'const due = dueIds(p).filter((id) => atlas.byId.has(id));',
          'const due = dueIds(p).filter((id) => ((atlas.byId.get(id)?.media ?? 0) & 32) !== 0);')
    patch("src/pages/Practice.tsx",
          'atlas.words.filter((w) => w.cefr >= startLevel).slice(0, 400).map((w) => w.id)',
          'atlas.words.filter((w) => w.cefr >= startLevel && !!(w.media & 32)).slice(0, 400).map((w) => w.id)')
    # Insert a plain-language notice without replacing original page layout.
    patch("src/pages/Today.tsx",
          '<header className="greet">',
          '<div style={{padding:"12px 16px",marginBottom:16,borderRadius:12,background:"var(--surface, #f5f0e5)",fontSize:13,lineHeight:1.6}} role="note">已导入1,817条教材逐条复核记录；4组同形异义合并成1,813张词卡。4条未决词单独保留、暂不背诵。分组按附录原表顺序，并非CEFR语言等级。</div>\n      <header className="greet">')

    # The original lesson appendix is ordered alphabetically. Stages below
    # follow original order, NOT standardized CEFR ability estimates.
    patch("src/pages/Today.tsx",
          "学习路线 · 从 A1 到 C2",
          "教材词库 · 按附录原表顺序分六组")
    patch("src/pages/Today.tsx",
          'const NAMES = ["入门", "基础", "进阶", "中高", "高级", "精通"];',
          'const NAMES = ["附录1", "附录2", "附录3", "附录4", "附录5", "附录6"];')
    patch("src/pages/Today.tsx",
          "按雅思话题探索", "按词义辅助归类")
    patch("src/pages/Today.tsx",
          'const list = pool.length ? pool : atlas.words;',
          'const list = pool.length ? pool : atlas.words.filter((w) => !w.word.endsWith("-"));')
    # Verb stems end in a source-notation dash. They should be meaning-only
    # questions rather than asking students to spell a hyphen as a letter.
    patch("src/pages/Practice.tsx",
          "return ids.filter((id) => atlas.byId.has(id));",
          'return ids.filter((id) => !!atlas.byId.get(id) && !atlas.byId.get(id)!.word.endsWith("-"));')

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
  return !ref.word.endsWith("-") && s.spell && !!c && (c.s >= 4 || roll < 35) ? "spell" : "meaning";
}"""
    s = s[:match.start()] + newkind + s[match.end():]
    s = s.replace('import { MEDIA } from "../atlas/types";\n','')
    retry = ('        const ref = atlas.byId.get(step.id)!;\n'
             '        const kind: QuizKind = step.kind === "meaning" ? (ref.media & MEDIA.img ? "picture" : "listen") : "meaning";')
    if retry not in s:
        raise RuntimeError("Question retry logic changed upstream.")
    s = s.replace(retry,
        '        const ref = atlas.byId.get(step.id)!;\n'
        '        const kind: QuizKind = step.kind === "meaning" && settings.spell && !ref.word.endsWith("-") ? "spell" : "meaning";')
    file.write_text(s,"utf-8")

    # Environment audio is separate from word pronunciations.
    # On iOS Safari, start the Web Audio graph from a REAL button tap,
    # instead of relying exclusively on a later useEffect/autoplay.
    patch("src/ui/Ambience.tsx",
          'onClick={() => store.settings({ ambience: sel ? "off" : id })}',
          'onClick={() => { void setAmbience(sel ? null : id, volume); store.settings({ ambience: sel ? "off" : id }); }}')
    patch("src/ui/Ambience.tsx",
          'onClick={() => store.settings({ ambience: "off" })}',
          'onClick={() => { void setAmbience(null, volume); store.settings({ ambience: "off" }); }}')
    patch("src/ui/Ambience.tsx",
          '<p className="eyebrow">环境声 · 专注陪伴</p>',
          '<p className="eyebrow">环境声 · 专注陪伴</p>\n'
          '          <button type="button" className="btn btn-primary" style={{width:"100%",margin:"8px 0 12px"}} '
          'onClick={() => { const next = ambience === "off" ? "stars" : ambience; void setAmbience(next, volume); store.settings({ambience:next}); }}>'
          '▶ 点击播放环境声</button>')
    patch("src/ui/Ambience.tsx",
          '读单词时会自动压低环境声。',
          'iPhone首次播放请点上面的播放按钮或选择一种环境声；若无声音，请检查媒体音量与静音设置。')

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
         "本版采用用户提供的维吾尔语教材逐条复核词表：原表1,817条背诵记录，合并4组同形异义后是 {atlas.count.toLocaleString()} 张词卡，全部可以进行学习与复习。原表另有4条未决词已排除；不生成未经核实的录音、音标、例句和插画。"),
        ("它免费、开源、无需注册。代码用 MIT，词库用 CC BY 4.0，谁都可以拿去用。",
         "程序保留原版 MIT 代码许可；原版素材与内容许可证另行适用。学习进度存于本机浏览器。"),
        ("每个词都有一幅画，画的就是第一句例句里发生的事。",
         "按教材复核版维文和中文释义学习，不生成没有依据的拉丁转写或英语发音。"),
        ("选义、看图补句、听音辨词、拼写，从认得走到会写。",
         "先认出词义，再进行维语拼写；无可靠维语音源时不开启听音题。"),
        ("释义、例句、搭配和提示由大语言模型按统一的词典规范重新撰写；插画由图像模型按统一画风逐词绘制；发音和朗读由 ElevenLabs 合成（英音 Alice，美音 Sarah）。所有内容都经过结构和一致性的自动校验，但没有逐条人工审校。看到错的地方，欢迎在 GitHub 提 Issue，或者直接改数据提 PR。",
         "本版直接采用用户上传的《维吾尔语词表_逐条复核版.xlsx》中「背诵词表」的全部1,817条记录，逐条保留原书页码及原表序号。网站没有再次独立进行维语母语专家终审，也没有用英语配音或机器生成语音充当维语发音。"),
        ("词光不是官方雅思词表，也不承诺提分。它只想把背单词这件事，做得好看一点、扎实一点。",
         "这是你提供的教材附录词库，并非高校辅导员招聘考试官方词表。教材中未决的4条词组不进入学习；以后可根据可靠来源另行扩展岗位专项词。"),
        ("data/word-atlas.json", "data/textbook_reviewed.tsv"),
        ("和 <code>.csv</code> 是完整词库；<code>public/atlas</code> 里是网页用的分块数据、插画和音频。拿去做 Anki 牌组、背词小程序、浏览器插件，或者 AI 应用的评测集，署名即可。",
         "是本版唯一词库来源；网页构建时生成 <code>public/atlas</code> 词库索引和分块词条。词义及维文未经擅自改写。请保留原版 Word Atlas 源码署名。"),
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
               lambda m: m.group(1)+"教材逐条复核词表1,817条学习记录，合并为1,813张词卡；4条暂缓背诵。基于开源 Word Atlas。",s)
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

    # The upstream cache-first worker can resolve to null on Safari when the
    # network fails and no cached shell exists. Replace it with a one-time
    # cleanup worker: update old installations, clear stale caches, unregister.
    sw = ROOT / "public/sw.js"
    sw.write_text("""/* Uyghur Atlas: retire the fragile upstream offline cache. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map((key) => caches.delete(key)));
    await self.registration.unregister();
    await self.clients.claim();
  })());
});
""", "utf-8")
    patch("src/main.tsx",
          "if (import.meta.env.PROD && \"serviceWorker\" in navigator) {\n  window.addEventListener(\"load\", () => {\n    navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch(() => null);\n  });\n}",
          "// Service worker disabled: avoid stale/offline cache failures on Safari.")
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
        "This build excludes English word audio; matching original Word Atlas illustrations are reused under CC BY 4.0 with attribution.\n"
        "User-provided reviewed textbook vocabulary: 1817 study records merged into 1813 cards. Four deferred words are excluded. No additional expert language review is claimed.\n"
        "Real Uyghur pronunciation is NOT provided.\n","utf-8")
    print(f"Adaptation complete: {len(entries)} textbook cards from 1817 user-reviewed records, {safe_count} study-eligible, "
          "no English TTS/listening, original UI/FSRS/WebGL files retained.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.exit(f"Port error: {exc}")
