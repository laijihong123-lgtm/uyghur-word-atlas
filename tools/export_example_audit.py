#!/usr/bin/env python3
"""Export the complete language review and a browser-readable audit table."""
from pathlib import Path
import csv
import json
import shutil

HOME = Path(__file__).resolve().parent.parent
AUDIT = HOME / "audit"
PUBLIC = HOME / "upstream/public/atlas/audit"
SOURCES = [
    {"key":"G","title":"Engesæth, Yakup & Dwyer (2009), Greetings from the Teklimakan",
     "url":"https://elkitab.org/wp-content/uploads/2020/04/uy-16.pdf",
     "scope":"教材结构参考；各行记录课次与语法判断，并不表示原创句子逐字来自教材。",
     "sections":"L1名词句；L2形容词、元音升高；L3现在将来时、向格、处所；L4疑问否定；L5宾格、从格、复数；L6数词、时间、bilen；L7进行时；L8属格领属；L9动名词；L10存在、比较；L11过去时；L12情态；L13未完成过去时、使动；L14副动词、祈使；L15辅助动词。"},
    {"key":"D","title":"Anatilim Uyghur–Chinese StarDict",
     "url":"https://raw.githubusercontent.com/colordict/colordict.github.io/master/stardict-anatilim-uyghur-chinese_uy-cn-2.4.2.tar.gz",
     "scope":"独立词形、义项和搭配线索；只对确实查询过的词目引用，不证明整句地道性。"},
    {"key":"U","title":"Nicholas Kontovas (2021), Reading Uyghur, §2 Table 1",
     "url":"https://www.turkolog.ist/pdf/KONTOVAS_Reading_Uyghur.pdf",
     "scope":"ULY字母对应及ë/é写法。此版统一ە=e、ې=ë，区分ن+گ与ڭ等复字母边界。"},
]


def main():
    rows=json.loads((AUDIT/"reviewed_examples.json").read_text("utf-8"))
    stats=json.loads((AUDIT/"statistics.json").read_text("utf-8"))
    headers=["关联ID","词卡ID","目标词","词卡原释义","原维语例句","原ULY","原中文","修订维语例句","修订ULY","修订中文","问题类别","原因","词形与语法分析","核验依据","审核状态","待核疑点","实际目标词形","是否修订"]
    keys=["id","wordId","word","meaning","ug","uly","zh","revised_ug","revised_uly","revised_zh","issues","reason","analysis","basis","status","uncertainty","target_form","changed"]
    with (AUDIT/"uyghur_examples_audit_1840.csv").open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.writer(f);writer.writerow(headers)
        for r in rows:
            writer.writerow(["；".join(r[k]) if isinstance(r[k],list) else ("是" if r[k] else "否") if k=="changed" else r[k] for k in keys])
    pending=stats["statusCounts"].get("待母语者复核",0)
    lines=["# 维吾尔语例句完整审校说明", "", "审校日期：2026年11月14日", "",
           f"从原仓库构建数据提取全部 **1,840 条关联记录**，覆盖 **1,813 张词卡**，逐条记录 AI 语言审校意见。修订 {stats['revisedRecords']} 条，保留三种文本均不变的 {1840-stats['revisedRecords']} 条；{pending} 条明确标为待母语者复核。", "",
           "审校方式为语言模型逐条阅读、词义和语法分析，并参考教材、独立词典及字母表。没有母语者参与，不能称作人工审校或母语专家审定。规则校验只用于记录完整性、ID、ULY和数据一致性，不构成语义合格判定。", "",
           "## 修订范围", "",
           f"- 维文发生变化：{stats['revisedUyghur']} 条。",
           f"- 中文发生变化：{stats['revisedChinese']} 条。",
           f"- ULY发生变化：{stats['revisedULY']} 条（多数随维文重写改变，不能都算原转写错误）。",
           "- 改写主要处理模板不自然、未展示目标词用法、缺少必要对象、词形变化、主语错配及机械汉译。正确、适用的原句保留。",
           "- 学习记录相关的词卡ID、数据集ID、顺序、例句关联ID、FSRS与收藏结构不变；未生成任何例句音频。",
           "- 专名、教材词条本身的冲突、罕见短语和未能确认的搭配保留具体疑点。待核句作为有标记的修订草稿展示，不标为正确。", "",
           "## 问题统计", "", "同一关联记录可有多类问题，以下计数不能相加当作错误句总数；“搭配自然度”等包含教学改写，不全是语法错误。", "", "| 类别 | 关联记录数 |", "| --- | ---: |"]
    lines.extend(f"| {k} | {v} |" for k,v in sorted(stats["issueCounts"].items(),key=lambda x:-x[1]))
    lines.extend(["", "## 审核状态", "", f"- AI逐条审校通过（非母语者审定）：{1840-pending} 条。",f"- 待母语者复核：{pending} 条。", "",
                  "“通过”表示此次AI审校未留下已知未解决疑点，不等于保证无误。完整表的“原因”“词形与语法分析”“核验依据”“待核疑点”用于追踪各条判断。", "", "## 来源及证据边界", ""])
    for s in SOURCES: lines.extend([f"- **{s['key']}** [{s['title']}]({s['url']})：{s['scope']}"])
    lines.extend(["", "词典证据只支持词目或义项，教材支持结构推理；新写句子的自然度仍属于AI判断。未把查无词目视为错误，也未伪造原创例句的出版出处。", "", "## 可复现与部署", "",
                  "原始记录保存在 original_examples.json，逐条决定保存在 reviews/batch0.json 至 batch6.json，汇总保存在 reviewed_examples.json。关联ID为固定词卡ID加原例句索引。构建时强制核对全部原始文本，避免漏条或把审核应用到变化后的语料。", "",
                  "构建脚本在修改前后比较除例句外的全部词卡字段，以及索引文件逐字节内容。GitHub Pages沿用原仓库工作流；部署状态以对应提交的Actions记录为准，不能用本说明代替成功记录。", "",
                  "ULY采用ë书写ې，不是IPA，也不是读音审听。此次没有生成或请求生成例句音频。", ""])
    (AUDIT/"REVISION_NOTES.md").write_text("\n".join(lines),"utf-8")
    (AUDIT/"sources.json").write_text(json.dumps(SOURCES,ensure_ascii=False,indent=2),"utf-8")
    PUBLIC.mkdir(exist_ok=True)
    for name in ("uyghur_examples_audit_1840.csv","REVISION_NOTES.md","sources.json"):
        shutil.copyfile(AUDIT/name,PUBLIC/name)
    shutil.copyfile(HOME/"tools/example_audit.html",PUBLIC/"index.html")
    # Only an audit link is added; no progress store, navigation or study logic changes.
    p=HOME/"upstream/src/pages/StudyRoom.tsx";t=p.read_text("utf-8")
    anchor='<h2>例句本</h2>'
    if anchor in t:
        t=t.replace(anchor,anchor+'<p><a href={import.meta.env.BASE_URL + "atlas/audit/"}>查看全部1,840条审校表与待复核清单</a></p>')
    else:
        anchor='<div className="uy-room-examples">'
        assert anchor in t
        t=t.replace(anchor,'<p><a href={import.meta.env.BASE_URL + "atlas/audit/"}>查看全部1,840条审校表与待复核清单</a></p>'+anchor)
    p.write_text(t,"utf-8")
    print("COMPLETE_AUDIT_EXPORTED",len(rows),"PENDING",pending,flush=True)


if __name__=="__main__":main()
