#!/usr/bin/env python3
"""Add a first draft of a Uyghur example for EVERY reviewed word card.

Never touches existing card IDs, glosses, ordering, FSRS states, or audio.
Curated reading examples (created by add_reading.py) take precedence.
Automatic text is explicitly marked as a draft requiring native proofreading;
complex function-word and idiom fallbacks are word-mention sentences, NOT
pretended usage examples. An override table can replace these later.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from port_uyghur import to_uly

HOME = Path(__file__).resolve().parent.parent
ATLAS = HOME / "upstream/public/atlas"

# Specific, beginner-friendly usage, rather than repeating generic templates.
MANUAL = {
    "مەن": ("مەن ھەر كۈنى ئۇيغۇرچە ئۆگىنىمەن.", "我每天学习维吾尔语。"),
    "سەن": ("سەن بۈگۈن نېمە قىلىسەن؟", "你今天做什么？"),
    "سىز": ("سىز نەگە بارىسىز؟", "您去哪里？"),
    "ئۇ": ("ئۇ بۈگۈن مەكتەپكە باردى.", "他/她今天去学校了。"),
    "بىز": ("بىز بىللە كىتاب ئوقۇيمىز.", "我们一起读书。"),
    "بۇ": ("بۇ مېنىڭ كىتابىم.", "这是我的书。"),
    "شۇ": ("شۇ ئۆي بەك چوڭ.", "那所房子很大。"),
    "كىم": ("بۇ كىم؟", "这是谁？"),
    "نېمە": ("بۇ نېمە؟", "这是什么？"),
    "قايسى": ("سىز قايسى كىتابنى ئوقۇۋاتىسىز؟", "您正在读哪本书？"),
    "قانداق": ("بۈگۈن ھاۋا قانداق؟", "今天天气怎么样？"),
    "قاچان": ("سىز قاچان كېلىسىز؟", "您什么时候来？"),
    "قانچە": ("بۇ قانچە پۇل؟", "这个多少钱？"),
    "نەچچە": ("ھازىر سائەت نەچچە؟", "现在几点？"),
    "بار": ("بۇ يەردە سۇ بار.", "这里有水。"),
    "ئەمەس": ("بۇ مېنىڭ كىتابىم ئەمەس.", "这不是我的书。"),
    "ھەئە": ("ھەئە، مەن بىلىمەن.", "是的，我知道。"),
    "ياق": ("ياق، مەن بارمايمەن.", "不，我不去。"),
    "بىلەن": ("مەن دوستۇم بىلەن كەلدىم.", "我和朋友一起来了。"),
    "ۋە": ("ئاپام ۋە دادام ئۆيدە.", "妈妈和爸爸都在家。"),
    "لېكىن": ("مەن باردىم، لېكىن ئۇ كەلمىدى.", "我去了，但是他没来。"),
    "چۈنكى": ("مەن ئۆيدە قالدىم، چۈنكى ھاۋا سوغۇق.", "我待在家，因为天气冷。"),
    "شۇڭا": ("بۈگۈن يامغۇر ياغدى، شۇڭا ئۆيدە قالدۇق.", "今天下雨了，所以我们待在家里。"),
    "ئەگەر": ("ئەگەر ۋاقتىڭىز بولسا، كېلىڭ.", "如果您有时间，请过来。"),
    "ياكى": ("چاي ياكى سۇ ئىچەمسىز؟", "您喝茶还是水？"),
    "ياخشى": ("بۇ كىتاب ياخشى.", "这本书很好。"),
    "يامان": ("بۇ يامان ئادەت.", "这是坏习惯。"),
    "چوڭ": ("بۇ ئۆي چوڭ.", "这所房子很大。"),
    "كىچىك": ("بۇ ئۆي كىچىك.", "这所房子很小。"),
    "يېڭى": ("بۇ مېنىڭ يېڭى كىتابىم.", "这是我的新书。"),
    "كونا": ("بۇ كونا ئۆي.", "这是一所旧房子。"),
    "ئۇزۇن": ("بۇ يول ئۇزۇن.", "这条路很长。"),
    "قىسقا": ("بۇ يول قىسقا.", "这条路很短。"),
    "يىل": ("بىر يىلدا ئون ئىككى ئاي بار.", "一年有十二个月。"),
    "ئاي": ("بىر يىلدا ئون ئىككى ئاي بار.", "一年有十二个月。"),
    "ھەپتە": ("بىر ھەپتىدە يەتتە كۈن بار.", "一周有七天。"),
    "ھازىر": ("مەن ھازىر ئۆيدە.", "我现在在家。"),
    "بۈگۈن": ("بۈگۈن ھاۋا ياخشى.", "今天天气很好。"),
    "ئەتە": ("ئەتە مەن مەكتەپكە بارىمەن.", "明天我去学校。"),
    "تۈنۈگۈن": ("تۈنۈگۈن دوستۇم كەلدى.", "昨天我的朋友来了。"),
    "بەك": ("بۇ تاماق بەك ياخشى.", "这顿饭很好。"),
    "ناھايىتى": ("بۇ كىتاب ناھايىتى ياخشى.", "这本书非常好。"),
    "ئىنتايىن": ("بۇ ئىش ئىنتايىن مۇھىم.", "这件事非常重要。"),
    "كۆپ": ("بۇ يەردە ئادەم كۆپ.", "这里人很多。"),
    "ئاز": ("مېنىڭ ۋاقتىم ئاز.", "我的时间很少。"),
    "كېرەك": ("ماڭا كىتاب كېرەك.", "我需要一本书。"),
    "لازىم": ("ماڭا سۇ لازىم.", "我需要水。"),
    "ئەڭ": ("بۇ ئەڭ ياخشى كىتاب.", "这是最好的书。"),
    "ھەر": ("ھەر كۈنى كىتاب ئوقۇيمەن.", "我每天读书。"),
    "ھەم": ("مەن ھەم ئوقۇيمەن، ھەم ئىشلەيمەن.", "我既学习也工作。"),
    "دوست": ("دوستۇم بۈگۈن كەلدى.", "我的朋友今天来了。"),
    "ئالما": ("مەن ئالما سېتىۋالدىم.", "我买了苹果。"),
    "مەكتەپ": ("مەن بۈگۈن مەكتەپكە بارىمەن.", "我今天去学校。"),
    "كىتاب": ("مەن كىتاب ئوقۇيمەن.", "我读书。"),
    "ئۇيغۇرچە": ("مەن ئۇيغۇرچە سۆزلەيمەن.", "我说维吾尔语。"),
    "مۇھىم": ("بۇ ئىنتايىن مۇھىم ئىش.", "这是一件非常重要的事。"),
    "تېز": ("ئۇ تېز ماڭىدۇ.", "他走得快。"),
    "ئاستا": ("ئۇ ئاستا ماڭدى.", "他走得慢。"),
    "بىر": ("بۇ يەردە بىر كىتاب بار.", "这里有一本书。"),
    "ئىككى": ("بۇ يەردە ئىككى كىتاب بار.", "这里有两本书。"),
    "ئۈچ": ("بۇ يەردە ئۈچ كىتاب بار.", "这里有三本书。"),
    "تۆت": ("بۇ يەردە تۆت كىتاب بار.", "这里有四本书。"),
    "بەش": ("بۇ يەردە بەش كىتاب بار.", "这里有五本书。"),
    "ئالتە": ("بۇ يەردە ئالتە كىتاب بار.", "这里有六本书。"),
    "يەتتە": ("بۇ يەردە يەتتە كىتاب بار.", "这里有七本书。"),
    "ئون": ("بۇ يەردە ئون كىتاب بار.", "这里有十本书。"),
    "پۇل": ("مېنىڭ پۇلۇم بار.", "我有钱。"),
    "سۇ": ("مەن سۇ ئىچىمەن.", "我喝水。"),
    "نان": ("مەن نان يەيمەن.", "我吃馕。"),
    "چاي": ("مەن چاي ئىچىمەن.", "我喝茶。"),
    "ئوقۇغۇچى": ("مەن ئوقۇغۇچى.", "我是一名学生。"),
    "ئوقۇتقۇچى": ("بۇ بىزنىڭ ئوقۇتقۇچىمىز.", "这是我们的老师。"),
    "ئائىلە": ("بۇ مېنىڭ ئائىلەم.", "这是我的家人。"),
    "يۈز": ("ئۇنىڭ يۈزى قىزاردى.", "他的脸红了。"),
    "بۇرۇن": ("ئۇ بۇرۇن بۇ يەردە تۇراتتى.", "他以前住在这里。"),
    "بار-": ("مەن مەكتەپكە باردىم.", "我去了学校。"),
    "كەل-": ("ئۇ بۈگۈن كەلدى.", "他今天来了。"),
    "كەت-": ("ئۇ ئۆيگە كەتتى.", "他回家去了。"),
    "ئوقۇ-": ("مەن كىتاب ئوقۇيمەن.", "我读书。"),
    "ياز-": ("مەن خەت يازدىم.", "我写了一封信。"),
    "ئاڭلا-": ("مەن مۇزىكا ئاڭلايمەن.", "我听音乐。"),
    "سۆزلە-": ("ئۇ ئۇيغۇرچە سۆزلەيدۇ.", "他会说维吾尔语。"),
    "ئۆگەن-": ("بىز ئۇيغۇرچە ئۆگىنىمىز.", "我们学习维吾尔语。"),
    "ئاچ-": ("ئۇ ئىشىكنى ئاچتى.", "他打开了门。"),
    "يە-": ("ئۇ نان يېدى.", "他吃了馕。"),
    "بەر-": ("ئۇ ماڭا كىتاب بەردى.", "他给了我一本书。"),
    "ئال-": ("ئۇ كىتاب ئالدى.", "他买了一本书。"),
    "قىل-": ("ئۇ ئۆي ئىشلىرىنى قىلدى.", "他做了家务。"),
    "ياغ-": ("بۈگۈن يامغۇر ياغدى.", "今天下雨了。"),
    "ئۇخلا-": ("بالا ئۇخلىدى.", "孩子睡着了。"),
    "ئىشلە-": ("ئۇ ئىشخانىدا ئىشلىدى.", "他在办公室工作。"),
    "ئويلا-": ("ئۇ بۇ ئىشنى ئويلىدى.", "他考虑了这件事。"),
    "كۆر-": ("ئۇ باغدىكى گۈللەرنى كۆردى.", "他看见了果园里的花。"),
    "ئولتۇر-": ("ئۇ ئورۇندۇقتا ئولتۇردى.", "他坐在椅子上。"),
    "ئۆيگە قايت-": ("ئۇ ئۆيگە قايتتى.", "他回家了。"),
    "بول-": ("ئۇ ياخشى ئوقۇغۇچى بولدى.", "他成了一名好学生。"),
    "تۇر-": ("ئۇ ئورنىدىن تۇردى.", "他站了起来。"),
    "چۈش-": ("ئۇ ئاپتوبۇستىن چۈشتى.", "他下了公共汽车。"),
    "يۇ-": ("ئۇ قولىنى يۇدى.", "他洗了手。"),
    "سېتىۋال-": ("ئۇ يېڭى كىتاب سېتىۋالدى.", "他买了一本新书。"),
    "بىل-": ("مەن بۇنى بىلىمەن.", "我知道这个。"),
    "كۈل-": ("ئۇ كۈلدى.", "他笑了。"),
    "ياخشى كۆر-": ("مەن ئانا تىلىمنى ياخشى كۆرىمەن.", "我热爱自己的母语。"),
    "ئۆچمەس": ("بۇ ئۆچمەس خاتىرە.", "这是一段不可磨灭的记忆。"),
    "قەدىمكى": ("بۇ قەدىمكى شەھەر.", "这是一座古城。"),
    "دورىلىق": ("بۇ دورىلىق ئۆسۈملۈك.", "这是一种药用植物。"),
    "تۈپتۈز": ("بۇ يول تۈپتۈز.", "这条路很平坦。"),
}
# Some Uyghur a/e vowels raise before past-tense suffixes. Other unreviewed
# conjugations are only drafts, never presented as human-verified grammar.
IRREGULAR_PAST = {
    "دە": "دېدى", "يە": "يېدى", "ئاڭلا": "ئاڭلىدى",
    "سۆزلە": "سۆزلىدى", "باشلا": "باشلىدى", "يۇ": "يۇدى",
    "ئويلا": "ئويلىدى", "ئىشلە": "ئىشلىدى", "ئۆگەن": "ئۆگەندى",
    "ئوقۇ": "ئوقۇدى", "كەل": "كەلدى", "بار": "باردى",
    "كەت": "كەتتى",
}
VOICELESS = set("پفتكسقچشخھ")
NUMBER = re.compile(r"^[零一二三四五六七八九十百千万亿两]+$")
PROPER = re.compile(r"男名|女名|人名|县名|地名|市名|（姓")
PLACE = re.compile(r"城市|国家|州|县|首都|省|自治区|地区|王府井|大学|学院|研究所|博物馆|图书馆|历史遗迹|颐和园|长城|大陆|亚洲|欧洲|美洲|大洋洲|非洲|中国|日本|北京|新疆|乌鲁木齐|阿克苏|布哈拉|邮局|商场|市场|旅馆")
FOOD = re.compile(r"苹果|香蕉|葡萄|西瓜|杏|石榴|馕|饺子|抓饭|米饭|拉面|面条|蔬菜|胡萝卜|白菜|洋葱|黄瓜|西红柿|辣椒|水果|饭菜|羊肉|牛肉|鸡肉|鸡蛋|包子|蛋糕|糖果|点心|饼干|牛奶|糕点|小麦|玉米|大米|面粉|核桃|干果|无花果")
DRINK = re.compile(r"饮用水|奶茶|茶叶|果汁|饮料|咖啡|乳汁|牛奶|茶$|水$")
CREATURE = re.compile(r"小狗|小猫|山羊|绵羊|兔子|狮子|老虎|狼|麻雀|昆虫|蝴蝶|蚊子|牲畜|羊羔|牛犊|骆驼|鸟儿|老鹰|猫|狗|鸡|狐狸|青蛙|动物|植物|花卉|花朵|树木|杨树|柏树|树叶|竹林|果园|种子|麦穗")
PERSON = re.compile(r"父亲|爸爸|母亲|妈妈|祖父|爷爷|奶奶|外公|哥哥|姐姐|弟弟|妹妹|老师|教师|学生|孩子|男孩|女孩|姑姑|叔叔|舅舅|嫂子|阿姨|朋友|演员|医生|厨师|科学家|作家|教授|劳动者|工人|售货员|农民|干部|领导|居民|群众|旅客|客人|主人|男人|女人")
OBJECT = re.compile(r"衣服|鞋|帽|裤|袜|手套|毛衣|衬衣|制服|围巾|裙|外套|书|本子|课本|作业本|铅笔|钢笔|纸|文件|机器|设备|器械|工具|电器|手机|电话|照相机|电脑|计算机|电视|电池|火车|汽车|自行车|书包|箱子|手提包|桌|椅|床|沙发|衣柜|家具|窗|门|玻璃|照片|相片|镜子|药物|笔记本|地图|塑料|棉花|木材|瓷器|陶器|铁器|钱|票|钥匙|灯|碗|盘|锅|刀|勺|杯|筷|钟表")
# Adjectival glosses can be predicates, but physical adjectives need an
# appropriate noun. Do not put "flat" or "cold" as attributes of "a task".
PROPERTY = re.compile(r"平坦|平整|宽|窄|长|短|高|矮|低|厚|薄|软|硬|冷|热|温暖|寒冷|干燥|潮湿|晴朗|碧绿|白色|黑色|红色|蓝色|黄色|卷曲|弯曲|尖锐")
ADJECTIVE = re.compile(r"的|很|非常|优良|良好|丰富|独特|巨大|珍贵|严格|漂亮|美丽|洁净|牢固|安全|艰难|容易|困难|重要|强壮|柔和|柔软|崇高|温柔|强烈|严重|新鲜|整洁|聪明|勤奋|活泼|善良|公平|熟练|安静|清楚|清晰|有趣")
FUNCTION = re.compile(r"介词|连词|语气词|助词|代词|副词|感叹词|问候语|语气|词尾|后缀|或者|要么|因为|所以|相反|同时|那样|这样|究竟|怎么|假如|虽然|如果|总之|但是|而且|即使|不仅|根据|按照|往北|往南|往东|往西|随着|无论|直到|稍微|尤其|逐渐|首先|接着|其次|从此|从前|过去|之前|以后|至于|只有|一方面|另一方面|所有|每一|每个|恰好|甚至|或多或少|好不容易|难得|有时|有时候|从头到尾|不一定|原来|已经|越来越|向|朝|把|被")
FUNCTION_ENDINGS = ("قاراپ","كېيىن","توغرىسىدا","ئۈچۈن","بىلەن","مۇ","بى","يا","دەپ","بولۇپ","ئاساسەن","كېلىپ","بېرىپ","چىقىپ","كەتكەندە","چاغدا","ھالدا")
ANOMALOUS_ADJECTIVES = {"ئىنتايىن","ئىنتايىنمۇ","قەدىمكى","دورىلىق","تۈپتۈز","ئۆچمەس"}

def first_gloss(zh):
    zh = re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩]", "", zh).split("②")[0]
    return re.split(r"[；;,，。／/]", zh, maxsplit=1)[0].strip()[:50]

def past(stem):
    tokens = stem.split(" ")
    root = tokens.pop()
    if root in IRREGULAR_PAST:
        form = IRREGULAR_PAST[root]
    elif root.endswith(("لا","لە")):
        # Many two-syllable -la/-le stems show stem-final a/e raising.
        form = root[:-1] + "ىدى"
    else:
        form = root + ("تى" if root[-1] in VOICELESS else "دى")
    return " ".join(tokens+[form])

def lexical(word, meaning):
    return (f"ئوقۇتقۇچى بۈگۈن «{word}» دېگەن سۆزنى چۈشەندۈردى.",
            f"老师今天讲解了“{word}”这个词（{meaning}）。", "word_mention")

def create_example(word, full_zh):
    meaning = first_gloss(full_zh)
    if word in MANUAL:
        ug, zh = MANUAL[word]
        return ug, zh, "manual"
    if word.endswith("-"):
        # Compounds preserve their object phrase; conjugate only the final verb.
        return f"ئۇ {past(word[:-1])}.", f"他/她{meaning}了。", "verb_draft"
    if PROPER.search(full_zh):
        name = re.sub(r"（[^）]+名）", "", meaning)
        return f"{word} بۈگۈن كەلدى.", f"{name}今天来了。", "name_context"
    if NUMBER.fullmatch(meaning) and len(word.split()) <= 4:
        return f"بۇ يەردە {word} كىتاب بار.", f"这里有{meaning}本书。", "number_context"
    if DRINK.search(meaning) and len(word.split()) <= 3:
        return f"مەن بۈگۈن {word} ئىچتىم.", f"我今天喝了{meaning}。", "beverage_context"
    if FOOD.search(meaning) and len(word.split()) <= 3:
        return f"مەن بۈگۈن {word} سېتىۋالدىم.", f"我今天买了{meaning}。", "food_context"
    if CREATURE.search(meaning) and len(word.split()) <= 3:
        return f"مەن باغدا {word} كۆردۈم.", f"我在果园里看见了{meaning}。", "nature_context"
    if PERSON.search(meaning) and len(word.split()) <= 3:
        return f"{word} بۈگۈن بىز بىلەن سۆزلەشتى.", f"{meaning}今天和我们交谈了。", "person_context"
    if PLACE.search(meaning) and len(word.split()) <= 5:
        return f"بىز {word} توغرىسىدا ئوقۇدۇق.", f"我们阅读了关于{meaning}的内容。", "place_context"
    if PROPERTY.search(meaning) and len(word.split()) == 1:
        if any(x in meaning for x in ("平坦","平整","宽","窄","长","短")):
            return f"بۇ يول {word}.", f"这条路{meaning}。", "property_context"
        if any(x in meaning for x in ("晴朗","白色","黑色","红色","蓝色","黄色","碧绿")):
            return f"بۇ گۈل {word}.", f"这朵花{meaning}。", "property_context"
        return f"بۇ ئۆي {word}.", f"这所房子{meaning}。", "property_context"
    if FUNCTION.search(meaning) or any(word.endswith(x) for x in FUNCTION_ENDINGS):
        return lexical(word, meaning)
    if ADJECTIVE.search(meaning) and len(word.split()) == 1 and len(meaning) <= 18 and "（" not in meaning:
        return f"بۇ ئىش {word}.", f"这件事{meaning.rstrip('的')}。", "quality_context"
    if OBJECT.search(meaning) and len(word.split()) <= 4:
        return f"بۇ {word} يېڭى.", f"这个{meaning}是新的。", "object_context"
    # Remaining nominal concepts: subject + "about" + predicate; no invented
    # case or possessive endings on the word, which protects textbook spelling.
    if (len(word.split()) > 5 or
        re.search(r"副词|助词|连词|动词|形容词|……|…|表达|表示|用在|表明|前缀", full_zh)):
        return lexical(word, meaning)
    return f"بىز {word} توغرىسىدا پاراڭلاشتۇق.", f"我们谈论了{meaning}。", "topic_context"

def main():
    idx_path = ATLAS/"index.json"
    idx = json.loads(idx_path.read_text("utf-8"))
    if idx.get("count") != 1813 or idx.get("id") != "uyghur-textbook-reviewed-20261113":
        raise RuntimeError("Not the approved 1813-card Uyghur dataset")
    rows = list(csv.DictReader((HOME/"data/textbook_reviewed.tsv").open(encoding="utf-8-sig"), delimiter="\t"))
    original = {}
    for row in rows:
        original.setdefault(row["维吾尔语"], row)
    if len(rows) != 1817 or len(original) != 1813:
        raise RuntimeError("Vocabulary fidelity check failed")
    sources = {}
    kinds = Counter()
    for word,row in original.items():
        ug, zh, kind = create_example(word, row["中文释义"])
        if not ug or not zh:
            raise RuntimeError("Missing sentence for "+word)
        sources["tb"+str(row["序号"]).zfill(4)] = {"en":ug,"zh":zh,"uly":to_uly(ug),"source":kind}
        kinds[kind] += 1
    paths = sorted((ATLAS/"entries").glob("*.json"), key=lambda p: int(p.stem))
    count = set()
    autoinserted = 0
    for path in paths:
        chunk = json.loads(path.read_text("utf-8"))
        for entry in chunk:
            id = entry["id"]
            sentence = sources.get(id)
            if sentence is None or entry["w"] not in original:
                raise RuntimeError("Unmapped card: "+id)
            count.add(id)
            if not entry["ex"]:
                entry["ex"].append(sentence)
                autoinserted += 1
        path.write_text(json.dumps(chunk,ensure_ascii=False,indent=2), "utf-8")
    if len(count) != 1813:
        raise RuntimeError("Incomplete example card coverage: "+str(len(count)))

    entries = [e for p in paths for e in json.loads(p.read_text("utf-8"))]
    if not all(e["ex"] and all(x["en"] and x["zh"] and x.get("uly") for x in e["ex"]) for e in entries):
        raise RuntimeError("Empty or untranslated examples remain")
    # Word sheet and reading-room example IDs must stay aligned to progress bookmarks.
    examples = [
        {"id":e["id"]+":"+str(i),"wordId":e["id"],"word":e["w"],
         "ug":x["en"],"uly":x["uly"],"zh":x["zh"],"source":x.get("source","curated")}
        for e in entries for i,x in enumerate(e["ex"])
    ]
    (ATLAS/"examples.json").write_text(json.dumps(examples,ensure_ascii=False,separators=(",",":")), "utf-8")
    idx["examples"] = len(examples)
    idx_path.write_text(json.dumps(idx,ensure_ascii=False,separators=(",",":")), "utf-8")
    report = {
        "wordCards":len(count),"cardWithExample":len(count),"totalExamples":len(examples),
        "newDraftExamples":autoinserted,"templateCategories":dict(kinds),
        "note":"Generated example drafts are not certified natural Uyghur. "
               "The word-mention examples illustrate recognition, not authentic lexical usage.",
    }
    (ATLAS/"example-coverage-report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),"utf-8")
    print("ALL_CARD_EXAMPLES_PRESENT",len(count),"EXAMPLES",len(examples),
          "ADDED_DRAFTS",autoinserted,"CATEGORIES",dict(kinds),flush=True)

if __name__ == "__main__":
    main()
