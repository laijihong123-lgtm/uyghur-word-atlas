#!/usr/bin/env python3
"""Curate 2000 source-crosschecked Uyghur-Chinese lexical candidates for counseling-oriented learning.

Spellings: 2009 imla headword list with human 'verified' status.
Chinese senses: GPL-labelled Anatilim Uyghur-Chinese StarDict (Colordict mirror).
Frequency: CC BY 4.0 Internet wordform list (only used to rank already-spelling-checked words).
This is automated crosschecking, NOT a human translation-proofread dictionary.
"""
from __future__ import annotations
import csv
import io
import json
import math
import re
import struct
import tarfile
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
OUTPUT=ROOT/"data"
OUTPUT.mkdir(exist_ok=True)
SOURCES={
 "imla":"https://huggingface.co/datasets/UyghurReferenceTexts/uyghur-headword-lists/resolve/main/data/imla_lughiti_2009/imla_lughiti_2009_headwords.tsv",
 "anatilim":"https://raw.githubusercontent.com/colordict/colordict.github.io/master/stardict-anatilim-uyghur-chinese_uy-cn-2.4.2.tar.gz",
 "frequency":"https://raw.githubusercontent.com/Uyghur-LRs/Uyghur-Wordlist/master/wordlist-Internet-v0.1.zip",
}
AREAS={
 "education":("校园教务",310,"学生 学校 大学 教师 老师 课堂 上课 学习 教育 课程 课本 作业 考试 课堂 研究 教学 知识 学问 文凭 毕业 新生 报名 入学 课程 训练 培训 班级 图书馆 学期 成绩 读书 教室"),
 "emotion":("心理关怀",240,"心理 情绪 情感 感受 感动 心情 忧虑 担心 焦虑 紧张 恐惧 害怕 痛苦 悲伤 安慰 鼓励 失望 自信 快乐 难过 生气 愤怒 孤独 压力 精神 慢慢 理解 害羞 希望 不安"),
 "society":("学生谈心与沟通",240,"关系 交往 交流 沟通 交谈 谈话 说话 倾听 听见 解释 理解 帮助 支持 建议 劝说 指导 问题 解决 困难 原因 事情 分享 朋友 家庭 同学 尊重 合作 信任 需要 请求 讨论"),
 "work":("就业与职业发展",180,"工作 职业 就业 创业 企业 职员 单位 人才 技能 经验 工资 收入 面试 岗位 招聘 毕业 实习 能力 选择 专业 未来 目标 计划 管理 办公 职责 责任"),
 "government":("纪律法规与安全",170,"法律 规则 规定 制度 纪律 法规 权利 义务 责任 安全 警察 报警 危险 保护 禁止 惩罚 错误 行为 要求 政府 组织 事故 违反 证明 公平 协议 保密"),
 "health":("健康与生活照护",170,"健康 身体 医生 医院 疾病 治疗 医药 感染 生病 疼痛 休息 睡眠 饮食 食物 干净 卫生 运动 检查 生命 烫伤 头疼 体温 心脏 腹痛"),
 "thinking":("面试观点与表达",250,"原因 结果 目的 观点 想法 认为 意义 意见 看法 影响 重要 方法 措施 处理 分析 总结 经验 判断 比较 可能 必须 应该 选择 合适 情况 态度 价值 改善 提高 发展 努力"),
 "daily":("生活高频与社交",440,"日常 时间 今天 明天 昨天 每天 早上 晚上 中午 现在 以后 家 房子 朋友 你好 再见 谢谢 请 走 去 来 买 卖 钱 吃 喝 水 饭 茶 衣服 门 路 城市 人 女人 男人 孩子 父亲 母亲"),
}
TOPICS={
 "education":"education","emotion":"emotion","society":"society","work":"work",
 "government":"government","health":"health","thinking":"thinking","daily":"daily"
}
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"UyghurWordAtlas/1.0 data research"})
 with urllib.request.urlopen(req,timeout=90) as res:
  return res.read()

def norm(t):
 return t.strip().replace("\u200f","").replace("\u200e","").replace("\u200c","").replace("\u200d","").replace("\ufeff","").replace("\u0640","")

def valid_word(w):
 return 2<=len(w)<=24 and re.fullmatch(r"[\u0621-\u06ff]+(?: [\u0621-\u06ff]+)?",w) is not None and not re.search(r"[\u064b-\u065f\u0660-\u0669]",w)

def read_verified_2009():
 dat=get(SOURCES["imla"]).decode("utf-8-sig")
 reader=csv.DictReader(io.StringIO(dat),delimiter="\t")
 result=set()
 levels={}
 for row in reader:
  w=norm(row.get("entry",""))
  if not valid_word(w) or row.get("type") not in ("headword","corrected_form","verb_stem"):
   continue
  status=next((row[k].strip().lower() for k in reversed(list(row)) if k.startswith("status_v") and row[k].strip()),"")
  if status not in ("verified","corrected","approved","accepted"):
   continue
  result.add(w)
  levels[w]={"row":row.get("row_id",""),"page":row.get("source_page","")}
 print("SPELLING_verified_2009",len(result),flush=True)
 return result,levels

def read_anatilim():
 raw=get(SOURCES["anatilim"])
 tf=tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz")
 ix=next(tf.extractfile(m).read() for m in tf.getmembers() if m.name.endswith(".idx"))
 meanings=next(tf.extractfile(m).read() for m in tf.getmembers() if m.name.endswith(".dict"))
 result=defaultdict(list);pos=0;rows=0
 while pos<len(ix):
  end=ix.find(bytes([0]),pos)
  if end<0 or end+9>len(ix):break
  word=norm(ix[pos:end].decode("utf-8","replace"))
  offset,size=struct.unpack(">II",ix[end+1:end+9])
  pos=end+9;rows+=1
  if not valid_word(word) or offset+size>len(meanings):continue
  original=meanings[offset:offset+size].decode("utf-8","replace").strip("\0 \r\n")
  # StarDict's bilingual entries start with a Chinese gloss then Chinese pinyin.
  original=original.lstrip("①②③④⑤⑥⑦⑧⑨0123456789.、： ")
  candidate=original.split("；")[0].split(";")[0]
  # Stop at pinyin or roman-character explanations.
  m=re.match(r"^([\u3400-\u9fff，、（）《》·\s]+)",candidate)
  if not m:continue
  zh=re.sub(r"\s+","",m.group(1)).strip("，、·（）《》")
  if not (1<=len(zh)<=16) or not re.search(r"[\u4e00-\u9fff]",zh):continue
  if any(x in zh for x in ["【","词语","请参见","同上","〔","详见"]):continue
  if zh not in result[word]: result[word].append(zh)
 print("BILINGUAL_dictionary_rows",rows,"usable_headwords",len(result),flush=True)
 return result

def read_frequency():
 try:
  raw=get(SOURCES["frequency"])
  z=zipfile.ZipFile(io.BytesIO(raw))
  print("FREQ_ARCHIVE",[(n,z.getinfo(n).file_size) for n in z.namelist()[:10]],flush=True)
  count={}
  for name in z.namelist():
   if name.endswith("/"):continue
   if z.getinfo(name).file_size>130_000_000:continue
   for line in z.read(name).decode("utf-8","replace").splitlines():
    a=line.strip().split(",")
    if len(a)<2: a=line.strip().split("\t")
    if len(a)<2:continue
    try: freq=int(a[1].strip())
    except ValueError:continue
    w=norm(a[0])
    if 2<=len(w)<=24:count[w]=max(count.get(w,0),freq)
   if len(count)>10000:break
  print("FREQ_ENTRIES",len(count),"TOP",sorted(count.items(),key=lambda x:-x[1])[:10],flush=True)
  return count
 except Exception as exc:
  print("FREQ_UNAVAILABLE",repr(exc),flush=True)
  return {}

def main():
 from wordfreq import zipf_frequency
 spelled,meta=read_verified_2009()
 dic=read_anatilim()
 freq=read_frequency()
 rows=[]
 for w,glosses in dic.items():
  if w not in spelled:continue
  # Prefer a short, explicit Chinese gloss; reject suspicious agglutinated explanatory strings.
  best=min(glosses,key=lambda x:(len(x)>8,len(x),x))
  if not (1<=len(best)<=12):continue
  if re.search(r"[\u3400-\u9fff]{11}",best) and len(best)>11:continue
  # Chinese frequency improves suitability, but is not a guarantee of translation correctness.
  z=zipf_frequency(best.split("，")[0].split("、")[0],"zh")
  if z<2.0:continue
  f=freq.get(w,0)
  score=z*8 + math.log1p(f)*2.0 + (3 if len(w)<=8 else 0) - (2 if len(best)>=9 else 0)
  # Avoid complex multiword compounds in the core pool without human review.
  if " " in w: score-=2
  hints={}
  for topic,(_,_,terms) in AREAS.items():
   patterns=terms.split()
   matched=[a for a in patterns if a in best]
   if matched:
    hints[topic]=len(matched)+sum(1 for a in matched if len(a)>=2)
  rows.append({"uy":w,"zh":best,"topic":"","latin":"","score":round(score,4),
               "freq":f,"imla_id":meta[w]["row"],"imla_page":meta[w]["page"],
               "semantic_tags":hints,
               "source":"Anatilim Uyghur-Chinese bilingual dictionary + 2009 imla headword list",
               "quality":"2009正字词形已标记verified；中文释义来自词典但未逐条人工复核"})
 print("CANDIDATES_crosschecked",len(rows),flush=True)
 if len(rows)<2000:raise RuntimeError("Not enough doubly sourced rows; no fake 2000.")
 # Establish a learning route: high-priority counselor/interview themes first.
 selected=[];used=set();counts={}
 for area,(label,quota,terms) in AREAS.items():
  if area=="daily":continue
  pool=[r for r in rows if r["uy"] not in used and area in r["semantic_tags"]]
  pool.sort(key=lambda r:(r["semantic_tags"][area]*4+r["score"]),reverse=True)
  for r in pool[:quota]:
   r["topic"]=TOPICS[area];r["category"]=label
   selected.append(r);used.add(r["uy"])
  counts[label]=min(quota,len(pool))
 # Reserve room for highly frequent everyday phrases and words.
 for r in sorted(rows,key=lambda r:r["score"],reverse=True):
  if len(selected)>=2000:break
  if r["uy"] in used:continue
  topic="daily"
  if r["semantic_tags"]:
   topic=max(r["semantic_tags"],key=lambda k:r["semantic_tags"][k])
  r["topic"]=TOPICS[topic];r["category"]=AREAS[topic][0]
  selected.append(r);used.add(r["uy"])
 if len(selected)!=2000:raise RuntimeError("Did not reach exactly 2000 candidates.")
 # Prioritize subject-specific words in learning sequence; the remainder sorted by frequency.
 for i,r in enumerate(selected,1): r["number"]=i
 out=OUTPUT/"word_bank_2000.json"
 out.write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding="utf-8")
 csvfile=OUTPUT/"word_bank_2000.tsv"
 with csvfile.open("w",encoding="utf-8",newline="") as f:
  wr=csv.writer(f,delimiter="\t")
  wr.writerow(["序号","维吾尔文","中文释义","备考主题","维语互联网词形出现次数","2009年词目编号","2009年词目页码","核查状态","来源"])
  for r in selected:wr.writerow([r["number"],r["uy"],r["zh"],r["category"],
                                 r["freq"],r["imla_id"],r["imla_page"],r["quality"],r["source"]])
 checks={"total":len(selected),"unique":len(used),"topic_counts":dict(__import__("collections").Counter(r["category"] for r in selected)),
         "spelling_source":SOURCES["imla"],"meaning_source":SOURCES["anatilim"],
         "frequency_source":SOURCES["frequency"],"not_an_expert_review":True,
         "samples":{key:[(r["uy"],r["zh"]) for r in selected if r["category"]==key][:8] for key in set(r["category"] for r in selected)}}
 (OUTPUT/"curation_report.json").write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding="utf-8")
 print("CREATED_2000_REPORT",json.dumps(checks,ensure_ascii=False),flush=True)

if __name__=="__main__":main()
