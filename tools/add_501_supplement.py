#!/usr/bin/env python3
"""Append the 363 authorized 501-course records after the original audited build.

The old pipeline and its exact example/audio checks remain intact. New cards
have stable IDs, retain original glosses, and receive clearly labeled
supplemental examples in a later, independently validated build step.
"""
from bisect import bisect_left
import shutil
import copy
import csv
import json
import re
from pathlib import Path
from port_uyghur import to_uly, learning_difficulty
from semantic_groups import CATEGORY_NAMES, CATEGORY_KEYS, SUBGROUPS

HOME=Path(__file__).resolve().parent.parent
ATLAS=HOME/'upstream/public/atlas'

def build(idx, entries, records):
    assert len(records)==363
    assert len(entries)==len(idx['words'])==idx['count']==1813
    assert len({e['id'] for e in entries})==1813
    old=copy.deepcopy(entries)
    byid={e['id']:e for e in entries}
    words={r[0]:r for r in idx['words']}
    forms={e['w']:e for e in entries}
    ordering={}
    old_scores=sorted(learning_difficulty({"uy":e["w"],"senses":[s["zh"] for s in e["senses"]],"seq":n})[0] for n,e in enumerate(entries))
    for e in entries:
        cat=words[e['id']][5]
        label=e['note'].split('。主题分组：',1)[1].split('。类别分配',1)[0].split('／',1)[1]
        sub=SUBGROUPS[cat].index(label)
        score=learning_difficulty({"uy":e["w"],"senses":[s["zh"] for s in e["senses"]],"seq":list(words).index(e["id"])})[0]
        ordering[e['id']]=(cat,sub,score,list(words).index(e['id']))
    report=[]
    for r in records:
        i=r['seq'];w=r['word'];cat=r['category'];sub=r['subgroup']
        assert 0<=cat<19 and 0<=sub<len(SUBGROUPS[cat])
        assert w not in forms,('Duplicate spelling requires explicit merge',w)
        assert w==('پالەك' if i==125 else r['originalWord'])
        wid=f's501{i:04d}'
        senses=[{'pos':'教材释义','zh':r['zh'],'en':''}]
        if r['supplement']:
            senses.append({'pos':'补充释义','zh':r['supplement'],'en':''})
        latin=to_uly(w)
        score=learning_difficulty({'uy':w,'senses':[r['zh']],'seq':1817+i})[0]
        level=min(5,bisect_left(old_scores,score)//303)
        joined=' ／ '.join(s['zh'] for s in senses)
        e={'id':wid,'w':w,'uk':latin,'us':'','senses':senses,
           'ex':[],'col':[],'fam':[],'syn':[],'ant':[],
           'tip':'拉丁转写按 ULY 规则自动生成（非 IPA）。',
           'cefr':f'难度{level+1}','topic':CATEGORY_KEYS[cat],'m':32,
           'note':f"来自501句词语补充表；第{r['lesson']}课，原PDF第{r['pdfPages']}页，教材词条{r['sourceIds']}。主题分组：{CATEGORY_NAMES[cat]}／{SUBGROUPS[cat][sub]}。保留原中文，另列补充释义；未添加未经核对的例句。"}
        byid[wid]=e; forms[w]=e
        words[wid]=[wid,w,joined,latin,level,cat,32]
        ordering[wid]=(cat,sub,score,1817+i)
        report.append({'id':wid,**r,'categoryName':CATEGORY_NAMES[cat],'subgroupName':SUBGROUPS[cat][sub]})
    order=sorted(words,key=lambda wid:ordering[wid])
    idx['words']=[words[wid] for wid in order]
    entries=[byid[wid] for wid in order]
    idx['count']=len(entries)
    idx['semanticCategoryCounts']=[sum(w[5]==i for w in idx['words']) for i in range(19)]
    idx['supplement501']={'records':363,'spellingCorrections':1,'supplementalGlosses':8,'source':'supplement-501.json'}
    assert idx['count']==2176 and sum(idx['semanticCategoryCounts'])==2176
    assert len({w[1] for w in idx['words']})==2176
    assert all(byid[e['id']]==e for e in old),'Original cards changed'
    assert [w[5] for w in idx['words']]==sorted(w[5] for w in idx['words'])
    assert len({w[0] for w in idx['words']})==2176
    return idx,entries,report

def main():
    idx=json.loads((ATLAS/'index.json').read_text())
    entries=[e for p in sorted((ATLAS/'entries').glob('*.json'),key=lambda p:int(p.stem)) for e in json.loads(p.read_text())]
    records=json.loads((HOME/'data/supplement_501.json').read_text())
    idx,entries,report=build(idx,entries,records)
    alias=next(e for e in entries if e['id']=='s5010294')
    target=next(e for e in entries if e['id']=='tb1195')
    assert re.sub(r'\s*-\s*','-',alias['w'])==target['w']
    target['senses'].append({'pos':'501句教材补充释义','zh':alias['senses'][0]['zh'],'en':''})
    target['note']+='；501句教材第42课词条42-03的空格异写已合并。'
    next(w for w in idx['words'] if w[0]==target['id'])[2]=' ／ '.join(x['zh'] for x in target['senses'])
    entries=[e for e in entries if e['id']!=alias['id']]
    idx['words']=[w for w in idx['words'] if w[0]!=alias['id']]
    idx['count']=2175
    idx['semanticCategoryCounts']=[sum(w[5]==i for w in idx['words']) for i in range(19)]
    idx['supplement501'].update(newCards=362,mergedRecords=1)
    next(x for x in report if x['id']==alias['id'])['canonical_id']=target['id']
    # Use the site's established fallback illustration palette, with a distinct
    # attribution file so the original attribution reports remain unchanged.
    import generate_fast_illustrations as art
    from PIL import Image
    added=[w for w in idx['words'] if w[0].startswith('s501')]
    icons={w[0]:art.mark_concept(w[2]) for w in added}
    images=art.load_icons(icons)
    for w in added:
        icon,kind=icons[w[0]]
        im=art.draw_one(w,icon,kind,images.get(icon))
        for folder,size in [('img',384),('thumb',104)]:
            dest=ATLAS/folder/(w[0]+'.webp')
            dest.parent.mkdir(exist_ok=True)
            im.resize((size,size),Image.Resampling.LANCZOS).save(dest,'WEBP',quality=75)
            assert dest.stat().st_size>400
        w[6]|=1
    for e in entries:
        if e['id'].startswith('s501'): e['m']|=1
    idx['illustrated']=sum(bool(w[6]&1) for w in idx['words'])
    # Only reuse supplemental audio when the prior artifact carries the same
    # stable IDs and exact word forms; never attach a recording by position.
    prior=HOME/'previous-website/atlas'
    metadata=prior/'supplement-501.json'
    if metadata.is_file():
        prior_words={r['id']:r['word'] for r in json.loads(metadata.read_text())['records']}
        for e in entries:
            audio=prior/'audio/uk'/(e['id']+'.mp3')
            if e['id'].startswith('s501') and prior_words.get(e['id'])==e['w'] and audio.is_file() and audio.stat().st_size>1000:
                shutil.copyfile(audio,ATLAS/'audio/uk'/(e['id']+'.mp3'))
                e['m']|=2
                next(w for w in idx['words'] if w[0]==e['id'])[6]|=2
    idx['voiced']=sum(bool(w[6]&2) for w in idx['words'])
    assert idx['illustrated']==2175
    for p in (ATLAS/'entries').glob('*.json'): p.unlink()
    for n in range(0,len(entries),100):
        (ATLAS/'entries'/f'{n//100}.json').write_text(json.dumps(entries[n:n+100],ensure_ascii=False,separators=(',',':')))
    (ATLAS/'index.json').write_text(json.dumps(idx,ensure_ascii=False,separators=(',',':')))
    (ATLAS/'supplement-501.json').write_text(json.dumps({'records':report,'illustrationLicense':'Lucide ISC (icon components), procedural muted watercolor scenes; original Word Atlas artwork retains CC BY 4.0 attribution'},ensure_ascii=False,indent=2))
    for relative in ['src/pages/Today.tsx','index.html','UYGHUR_PORT_NOTICE.md']:
        p=HOME/'upstream'/relative
        text=p.read_text()
        text=text.replace('只使用网站现有的 1,813 张词卡','使用全部 2,175 张词卡')
        text=text.replace('已导入1,817条教材逐条复核记录；4组同形异义合并成1,813张词卡。','原有1,813张词卡，补入501句教材363条，共2,175张词卡。')
        text=text.replace('教材逐条复核词表1,817条学习记录，合并为1,813张词卡','教材原有1,813张词卡，新增501句教材363条，共2,175张词卡')
        p.write_text(text)
    # Version JSON requests so existing browsers cannot mix old index/chunks
    # with the expanded deck. Dataset and card IDs stay stable for progress.
    loader=HOME/'upstream/src/atlas/data.ts'
    text=loader.read_text()
    old='const url = (p: string) => `${BASE}/atlas/${p}`;'
    new='const url = (p: string) => `${BASE}/atlas/${p}${p.endsWith(".json") ? "?v=501-merged-20261117" : p.endsWith(".webp") ? "?v=painted-20261117" : ""}`;'
    assert old in text
    loader.write_text(text.replace(old,new))
    # Final product copy and controls for the Uyghur edition.
    root=HOME/'upstream'
    me=root/'src/pages/Me.tsx'
    ms=me.read_text('utf-8')
    start=ms.index('          <Field label="发音">')
    end=ms.index('          </Field>',start)+len('          </Field>')
    ms=ms[:start]+'''          <Field label="维吾尔语读音" hint="单词使用维吾尔语 AI 合成录音；可在下方控制是否自动播放。">
            <div>维吾尔语 AI 合成 · 单一读音</div>
          </Field>'''+ms[end:]
    ms=ms.replace('从哪个难度开始','学习起点').replace('跳过已经熟悉的低级别词。','选择开始学习的词汇范围；已学词继续按复习安排出现。')
    me.write_text(ms,'utf-8')
    for file in list((root/'src').rglob('*.tsx'))+[root/'index.html']:
        s=file.read_text('utf-8').replace('维语词光 Uyghur Atlas','维语星球 ئۇيغۇرچە سەييارە').replace('维语词光','维语星球').replace('词光 Word Atlas','维语星球 ئۇيغۇرچە سەييارە').replace('词光','维语星球')
        s=s.replace('欢迎来到雅思大门','欢迎来到维语星球').replace('欢迎来到维语大门','欢迎来到维语星球')
        file.write_text(s,'utf-8')
    for file in [root/'public/manifest.json',root/'public/manifest.webmanifest']:
        if file.exists():
            s=file.read_text('utf-8').replace('维语词光','维语星球').replace('Uyghur Atlas','ئۇيغۇرچە سەييارە')
            file.write_text(s,'utf-8')
    galaxy=root/'src/galaxy/Galaxy.tsx'
    gs=galaxy.read_text('utf-8')
    gs=gs.replace('playFile("voice-galaxy-hello.mp3", 0.9)', 'Promise.resolve()').replace('playFile("voice-galaxy-lit.mp3", 0.9)', 'Promise.resolve()')
    # No longer call playFile anywhere in Galaxy: remove the import as well,
    # otherwise strict TypeScript noUnusedLocals blocks the Pages build.
    old_import='import { cue, playFile } from "../lib/sound";'
    assert old_import in gs
    gs=gs.replace(old_import,'import { cue } from "../lib/sound";')
    galaxy.write_text(gs,'utf-8')
    for file in [root/'src/pages/Today.tsx',root/'src/pages/Onboarding.tsx',root/'src/pages/About.tsx']:
        s=file.read_text('utf-8').replace('六组按常用程度与难度估计排序，同组穿插话题','按主题和语义小组学习，组内从基础词到扩展词')
        s=s.replace('欢迎来到维语星球','欢迎来到维语星球')
        file.write_text(s,'utf-8')
    print('SUPPLEMENT_501_VERIFIED',idx['count'],idx['semanticCategoryCounts'],flush=True)

if __name__=='__main__':main()
