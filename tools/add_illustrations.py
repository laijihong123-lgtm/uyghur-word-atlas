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
    uid,english,uyu,zh=item
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
            "source":f"https://github.com/designfuchen/word-atlas/blob/main/public/atlas/img/{english}.webp",
            "filesizes":images}

def main():
    if not (ATLAS/"index.json").exists():raise RuntimeError("Run AFTER port_uyghur.py")
    idx=json.loads((ATLAS/"index.json").read_text("utf8"))
    original=json.loads(fetch(ORIGINAL+"/index.json"))
    lookup=defaultdict(list)
    original_by_id={}
    for r in original["words"]:
        english,_,zh,_,level,topic,_=r
        original_by_id[english]=r
        for term in senses(zh):
            if len(term)>=2:
                lookup[term].append(r)
    targets=[]
    for row in idx["words"]:
        uid,uy,zh,*_=row
        raw=senses(zh)
        original=None
        # FIRST sense is the primary meaning; allow later senses only if
        # the first has no suitable English target.
        for order,term in enumerate(raw):
            c=lookup.get(term,[])
            if len(term)==1 and term in CONCRETE:
                src=original_by_id.get(CONCRETE[term])
                c=[src] if src else []
            # Reject misleading same-gloss English noun images for Uyghur verb stems.
            if uy.endswith("-"):
                c=[r for r in c if r[2].startswith("v.")]
            elif len(c)>1:
                # Prefer everyday, direct lexical labels over unusual advanced senses
                c.sort(key=lambda r:(r[4],0 if r[2].startswith("n.") else 1,len(r[1])))
            if not c:continue
            original=c[0];break
        if original:
            targets.append((uid,original[0],uy,zh))
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
        "modification":"Illustrations reassigned to Uyghur words with corresponding Chinese glosses; originals unchanged",
        "count":len(matched),
        "mappings":matched
    },ensure_ascii=False,indent=2),"utf8")
    print("ILLUSTRATIONS_READY",len(matched),"OF",len(idx["words"]),flush=True)
    if len(matched)<140:
        raise RuntimeError("Insufficient successful matches; release would misrepresent coverage")

if __name__=="__main__":main()
