import { ArrowLeft, BookOpen, Bookmark, BookmarkCheck, CheckCircle2, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useAtlas } from "../atlas/context";
import { openWord } from "../lib/router";
import { isMastered } from "../store/srs";
import { store, toggleBookmark, toggleExampleBookmark, useStore } from "../store/store";

type ReadingLine = { ug: string; zh: string; uly: string; refs: string[] };
type ReadingQuestion = { q: string; answer: "true" | "false" | "ng"; why: string };
type ReadingStory = { id: string; title: string; titleZh: string; level: number; description: string; lines: ReadingLine[]; questions: ReadingQuestion[] };
type ExampleItem = { id: string; wordId: string; word: string; ug: string; uly: string; zh: string };

const answerOptions: { value: ReadingQuestion["answer"]; label: string }[] = [
  { value: "true", label: "正确" },
  { value: "false", label: "错误" },
  { value: "ng", label: "未提及" },
];

function UyghurLine({ line }: { line: ReadingLine }) {
  const atlas = useAtlas();
  const lexicon = useMemo(
    () => line.refs.map((id) => atlas.byId.get(id)).filter((w): w is NonNullable<typeof w> => !!w),
    [atlas, line.refs],
  );
  return (
    <p className="uy-reader-line" lang="ug" dir="rtl">
      {line.ug.split(/(\s+)/).map((token, i) => {
        if (!token.trim()) return <span key={i}>{token}</span>;
        const cleaned = token.replace(/[.,،؛؟!?«»“”()]/g, "");
        const word = lexicon.find((w) => {
          const base = w.word.replace(/-$/, "");
          return cleaned === w.word || (base.length >= 3 && cleaned.startsWith(base));
        });
        return word ? (
          <button type="button" key={i} className="uy-reader-token" onClick={() => openWord(word.id)} title={word.zh}>
            {token}
          </button>
        ) : <span key={i}>{token}</span>;
      })}
    </p>
  );
}

export function StudyRoom() {
  const atlas = useAtlas();
  const progress = useStore((s) => s.progress);
  const [stories, setStories] = useState<ReadingStory[]>([]);
  const [examples, setExamples] = useState<ExampleItem[]>([]);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"reading" | "words" | "examples">("reading");
  const [storyId, setStoryId] = useState<string | null>(null);
  const [translations, setTranslations] = useState(true);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [query, setQuery] = useState("");
  const [onlySaved, setOnlySaved] = useState(false);
  const [wordFilter, setWordFilter] = useState<"saved" | "learning" | "due" | "mastered">("saved");
  const [limit, setLimit] = useState(80);

  useEffect(() => {
    let active = true;
    const base = import.meta.env.BASE_URL + "atlas/";
    Promise.all([
      fetch(base + "reading.json").then((r) => { if (!r.ok) throw new Error("短文未能加载"); return r.json(); }),
      fetch(base + "examples.json").then((r) => { if (!r.ok) throw new Error("例句未能加载"); return r.json(); }),
    ]).then(([a, b]: [ReadingStory[], ExampleItem[]]) => {
      if (active) { setStories(a); setExamples(b); setError(""); }
    }).catch((e: Error) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [atlas.id]);

  const bookmarked = useMemo(() => new Set(progress.bookmarks), [progress.bookmarks]);
  const exampleBookmarks = useMemo(() => new Set(progress.exampleBookmarks), [progress.exampleBookmarks]);
  const readDone = useMemo(() => new Set(progress.readingDone), [progress.readingDone]);
  const learned = useMemo(() => Object.keys(progress.cards).length, [progress.cards]);
  const due = useMemo(() => Object.values(progress.cards).filter((c) => c.due <= Date.now()).length, [progress.cards]);
  const activeStory = stories.find((s) => s.id === storyId);
  const filteredWords = useMemo(() => {
    const q = query.trim().toLowerCase();
    return atlas.words.filter((w) => {
      const c = progress.cards[w.id];
      const flag = wordFilter === "saved" ? bookmarked.has(w.id)
        : wordFilter === "learning" ? !!c && !isMastered(c)
        : wordFilter === "mastered" ? !!c && isMastered(c)
        : !!c && c.due <= Date.now();
      return flag && (!q || (w.word + " " + w.zh + " " + w.ipa).toLowerCase().includes(q));
    });
  }, [atlas.words, bookmarked, progress.cards, wordFilter, query]);
  const filteredExamples = useMemo(() => {
    const q = query.trim().toLowerCase();
    const fromWords = examples.filter((x) =>
      (!onlySaved || exampleBookmarks.has(x.id)) &&
      (!q || (x.ug + " " + x.zh + " " + x.uly + " " + x.word).toLowerCase().includes(q)));
    const fromReadings = stories.flatMap((story) => story.lines.map((line, i) => ({
      id: "story:" + story.id + ":" + i, wordId: "", word: story.titleZh,
      ug: line.ug, uly: line.uly, zh: line.zh,
    }))).filter((x) => exampleBookmarks.has(x.id) && (!q || (x.ug + " " + x.zh + " " + x.uly).toLowerCase().includes(q)));
    return [...fromReadings, ...fromWords];
  }, [examples, stories, onlySaved, exampleBookmarks, query]);

  const chooseAnswer = (story: ReadingStory, i: number, selected: string) => {
    setAnswers((prev) => ({ ...prev, [story.id + ":" + i]: selected }));
  };
  const finishReading = (id: string) => {
    store.progress((p) => ({ ...p, readingDone: p.readingDone.includes(id) ? p.readingDone : [...p.readingDone, id] }));
  };

  return (
    <div className="uy-room">
      <div className="uy-room-header">
        <p className="eyebrow">UYGHUR READING ROOM · 维语词光</p>
        <h1>书房</h1>
        <p>从一小段真实语境开始，慢慢把认识的词连成句子。点亮维语词可以打开原词卡。</p>
      </div>
      <div className="uy-room-stats">
        <div><strong>{learned}</strong><span>已接触词汇</span></div>
        <div><strong>{due}</strong><span>待复习单词</span></div>
        <div><strong>{progress.bookmarks.length}</strong><span>收藏生词</span></div>
        <div><strong>{readDone.size}/{stories.length}</strong><span>读完短文</span></div>
      </div>
      <nav className="uy-room-tabs" aria-label="书房栏目">
        <button className={tab === "reading" ? "is-selected" : ""} onClick={() => { setTab("reading"); setStoryId(null); setQuery(""); }}>分级阅读</button>
        <button className={tab === "words" ? "is-selected" : ""} onClick={() => { setTab("words"); setStoryId(null); setQuery(""); }}>生词本</button>
        <button className={tab === "examples" ? "is-selected" : ""} onClick={() => { setTab("examples"); setStoryId(null); setQuery(""); }}>例句本</button>
      </nav>
      {error && <p role="alert" className="uy-room-error">{error}。可尝试刷新网页。</p>}

      {tab === "reading" && (!activeStory ? (
        <section className="uy-room-shelf">
          <div className="uy-room-intro"><h2>维语分级短文</h2><p>目前收录 {stories.length} 篇入门短文，含逐句译文、拉丁转写和判断题；按难度逐步阅读。</p></div>
          <div className="uy-room-story-grid">
            {stories.map((story, index) => (
              <button key={story.id} className="uy-room-story" onClick={() => { setStoryId(story.id); setAnswers({}); setTranslations(true); }}>
                <span className="uy-room-story-number">{String(index + 1).padStart(2, "0")}</span>
                <span className="chip">第{story.level}阶段</span>
                {readDone.has(story.id) && <span className="uy-room-done"><CheckCircle2 size={15} /> 已读</span>}
                <strong lang="ug" dir="rtl">{story.title}</strong>
                <b>{story.titleZh}</b>
                <small>{story.description} · {story.lines.length} 句</small>
                <span className="uy-room-open">开始阅读 →</span>
              </button>
            ))}
          </div>
        </section>
      ) : (
        <article className="uy-reader">
          <button className="uy-room-back" onClick={() => setStoryId(null)}><ArrowLeft size={16} /> 返回书架</button>
          <div className="uy-reader-title"><span className="chip">第{activeStory.level}阶段</span><h2 lang="ug" dir="rtl">{activeStory.title}</h2><p>{activeStory.titleZh} · {activeStory.description}</p></div>
          <label className="uy-room-toggle"><input type="checkbox" checked={translations} onChange={(e) => setTranslations(e.target.checked)} /> 显示拉丁转写和中文</label>
          <ol className="uy-reader-lines">
            {activeStory.lines.map((line, i) => (
              <li key={i}>
                <div className="uy-reader-linehead"><small>第 {i + 1} 句</small><button aria-label="收藏这一句" className="uy-room-save" onClick={() => toggleExampleBookmark("story:" + activeStory.id + ":" + i)}>{exampleBookmarks.has("story:" + activeStory.id + ":" + i) ? <BookmarkCheck size={17}/> : <Bookmark size={17}/>}</button></div>
                <UyghurLine line={line} />
                {translations && <><p className="uy-reader-uly" dir="ltr">{line.uly}</p><p className="uy-reader-zh">{line.zh}</p></>}
              </li>
            ))}
          </ol>
          <section className="uy-reader-quiz">
            <h3>阅读小测</h3><p>根据文章判断：正确 / 错误 / 未提及。</p>
            {activeStory.questions.map((q, i) => {
              const choice = answers[activeStory.id + ":" + i];
              return <div className="uy-reader-question" key={i}>
                <strong>{i + 1}. {q.q}</strong>
                <div className="uy-reader-options">
                  {answerOptions.map((o) => <button key={o.value} className={choice === o.value ? "is-selected" : ""} onClick={() => chooseAnswer(activeStory, i, o.value)}>{o.label}</button>)}
                </div>
                {choice && <p className={choice === q.answer ? "is-correct" : "is-wrong"}>{choice === q.answer ? "答对了。" : "再看一遍：" } {q.why}</p>}
              </div>;
            })}
            <button className="btn btn-primary" onClick={() => finishReading(activeStory.id)}>{readDone.has(activeStory.id) ? "已记录完成" : "完成本篇阅读"}</button>
          </section>
        </article>
      ))}

      {tab === "words" && <section className="uy-room-shelf">
        <div className="uy-room-intro"><h2>我的生词本</h2><p>沿用你在词卡中收藏的单词和原来的 FSRS 复习状态，不会重置学习记录。</p></div>
        <div className="uy-room-filters">
          {([["saved","已收藏"],["learning","学习中"],["due","待复习"],["mastered","已掌握"]] as const).map(([v,label]) => <button key={v} className={wordFilter === v ? "is-selected" : ""} onClick={() => { setWordFilter(v);setLimit(80); }}>{label}</button>)}
        </div>
        <label className="uy-room-search"><Search size={17} /><input aria-label="搜索生词" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜索维语 / 拉丁 / 中文释义" /></label>
        <p className="uy-room-count">共 {filteredWords.length} 个单词</p>
        {filteredWords.length === 0 && <p className="uy-room-empty">这里还没有符合条件的词。可先到「图鉴」中收藏单词，或完成一轮学习。</p>}
        <div className="uy-room-words">{filteredWords.slice(0, limit).map((w) => (
          <div key={w.id} className="uy-room-word">
            <button className="uy-room-word-main" onClick={() => openWord(w.id)}>
              <strong lang="ug" dir="rtl">{w.word}</strong><span className="uy-reader-uly">{w.ipa}</span><small>{w.zh}</small>
            </button>
            <button className="uy-room-save" aria-label={bookmarked.has(w.id) ? "取消收藏" : "收藏"} onClick={() => toggleBookmark(w.id)}>{bookmarked.has(w.id) ? <BookmarkCheck size={19}/> : <Bookmark size={19}/>}</button>
          </div>
        ))}</div>
        {filteredWords.length > limit && <button className="btn" onClick={() => setLimit((v) => v + 80)}>再显示 80 个</button>}
        <a className="btn btn-primary uy-room-practice" href="#/">回到今日，开始复习</a>
      </section>}

      {tab === "examples" && <section className="uy-room-shelf">
        <div className="uy-room-intro"><h2>例句本</h2><p>维文、拉丁转写、中文对照；点击对应单词进入词卡，点书签收藏句子。</p></div>
        <div className="uy-room-filters"><button className={!onlySaved ? "is-selected" : ""} onClick={() => { setOnlySaved(false);setLimit(80); }}>全部例句</button><button className={onlySaved ? "is-selected" : ""} onClick={() => { setOnlySaved(true);setLimit(80); }}>我的收藏</button></div>
        <label className="uy-room-search"><Search size={17} /><input aria-label="搜索例句" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="按维语 / 拉丁 / 中文搜索" /></label>
        <p className="uy-room-count">共 {filteredExamples.length} 条</p>
        {filteredExamples.length === 0 && <p className="uy-room-empty">暂时没有符合条件的例句。可以去分级阅读里收藏喜欢的句子。</p>}
        <div className="uy-room-examples">{filteredExamples.slice(0, limit).map((x) => (
          <article key={x.id} className="uy-room-example">
            <div className="uy-reader-linehead">{x.wordId ? <button className="uy-room-example-word" onClick={() => openWord(x.wordId)}>{x.word} · 查看词卡</button> : <span>{x.word}</span>}
              <button className="uy-room-save" aria-label={exampleBookmarks.has(x.id) ? "取消收藏例句" : "收藏例句"} onClick={() => toggleExampleBookmark(x.id)}>{exampleBookmarks.has(x.id) ? <BookmarkCheck size={18}/> : <Bookmark size={18}/>}</button>
            </div>
            <p className="uy-reader-line" dir="rtl" lang="ug">{x.ug}</p>
            <p className="uy-reader-uly" dir="ltr">{x.uly}</p>
            <p className="uy-reader-zh">{x.zh}</p>
          </article>
        ))}</div>
        {filteredExamples.length > limit && <button className="btn" onClick={() => setLimit((v) => v + 80)}>再显示 80 条</button>}
      </section>}
      <p className="uy-room-caution"><BookOpen size={15}/> 阅读和例句为入门试用内容，尚未经过维语母语专家逐句审校；遇到疑问以教材和母语者纠正为准。当前不提供句子朗读音频。</p>
    </div>
  );
}
