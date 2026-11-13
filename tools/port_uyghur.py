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


# Uyghur Latin Yéziqi (ULY). An orthographic transliteration, not phonetic IPA.
ULY = {
    "ا":"a", "ە":"e", "و":"o", "ۇ":"u", "ۆ":"ö", "ۈ":"ü", "ې":"ë",
    "ى":"i", "ي":"y", "ب":"b", "پ":"p", "ت":"t", "ج":"j", "چ":"ch",
    "خ":"x", "د":"d", "ر":"r", "ز":"z", "ژ":"zh", "س":"s", "ش":"sh",
    "غ":"gh", "ف":"f", "ق":"q", "ك":"k", "گ":"g", "ڭ":"ng", "ل":"l",
    "م":"m", "ن":"n", "ھ":"h", "ۋ":"w",
}
ULY_VOWELS = set("اەوۇۆۈېى")

def to_uly(value: str) -> str:
    """Convert textbook Uyghur spelling to ULY; preserve spaces and marks."""
    out = []
    for i, ch in enumerate(value):
        if ch == "ئ":
            # Initial hamza carries a vowel; medial hamza separates vowel syllables.
            if i and value[i-1] not in " \t\n-–—«(." and i+1 < len(value) and value[i+1] in ULY_VOWELS:
                out.append("'")
            continue
        if ch in ULY:
            out.append(ULY[ch])
        elif "\u0600" <= ch <= "\u06ff" and ch != "؛":
            raise ValueError(f"Missing ULY mapping U+{ord(ch):04X} in {value!r}")
        else:
            out.append(ch)
    return "".join(out)


# The original Word Atlas puts easier words before harder ones and varies
# topics within a level. This Uyghur adaptation makes an ESTIMATED
# pedagogical order, NOT measured corpus-frequency ranks or CEFR levels.
# The human-selected core consists only of spellings found in the reviewed
# textbook. Every card retains its immutable tb<original sequence> ID.
CORE_START = """
مەن
سەن
سىز
ئۇ
بىز
بۇ
شۇ
كىم
نېمە
قايسى
قانداق
قاچان
قانچە
نەچچە
نە
بار
ئەمەس
ھەئە
ياق
ياخشى
ياخشىمۇسىز
ئەسسالامۇ ئەلەيكۇم
رەھمەت سىزگە
بىر
ئىككى
تۆت
بەش
ئالتە
يەتتە
ئون
ئادەم
كىشى
ئاتا
ئانا
ئاپا
دادا
دوست
ئۆي
ئائىلە
سۇ
نان
تاماق
ئاش
پۇل
كىتاب
مەكتەپ
ئوقۇغۇچى
خىزمەت
ئىش
بۈگۈن
ئەتە
تۈنۈگۈن
ھازىر
بار-
كەل-
كەت-
قىل-
ئەت-
ئال-
بەر-
يە-
قارا-
ئاڭلا-
دە-
بىل-
ئوقۇ-
ياز-
ئۆگەن-
سۆزلە-
ماڭ-
يۈر-
سېتىۋال-
ياخشى كۆر-
بەك
ناھايىتى
كۆپ
ئاز
كېرەك
لازىم
بىلەن
ۋە
لېكىن
چۈنكى
شۇڭا
ئەگەر
ياكى
يىل
ئاي
ھەپتە
ئوغۇل
قىز
ئۇخلا-
ئويلا-
ئاچ-
ياخشى
يامان
چوڭ
كىچىك
يېڭى
كونا
ئۇزۇن
قىسقا
ماۋۇ
ئاۋۇ
شۇ
ھەر
ھەم
""".strip().splitlines()
CORE_RANK = {word: i for i, word in enumerate(dict.fromkeys(CORE_START))}

# Exact Chinese textbook senses, intentionally not free-form substrings:
# false matches such as "白种人"->"白" or "阿丽亚(女名)"->"人" would be harmful.
COMMON_SENSES = set("""
你 我 您 我们 他 她 它 他们 你们 谁 什么 哪儿 哪里 多少 几 哪 个
这 那 这里 那里 现在 今天 明天 昨天 后天 前天 早晨 早上 中午 晚上
年 月 星期 周 天 小时 分钟 时间 时候 第一 第二
一个 一 二 三 四 五 六 七 八 九 十 百 千 万
有 没有 不是 好 好吧 是 是的 不 是的 不行 也 都 还 很 非常 特别
因为 所以 但是 可是 如果 或者 和 与 跟 一起 每 每个 
吃 喝 走 去 来 看 听 写 读 念 学习 学 做 干 给 拿 买 卖
想 喜欢 爱 需要 要 知道 会 懂 说 说话 讲话 工作 睡觉 跑 
父亲 爸爸 母亲 妈妈 家 家庭 人 朋友 孩子 男人 女人 男 女
水 饭 饭菜 馕 茶 肉 米饭 苹果 水果 书 学校 学生 老师 钱
衣服 鞋 房子 房间 商店 汽车 公共汽车 医院 医生
大 小 多 少 长 短 高 低 新 旧 快 慢 远 近 冷 热
""".split())
USEFUL_SENSES = set("""
欢迎 你好 您好 谢谢 再见 请 对不起 不客气 学习 去年 今年 明年
上午 下午 晚饭 早饭 中饭 课本 读书 同学 课堂 教室 课
问 答 回答 认识 了解 爷爷 奶奶 姐姐 哥哥 弟弟 妹妹
丈夫 妻子 儿子 女儿 名字 名称 生日 姓 宾客 客人
东西 物品 水果 蔬菜 肉 牛奶 面条 拉面 抓饭 鸡蛋 饺子
饭店 餐馆 厨师 美味 好吃 饿 渴 甜 酸 咸
价格 便宜 贵 工厂 市场 公交 地铁 火车 出租车 自行车
路 道路 左 右 里面 外面 上面 下面 前面 后面 旁边 中间
容易 困难 能 可以 应该 开始 结束 停止 继续 见面 回来 出去
健康 身体 耳朵 眼睛 鼻子 嘴 手 脚 头 脸 发烧 生病 感冒
天气 下雨 雪 风 太阳 月亮 花 树 草 河 山
电脑 手机 电话 电视 网络 颜色 黑色 白色 红色 蓝色 黄色
""".split())
# Short grammatical terms are often high-frequency but poor standalone
# visual concepts; retain them, without assigning fabricated CEFR labels.
GRAMMAR_CUES = ("助词","语气词","代词","副词","后缀","词尾","语法","介词","连词")
FORMAL_CUES = (
    "主义","哲学","物理","化学","医学","文学","艺术","思想","理论","学术",
    "制度","国家","社会","经济","政治","科技","政策","法律","民族",
    "学位","学科","自治区","官员","历史","文献","论文","翻译","图书馆",
    "宗教","组织","机构","协会","科研","农业","工业","公民","国际",
)
PROPER_CUES = ("男名","女名","人名","（姓","地名","人名","地理名称")
ADVANCED_PHRASE_CUES = ("成语","熟语","比喻","谚语","俗语","方言","古语")

def learning_senses(text: str) -> list[str]:
    text = re.sub("[①②③④⑤⑥⑦⑧⑨⑩]", "；", text)
    return [x.strip(" ！？。．；,，、：:") for x in re.split(r"[；;,，、／/]", text)
            if x.strip(" ！？。．；,，、：:")]

def learning_topic(row: dict) -> str:
    gloss = "／".join(row["senses"])
    uy = row["uy"]
    terms = learning_senses(gloss)
    if any(re.fullmatch(r"[零一二三四五六七八九十百千万两]+", t) for t in terms):
        return "number"
    if any(x in gloss for x in ("爸爸","妈妈","父亲","母亲","爷爷","奶奶","亲戚","哥哥","姐姐","弟弟","妹妹","朋友","家庭","儿子","女儿")):
        return "family"
    if any(x in gloss for x in ("吃","喝","饭","菜","馕","面","肉","水果","水","茶","饼","包子","厨房","餐","馄饨","烤")):
        return "food"
    if any(x in gloss for x in ("今天","明天","昨天","早上","晚上","小时","分钟","日子","星期","一年","月份","时候","时间")):
        return "time"
    if any(x in gloss for x in ("学校","学生","老师","课","读","写","学习","教授","书","考试","字母","词语")):
        return "education"
    if any(x in gloss for x in ("公交","汽车","火车","交通","机场","飞机","公路","走","车站","路","旅行","旅馆")):
        return "travel"
    if any(x in gloss for x in ("天气","植物","动物","鸟","山","河","湖","树","花","风","雨","雪")):
        return "nature"
    if uy.endswith("-"):
        return "action"
    if any(x in gloss for x in ("政府","工作","公司","工业","机构","社会","政治","职业","研究","经济")):
        return "formal"
    return "daily"

def learning_difficulty(row: dict) -> tuple[int, int]:
    """Heuristic rank: basic use first, complex/rare/proper names later.

    No independent Uyghur frequency corpus or expert CEFR labels are claimed.
    Sorting ties by source sequence makes re-builds deterministic.
    """
    uy = row["uy"]
    zh = " ／ ".join(row["senses"])
    meanings = learning_senses(zh)
    source_seq = row["seq"]
    if uy in CORE_RANK:
        return (-10000 + CORE_RANK[uy], source_seq)

    letters = len(re.findall(r"[\u0600-\u06ff]", uy))
    token_count = len(uy.split())
    # Long compound expressions are substantially more difficult to memorize.
    score = 90 + letters * 2.0 + max(0, token_count - 1) * 20
    score += (len(meanings) - 1) * 2.5
    if uy.endswith("-"):
        score -= 7 # stems of everyday verbs are useful early
    if any(m in COMMON_SENSES for m in meanings):
        score -= 75
    elif any(m in USEFUL_SENSES for m in meanings):
        score -= 47
    if any(m in zh for m in PROPER_CUES):
        score += 170
    if any(m in zh for m in ADVANCED_PHRASE_CUES):
        score += 90
    if any(x in zh for x in FORMAL_CUES):
        score += 33
    if any(x in zh for x in GRAMMAR_CUES):
        score += 26
    # Proper-noun descriptions and literary quotations require contexts.
    if "《" in zh or "»" in uy or "«" in uy:
        score += 110
    if any(ch.isdigit() for ch in uy):
        score += 45
    if len(zh) > 45:
        score += 20
    return (int(score * 10), source_seq)

def interleave_learning_topics(rows: list[dict], window: int = 36) -> list[dict]:
    """Mix topic buckets locally while keeping overall difficulty progression."""
    from collections import defaultdict
    mixed = []
    for start in range(0, len(rows), window):
        chunk = rows[start:start + window]
        buckets = defaultdict(list)
        for row in chunk:
            buckets[learning_topic(row)].append(row)
        last = None
        while any(buckets.values()):
            available = [(len(v), k) for k, v in buckets.items() if v]
            # Prefer the biggest topic bucket but avoid immediate repetitions.
            available.sort(key=lambda t: (-t[0], t[1]))
            topic = next((k for _, k in available if k != last), available[0][1])
            mixed.append(buckets[topic].pop(0))
            last = topic
    return mixed

def order_learning_path(dataset: list[dict]) -> list[dict]:
    ranked = sorted(dataset, key=learning_difficulty)
    # Six stages each contain three daily lessons. The first 17 lessons
    # have 101 words, and the eighteenth has 96: 1,813 words in total.
    # Keep the 101-word boundaries aligned with 6 stages.
    sizes = [303] * 5 + [len(ranked) - 303 * 5]
    out = []
    start = 0
    for size in sizes:
        out.extend(interleave_learning_topics(ranked[start:start + size]))
        start += size
    assert len(out) == len(dataset)
    assert {r["seq"] for r in out} == {r["seq"] for r in dataset}
    return out

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
    # Preserve tbXXXX card IDs so prior study scores, bookmarks and review
    # scheduling in iPhone Safari remain attached to the SAME words.
    dataset=order_learning_path(dataset)
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
        latin=to_uly(uy)
        if not latin:raise RuntimeError(f"Missing ULY transliteration for {uy}")
        topic=inferred_topic(joined)
        wid=f"tb{row['seq']:04d}"
        # Six equal-sized tiers in estimated daily usefulness/difficulty order.
        level=min(5, i//303)
        if topic not in topics:topic="daily"
        index_rows.append([wid,uy,joined,latin,level,topics.index(topic),32])
        provenance="；".join(f"原表{n}·教材第{p}页" for n,p,_ in row["sources"])
        entries.append({
            "id":wid,"w":uy,"uk":latin,"us":"",
            "senses":[{"pos":"教材释义","zh":meaning,"en":""} for meaning in row["senses"]],
            "ex":[],"col":[],"fam":[],"syn":[],"ant":[],
            "tip":("词尾 - 是教材的动词词干标记，不发音。拉丁转写按 ULY 规则自动生成（非 IPA）。"
                   if uy.endswith("-") else
                   "拉丁转写按 ULY 规则自动生成，帮助认字；不是 IPA 音标，未经过真人逐词核音。"),
            "cefr":f"第{level+1}组","topic":topic,"m":32,
            "note":"来自用户提供的逐条复核教材词表；"+provenance+
                   "。学习分组按基础实用词、词形复杂度、词义领域及专有名词等估计排序；并非正式CEFR评级。",
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
          '<div style={{padding:"12px 16px",marginBottom:16,borderRadius:12,background:"var(--surface, #f5f0e5)",fontSize:13,lineHeight:1.6}} role="note">已导入1,817条教材逐条复核记录；4组同形异义合并成1,813张词卡。4条未决词单独保留、暂不背诵。六组按常用程度与难度估计排序，同组穿插话题；不是官方CEFR评级。</div>\n      <header className="greet">')

    # Emulate the original easy-to-hard path, but DO NOT claim Uyghur CEFR certification.
    patch("src/pages/Today.tsx",
          "学习路线 · 从 A1 到 C2",
          "学习路线 · 按实用与难度分六组")
    patch("src/pages/Today.tsx",
          'const NAMES = ["入门", "基础", "进阶", "中高", "高级", "精通"];',
          'const NAMES = ["入门", "基础", "日常", "拓展", "进阶", "专题"];')
    # Daily lesson target: keep all existing choices and add 100.
    # The setting parser already accepts integers from 0 to 100.
    patch("src/pages/Me.tsx",
          "[5, 10, 15, 20, 30].map((n) => (",
          "[5, 10, 15, 20, 30, 100].map((n) => (")
    # Wrapping lets the 100-word button be visible on iPhone Safari.
    patch("src/pages/Me.tsx",
          '<Field label="每日新词" hint="复习不设上限，算法只安排快要遗忘的词。">\n            <div className="segmented">',
          '<Field label="每日新词" hint="每天最多可选100个新词；到期复习另算。">\n            <div className="segmented" style={{flexWrap:"wrap",borderRadius:16}}>')
    # Restore a proper first-stage entry point: upstream onboarding still
    # contains IELTS/CEFR labels, which are invalid for the Uyghur deck.
    patch("src/pages/Onboarding.tsx",
          'const LEVELS = [\n  ["A2", "基础", "日常词还不太稳"],\n  ["B1", "进阶", "目标 5.5 – 6 分"],\n  ["B2", "中高", "目标 6.5 – 7 分"],\n  ["C1", "高级", "冲刺 7.5 分以上"],\n];',
          'const LEVELS = [\n  ["第1组", "入门", "最基础的实用词"],\n  ["第2组", "基础", "常见日常用语"],\n  ["第3组", "日常", "生活与交流词汇"],\n  ["第4组", "拓展", "更丰富的表达"],\n  ["第5组", "进阶", "较复杂的词义"],\n  ["第6组", "专题", "书面语和专门词"],\n];')
    patch("src/pages/Onboarding.tsx",
          'const [level, setLevel] = useState(1);',
          'const [level, setLevel] = useState(0);')
    patch("src/pages/Onboarding.tsx",
          "[5, 10, 15, 20].map((n) => (",
          "[5, 10, 15, 20, 30, 100].map((n) => (")
    patch("src/pages/Onboarding.tsx",
          '<div className="segmented segmented-wide">',
          '<div className="segmented segmented-wide" style={{flexWrap:"wrap",borderRadius:16}}>')


    # A self-paced 18-day path that preserves the original 6 stages.
    # Exactly 17 lessons of 101 cards plus one of 96. Every card is
    # selected by stable ID, so existing FSRS states and bookmarks carry over.
    patch("src/pages/Today.tsx",
          "        <LevelPath />",
          "        <ChallengePath />\n        <LevelPath />")
    challenge_component = r"""
function ChallengePath() {
  const atlas = useAtlas();
  const progress = useStore((s) => s.progress);
  const settings = useStore((s) => s.settings);
  const active = progress.session && !progress.session.finished;
  const stageNames = ["入门", "基础", "日常", "拓展", "进阶", "专题"];
  const lessons = useMemo(
    () => Array.from({ length: 18 }, (_, day) =>
      atlas.words.slice(day * 101, Math.min((day + 1) * 101, atlas.words.length))),
    [atlas]
  );
  const learned = lessons.map((group) => group.reduce(
    (n, w) => n + (progress.cards[w.id] ? 1 : 0), 0
  ));
  const totalSeen = learned.reduce((a, b) => a + b, 0);
  const startLesson = (day: number) => {
    if (active) return;
    const ids = lessons[day].map((w) => w.id);
    if (!ids.length) return;
    const session = buildSession(atlas, progress, settings, { ids });
    if (!session.steps.length) return;
    store.progress((p) => ({ ...p, session }));
    if (settings.sfx) void cue("start");
    go({ page: "learn" });
  };

  return (
    <section className="panel uy-challenge" aria-label="18天词汇学习挑战">
      <div className="panel-head">
        <div>
          <h3 className="eyebrow">18 天学习挑战</h3>
          <p className="uy-challenge-subtitle">6 个难度阶段 · 每阶段 3 关 · 新词由易到难</p>
        </div>
        <span className="uy-challenge-total">{totalSeen} / {atlas.count} 已学</span>
      </div>
      <p className="uy-challenge-note">
        每关约 100 词，前 17 关各 101 词，最后一关 96 词。可以暂停、分几天完成；
        已学不等于记牢，系统仍会安排间隔复习。
      </p>
      {active && (
        <div className="uy-challenge-active">
          <span>已有进行中的旅程。完成或继续当前旅程后，再选择其他关卡。</span>
          <button className="btn btn-primary" onClick={() => go({ page: "learn" })}>继续旅程</button>
          <button className="btn btn-ghost" onClick={() => {
            if (window.confirm("结束当前未完成的旅程并重新选关？已经记录的学习进度会保留。")) {
              store.progress((p) => ({ ...p, session: null }));
            }
          }}>重新选关</button>
        </div>
      )}
      <div className="uy-challenge-stages">
        {stageNames.map((stage, stageIndex) => (
          <div className="uy-challenge-stage" key={stage}>
            <div className="uy-challenge-stage-title">
              <b>阶段 {stageIndex + 1} · {stage}</b>
              <small>{lessons.slice(stageIndex * 3, stageIndex * 3 + 3)
                .reduce((n, group) => n + group.length, 0)} 词</small>
            </div>
            <div className="uy-challenge-grid">
              {[0, 1, 2].map((offset) => {
                const day = stageIndex * 3 + offset;
                const group = lessons[day];
                const seen = learned[day];
                const complete = seen === group.length;
                return (
                  <button
                    key={day}
                    type="button"
                    disabled={!!active || group.length === 0}
                    onClick={() => startLesson(day)}
                    className={"uy-challenge-day" + (complete ? " is-complete" : "")}
                    aria-label={"第" + (day + 1) + "关，" + group.length + "词，已学" + seen + "词"}
                  >
                    <span className="uy-challenge-day-title">第 {day + 1} 关</span>
                    <b>{seen}<small> / {group.length}</small></b>
                    <span className="uy-challenge-track"><i style={{ width: (group.length ? seen / group.length * 100 : 0) + "%" }} /></span>
                    <span className="uy-challenge-action">{complete ? "巩固复习" : seen ? "继续学习" : "开始学习"}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

"""
    patch("src/pages/Today.tsx", "function LevelPath() {", challenge_component + "function LevelPath() {")

    challenge_css = r"""
/* Uyghur 18-day self-paced learning path. Touch-friendly on Safari. */
.uy-challenge { grid-column:1 / -1; margin-top: 20px; }
.uy-challenge .panel-head { display:flex; gap:12px; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; }
.uy-challenge-subtitle { font-size:14px; font-weight:600; margin:6px 0 0; color:var(--ink-2); }
.uy-challenge-total { font-size:13px; font-weight:700; color:var(--terra-ink); white-space:nowrap; }
.uy-challenge-note { font-size:13px; line-height:1.7; color:var(--ink-3); margin:4px 0 16px; }
.uy-challenge-active { padding:12px; margin-bottom:16px; display:flex; flex-wrap:wrap; align-items:center; gap:10px; background:var(--paper-2); border-radius:12px; font-size:13px; }
.uy-challenge-stages { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
.uy-challenge-stage { padding:14px; border:1px solid var(--line); border-radius:16px; background:var(--card-2); min-width:0; }
.uy-challenge-stage-title { display:flex; justify-content:space-between; flex-wrap:wrap; align-items:baseline; gap:8px; margin-bottom:12px; font-size:14px; color:var(--ink); }
.uy-challenge-stage-title small { font-size:12px; color:var(--ink-3); }
.uy-challenge-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; }
.uy-challenge-day { display:flex; flex-direction:column; align-items:stretch; text-align:left; min-height:116px; min-width:0; padding:11px 8px; border-radius:12px; border:1px solid var(--line); background:var(--card); color:var(--ink); transition:border-color .2s ease, transform .2s ease; }
.uy-challenge-day:hover:not(:disabled),.uy-challenge-day:focus-visible { border-color:var(--terra); transform:translateY(-1px); }
.uy-challenge-day:disabled { opacity:.65; cursor:not-allowed; }
.uy-challenge-day-title { font-size:13px; font-weight:650; }
.uy-challenge-day b { font-size:19px; margin-top:6px; font-variant-numeric:tabular-nums; }
.uy-challenge-day b small { font-size:11px; font-weight:500; color:var(--ink-3); }
.uy-challenge-track { height:5px; width:100%; display:block; margin:9px 0 7px; border-radius:99px; overflow:hidden; background:var(--paper-3); }
.uy-challenge-track i { display:block; height:100%; border-radius:99px; background:var(--sage); }
.uy-challenge-action { font-size:11px; color:var(--ink-3); }
.uy-challenge-day.is-complete { border-color:var(--sage); }
@media(max-width:820px) { .uy-challenge-stages { grid-template-columns:1fr; } }
@media(max-width:420px) { .uy-challenge-stage { padding:12px; } .uy-challenge-grid { gap:6px; } .uy-challenge-day { padding:10px 7px; min-height:110px; } .uy-challenge-day-title { font-size:12px; } .uy-challenge-day b { font-size:17px; } }
"""
    css_path=ROOT/"src/styles/app.css"
    css_path.write_text(css_path.read_text("utf-8") + "\n" + challenge_css, "utf-8")

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

    # The inherited UK/US toggle refers to English; Uyghur has a single
    # verified language audio channel in our pilot, regardless of that setting.
    patch("src/ui/EntryView.tsx",
          'url={atlas.audio(refw, acc)}',
          'url={atlas.audio(refw, "uk")}')
    patch("src/ui/EntryView.tsx",
          '<em>{label}</em>',
          '<em>{atlas.audio(refw, "uk") ? "AI合成" : label}</em>')
    patch("src/pages/Learn.tsx",
          'atlas.audio(entry, settings.accent)',
          'atlas.audio(entry, "uk")')
    patch("src/pages/Atlas.tsx",
          'url={atlas.audio(w, accent)}',
          'url={atlas.audio(w, "uk")}')


    patch("src/pages/Learn.tsx",
          'className="headword" lang="en"', 'className="headword" lang="ug" dir="rtl"')

    # Show ULY on catalog tiles, in lists, and in search.
    patch("src/pages/Atlas.tsx",
          'const rowH = cell + (width < 560 ? 62 : 74) + gap;',
          'const rowH = cell + (width < 560 ? 84 : 96) + gap;')
    patch("src/pages/Atlas.tsx",
          '<span className="tile-word" lang="en"',
          '<span className="tile-word" lang="ug" dir="rtl"')
    patch("src/pages/Atlas.tsx",
          '<span className="tile-zh">{w.zh}</span>',
          '<span className="tile-uly" lang="ug-Latn">{w.ipa}</span>\n              <span className="tile-zh">{w.zh}</span>')
    patch("src/pages/Atlas.tsx",
          'className="row-word" lang="en"',
          'className="row-word" lang="ug" dir="rtl"')
    patch("src/ui/Palette.tsx",
          'else if (word.includes(q)) score = 200 - word.indexOf(q) - word.length;',
          '''else if (word.includes(q)) score = 200 - word.indexOf(q) - word.length;
      else if (w.ipa.toLowerCase() === q) score = 950;
      else if (w.ipa.toLowerCase().startsWith(q)) score = 450 - w.ipa.length;
      else if (w.ipa.toLowerCase().includes(q)) score = 150 - w.ipa.length;''')
    patch("src/ui/Palette.tsx",
          'placeholder="搜索英文或中文，例如 serendipity / 环境"',
          'placeholder="搜索维语、拉丁转写或中文，例如 apa / 母亲"')
    patch("src/ui/Palette.tsx",
          'className="palette-word" lang="en"',
          'className="palette-word" lang="ug" dir="rtl"')
    patch("src/ui/Palette.tsx",
          '<span className="palette-zh">{w.zh}</span>',
          '<span className="palette-zh">{w.ipa} · {w.zh}</span>')
    patch("src/ui/Palette.tsx",
          '支持英文前缀与中文释义搜索',
          '支持维吾尔文、ULY 转写与中文释义搜索')

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
         "本版采用用户提供的维吾尔语教材逐条复核词表：原表1,817条背诵记录，合并4组同形异义后是 {atlas.count.toLocaleString()} 张词卡，全部可以进行学习与复习。原表另有4条未决词已排除；按词义复用原版许可插画，另补绘部分新图；不提供未经核实的维语录音和例句。"),
        ("它免费、开源、无需注册。代码用 MIT，词库用 CC BY 4.0，谁都可以拿去用。",
         "程序沿用原版 MIT 代码许可；复用插画署名 Word Atlas contributors — CC BY 4.0（https://creativecommons.org/licenses/by/4.0/），本版重新按维语释义配图，并增加新插画。学习进度存于本机浏览器。"),
        ("每个词都有一幅画，画的就是第一句例句里发生的事。",
         "按教材复核版的维文与中文释义学习；只有确实能对应词义的原版插画或新生成插画才配到词卡上。"),
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
      .uyghur-translit,.row-ipa{direction:ltr;unicode-bidi:plaintext}
      .tile-uly{grid-column:1 / -1;direction:ltr;unicode-bidi:plaintext;display:block;font:500 11px/1.15 system-ui,sans-serif;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px}
      .tile-word,.row-word{font-family:"Geeza Pro","Noto Naskh Arabic","Noto Sans Arabic",serif}
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
