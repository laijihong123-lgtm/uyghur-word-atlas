#!/usr/bin/env python3
"""Attach 362 clearly labeled supplementary example drafts to the 501-course cards.

Run AFTER add_501_supplement.py: the original 1,840 reviewed examples remain
untouched. Do not treat these new illustrative sentences as textbook quotations
or as mother-tongue-reviewed material.
"""
from __future__ import annotations

import json
from pathlib import Path

from apply_example_review import sentence_uly

ROOT = Path(__file__).resolve().parent.parent
ATLAS = ROOT / "upstream/public/atlas"
DATA_FILES = [
    "supplement_examples_001_120.txt",
    "supplement_examples_121_240.txt",
    "supplement_examples_241_363.txt",
]
LABEL = "AI编写例句草稿（待母语者核验）"


def load_examples() -> dict[int, tuple[str, str]]:
    result: dict[int, tuple[str, str]] = {}
    for name in DATA_FILES:
        for line_number, line in enumerate((ROOT / "data" / name).read_text("utf-8").splitlines(), 1):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("|")
            if len(parts) != 3:
                raise ValueError(f"{name}:{line_number}: expected seq|Uyghur|Chinese")
            seq_text, ug, zh = (value.strip() for value in parts)
            seq = int(seq_text)
            if seq in result:
                raise ValueError(f"Duplicate example ID: {seq}")
            if not ug or not zh or not any("\u0600" <= c <= "\u06ff" for c in ug):
                raise ValueError(f"Missing/invalid Uyghur or Chinese at {name}:{line_number}")
            result[seq] = ug, zh
    source = json.loads((ROOT / "data/supplement_501.json").read_text("utf-8"))
    expected = {r["seq"] for r in source if r["seq"] != 294}
    if len(source) != 363 or len(result) != 362 or set(result) != expected:
        raise ValueError(f"Example coverage mismatch: missing={sorted(expected - set(result))}, "
                         f"extra={sorted(set(result) - expected)}")
    return result


def main() -> None:
    samples = load_examples()
    idx_path = ATLAS / "index.json"
    idx = json.loads(idx_path.read_text("utf-8"))
    if idx["count"] != 2175 or idx["examples"] != 1840:
        raise RuntimeError("Expected 2,175 cards and 1,840 pre-reviewed examples")
    paths = sorted((ATLAS / "entries").glob("*.json"), key=lambda p: int(p.stem))
    chunks = [(p, json.loads(p.read_text("utf-8"))) for p in paths]
    entries = [e for _, chunk in chunks for e in chunk]
    by_id = {e["id"]: e for e in entries}
    original_ids = {e["id"] for e in entries if not e["id"].startswith("s501")}
    supplemental_ids = {e["id"] for e in entries if e["id"].startswith("s501")}
    expected_new_ids = {f"s501{i:04d}" for i in samples}
    if len(original_ids) != 1813 or supplemental_ids != expected_new_ids:
        raise RuntimeError("Unexpected original or supplementary word IDs")

    existing_examples = json.loads((ATLAS / "examples.json").read_text("utf-8"))
    if len(existing_examples) != 1840 or len({e["id"] for e in existing_examples}) != 1840:
        raise RuntimeError("Previously reviewed examples changed")
    original_examples_snapshot = json.dumps(existing_examples, ensure_ascii=False, sort_keys=True)
    for seq, (ug, zh) in sorted(samples.items()):
        card_id = f"s501{seq:04d}"
        entry = by_id[card_id]
        if entry["ex"]:
            raise RuntimeError(f"New card already has an example: {card_id}")
        uly = sentence_uly(ug)
        if not uly.strip() or any("\u0600" <= c <= "\u06ff" for c in uly):
            raise RuntimeError(f"ULY conversion failed: {card_id}: {uly}")
        example = {
            "en": ug, "zh": zh, "uly": uly, "source": "ai_supplement_draft",
            "reviewStatus": LABEL, "reviewNote": "",
        }
        entry["ex"] = [example]
        existing_examples.append({
            "id": card_id + ":0", "wordId": card_id, "word": entry["w"],
            "ug": ug, "uly": uly, "zh": zh, "source": "ai_supplement_draft",
            "reviewStatus": LABEL, "reviewNote": "",
        })
    assert json.dumps(existing_examples[:1840], ensure_ascii=False, sort_keys=True) == original_examples_snapshot
    assert len(entries) == 2175 and all(e["ex"] for e in entries)
    assert len(existing_examples) == 2202
    assert len({x["id"] for x in existing_examples}) == 2202
    assert len({x["wordId"] for x in existing_examples}) == 2175
    for path, chunk in chunks:
        path.write_text(json.dumps(chunk, ensure_ascii=False, indent=2), "utf-8")
    (ATLAS / "examples.json").write_text(
        json.dumps(existing_examples, ensure_ascii=False, separators=(",", ":")), "utf-8"
    )
    idx["examples"] = 2202
    idx["supplement501"].update(examples=362, exampleStatus="AI草稿，待母语者核验")
    idx_path.write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), "utf-8")
    report_path = ATLAS / "example-coverage-report.json"
    report = json.loads(report_path.read_text("utf-8"))
    report["supplement501Examples"] = 362
    report["allWordCardsWithExamples"] = 2175
    report["totalLinkedExamplesAfterSupplement"] = 2202
    report["supplementQuality"] = LABEL
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    metadata_path = ATLAS / "supplement-501.json"
    metadata = json.loads(metadata_path.read_text("utf-8"))
    metadata["exampleDrafts"] = 362
    metadata["exampleStatus"] = LABEL
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), "utf-8")
    # Bump both vocabulary and reading-room URLs so mobile browsers cannot
    # silently reuse pre-example JSON from the earlier 501-card deployment.
    loader_path = ROOT / "upstream/src/atlas/data.ts"
    loader = loader_path.read_text("utf-8")
    old_version = "501-merged-20261117"
    if loader.count(old_version) != 1:
        raise RuntimeError("Unable to safely version the atlas JSON loader")
    loader_path.write_text(loader.replace(old_version, "501-examples-20261117"), "utf-8")
    room_path = ROOT / "upstream/src/pages/StudyRoom.tsx"
    room = room_path.read_text("utf-8")
    old_fetch = 'fetch(base + "examples.json")'
    if room.count(old_fetch) != 1:
        raise RuntimeError("Unable to safely version the study-room example fetch")
    room_path.write_text(
        room.replace(old_fetch, 'fetch(base + "examples.json?v=501-examples-20261117")'),
        "utf-8",
    )
    print("SUPPLEMENT_EXAMPLES_COMPLETE", len(samples),
          "TOTAL_WORDS", len(entries), "TOTAL_LINKED_EXAMPLES", len(existing_examples),
          flush=True)


if __name__ == "__main__":
    main()
