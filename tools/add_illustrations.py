#!/usr/bin/env python3
"""Attach meaning-matched CC BY 4.0 illustrations from original Word Atlas.
Uses ONLY Chinese glosses that exactly overlap a sense in the user-reviewed Uyghur glossary.
Never back-translates an uncertain Uyghur entry to guess a picture.
Keeps unmatched cards image-free until a purposeful illustration is available.
"""
from __future__ import annotations
import concurrent.futures, json, re, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
ATLAS=ROOT/"upstream/public/atlas"
ORIGINAL="https://raw.githubusercontent.com/designfuchen/word-atlas/main/public/atlas"
OUT=ATLAS/"image-attributions.json"

# Single-character Chinese glosses are too ambiguous except for a tightly
# defined concrete concept with a visually unambiguous English headword.
CONCRETE={
 "马":"horse","书":"book","水":"water","火":"fire","牛":"cow",
 "鸟":"bird","猫":"cat","狗":"dog","鱼":"fish","山":"mountain",
 "树":"tree","草":"grass","茶":"tea","手":"hand","耳":"ear",
 "眼":"eye","鼻":"nose","嘴":"mouth","车":"car","床":"bed",
 "桥":"bridge","云":"cloud","花":"flower","雨":"rain","雪":"snow"
}
# Carefully curated near-synonyms. Each is an exact Chinese sense from the
# reviewed textbook mapped to a specific original English headword. Do NOT
# use arbitrary substring matching: "六十五" is not "六十", "长城"
# is not any wall, and "山脚" is not a human foot.
# Missing original headwords are skipped, never guessed.
SEMANTIC_PAIRS = """
人|person
人们|people
人群|crowd
成年人|adult
男人|man
女人|woman
男孩|boy
女孩|girl
姑娘|girl
孩子|child
小孩|child
青年|youth
老人|elderly
父母|parent
哥哥|brother
弟弟|brother
姐姐|sister
妹妹|sister
爷爷|grandfather
外公|grandfather
奶奶|grandmother
外婆|grandmother
厨师|chef
教师|teacher
老师|teacher
高等院校|university
学府|university
正教授|professor
教授|professor
作者|author
笔者|writer
劳动者|laborer
领导|leader
领导人|leader
医生|doctor
身体各部位|body
肌体|body
胃|stomach
脚|foot
鞋|shoe
球|ball
墙|wall
灯|lamp
水桶|bucket
碗|bowl
瓷碗|bowl
菜|vegetable
凉菜|salad
烟|cigarette
烟草|tobacco
香烟|cigarette
麦穗|wheat
大米|rice
饭|rice
抓饭|rice
小圆馕|bread
馕|bread
烤馕|bread
汤|soup
点心|dessert
甜点|dessert
银币|coin
银元|coin
金子|gold
钱|money
财富|wealth
财富源泉|wealth
金属|metal
铁|iron
砖|brick
泥|mud
土地|land
山|mountain
河|river
风|wind
大风|wind
暴风|storm
白色|white
黑色|black
红色|red
黄的|yellow
黄|yellow
淡黄|yellow
晴|sunny
晴朗|sunny
凉爽|cool
浅|shallow
快速|fast
急速|fast
赶快|quickly
低|low
矮|short
高|high
大|big
巨大|huge
重大|major
小|small
少|few
多|many
多余|redundant
一|one
三|three
四|four
百万|million
一百万|million
第一|first
昨天|yesterday
明天|tomorrow
今天|today
现在|now
将来|future
未来|future
早晨|morning
早上|morning
早晨的|morning
下午|afternoon
中午|noon
晚上|evening
夜晚|night
那|that
那样的|such
她们|they
他们|they
做|perform
给|give
来|come
拿|take
带走|take
送去|send
带去|lead
领去|lead
领着去|lead
送达|deliver
听|listen
听见|hear
看|look
看见|see
说|say
叫|call
读|read
写|write
问|ask
切|cut
剁|chop
拉|pull
抓|grab
握|hold
拿|take
擦|wipe
吸|suck
画|draw
唱歌|sing
发音|pronounce
高兴|cheerful
愉快|cheerful
快乐|cheerful
满意|satisfied
容易|easy
难|difficult
困难|difficult
漂亮|pretty
好看|beautiful
优秀|excellent
优良|excellent
优异|excellent
好|good
坏的|bad
积极|positive
主动|active
忙的|busy
忙|busy
忙碌|busy
详细|detailed
仔细|careful
进步|progress
延伸|extend
继续|continue
开始|start
结束|end
完成|finish
区别|distinguish
划分|divide
分解|decompose
分泌|secrete
调查|investigate
研究|research
进修|study
学习|study
教育|education
体育|sport
体育运动|sport
毕业|graduation
学校|school
课文|text
文章|article
语言|language
物理|physics
数学|mathematics
地理|geography
历史|history
诗|poem
词|word
词语|word
字|letter
本子|notebook
信|letter
信件|letter
图画|picture
图像|image
书籍|book
报纸|newspaper
药|medicine
药材|medicine
药学|pharmacy
健康|health
组织|organization
机构|organization
政府|government
公共|public
公众|public
群众|people
政治|politics
国家|country
自治区|region
地区|region
城市|city
首都|capital
世界|world
外国人|foreigner
阿拉伯|arabian
朝鲜|korean
田野|field
建筑|building
建筑物|building
商店|shop
市场|market
百货|goods
邮电局|post-office
邮局|post
车|car
汽车|car
公共汽车|bus
火车|train
飞机|plane
广播|broadcast
电话|telephone
衣服|clothes
服装|clothes
帽子|hat
围脖|scarf
胡须|beard
胡子|beard
款式|style
样式|style
银币|coin
零钱|change
队|team
队伍|team
队列|row
前|front
前面|front
前边|front
中间|middle
在中间|middle
之间|between
旁边|beside
左|left
右|right
东|east
南|south
西|west
北|north
上面|above
下面|below
底下|under
外|outside
外面|outside
那里|there
很久|long
长时间|long
不久|soon
相继|successive
陆续|successive
连续|continuous
不断|continuous
方的|square
正方形的|square
直接|direct
勤劳|industrious
勤奋|diligent
友好|friendly
勇敢|brave
害怕|afraid
艰苦|hardship
保留|keep
保存|save
流|flow
淌|flow
漏|leak
热销|best-selling
畅销|best-selling
自然|nature
很自然地|naturally
湿|wet
干燥|dry
强壮|strong
力量|strength
身体|body
话|word
句子|sentence
造句|sentence
句型|pattern
数字|number
数|number
数词|numeral
次序|order
篇|article
张|sheet
片|piece
块|piece
棵|tree
株|plant
手提包|handbag
书包|bag
背包|backpack
包|bag
东西|thing
事情|matter
时间|time
日|day
号|date
周|week
星期|week
月|month
年|year
季节|season
一顿饭|meal
一顿|meal
雪|snow
水|water
土|soil
土壤|soil
麦子|wheat
香皂|soap
伞|umbrella
鲜花|flower
花|flower
花园|garden
左边|left
右边|right
乌黑色的|black
大自然|nature
到达|arrive
进入|enter
离开|leave
上饭|serve
上菜|serve
回答|answer
询问|ask
您好|hello
请|please
"""
SEMANTIC_TO_ORIGINAL = dict(
    line.split("|", 1) for line in SEMANTIC_PAIRS.strip().splitlines()
    if "|" in line
)
def normalize_gloss(s):
    """Only grammatical endings: 容易的/容易, 在昨天/昨天."""
    s = s.strip()
    if len(s) >= 3 and s.endswith(("的", "地")):
        s = s[:-1]
    if len(s) >= 3 and s.startswith("在") and "…" not in s and "..." not in s:
        s = s[1:]
    return s

POSET={"n","v","adj","adv","num"}
def clean(s):
    return re.sub(r"\s+","",re.sub(r"^(?:(?:n|v|adj|adv|prep|pron|conj|num|interj)\.)\s*","",s,flags=re.I))
def senses(s):
    s=re.sub("[①②③④⑤⑥⑦⑧⑨⑩]","；",s)
    ss=[clean(re.sub(r"（[^）]*）|\([^)]*\)","",w)).strip("；、，,.。！？") for w in re.split(r"[；;,，、\n]",s)]
    return [q for q in ss if q]
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"UyghurAtlas-licensed-illustration-adapter/1.0"})
    with urllib.request.urlopen(req,timeout=55) as res:return res.read()
def download_match(item):
    uid,english,uyu,zh,match_type,matched_sense=item
    images={}
    for size in ("img","thumb"):
        url=f"{ORIGINAL}/{size}/{english}.webp"
        try:
            blob=fetch(url)
            if blob[:4]!=b"RIFF" or blob[8:12]!=b"WEBP":raise ValueError("not a WebP image")
            file=ATLAS/size/f"{uid}.webp"
            file.write_bytes(blob)
            images[size]=len(blob)
        except Exception as exc:
            print("MISSING_ILLUSTRATION",english,size,str(exc)[:140],flush=True)
            return None
    return {"word_id":uid,"uy":uyu,"zh":zh,"original_word":english,
            "match_type":match_type,"matched_sense":matched_sense,
            "source":f"https://github.com/designfuchen/word-atlas/blob/main/public/atlas/img/{english}.webp",
            "filesizes":images}

def main():
    if not (ATLAS/"index.json").exists():raise RuntimeError("Run AFTER port_uyghur.py")
    idx=json.loads((ATLAS/"index.json").read_text("utf8"))
    original=json.loads(fetch(ORIGINAL+"/index.json"))
    lookup=defaultdict(list)
    variant_lookup=defaultdict(list)
    original_by_id={}
    for r in original["words"]:
        english,_,original_zh,_,level,topic,_=r
        original_by_id[english]=r
        for term in senses(original_zh):
            if len(term)>=2:
                lookup[term].append(r)
                variant=normalize_gloss(term)
                if len(variant)>=2 and variant!=term:
                    variant_lookup[variant].append(r)
    def preferred(candidates,uy):
        candidates=[r for r in candidates if r and
                    (not uy.endswith("-") or r[2].startswith("v."))]
        return min(candidates,key=lambda r:(r[4],0 if r[2].startswith("n.") else 1,len(r[1]))) if candidates else None
    targets=[]
    stats={"exact":0,"grammar_variant":0,"curated_synonym":0}
    for row in idx["words"]:
        uid,uy,zh,*_=row
        raw=senses(zh)
        chosen=None
        match_type=None
        matched_sense=None
        # Prefer literal meaning matches, even if they occur in a later sense.
        for term in raw:
            candidates=lookup.get(term,[])
            if len(term)==1 and term in CONCRETE:
                candidates=[original_by_id.get(CONCRETE[term])]
            chosen=preferred(candidates,uy)
            if chosen:
                match_type="exact"
                matched_sense=term
                break
        # Explicitly reviewed near-synonyms and concrete parent categories.
        if not chosen:
            for term in raw:
                english=SEMANTIC_TO_ORIGINAL.get(term)
                chosen=preferred([original_by_id.get(english)] if english else [],uy)
                if chosen:
                    match_type="curated_synonym"
                    matched_sense=term
                    break
        # Inflection variants: "容易" = "容易的", "明天" = "在明天".
        # No generic Chinese-substring matching, which causes false pictures.
        if not chosen:
            for term in raw:
                if len(normalize_gloss(term))<2:continue
                chosen=preferred(variant_lookup.get(normalize_gloss(term),[]),uy)
                if chosen:
                    match_type="grammar_variant"
                    matched_sense=term
                    break
        if chosen:
            targets.append((uid,chosen[0],uy,zh,match_type,matched_sense))
            stats[match_type]+=1
    print("MATCH_METHODS",stats,flush=True)
    print("MEANING_ALIGNED_TARGETS",len(targets),"OF",len(idx["words"]),flush=True)
    print("FIRST_MATCHES",targets[:22],flush=True)
    print("FIRST_UNMATCHED",[(r[1],r[2]) for r in idx["words"] if r[0] not in {t[0] for t in targets}][:22],flush=True)
    for p in ("img","thumb"):(ATLAS/p).mkdir(exist_ok=True)
    matched=[]
    # Limit concurrent requests to reduce load on upstream Github CDN.
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        for result in pool.map(download_match,targets):
            if result: matched.append(result)
    by_id={r["word_id"] for r in matched}
    for row in idx["words"]:
        if row[0] in by_id:row[6]=row[6]|1
    idx["illustrated"]=len(matched)
    (ATLAS/"index.json").write_text(json.dumps(idx,ensure_ascii=False,separators=(",",":")),"utf8")
    entries_dir=ATLAS/"entries"
    for path in sorted(entries_dir.glob("*.json"),key=lambda p:int(p.stem)):
        arr=json.loads(path.read_text("utf8"))
        for e in arr:
            if e["id"] in by_id:e["m"]=e.get("m",0)|1
        path.write_text(json.dumps(arr,ensure_ascii=False,separators=(",",":")),"utf8")
    OUT.write_text(json.dumps({
        "license":"CC BY 4.0","license_url":"https://creativecommons.org/licenses/by/4.0/",
        "credit":"Word Atlas contributors — CC BY 4.0",
        "source":"https://github.com/designfuchen/word-atlas",
        "modification":"Original illustrations unchanged, matched by exact Chinese sense, grammatical variant or curated near-synonym; attribution includes match method",
        "count":len(matched),
        "mappings":matched
    },ensure_ascii=False,indent=2),"utf8")
    print("ILLUSTRATIONS_READY",len(matched),"OF",len(idx["words"]),flush=True)
    if len(matched)<140:
        raise RuntimeError("Insufficient successful matches; release would misrepresent coverage")

if __name__=="__main__":main()
