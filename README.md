# 维语词光 · 教材逐条复核正式词库版

网站：https://laijihong123-lgtm.github.io/uyghur-word-atlas/

本项目在 [designfuchen/word-atlas](https://github.com/designfuchen/word-atlas) 的原版开源 React / WebGL2 / FSRS 应用上改造，采用用户提供的 **《维吾尔语词表_逐条复核版.xlsx》** 作为学习词库。维吾尔文从右向左排版。

## 正式词库

- **1,817 条**教材「背诵词表」记录，全部保留维文、中文释义、教材页码和原始表序号
- **1,813 张**可学习词卡：4 组**同形异义词**合并为一张带多个释义的卡片，避免无语境歧义测验；原始义项仍完整保留
- **4 条**待确认词来自原文件「暂缓背诵」工作表，保存在 data/textbook_deferred.tsv，不进入词卡和测试
- 正式词库的唯一构建输入：data/textbook_reviewed.tsv；旧的 data/words.txt、data/counselor_focus_candidates.txt、tools/curate_2000.py 为历史研究文件，**不再用于正式网站**
- 按教材附录原表顺序学习，分为六组。组号不代表 CEFR 或其他语言能力等级
- 主题归类根据中文释义关键词自动辅助生成，不是教材自带分类

## 学习功能

保留原版每日学习、间隔复习（FSRS）、统计、收藏和 3D 星图。由于没有经核实的维语录音，禁用英语替代朗读、听音题和音频。原表没有完整例句及可靠拉丁转写，不自动生成未经审核的内容。对原表以 - 结尾的动词词干，保留教材标记但不强制考拼写连字符。

旧的 46 词候选版以及 2000 词候选版有不同 datasetId；新版学习记录使用独立命名空间，避免不同词义的历史复习进度被错配到教材词。

## 构建与校验

GitHub Actions 自动克隆原版源码、通过 tools/port_uyghur.py 导入词库、执行逐条保真校验、运行原版测试并编译两个版本：
- uyghur-atlas-website：GitHub Pages 子目录版本
- uyghur-atlas-netlify：适用于 Netlify Drop 的根目录版本

构建必须确认 1,817 行源记录、1,813 张词卡、所有源释义逐字一致、4 条暂缓词未被导入，否则自动失败。此程序依据用户提供的词表复核记录，不声称网站额外进行了母语专家逐项审校。

## 来源及版权

Word Atlas 原版代码 MIT License，上游的图片、数据和其他素材另有许可条件。请查阅 [上游仓库](https://github.com/designfuchen/word-atlas) 原始说明。本版保留原作者的来源说明，不使用英语录音假装维语发音。
