import { useMemo, useState } from "react";
import type { Atlas, WordRef } from "../atlas/types";
import { openWord } from "../lib/router";
import { isMastered } from "../store/srs";
import { useStore } from "../store/store";

interface Props {
  atlas: Atlas;
  cat: number;
  active: boolean;
  onStart: (ids: string[]) => void;
}

/** Expand the 19 topics into independently studyable semantic subunits. */
export function SubgroupPicker({ atlas, cat, active, onStart }: Props) {
  const progress = useStore((s) => s.progress);
  const [expanded, setExpanded] = useState(false);
  const [browsing, setBrowsing] = useState<number | null>(null);
  const labels = atlas.semanticSubgroups?.[cat] ?? [];
  const index = atlas.semanticWordSubgroups;
  const bins = useMemo(() => {
    const result: WordRef[][] = Array.from({ length: atlas.semanticSubgroups?.[cat]?.length ?? 0 }, () => []);
    if (!atlas.semanticWordSubgroups) return result;
    for (const w of atlas.words) {
      if (w.topic !== cat) continue;
      const sub = atlas.semanticWordSubgroups[w.order];
      if (Number.isInteger(sub) && result[sub]) result[sub].push(w);
    }
    return result;
  }, [atlas, cat]);
  const available = bins.filter((group) => group.length > 0).length;
  if (!labels.length || !index) return null;
  return (
    <div className="uy-subgroup-section">
      <button
        type="button"
        className="uy-subgroup-toggle"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
      >
        <span>{expanded ? "收起" : "展开"} {available} 个可学子单元</span>
        <span aria-hidden="true">{expanded ? "−" : "＋"}</span>
      </button>
      {expanded && (
        <div className="uy-subgroup-list">
          {labels.map((label, sub) => {
            const words = bins[sub] || [];
            if (!words.length) return null;
            const seen = words.filter((w) => !!progress.cards[w.id]).length;
            const mastered = words.filter((w) => {
              const card = progress.cards[w.id];
              return card ? isMastered(card) : false;
            }).length;
            const complete = words.length > 0 && seen === words.length;
            return (
              <div className="uy-subgroup-card" key={sub}>
                <div className="uy-subgroup-head">
                  <span className="uy-subgroup-name">
                    <small>{String(sub + 1).padStart(2, "0")}</small> {label}
                  </span>
                  <span className="uy-subgroup-number">{seen}/{words.length} 已学</span>
                </div>
                <div className="uy-subgroup-track" aria-label={"已学" + seen + "个，共" + words.length + "个"}>
                  <i style={{ width: (words.length ? (seen / words.length) * 100 : 0) + "%" }} />
                </div>
                <div className="uy-subgroup-foot">
                  <small>{mastered} 已掌握</small>
                  <div className="uy-subgroup-actions">
                    <button
                      type="button"
                      className="uy-subgroup-browse"
                      disabled={!words.length}
                      aria-expanded={browsing === sub}
                      onClick={() => setBrowsing((current) => current === sub ? null : sub)}
                    >
                      {browsing === sub ? "收起词汇" : "浏览词汇"}
                    </button>
                    <button
                      type="button"
                      className="uy-subgroup-start"
                      disabled={active || !words.length}
                      onClick={() => onStart(words.map((w) => w.id))}
                    >
                      {!words.length ? "暂无词汇" : complete ? "复习单元" : seen ? "继续单元" : "开始学习"}
                    </button>
                  </div>
                </div>
                {browsing === sub && (
                  <div className="uy-subgroup-words" aria-label={label + "词汇列表"}>
                    {words.map((w) => (
                      <button
                        type="button"
                        key={w.id}
                        onClick={() => openWord(w.id)}
                        className="uy-subgroup-word"
                        title={w.zh}
                      >
                        <b lang="ug" dir="rtl">{w.word}</b>
                        <span>{w.zh}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
