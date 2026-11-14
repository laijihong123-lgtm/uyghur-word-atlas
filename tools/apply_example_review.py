#!/usr/bin/env python3
"""Apply explicit row-level linguistic decisions, never infer approval from rules.

Run after add_reading.py and complete_examples.py. Source sentences and stable
example IDs must match the frozen extraction exactly or publication stops.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from port_uyghur import to_uly

HOME = Path(__file__).resolve().parent.parent
ATLAS = HOME / "upstream/public/atlas"
AUDIT = HOME / "audit"
PENDING = "待母语者复核"
REVIEWED = "AI逐条审校通过（非母语者审定）"


def sentence_uly(text: str) -> str:
    # Distinguish two consonants from a digraph: ن+گ is n'g, not ڭ/ng.
    # Insert separators before conversion; initial/intervocalic hamza still
    # follows the existing project's ULY conventions. Word-card ULY is untouched.
    text = re.sub(r"(?<=[نگسز])(?=[گغھ])", lambda m: "'" if
                  (text[m.start()-1:m.start()+1] in {"نگ", "نغ", "گھ", "سھ", "زھ"}) else "", text)
    return to_uly(text)


def load_decisions():
    rows = []
    for i in range(7):
        rows.extend(json.loads((AUDIT / f"reviews/batch{i}.json").read_text("utf-8")))
    return rows


def main():
    original = json.loads((AUDIT / "original_examples.json").read_text("utf-8"))
    decisions = load_decisions()
    expected = {x["id"]: x for x in original}
    reviewed = {x["id"]: x for x in decisions}
    assert len(expected) == len(original) == len(reviewed) == len(decisions) == 1840
    assert expected.keys() == reviewed.keys(), "Missing/extra review decision"
    for x in decisions:
        assert x["status"] in {PENDING, REVIEWED}, x["id"]
        for key in ("ug", "zh", "reason", "analysis", "target_form"):
            assert isinstance(x[key], str) and x[key].strip(), (x["id"], key)
        assert isinstance(x["issues"], list) and isinstance(x["basis"], list) and x["basis"], x["id"]
        assert bool(x["uncertainty"]) == (x["status"] == PENDING), x["id"]

    current = json.loads((ATLAS / "examples.json").read_text("utf-8"))
    assert len(current) == 1840
    for x in current:
        old = expected[x["id"]]
        assert all(x[k] == old[k] for k in ("id", "wordId", "word", "ug", "uly", "zh", "source")), x["id"]

    paths = sorted((ATLAS / "entries").glob("*.json"), key=lambda p: int(p.stem))
    chunks = [(p, json.loads(p.read_text("utf-8"))) for p in paths]
    entries = [e for _, c in chunks for e in c]
    before = json.dumps([{k: v for k, v in e.items() if k != "ex"} for e in entries], ensure_ascii=False, sort_keys=True)
    index_before = (ATLAS / "index.json").read_bytes()
    all_rows = []
    examples = []
    for e in entries:
        for i, ex in enumerate(e["ex"]):
            id = e["id"] + ":" + str(i)
            old, d = expected[id], reviewed[id]
            assert ex["en"] == old["ug"] and ex["zh"] == old["zh"], id
            uly = sentence_uly(d["ug"])
            assert uly.strip() and not re.search(r"[\u0600-\u06ff]", uly), id
            ex.update(en=d["ug"], zh=d["zh"], uly=uly, source="ai_linguistic_review",
                      reviewStatus=d["status"], reviewNote=d["uncertainty"])
            examples.append(dict(id=id, wordId=e["id"], word=e["w"], ug=ex["en"],
                                 zh=ex["zh"], uly=uly, source=ex["source"],
                                 reviewStatus=d["status"], reviewNote=d["uncertainty"]))
            all_rows.append({**old, "revised_ug": d["ug"], "revised_uly": uly, "revised_zh": d["zh"],
                             "issues": d["issues"], "reason": d["reason"], "analysis": d["analysis"],
                             "basis": d["basis"], "status": d["status"], "uncertainty": d["uncertainty"],
                             "target_form": d["target_form"],
                             "changed": any(old[k] != v for k,v in [("ug",d["ug"]),("uly",uly),("zh",d["zh"])])})
    assert before == json.dumps([{k: v for k, v in e.items() if k != "ex"} for e in entries], ensure_ascii=False, sort_keys=True)
    assert index_before == (ATLAS / "index.json").read_bytes()
    assert {x["id"] for x in examples} == expected.keys()
    assert len({x["wordId"] for x in examples}) == 1813
    for p,c in chunks:
        p.write_text(json.dumps(c, ensure_ascii=False, indent=2), "utf-8")
    (ATLAS/"examples.json").write_text(json.dumps(examples, ensure_ascii=False, separators=(",",":")), "utf-8")
    all_rows.sort(key=lambda x:x["record"])
    report = {
        "date":"2026-11-14", "source_commit":"3a0f33c05c4957b234bbf30d42e37b85d0f533e4",
        "records":1840,"wordCards":1813,"reviewedRecords":len(all_rows),
        "revisedRecords":sum(x["changed"] for x in all_rows),
        "revisedUyghur":sum(x["ug"] != x["revised_ug"] for x in all_rows),
        "revisedChinese":sum(x["zh"] != x["revised_zh"] for x in all_rows),
        "revisedULY":sum(x["uly"] != x["revised_uly"] for x in all_rows),
        "statusCounts":dict(Counter(x["status"] for x in all_rows)),
        "issueCounts":dict(Counter(k for x in all_rows for k in set(x["issues"]))),
        "untouchedCardDataSHA256":hashlib.sha256(before.encode()).hexdigest(),
        "indexSHA256":hashlib.sha256(index_before).hexdigest(),
        "method":"AI逐条阅读与语言判断，辅以词典和教材结构核对；非真人或母语专家审定。规则仅做完整性、ULY和身份一致性校验。",
        "sentenceAudioGenerated":False,
    }
    (AUDIT/"reviewed_examples.json").write_text(json.dumps(all_rows, ensure_ascii=False, indent=2),"utf-8")
    (AUDIT/"statistics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),"utf-8")
    public = ATLAS/"audit"; public.mkdir(exist_ok=True)
    for name in ("reviewed_examples.json", "statistics.json"):
        shutil.copyfile(AUDIT/name, public/name)
    (ATLAS/"example-coverage-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf-8")
    # Carry the review label into both existing example surfaces.
    p = HOME/"upstream/src/atlas/types.ts"
    t = p.read_text("utf-8").replace("  source?: string;", "  source?: string;\n  reviewStatus?: string;\n  reviewNote?: string;")
    p.write_text(t,"utf-8")
    p = HOME/"upstream/src/ui/EntryView.tsx"
    t = p.read_text("utf-8")
    old = '{x.source === "word_mention" ? "词形识别示例·不展示自然用法" : "自动生成例句·待校对"}'
    assert old in t
    t=t.replace(old,'{x.reviewStatus || "待校对"}{x.reviewNote ? "：" + x.reviewNote : ""}')
    p.write_text(t,"utf-8")
    p = HOME/"upstream/src/pages/StudyRoom.tsx"
    t = p.read_text("utf-8").replace("source?: string };", "source?: string; reviewStatus?: string; reviewNote?: string };")
    old = '{x.source === "word_mention" ? "词形识别示例（非真实用法）" : "自动生成例句·待校对"}'
    assert old in t
    t=t.replace(old,'{x.reviewStatus || "待校对"}{x.reviewNote ? "：" + x.reviewNote : ""}')
    p.write_text(t,"utf-8")
    print("ROW_LEVEL_LANGUAGE_REVIEW_APPLIED",json.dumps(report,ensure_ascii=False),flush=True)


if __name__ == "__main__":
    main()
