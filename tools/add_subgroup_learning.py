#!/usr/bin/env python3
"""Expose all 179 pre-existing semantic subgroups as selectable study units.

Run after add_501_examples.py, when the final 2,175 cards are present. This is
a navigation-only feature: no card IDs, dataset ID, existing entry order,
glosses, SRS records, image or audio assets are modified.
"""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "upstream"
ATLAS = UPSTREAM / "public/atlas"


def patch(file: Path, old: str, new: str):
    value = file.read_text("utf-8")
    if value.count(old) != 1:
        raise RuntimeError(f"Expected exactly one marker {old!r} in {file}")
    file.write_text(value.replace(old, new), "utf-8")


def main():
    idx_path = ATLAS / "index.json"
    idx = json.loads(idx_path.read_text("utf-8"))
    paths = sorted((ATLAS / "entries").glob("*.json"), key=lambda p: int(p.stem))
    entries = [e for p in paths for e in json.loads(p.read_text("utf-8"))]
    assert len(idx["words"]) == len(entries) == idx["count"] == 2175
    labels = idx["semanticSubgroups"]
    assert len(labels) == 19 and sum(len(g) for g in labels) == 179
    assert [w[0] for w in idx["words"]] == [e["id"] for e in entries], "Misaligned index and entry chunks"
    subgroups = []
    for w, e in zip(idx["words"], entries):
        cat = w[5]
        if e["topic"] != f"cat{cat + 1:02d}" or "。主题分组：" not in e["note"]:
            raise RuntimeError(f"Missing semantic provenance for {e['id']}")
        tagged = e["note"].split("。主题分组：", 1)[1].split("。", 1)[0]
        if "／" not in tagged:
            raise RuntimeError(f"Missing subunit label for {e['id']}")
        category, subname = tagged.split("／", 1)
        if category != idx["topics"][cat][1] or subname not in labels[cat]:
            raise RuntimeError(f"Unknown subgroup for {e['id']}: {tagged}")
        subgroups.append(labels[cat].index(subname))
    idx["semanticWordSubgroups"] = subgroups
    assert len(subgroups) == 2175
    counts = [[0] * len(names) for names in labels]
    for w, sub in zip(idx["words"], subgroups):
        counts[w[5]][sub] += 1
    assert sum(sum(row) for row in counts) == 2175
    assert [sum(row) for row in counts] == idx["semanticCategoryCounts"]
    idx["semanticSubgroupCounts"] = counts
    idx_path.write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), "utf-8")

    # Expose metadata on the existing Atlas object (old public/private datasets
    # can omit these optional fields without changing their behavior).
    types = UPSTREAM / "src/atlas/types.ts"
    patch(types, "  topics: [string, string][];\n  cefr: string[];\n  words: WordRef[];",
          "  topics: [string, string][];\n  cefr: string[];\n"
          "  semanticSubgroups?: string[][];\n  semanticWordSubgroups?: number[];\n  words: WordRef[];")
    loader = UPSTREAM / "src/atlas/data.ts"
    patch(loader, "  topics: [string, string][];\n  cefr: string[];\n  words: IndexRow[];",
          "  topics: [string, string][];\n  cefr: string[];\n"
          "  semanticSubgroups?: string[][];\n  semanticWordSubgroups?: number[];\n  words: IndexRow[];")
    patch(loader, "    topics: idx.topics,\n    cefr: idx.cefr,",
          "    topics: idx.topics,\n    cefr: idx.cefr,\n"
          "    semanticSubgroups: idx.semanticSubgroups,\n"
          "    semanticWordSubgroups: idx.semanticWordSubgroups,")
    # Preserve the cache key for artwork, version JSON to prevent mixing a
    # new index with older chunks from the 501-word deployment.
    patch(loader, "?v=501-examples-20261117", "?v=semantic-units-20261117")

    today = UPSTREAM / "src/pages/Today.tsx"
    patch(today, 'import { Illustration } from "../ui/Illustration";',
          'import { Illustration } from "../ui/Illustration";\n'
          'import { SubgroupPicker } from "../ui/SubgroupPicker";')
    marker = "  return (\n    <section className=\"panel uy-challenge\""
    added = """  const startSubset = (ids: string[]) => {
    if (active || !ids.length) return;
    const fresh = ids.filter((id) => !progress.cards[id]);
    const perSession = Math.max(5, Math.min(100, settings.dailyNew || 100));
    const selected = (fresh.length ? fresh : ids).slice(0, perSession);
    if (!selected.length) return;
    const session = buildSession(atlas, progress, settings, { ids: selected });
    if (!session.steps.length) return;
    store.progress((p) => ({ ...p, session }));
    if (settings.sfx) void cue("start");
    go({ page: "learn" });
  };
"""
    patch(today, marker, added + marker)
    button_tail = '''                <span className="uy-challenge-action">{complete ? "巩固复习" : seen ? "继续本组" : "开始本组"}</span>
              </button>
            </div>'''
    patch(today, button_tail, '''                <span className="uy-challenge-action">{complete ? "巩固复习" : seen ? "继续本组" : "开始本组"}</span>
              </button>
              <SubgroupPicker atlas={atlas} cat={i} active={active} onStart={startSubset} />
            </div>''')
    patch(today, "按主题和语义小组归类，再从常用到扩展",
          "19个主题，179个语义子单元；可按子单元独立学习")
    patch(today, "一组可分多次完成；已学过的单词继续由间隔复习系统安排。",
          "可展开各组选择子单元学习；已学过的单词继续由间隔复习系统安排。")
    picker = ROOT / "tools/SubgroupPicker.tsx"
    (UPSTREAM / "src/ui/SubgroupPicker.tsx").write_text(picker.read_text("utf-8"), "utf-8")

    css_path = UPSTREAM / "src/styles/app.css"
    css_path.write_text(css_path.read_text("utf-8") + "\n" + r"""
/* Collapsible semantic subunits within the 19 group cards. */
.uy-subgroup-section { margin-top:12px; }
.uy-subgroup-toggle { width:100%; display:flex; align-items:center; justify-content:space-between;
  padding:12px 13px; border:1px solid var(--line); border-radius:12px; background:var(--paper-2);
  color:var(--ink); font-weight:650; font-size:13px; cursor:pointer; text-align:left; }
.uy-subgroup-toggle:focus-visible,.uy-subgroup-actions button:focus-visible,
.uy-subgroup-word:focus-visible { outline:2px solid var(--terra); outline-offset:2px; }
.uy-subgroup-list { display:flex; flex-direction:column; gap:10px; margin-top:12px; }
.uy-subgroup-card { border:1px solid var(--line); background:var(--card); border-radius:12px; padding:12px; min-width:0; }
.uy-subgroup-head { display:flex; justify-content:space-between; align-items:start; gap:7px; flex-wrap:wrap; }
.uy-subgroup-name { min-width:0; font-size:13px; color:var(--ink); font-weight:700; }
.uy-subgroup-name small { display:inline-block; margin-right:6px; color:var(--terra); }
.uy-subgroup-number { font-size:12px; color:var(--ink-3); font-variant-numeric:tabular-nums; }
.uy-subgroup-track { display:block; height:5px; border-radius:99px; background:var(--paper-3); overflow:hidden; margin:9px 0 10px; }
.uy-subgroup-track i { display:block; height:100%; background:var(--sage); border-radius:99px; }
.uy-subgroup-foot { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:9px; }
.uy-subgroup-foot > small { font-size:12px; color:var(--ink-3); }
.uy-subgroup-actions { display:flex; gap:7px; flex-wrap:wrap; }
.uy-subgroup-actions button { padding:8px 10px; border-radius:10px; font-size:12px; font-weight:650; cursor:pointer; }
.uy-subgroup-start { color:#fff; background:var(--terra); border:1px solid var(--terra); }
.uy-subgroup-browse { color:var(--ink); background:var(--paper-2); border:1px solid var(--line); }
.uy-subgroup-actions button:disabled { opacity:.5; cursor:not-allowed; }
.uy-subgroup-words { margin-top:10px; padding:6px; background:var(--paper-2); border-radius:10px;
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:5px; max-height:300px; overflow:auto; }
.uy-subgroup-word { border:1px solid var(--line); border-radius:8px; background:var(--card);
  min-width:0; display:flex; flex-direction:column; gap:3px; padding:9px; text-align:left; cursor:pointer; }
.uy-subgroup-word b { font-size:16px; text-align:right; color:var(--ink); }
.uy-subgroup-word span { font-size:12px; color:var(--ink-3); overflow-wrap:anywhere; }
@media(max-width:420px) { .uy-subgroup-words { grid-template-columns:1fr; } }
""", "utf-8")

    print("SEMANTIC_SUBGROUP_NAV_READY", len(idx["words"]),
          "SUBUNITS", sum(map(len, labels)),
          "NONEMPTY", sum(bool(n) for row in counts for n in row),
          "CARD_IDS_UNCHANGED", True, flush=True)


if __name__ == "__main__":
    main()
