#!/usr/bin/env python3
"""Generate fast, compact, consistently styled pictographic illustrations for missing cards.

This does NOT claim 952 bespoke scene paintings: each image is a distinct
word-labeled painterly pictogram, chosen from a meaning-based icon palette.
This is the deliberately fast visual fallback for complex/abstract vocabulary.
The user's source spellings and definitions are never modified.
Icons: Lucide (ISC license); original 855 pictures: Word Atlas CC BY 4.0.
"""
from __future__ import annotations
import concurrent.futures
import hashlib
import io
import json
import math
import random
import re
import urllib.request
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import cairosvg

ROOT = Path(__file__).resolve().parent.parent
ATLAS = ROOT / "upstream/public/atlas"
WIDTH = 384
ICONSOURCE = "https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/"
# Each exact clue maps to a distinguishable pictogram. Multi-character terms
# are prioritized over generic words to avoid accidental word fragments.
CONCEPTS = [
 ("公共汽车 地铁 大巴 公交", "bus-front", "transport"),
 ("火车 铁路 车站 轨道 列车", "train-front", "transport"),
 ("飞机 机场 航空", "plane", "transport"),
 ("轮船 船舶 渡口 航海 航行", "ship", "transport"),
 ("汽车 轿车 车辆 司机 停车", "car-front", "transport"),
 ("自行车 骑车", "bike", "transport"),
 ("摩托车", "bike", "transport"),
 ("桥梁 桥上", "bridge", "travel"),
 ("道路 公路 街道 沥青 行走", "route", "travel"),
 ("地图 地理 方向 东方 西方 南方 北方", "map", "travel"),
 ("国家 自治区 城市 市区 地区 县城 首都", "landmark", "city"),
 ("楼房 建筑 房屋 房子 公寓 宿舍 住宅", "house", "city"),
 ("工厂 工业 生产 车间", "factory", "work"),
 ("商店 商场 超市 市场 商业 买卖", "store", "commerce"),
 ("银行 存款 贷款 金融", "landmark", "commerce"),
 ("货币 现金 金钱 价格 工资 费用 收入 钱", "wallet", "commerce"),
 ("合同 签约 盖章 证件 证明", "file-check", "work"),
 ("法律 法院 法官 判决 诉讼", "scale", "civic"),
 ("监狱 警察 公安", "shield-check", "civic"),
 ("政府 政治 公共 机关 机构 组织", "landmark", "civic"),
 ("规则 纪律 规章 制度 规范 规定", "clipboard-check", "civic"),
 ("安全 危险 警报 保护", "shield-alert", "civic"),
 ("战争 军队 士兵 武器", "shield", "civic"),
 ("学校 大学 中学 小学 校园 教室 课堂", "school", "school"),
 ("教师 老师 教员 教学 讲课", "presentation", "school"),
 ("考试 考题 试题 成绩 测验", "clipboard-list", "school"),
 ("学生 同学 学业 读书 学习 研习", "graduation-cap", "school"),
 ("毕业 文凭 学位 学历", "graduation-cap", "school"),
 ("课本 书籍 图书 书本 书页 小说 词典 阅读", "book-open", "school"),
 ("字典 字母 文字 语法 拼写", "book-a", "school"),
 ("写字 写作 书写 笔记 文章 作文", "pen-line", "school"),
 ("文艺 报纸 刊物 杂志 出版 印刷", "newspaper", "school"),
 ("词语 词汇 术语 语言 口语 说话", "languages", "school"),
 ("体育 运动 体育课 锻炼 训练", "dumbbell", "sport"),
 ("足球 球员 踢球", "volleyball", "sport"),
 ("篮球 篮筐", "circle-dot", "sport"),
 ("游泳 游水", "waves", "sport"),
 ("跑步 奔跑 竞赛 比赛", "footprints", "sport"),
 ("音乐 歌曲 歌唱 唱歌", "music", "art"),
 ("绘画 画家 画作 画笔", "palette", "art"),
 ("摄影 照相 照片", "camera", "art"),
 ("戏剧 电影 演员 表演", "clapperboard", "art"),
 ("舞蹈 跳舞", "person-standing", "art"),
 ("艺术 美术 文化", "palette", "art"),
 ("医院 诊所 医生 大夫 护士 医疗", "hospital", "health"),
 ("疾病 生病 病人 病痛 疼痛 疗养", "heart-pulse", "health"),
 ("药品 药物 药片 药剂", "pill", "health"),
 ("牙齿 牙医", "smile", "health"),
 ("眼睛 视力 眼镜", "eye", "health"),
 ("耳朵 听力", "ear", "health"),
 ("鼻子", "scan-face", "health"),
 ("心脏 心跳", "heart-pulse", "health"),
 ("健康 身体 卫生 清洁 洗澡", "heart-handshake", "health"),
 ("食品 饮食 食物 饭菜 吃饭 烹饪 做饭", "cooking-pot", "food"),
 ("面条 拉面 馄饨 饺子", "soup", "food"),
 ("米饭 大米 谷物 粮食", "wheat", "food"),
 ("羊肉 牛肉 肉类 烤肉", "beef", "food"),
 ("蔬菜 萝卜 黄瓜 洋葱", "salad", "food"),
 ("苹果 梨子 香蕉 果实 水果", "apple", "food"),
 ("茶叶 茶水 喝茶 热茶", "coffee", "food"),
 ("咖啡 奶茶", "coffee", "food"),
 ("牛奶 奶酪 乳制品", "milk", "food"),
 ("饮水 水源 水杯", "glass-water", "food"),
 ("馕饼 面包", "sandwich", "food"),
 ("父亲 母亲 爸爸 妈妈 父母", "users-round", "people"),
 ("丈夫 妻子 夫妻 婚姻 结婚", "heart-handshake", "people"),
 ("儿子 女儿 孩子 儿童 婴儿", "baby", "people"),
 ("哥哥 弟弟 姐姐 妹妹 兄弟 姐妹", "users-round", "people"),
 ("家人 家庭 亲属 亲戚", "house", "people"),
 ("朋友 同伴 伙伴 友情", "users-round", "people"),
 ("老人 老年 青年 年轻", "user-round", "people"),
 ("男人 女人 男子 女子", "user-round", "people"),
 ("客人 宾客", "handshake", "people"),
 ("工作 职业 劳动 上班 职工 员工", "briefcase-business", "work"),
 ("招聘 求职 就业 入职 实习 面试", "briefcase-business", "work"),
 ("管理 经理 主管 领导", "users-round", "work"),
 ("农业 田地 农田 农村 耕地", "tractor", "nature"),
 ("农民 牧民 放牧", "sprout", "nature"),
 ("牲畜 牛羊 牦牛", "beef", "nature"),
 ("马匹 骏马", "paw-print", "nature"),
 ("骆驼", "paw-print", "nature"),
 ("动物 野兽 狗 猫 兔 鼠", "paw-print", "nature"),
 ("鸟类 飞鸟 麻雀 鸡 鸭 鹅", "bird", "nature"),
 ("昆虫 蜜蜂 蚂蚁 蚊子", "bug", "nature"),
 ("树木 森林 林地 树枝 树叶", "trees", "nature"),
 ("花朵 花卉 玫瑰 花园", "flower-2", "nature"),
 ("草原 草地 植物 种子 发芽", "sprout", "nature"),
 ("沙漠 沙丘", "mountain", "nature"),
 ("山峰 高山 山脉", "mountain", "nature"),
 ("河流 河水 溪流 江河", "waves", "nature"),
 ("海洋 海水 湖泊 池塘", "waves", "nature"),
 ("天空 星星 星空", "stars", "nature"),
 ("太阳 日光 阳光 白昼", "sun", "weather"),
 ("月亮 夜晚 月光", "moon-star", "weather"),
 ("雨水 下雨 雨天", "cloud-rain", "weather"),
 ("雪花 下雪 冰雪", "snowflake", "weather"),
 ("风暴 狂风 刮风 风力", "wind", "weather"),
 ("温度 寒冷 炎热 天气 气候", "thermometer-sun", "weather"),
 ("春天 春季 夏季 秋季 冬季", "leaf", "weather"),
 ("时间 小时 分钟 日期 日子 年代", "clock-3", "time"),
 ("星期 周末 日历 日程", "calendar-days", "time"),
 ("今天 明天 昨天 前天 后天", "calendar-check", "time"),
 ("早晨 早餐 黎明", "sunrise", "time"),
 ("晚上 傍晚 黄昏", "sunset", "time"),
 ("颜色 红色 绿色 蓝色 黄色 黑色 白色", "palette", "abstract"),
 ("大小 长短 高低 长度 高度 宽度", "ruler", "abstract"),
 ("数量 数字 数学 计算 统计", "calculator", "abstract"),
 ("增加 减少 上升 下降 增长", "chart-no-axes-column-increasing", "abstract"),
 ("重要 价值 优点 缺点 成功 失败", "target", "abstract"),
 ("希望 梦想 理想 目标 愿望", "sparkles", "abstract"),
 ("相信 信任 诚实 真诚", "handshake", "abstract"),
 ("快乐 幸福 愉快 高兴", "smile", "emotion"),
 ("伤心 悲伤 哀愁 忧愁", "frown", "emotion"),
 ("担心 焦虑 紧张 压力 害怕", "cloud-lightning", "emotion"),
 ("愤怒 生气 不满", "flame", "emotion"),
 ("爱情 喜爱 喜欢 爱护", "heart", "emotion"),
 ("思想 思考 思维 理解 认识 知识", "brain", "abstract"),
 ("意见 建议 观点 观念 看法", "message-square", "abstract"),
 ("语言 说话 谈话 交谈 交流 讨论", "messages-square", "people"),
 ("合作 互助 帮助 援助 支援", "hand-heart", "people"),
 ("问题 解答 解释 回答 询问 提问", "message-circle-question-mark", "abstract"),
 ("决定 选择 计划 安排 方案", "list-check", "abstract"),
 ("研究 分析 检查 比较 考察", "search-check", "abstract"),
 ("因为 原因 所以 结果", "git-branch", "abstract"),
 ("可能 一定 必须 应当", "circle-help", "abstract"),
 ("过去 现在 将来 未来", "history", "time"),
 ("开始 结束 完成 继续", "flag", "time"),
 ("打开 关闭 出入 进出", "door-open", "objects"),
 ("窗户 门口 屋门", "door-open", "objects"),
 ("桌子 书桌", "table-2", "objects"),
 ("椅子 凳子 座位", "armchair", "objects"),
 ("床铺 被褥 枕头", "bed", "objects"),
 ("衣服 裤子 外套 服装 衬衫", "shirt", "objects"),
 ("鞋子 袜子", "footprints", "objects"),
 ("帽子 围巾", "hat-glasses", "objects"),
 ("钥匙 锁头", "key-round", "objects"),
 ("手机 电话 通话", "smartphone", "objects"),
 ("电脑 计算机 网络", "laptop", "objects"),
 ("电视 节目 广播", "tv", "objects"),
 ("信件 邮件 包裹", "mail", "objects"),
 ("纸张 文件 资料 文书", "file-text", "objects"),
 ("工具 设备 机器 机械", "wrench", "objects"),
 ("钟表 手表", "watch", "objects"),
 ("节日 庆祝 生日 礼物", "gift", "people"),
 ("旅行 旅游 游客", "luggage", "travel"),
 ("历史 古迹 古老 遗址", "landmark", "city"),
 ("宗教 信仰 礼拜", "landmark", "civic"),
]
GROUP_COLORS = {
 "city": ((245,198,135),(168,107,74),(88,105,121)),
 "people": ((252,210,160),(165,108,97),(122,146,112)),
 "work": ((235,198,163),(125,140,142),(96,116,108)),
 "school": ((239,209,160),(104,141,133),(125,94,78)),
 "food": ((254,212,138),(181,112,75),(125,142,96)),
 "nature": ((237,208,142),(103,148,118),(72,118,124)),
 "weather": ((242,208,168),(142,160,166),(108,130,159)),
 "time": ((240,201,153),(175,124,111),(97,125,126)),
 "health": ((239,215,170),(117,154,150),(132,114,116)),
 "abstract": ((245,202,167),(127,145,144),(144,109,127)),
 "emotion": ((251,210,160),(172,114,117),(122,137,145)),
 "civic": ((239,194,152),(120,135,138),(150,114,97)),
 "commerce": ((245,206,169),(142,151,114),(158,113,107)),
 "travel": ((241,204,153),(119,150,142),(110,125,137)),
 "transport": ((242,211,173),(121,148,156),(126,120,101)),
 "art": ((246,201,165),(170,122,135),(104,135,133)),
 "sport": ((236,208,156),(117,156,126),(138,104,91)),
 "objects": ((251,212,163),(158,124,118),(110,145,142)),
}
BG_INK=(65,73,71)
def to_hex(rgb):return "#%02x%02x%02x"%rgb
def blend(a,b,t):return tuple(int(a[i]*(1-t)+b[i]*t) for i in range(3))
# Fast fallback for short textbook glosses. Concept icons are approximate aids,
# and the unmodified original Chinese definition remains printed on the image.
SHORT_RULES=[
 ("人 人口 人们 男人 女人 父母 亲人 朋友 同伴 群众","users-round","people"),
 ("老 老人 青年 年轻","user-round","people"),
 ("大 巨大 高 高的","maximize","abstract"),
 ("小 微小 低 低的","minimize","abstract"),
 ("长 长度 宽 宽阔","move-horizontal","abstract"),
 ("短 窄","minus","abstract"),
 ("多 多余 多数","plus","abstract"),
 ("少 少数 少量","minus","abstract"),
 ("快 快速 迅速","gauge","abstract"),
 ("慢 缓慢","snail","nature"),
 ("新 新的","sparkles","abstract"),
 ("旧 旧的","history","time"),
 ("热 热的 炎热","thermometer-sun","weather"),
 ("冷 寒冷","snowflake","weather"),
 ("风 大风","wind","weather"),
 ("雨 下雨","cloud-rain","weather"),
 ("雪 下雪","snowflake","weather"),
 ("云 天空 天","cloud-sun","weather"),
 ("山 河 湖 海 水","waves","nature"),
 ("草 树 叶 花","sprout","nature"),
 ("牛 羊 马 狗 猫 鸟 鱼 鸡","paw-print","nature"),
 ("苹果 水果 果实","apple","food"),
 ("饭 吃 吃饭","utensils","food"),
 ("做 做饭 烹饪","cooking-pot","food"),
 ("喝 喝茶 茶","coffee","food"),
 ("奶 奶油","milk","food"),
 ("金 黄金 金子","coins","commerce"),
 ("钱 价格 财富","wallet","commerce"),
 ("看 看见 观看","eye","people"),
 ("听 听见","ear","people"),
 ("说 说话 讲话","message-circle","people"),
 ("问 提问 询问","circle-help","abstract"),
 ("答 回答","message-circle-check","abstract"),
 ("写 写字 书写","pen","school"),
 ("读 朗读 阅读","book-open","school"),
 ("学 学习","graduation-cap","school"),
 ("教 教育","presentation","school"),
 ("知 知道 懂 了解","lightbulb","abstract"),
 ("想 思考 思念","brain","abstract"),
 ("找 寻找","search","abstract"),
 ("买 购买","shopping-cart","commerce"),
 ("卖 出售","store","commerce"),
 ("去 出去 送去","send","travel"),
 ("来 到达","map-pin","travel"),
 ("走 行走","footprints","travel"),
 ("跑 跑步","footprints","sport"),
 ("站 站立","person-standing","people"),
 ("坐 坐下","armchair","objects"),
 ("睡 睡觉","bed","objects"),
 ("开 打开","door-open","objects"),
 ("关 关闭","door-closed","objects"),
 ("起 起床","sunrise","time"),
 ("给 给予","hand-heart","people"),
 ("拿 拿起","hand","people"),
 ("借 借用","handshake","people"),
 ("还 归还","undo","abstract"),
 ("帮助 支持","hand-heart","people"),
 ("相信 信任","handshake","people"),
 ("笑 微笑 快乐 愉快 高兴 幸福","smile","emotion"),
 ("哭 悲伤 伤心","frown","emotion"),
 ("生气 愤怒","flame","emotion"),
 ("害怕 担心 忧虑","shield-alert","emotion"),
 ("喜欢 喜爱 爱 爱护","heart","emotion"),
 ("好 优良","thumbs-up","emotion"),
 ("坏 差 错","thumbs-down","emotion"),
 ("是 对 正确","check","abstract"),
 ("不 不是 没有 无","x","abstract"),
 ("有 存在","check-circle","abstract"),
 ("难 困难","mountain","abstract"),
 ("容易 简单","check","abstract"),
 ("很 非常 太 最 更","gauge","abstract"),
 ("早 早晨 先","sunrise","time"),
 ("晚 傍晚 夜","sunset","time"),
 ("时间 小时 分钟 时 分","clock","time"),
 ("今天 明天 昨天","calendar-days","time"),
 ("月 月份 年 年份","calendar-days","time"),
 ("过去 以前","history","time"),
 ("现在 正在","clock","time"),
 ("开始","play","time"),
 ("结束 完成","check-circle","time"),
 ("继续 重复 再 又","repeat","time"),
 ("上 上方","arrow-up","travel"),
 ("下 下方","arrow-down","travel"),
 ("左 左边","arrow-left","travel"),
 ("右 右边","arrow-right","travel"),
 ("前 前面","arrow-left","travel"),
 ("后 后面","arrow-right","travel"),
 ("那里 这里 地方","map-pin","travel"),
 ("国家 自治区 政府","landmark","civic"),
 ("城市 城镇 村庄","building-2","city"),
 ("法律 规则","scale","civic"),
 ("学校 课堂 学堂","school","school"),
 ("书 图书 词典","book-open","school"),
 ("老师 教师","presentation","school"),
 ("医院 医生","hospital","health"),
 ("生病 病 疼","heart-pulse","health"),
 ("药 药物","pill","health"),
 ("桌 桌子","table","objects"),
 ("椅 椅子","armchair","objects"),
 ("床 睡觉","bed","objects"),
 ("衣 衣服 衣裳","shirt","objects"),
 ("鞋 鞋子","footprints","objects"),
 ("手机 电话","smartphone","objects"),
 ("头 头发 脸","scan-face","people"),
 ("眼 眼睛","eye","people"),
 ("耳 耳朵","ear","people"),
 ("手 手指","hand","people"),
 ("脚 双脚","footprints","people"),
 ("我 我的 你 你的 他 他的 她 她的","user-round","people"),
 ("我们 你们 他们","users-round","people"),
 ("谁 什么 为什么 如何 怎样","circle-help","abstract"),
 ("和 与 跟 一起","link-2","people"),
 ("但是 然而","split","abstract"),
 ("因为 所以 因此","git-branch","abstract"),
 ("如果 假如","circle-help","abstract"),
 ("所有 全部 一切","list-check","abstract"),
 ("一定 必须 应当","badge-check","abstract"),
 ("准备 计划 方案","list-check","abstract"),
 ("情况 状态","sliders-horizontal","abstract"),
 ("位置 距离 方向","compass","travel"),
 ("颜色 红色 绿色 白色 黑色","palette","art"),
 ("音乐 歌曲 唱歌","music","art"),
 ("照片 照相","camera","art"),
 ("环境 自然","trees","nature"),
 ("劳动 工作 上班","briefcase-business","work"),
 ("孩子 孩童 儿童","baby","people"),
]
SHORT_MAP={}
for words,icon,kind in SHORT_RULES:
    for word in words.split():SHORT_MAP[word]=(icon,kind)

def mark_concept(zh):
    norm = re.sub(r"[①②③④⑤⑥⑦⑧⑨（）()《》]", "", zh)
    # Prefer distinctive multiword cues and preserve first-sense priority.
    clauses=re.split(r"[；;，,、／/]",norm)
    clauses=[q.strip() for q in clauses if q.strip()]
    for c in clauses[:3]:
        best=None
        for patterns,icon,kind in CONCEPTS:
            for term in patterns.split():
                if term in c and (len(term)>1 or c==term):
                    score=len(term)
                    if best is None or score>best[0]:best=(score,icon,kind)
        if best:return best[1:]
    for clause in clauses[:3]:
        if clause in SHORT_MAP:return SHORT_MAP[clause]
        if len(clause)<=6:
            partial=sorted((q for q in SHORT_MAP if len(q)>=2 and q in clause),key=len,reverse=True)
            if partial:return SHORT_MAP[partial[0]]
        if len(clause)<=3 and clause and clause[0] in SHORT_MAP:
            return SHORT_MAP[clause[0]]
    # Chinese glossary morphology: match names, places, concrete nouns and
    # distinctive characters before falling back to a generic abstract icon.
    phrases = [
        ("男名 女名 人名 姓名 名字", "user-round", "people"),
        ("维吾尔族 汉族 回族 柯尔克孜 塔吉克 哈萨克 蒙古族 达斡尔 壮族 彝族 锡伯族 满族 乌孜别克 俄罗斯人 阿拉伯人 波斯人 民族 人种", "users-round", "people"),
        ("阿克苏 乌鲁木齐 喀什 伊宁 北京 布哈拉 哈密 王府井 嘉峪关 中关村 阿拉伯 美洲 非洲 亚洲 中国 新疆 外国 地名", "map-pin", "city"),
        ("自治区 祖国 国民党 共产党 党 改革 革命", "landmark", "civic"),
        ("高等院校 院校 学校 优等生 进修 正教授 师生们 学位 文凭", "graduation-cap", "school"),
        ("日报 报纸 作品 著作 论文 课文 诗 语句 句型 造句 复习 阅读室 阅览室", "book-open", "school"),
        ("母语 维吾尔语 外国语 阿拉伯语 声波 发音 词语 生词", "languages", "school"),
        ("文艺 文学 世界史 古兰经 福乐智慧", "book-open", "school"),
        ("阿凡提 人物传记", "user-round", "people"),
        ("厨师 售货员 店员 炒菜 做饭", "cooking-pot", "food"),
        ("胃 肝癌 肺 血管 新陈代谢 血液 背部 脊背 身材", "heart-pulse", "health"),
        ("石榴 苹果 桃 杏 哈密瓜 梨 果子 油果子 点心 馓子 包子 馕 饭", "apple", "food"),
        ("烧烤 烤馕 烤肉 炒菜声 炉子 锅 碗 汤 盖碗 瓷碗", "cooking-pot", "food"),
        ("糖 淀粉 蜂蜜", "candy", "food"),
        ("爷爷 奶奶 外公 外婆 家属院", "house", "people"),
        ("果园 竹林 针叶松 榆树 柏树 树木 麦穗 麦 叶子 草 苗 菜 枝 根 巢", "trees", "nature"),
        ("兔子 狼 鹿 乌鸦 宰羊 鸡鸭", "paw-print", "nature"),
        ("泥土 土地 土 坑 砖 矿 石", "mountain", "nature"),
        ("水波 流水 流口水 汤汁 瀑布 淌漏", "waves", "nature"),
        ("艾特莱斯绸 绸缎 衣料 穿 围脖 花帽","shirt","objects"),
        ("邮电局 邮局 信封 邮票", "mail", "objects"),
        ("理发 理发馆 胡须", "scissors", "objects"),
        ("香皂 扫帚 擦 洗 清洁", "brush-cleaning", "health"),
        ("传呼机 鼠标 软盘 电脑 电子游戏", "laptop", "objects"),
        ("拖拉机 畜牧业 农业","tractor","nature"),
        ("票 车票 车牌 814路", "ticket", "transport"),
        ("舞 交际舞 迪斯科 唱歌", "music", "art"),
        ("绘画 有图画 彩色 图形", "palette", "art"),
        ("球 足球 篮球","volleyball","sport"),
        ("玉石 宝石","gem","commerce"),
        ("付款 银元 货币 元 钱 包括", "wallet", "commerce"),
        ("节日 春节 国庆节 肉孜节 库尔班节 封斋 拜年", "gift", "people"),
        ("穆斯林 伊斯兰 信仰 礼拜", "landmark", "civic"),
        ("战斗 英勇 勇敢 军政 军队", "shield", "civic"),
        ("调查 实地 物理 生态平衡 科学", "flask-conical", "school"),
        ("打针 发烧 感冒 疗养 治疗", "hospital", "health"),
        ("高兴 兴高采烈 喜悦 心里话","smile","emotion"),
        ("惊呆 发愣 害羞 恼怒 烦恼 犹豫","cloud-lightning","emotion"),
        ("认真 注意 自觉 觉悟 重点","target","abstract"),
        ("相继 连续 一步一步 从头到尾 越来越 同时","arrow-right-left","time"),
        ("当时 过去 刚才 此次 暂时 随时","clock","time"),
        ("次 次数 第几 一顿 一句 第一次","hash","abstract"),
        ("南 北 东 西 方位 方向","compass","travel"),
        ("提前 迟到","clock","time"),
        ("尺寸 大小 范围 层 次 斤 公里 千米","ruler","abstract"),
        ("情形 样式 情况 变化 发生 改变 反映","repeat-2","abstract"),
        ("基础 奠基 基地","layers","abstract"),
        ("表示 说话 健谈 道谢 道歉 祝愿","message-circle","people"),
        ("联系 交流 沟通 互相 和睦 友好","handshake","people"),
        ("找到 寻找 调查 比较 区别 划分","search","abstract"),
        ("明确 确实 详细 仔细","search-check","abstract"),
        ("依照 按照 沿着 顺着 依据","route","travel"),
        ("扮演角色 演员 故事片 电影","clapperboard","art"),
        ("生计 穷人 外贸 经济效益","wallet","commerce"),
        ("雷鸣 咕噜 咝咝 声响 哗啦 喧哗","volume-2","objects"),
        ("接着 继续 促进 进一步","arrow-right","abstract"),
    ]
    for clause in clauses[:3]:
        for words,icon,kind in phrases:
            if any(w in clause for w in words.split()):
                return icon,kind
    if re.search(r"[一二三四五六七八九十百千万亿零两〇]+", clauses[0] if clauses else ""):
        return "hash","abstract"
    distinctive = {
      "树":("tree-pine","nature"),"竹":("trees","nature"),
      "花":("flower-2","nature"),"草":("sprout","nature"),
      "茶":("coffee","food"),"饭":("utensils","food"),"瓜":("apple","food"),
      "果":("apple","food"),"菜":("salad","food"),"肉":("beef","food"),
      "鱼":("fish","nature"),"鸟":("bird","nature"),"狼":("paw-print","nature"),
      "米":("wheat","food"),"瓜":("apple","food"),"酒":("wine","food"),
      "报":("newspaper","school"),"页":("file-text","school"),"笔":("pencil","school"),
      "文":("book-open","school"),"词":("book-open","school"),
      "语":("languages","school"),"句":("book-open","school"),
      "声":("volume-2","people"),"听":("ear","people"),"说":("message-circle","people"),
      "问":("circle-help","abstract"),"答":("message-circle","people"),
      "读":("book-open","school"),"写":("pencil","school"),
      "画":("palette","art"),"唱":("music","art"),"歌":("music","art"),
      "手":("hand","people"),"头":("scan-face","people"),"脚":("footprints","people"),
      "腿":("footprints","people"),"心":("heart","emotion"),"血":("droplets","health"),
      "病":("heart-pulse","health"),"药":("pill","health"),
      "医":("hospital","health"),"肚":("heart-pulse","health"),
      "火":("flame","weather"),"冰":("snowflake","weather"),
      "雪":("snowflake","weather"),"雨":("cloud-rain","weather"),
      "风":("wind","weather"),"冷":("snowflake","weather"),
      "热":("thermometer-sun","weather"),"晒":("sun","weather"),
      "前":("arrow-left","travel"),"后":("arrow-right","travel"),
      "东":("compass","travel"),"西":("compass","travel"),
      "南":("compass","travel"),"北":("compass","travel"),
      "来":("map-pin","travel"),"去":("send","travel"),
      "走":("footprints","travel"),"跑":("footprints","sport"),
      "跳":("person-standing","sport"),"骑":("bike","transport"),
      "路":("route","travel"),"车":("car-front","transport"),
      "船":("ship","transport"),"机":("laptop","objects"),
      "局":("landmark","civic"),"校":("school","school"),
      "师":("presentation","school"),"学":("graduation-cap","school"),
      "府":("landmark","civic"),"国":("landmark","civic"),
      "房":("house","objects"),"门":("door-open","objects"),
      "桌":("table","objects"),"椅":("armchair","objects"),
      "吃":("utensils","food"),"喝":("glass-water","food"),
      "买":("shopping-cart","commerce"),"卖":("store","commerce"),
      "钱":("wallet","commerce"),"金":("coins","commerce"),
      "礼":("gift","people"),"笑":("smile","emotion"),
      "怒":("flame","emotion"),"愁":("cloud-rain","emotion"),
      "忙":("briefcase-business","work"),"劳":("briefcase-business","work"),
      "工":("briefcase-business","work"),"商":("store","commerce"),
      "演":("clapperboard","art"),"种":("sprout","nature"),
    }
    for clause in clauses[:2]:
        for char,(icon,kind) in distinctive.items():
            if char in clause:
                return icon,kind
    return "notebook-pen", "abstract"
def font(paths,size):
    for p in paths:
        if Path(p).exists():return ImageFont.truetype(p,size)
    return ImageFont.load_default()
CHINESE=[
 "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
 "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
 "/usr/share/fonts/truetype/arphic/ukai.ttc",
]
FONT_LARGE=font(CHINESE,25)
FONT_SMALL=font(CHINESE,18)
def icon_data(name):
    url=ICONSOURCE+name+".svg"
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Uyghur-Atlas-Illustration/1.0"}),timeout=18) as f:
            svg=f.read().decode("utf8")
        if "<svg" not in svg:raise ValueError("Not SVG")
        svg=svg.replace('stroke="currentColor"', 'stroke="#4B5D58"').replace('stroke-width="2"','stroke-width="1.6"')
        png=cairosvg.svg2png(bytestring=svg.encode("utf8"),output_width=228,output_height=228)
        return Image.open(io.BytesIO(png)).convert("RGBA")
    except Exception:
        return None
def load_icons(mapping):
    wanted={x[0] for x in mapping.values()}|{"notebook-pen"}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        vals=list(pool.map(icon_data,sorted(wanted)))
    result=dict(zip(sorted(wanted),vals))
    print("ICON_LIBRARY",len(result),"ok",sum(v is not None for v in result.values()),flush=True)
    return result
def painter_background(seed,kind):
    rng=random.Random(seed)
    cream,grass,ink=GROUP_COLORS[kind]
    im=Image.new("RGB",(WIDTH,WIDTH),cream)
    d=ImageDraw.Draw(im,"RGB")
    # Coherent translucent gouache-like washes, golden hour at top.
    for y in range(WIDTH):
        t=y/WIDTH
        col=blend(cream,blend(cream,grass,0.36),max(0,(t-.20)*1.25))
        d.line((0,y,WIDTH,y),fill=col)
    sun_x=70+rng.randint(0,250)
    d.ellipse((sun_x-42,22,sun_x+42,106),fill=blend(cream,(255,244,199),.68))
    # Hills, clouds, foliage, and broken pigment strokes.
    for j in range(3):
        wave=[]
        baseline=220+j*31+rng.randint(-12,13)
        for x in range(0,WIDTH+15,12):
            wave.append((x,baseline+int(11*math.sin(x/56+j*1.7))+rng.randint(-4,4)))
        wave.extend([(WIDTH,WIDTH),(0,WIDTH)])
        hill=blend(grass,cream,0.58-j*0.14)
        d.polygon(wave,fill=hill)
    # subtle textured paint dabs at edge and lower half
    for _ in range(150):
        x=rng.randint(-20,WIDTH+20); y=rng.randint(6,WIDTH+15)
        r=rng.randint(2,13)
        original=im.getpixel((min(WIDTH-1,max(0,x)),min(WIDTH-1,max(0,y))))
        color=blend(original,rng.choice([cream,grass,(246,239,210),ink]),rng.uniform(.03,.20))
        d.ellipse((x-r,y-r//3,x+r,y+r//3),fill=color)
    return im
def display_label(zh):
    s=re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", " ", zh).strip()
    s=re.sub(r"（[^）]*）|\([^)]*\)", "", s).strip()
    s=re.split(r"[；;／/，,、]",s)[0].strip()
    return s[:19] if s else "词汇"
def draw_one(row,icon_name,kind,icon_img):
    uid,uy,zh=row[0],row[1],row[2]
    digest=int(hashlib.sha256(uid.encode()).hexdigest()[:12],16)
    rng=random.Random(digest)
    cream,land,ink=GROUP_COLORS[kind]
    im=painter_background(digest,kind)
    d=ImageDraw.Draw(im,"RGBA")
    # Expressive painted frame and light illustration surface, same family as original artwork.
    d.rounded_rectangle((27,56,WIDTH-27,316),radius=46,fill=(254,242,220,195),outline=land+(115,),width=3)
    for j in range(14):
        r=6+rng.randint(0,6)
        cx=rng.randint(32,WIDTH-32);cy=rng.choice([rng.randint(75,105),rng.randint(277,310)])
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=land+(rng.randint(12,42),))
    # Soft pastel blobs behind the hand-drawn pictogram.
    d.ellipse((62,79,WIDTH-62,292),fill=blend(cream,land,.32)+(95,))
    d.ellipse((95,109,WIDTH-95,267),fill=(255,248,229,116))
    if icon_img:
        # Drop a warm, low-opacity offset shadow under the actual semantic icon.
        shadow=Image.new("RGBA",icon_img.size,(0,0,0,0))
        alpha=icon_img.getchannel("A")
        ink_shadow=Image.new("RGBA",icon_img.size,ink+(70,))
        ink_shadow.putalpha(alpha.point(lambda v:int(v*.2)))
        shadow.alpha_composite(ink_shadow)
        im=im.convert("RGBA")
        im.alpha_composite(shadow,(83,105))
        im.alpha_composite(icon_img,(78,99))
        im=im.convert("RGB")
    else:
        # Graceful offline fallback: a pictographic folio with a sunlit center.
        d=ImageDraw.Draw(im,"RGB")
        d.rounded_rectangle((140,148,244,233),radius=12,outline=ink,width=7)
        d.line((192,149,192,233),fill=ink,width=5)
    d=ImageDraw.Draw(im,"RGBA")
    # Label makes ambiguous grammar/abstract-meaning icons identifiable without inventing a scene.
    caption=display_label(zh)
    f=FONT_LARGE if len(caption)<=10 else FONT_SMALL
    maxw=WIDTH-42
    # Center and auto shorten until line fits, retaining primary Chinese gloss.
    while d.textbbox((0,0),caption,font=f)[2]>maxw and len(caption)>2:
        caption=caption[:-1]
    bounds=d.textbbox((0,0),caption,font=f)
    tw=bounds[2]-bounds[0]
    # Pale banner hugs caption without blocking pictorial component.
    d.rounded_rectangle((27,326,WIDTH-27,371),radius=15,fill=(255,244,221,232))
    d.text(((WIDTH-tw)/2,333),caption,font=f,fill=BG_INK+(255,),stroke_width=0)
    # Harmonized perimeter brushmarks.
    d.line([(31,39),(WIDTH-44,39)],fill=land+(120,),width=4)
    return im
def main():
    idxpath=ATLAS/"index.json"
    idx=json.loads(idxpath.read_text("utf8"))
    missing=[r for r in idx["words"] if not (r[6]&1)]
    existing=sum(bool(r[6]&1) for r in idx["words"])
    print("FAST_BEFORE",existing,"MISSING",len(missing),"TOTAL",idx["count"],flush=True)
    if idx["count"]!=1813 or not 900<=len(missing)<=1000:
        raise RuntimeError("Expected approximately 952 missing textbook cards; refusing to change unexpected catalog")
    candidates={r[0]:mark_concept(r[2]) for r in missing}
    icon_imgs=load_icons(candidates)
    generated=[]
    for no,row in enumerate(missing,1):
        uid,uy,zh=row[0],row[1],row[2]
        icon,kind=candidates[uid]
        im=draw_one(row,icon,kind,icon_imgs.get(icon))
        file=ATLAS/"img"/(uid+".webp")
        thumb=ATLAS/"thumb"/(uid+".webp")
        im.save(file,"WEBP",quality=72,method=3)
        im.resize((104,104),Image.Resampling.LANCZOS).save(thumb,"WEBP",quality=70,method=3)
        if file.stat().st_size<1000 or thumb.stat().st_size<600:raise RuntimeError("Bad webp "+uid)
        row[6] |=1
        generated.append({"id":uid,"word":uy,"gloss":zh,"icon":icon,
                          "style":kind,"type":"fast generated meaning-label + semantic pictogram",
                          "full_size":file.stat().st_size,"thumb_size":thumb.stat().st_size})
        if no%200==0:print("GENERATED",no,flush=True)
    idx["illustrated"]=sum(bool(r[6]&1) for r in idx["words"])
    if idx["illustrated"]!=1813 or len(generated)+existing!=1813:raise RuntimeError("Incorrect final illustration count")
    idxpath.write_text(json.dumps(idx,ensure_ascii=False,separators=(",",":")),"utf8")
    byid={g["id"] for g in generated}
    for p in sorted((ATLAS/"entries").glob("*.json"),key=lambda p:int(p.stem)):
        es=json.loads(p.read_text("utf8"))
        for e in es:
            if e["id"] in byid:e["m"] |= 1
        p.write_text(json.dumps(es,ensure_ascii=False,separators=(",",":")),"utf8")
    (ATLAS/"fast-generated-illustrations.json").write_text(
        json.dumps({"count":len(generated),"type":"fast vector/painterly graphical illustrations",
                    "notes":"Symbolic pictograms (not bespoke AI-painted scenes), meaning labels from user-reviewed Chinese glosses",
                    "icon_license":"Lucide ISC",
                    "icon_source":"https://github.com/lucide-icons/lucide",
                    "items":generated},ensure_ascii=False,indent=2),"utf8")
    # A preview grid supports quality checking without opening 952 files.
    preview=Image.new("RGB",(384*4,384*4),(255,246,231))
    for n,row in enumerate(missing[:16]):
        with Image.open(ATLAS/"img"/(row[0]+".webp")) as card:
            preview.paste(card,((n%4)*384,(n//4)*384))
    preview.resize((960,960),Image.Resampling.LANCZOS).save(ROOT/"upstream/public/fast-illustrations-preview.webp","WEBP",quality=78)
    print("FAST_IMAGE_READY",len(generated),"ALL_ILLUSTRATED",idx["illustrated"],
          "CATEGORIES",dict(Counter(c[1] for c in candidates.values())),flush=True)

if __name__=="__main__":main()
