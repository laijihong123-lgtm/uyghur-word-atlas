#!/usr/bin/env python3
"""Independent reference comparison of the LIVE Uyghur Atlas word list.

Outputs evidence, NOT a certification. A spelling missing from a source does not
mean incorrect; dictionary meanings are often polysemous, and a literal string
match is not a trustworthy semantic evaluation.
"""
import csv, io, json, re, struct, tarfile, urllib.request
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

OUT=Path("audit_outputs"); OUT.mkdir(exist_ok=True)
BASE="https://laijihong123-lgtm.github.io/uyghur-word-atlas/"
SOURCES={
 "imla_2009":"https://huggingface.co/datasets/UyghurReferenceTexts/uyghur-headword-lists/resolve/main/data/imla_lughiti_2009/imla_lughiti_2009_headwords.tsv",
 "imla_2009_sub":"https://huggingface.co/datasets/UyghurReferenceTexts/uyghur-headword-lists/resolve/main/data/imla_lughiti_2009/imla_lughiti_2009_subentries.tsv",
 "izah_2011_1":"https://huggingface.co/datasets/UyghurReferenceTexts/uyghur-headword-lists/resolve/main/data/izahliq_lughet_2011/izahliq_lughet_2011_v1_headwords.tsv",
 "izah_2011_2":"https://huggingface.co/datasets/UyghurReferenceTexts/uyghur-headword-lists/resolve/main/data/izahliq_lughet_2011/izahliq_lughet_2011_v2_headwords.tsv",
 "anatilim":"https://raw.githubusercontent.com/colordict/colordict.github.io/master/stardict-anatilim-uyghur-chinese_uy-cn-2.4.2.tar.gz",
}

def fetch(url):
    r=urllib.request.Request(url,headers={"User-Agent":"Uyghur-Atlas-Vocab-Evidence-Audit/1.0"})
    with urllib.request.urlopen(r,timeout=90) as f:return f.read()

def norm(s):
    return re.sub(r"\s+"," ",s.replace("\u200f","").replace("\u200e","").replace("\u200c","").replace("\ufeff","")).strip()

def variants(w):
    w=norm(w); v={w}
    if w.endswith("-"):
        stem=w[:-1];v.update((stem,stem+"ماق",stem+"مەك"))
    if "؛" in w:
        v.update(norm(q) for q in w.split("؛"))
    if "(" in w:
        v.add(norm(re.sub(r"\s*\([^)]*\)","",w)))
    return {x for x in v if x}

def orthography():
    lookup=defaultdict(list); all_terms=set()
    for name in ["imla_2009","imla_2009_sub","izah_2011_1","izah_2011_2"]:
        dat=fetch(SOURCES[name]).decode("utf-8-sig")
        reader=csv.DictReader(io.StringIO(dat),delimiter="\t")
        c=0
        for row in reader:
            term=norm(row.get("entry") or row.get("phrase") or "")
            if not term:continue
            typ=row.get("type","subentry")
            if typ in ("nonstandard",):continue
            statuses=[(k,row.get(k,"")) for k in row if k.startswith("status_v")]
            status=next((x.strip() for k,x in reversed(statuses) if x.strip()),"unknown")
            info={"book":name,"status":status,"type":typ,
                  "row_id":row.get("row_id",row.get("sub_id","")),
                  "page":row.get("source_page","")}
            all_terms.add(term);lookup[term].append(info);c+=1
        print("ORTHO",name,c,flush=True)
    return lookup,all_terms

def chinese_gloss(text):
    text=text.strip("\0 \r\n")
    chunks=[]
    for piece in re.split(r"[；;\n]",text[:1000]):
        m=re.match(r"^\s*(?:[①②③④⑤⑥⑦⑧⑨0-9、 ]*)?([\u3400-\u9fff，、（）《》\s]+)",piece)
        if m:
            c=re.sub(r"\s+","",m.group(1)).strip("，、（）《》")
            if c and len(c)<100 and c not in chunks:chunks.append(c)
        if len(chunks)>=10:break
    return chunks

def bilingual():
    tar=tarfile.open(fileobj=io.BytesIO(fetch(SOURCES["anatilim"])),mode="r:gz")
    blobs={item.name.split("/")[-1]:tar.extractfile(item).read()
           for item in tar.getmembers() if item.name.endswith((".idx",".dict"))}
    idx=next(x for k,x in blobs.items() if k.endswith(".idx"))
    body=next(x for k,x in blobs.items() if k.endswith(".dict"))
    out=defaultdict(list); p=0;n=0
    while p<len(idx):
        e=idx.find(b"\0",p)
        if e<0 or e+9>len(idx):break
        term=norm(idx[p:e].decode("utf-8","replace"));offset,size=struct.unpack(">II",idx[e+1:e+9])
        p=e+9;n+=1
        if offset+size>len(body):continue
        gloss=body[offset:offset+size].decode("utf-8","replace")
        if term:
            for z in chinese_gloss(gloss):
                if z not in out[term]:out[term].append(z)
    print("ANATILIM",n,"distinct",len(out),flush=True)
    return out

def compare_zh(zh,glosses):
    if not glosses:return "无直接词典释义可比较"
    cleaned=re.sub(r"^[①②③④⑤⑥⑦⑧⑨]+","",zh)
    bits=[re.sub(r"[①②③④⑤⑥⑦⑧⑨\s（）()]+","",x) for x in re.split(r"[；;，,、。]",cleaned)]
    bits=[x for x in bits if x and x not in ("等","的")]
    canon=" | ".join(glosses)
    if not bits:return "中文义项结构复杂，人工审查"
    if any(len(b)>=2 and b in canon for b in bits):
        return "有部分中文义项字面对应（非语义认证）"
    if any(len(g)>=2 and g in b for g in glosses[:8] for b in bits):
        return "词典较短释义被原表包含（非语义认证）"
    if all(len(b)==1 for b in bits):
        return "单字释义，不宜用字面匹配判断"
    return "未发现字面对应，需要人工比较义项"

def main():
    index=json.loads(fetch(BASE+"atlas/index.json"))
    print("SITE",index.get("id"),index.get("count"),flush=True)
    chunks=(len(index["words"])+index.get("chunk",100)-1)//index.get("chunk",100)
    entries={}
    for i in range(chunks):
        d=json.loads(fetch(BASE+f"atlas/entries/{i}.json"))
        for row in d:
            entries[row["id"]]=row
    items=[]
    for ref in index["words"]:
        entry=entries.get(ref[0],{})
        zh="；".join((s.get("zh","") for s in entry.get("senses",[]) if s.get("zh"))) or str(ref[2])
        items.append({"id":ref[0],"word":ref[1],"meaning":zh,"raw":entry})
    print("ENTRY_COUNT",len(items),"LOADED",len(entries),flush=True)
    lookup,terms=orthography()
    lex=bilingual()
    results=[]
    for x in items:
        forms=variants(x["word"])
        orth=[a for v in forms for a in lookup.get(v,[])]
        glosses=[]
        lexterms=[]
        for w in forms:
            if w in lex:
                lexterms.append(w)
                for z in lex[w]:
                    if z not in glosses:glosses.append(z)
        valid_ortho=[i for i in orth if i.get("status")=="verified"]
        orth_level=("已核词形" if valid_ortho else "收录但该词目未标已核" if orth else "未收录或为复合词/词形变化")
        comparison=compare_zh(x["meaning"],glosses)
        results.append({
            "id":x["id"],"word":x["word"],"site_meaning":x["meaning"],
            "orthography_level":orth_level,"orthography_sources":orth[:4],
            "anatilim_present":bool(lexterms),"anatilim_terms":lexterms[:3],
            "anatilim_chinese":glosses[:10],"meaning_comparison":comparison,
            "flag_type": ("拼写和释义均需独立复查" if not orth and not lexterms
                          else "释义未见字面对应" if glosses and comparison.startswith("未发现")
                          else "词形未获规范表支持" if not orth
                          else "核对材料齐备但未人工逐条确认"),
        })
    Path(OUT/"word_reference_audit.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),"utf8")
    ct=Counter(r["orthography_level"] for r in results)
    ct2=Counter(r["meaning_comparison"] for r in results)
    report={
      "site_word_count":len(items),"dictionary_hit":sum(r["anatilim_present"] for r in results),
      "orthography":dict(ct),"meaning_literal_comparison":dict(ct2),
      "source_urls":SOURCES,
      "disclaimer":"Automated reference lookup; NOT a 1817-word independent semantic certification. Nonhits can be phrases, inflections, or source omissions; literal gloss agreement is not conclusive.",
    }
    Path(OUT/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf8")
    print("RESULT",json.dumps(report,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
