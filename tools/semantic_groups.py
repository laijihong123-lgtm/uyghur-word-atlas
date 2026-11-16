#!/usr/bin/env python3
"""Semantic study order for the user's *existing* Uyghur Word Atlas vocabulary.

The previous 19-category classified reference contributes its topic structure
and grouping principle ONLY; this file never imports or changes a word form,
gloss, or card ID. Subgroup decisions without an exact reference alignment are
heuristic, NOT a claim of expert linguistic verification.
"""
from __future__ import annotations
from collections import Counter
import re
import base64
import zlib
from pathlib import Path

CATEGORY_NAMES = [
    "人称·指示·疑问与功能词",
    "家庭·亲属与人际身份",
    "职业·劳动与组织身份",
    "身体·健康与医疗",
    "服饰·仪容与起居",
    "饮食·食材与烹饪",
    "家居·建筑与生活用品",
    "校园·语言·书写与知识",
    "经济·商业与生产活动",
    "地点·交通·出行与空间",
    "时间·数字·数量与度量",
    "自然·天气·地理与生态",
    "地名·国家·民族与人名",
    "社会·政治·法律与公共生活",
    "文学·艺术·体育与娱乐",
    "思想·情感·沟通与人际行为",
    "常见动作·行为与变化",
    "性质·状态与对比描述",
    "程度·方式·比较与惯用表达",
]
assert len(CATEGORY_NAMES) == 19
CATEGORY_KEYS = [f"cat{i+1:02d}" for i in range(19)]

# Same 19-primary/179-secondary structure as the older classified vocabulary.
# Topic titles are grouped pedagogically; individual website-card placement is
# assessed using the site's own original Chinese gloss, not an older spelling.
SUBGROUPS = [
    "人称、领属与反身|近指｜这、这个、这里|远指｜那、那个、那里|疑问人事与方式|肯定、否定与存在|并列、连接与并进|转折、让步与选择|因果、承接与递进|条件、因果与目的|介词、关系与方向|语气、助词及其他功能词",
    "父母与长辈|兄弟姐妹|夫妻与配偶|儿女和晚辈|亲属与宗族|朋友与熟人|人际称谓与身份|人生阶段与家庭关系",
    "常见职业|教师与教育从业者|医生与专业人员|工人和劳动者|组织及岗位身份|职业活动与劳动",
    "头部和面部|眼耳鼻口|手臂与肢体|身体器官|身体感受|疾病与症状|诊疗与用药|健康与运动",
    "衣服与服饰|鞋帽与穿戴|仪容整理|个人起居",
    "主食与面食|肉类与食材|水果及蔬菜|饮品与茶|烹饪过程|餐具和厨房|吃饭与就餐|味道和饮食感受",
    "家与住房|房间与建筑|家具用品|家用电器|日常器具",
    "校园与学校|教师和学生|课程与课堂|教材与书本|读写与文字|语言及语法|文具和工具|学习与考试|知识与学科|研究与科研|教育机构|说明与解释|图书与阅读",
    "市场和商店|买卖交易|货币与价格|企业与公司|工业和工厂|农业生产|经济和金融|职业经营活动|工具和产品",
    "城市与村落|交通工具|道路与交通|步行与出行|旅行与住宿|方向和方位|远近与位置|进出与来往|场所和设施",
    "基本数字｜一至十|十位与复合数字|百千和更大数|序数与名次|数量与计量|多与少|一点与若干|今天昨天与明天|昼夜与时辰|星期与周|月和季节|年份与年代|时间先后|时间长短和持续|频率与重复|先后顺序|年龄与生日|尺寸和重量|数学与计算|时间其他表达",
    "天气与气候|太阳月亮和星空|山川与河流|植物与树木|花草及果实|动物与昆虫|土地与地貌|环境与生态|自然现象",
    "中国与各地|新疆地区与地名|国家与首都|民族和语种|世界各洲|男性人名|女性人名|专有名称",
    "政府与行政|国家与社会|法律和司法|政治与制度|公共服务|历史和公共生活",
    "文学与作品|音乐与演唱|绘画与艺术|影视与表演|体育与比赛|节日和娱乐",
    "情感与心情|爱与喜欢|思考与认识|记忆与理解|交流与谈话|态度与意见|关系与合作|意愿与希望|信念与价值|尊重与礼貌|冲突与评价|思想及其他活动",
    "走与跑|来与去|进入与离开|拿与放|给予与接受|做与工作|开始与结束|看与听|说与写|改变与发展|运动和操作|其他动作和变化",
    "大小与多少|高低与长短|宽窄与厚薄|新旧与年龄|冷热与温度|颜色与外形|好坏与优劣|快慢与速度|难易与复杂|整齐与整洁|软硬与重量|强弱与力量|美丑与外观|能力与态度|性质与特点|状态与情况|其他描述",
    "程度和强调|比较与最高级|方式和方法|动作速度与节奏|频率和重复|否定与限制|先后与过程|惯用表达",
]
SUBGROUPS = [s.split("|") for s in SUBGROUPS]
assert len(SUBGROUPS)==19, len(SUBGROUPS)
assert [len(s) for s in SUBGROUPS] == [11,8,6,8,4,8,5,13,9,9,20,9,8,6,6,12,12,17,8], [len(s) for s in SUBGROUPS]
assert sum(map(len,SUBGROUPS)) == 179

# First 997 exact historical classification records from the user's old
# classified workbook. These are ONLY category/subgroup hints, never imported
# Uyghur spellings or translations; matched on the website's original record ID.
ORIGINAL_SUBGROUPS_FIRST_11 = [["人称、领属与反身","近指｜这、这个、这里","远指｜那、那个、那里","疑问人事与方式","肯定、否定与存在","并列、连接与并进","转折、让步与选择","因果、承接与递进","条件、因果与目的","范围、选择与指数量词","语气、应答与话语衔接"],["父母与祖辈","兄弟姐妹与子女","婚姻、家庭与亲戚","交友与人际称谓","年龄、性别与生命阶段","人、人类与人物","人民、群众与公众","成员、居民与社会群体"],["学生、教师与学术身份","政务、管理与公共职业","农牧、工矿与生产职业","医护、服务与商业职业","文艺、体育与其他职业","就业与职场日常"],["头面部与五官","身体、体格与身材","四肢、肩背与关节","内脏、血液与组织","生理、感觉与生命","疾病、症状与诊断","治疗、医院与药物","运动保健与体能"],["衣服与民族服饰","鞋帽与随身物品","洗漱、卫生与打扮","日常起居与个人习惯"],["饮食总称与餐次","主食与面点","肉类、畜产品与蛋奶","鲜果、瓜类与果汁","蔬菜、辛香与食材","茶水饮料与调味","烹饪、进食与宴饮","厨房、餐厅与炊具"],["家、房屋与房间","门窗、家具与寝具","家务工具与日用器皿","公共建筑与场馆","建造、设施与维修"],["学校、教室与院系","课堂、课程与考试","学习、研究与认知","书籍、文章与文献","词语、字母与文字","语言、语法与发音","书写、翻译与教学用具","书信、信函与署名","电话、电子与通信设备","新闻、报刊与出版传播","照片、图片与记录资料","声音、声学与音响","学术专业与理论概念"],["市场、买卖与商业往来","货币、价格与财富","农田、麦穗与粮食","种植、树苗与农事","收割、农业劳动与农产","牧业、养殖与畜群","工业、机械与资源","组织、经营与管理","质量、成果与效率"],["道路街巷与地点","东、西、南、北方向","上、下、前、后方位","左、右、里、外与周边","车辆与交通工具","交通设施与旅途","去、来、出发与返回","行走、路过与旅途","空间关系与位置表达"],["基本数字｜零至十","十位与复合数字","百、千、万与更大数","序数与名次｜第几、第X","数量、多寡与计量","多、少与总体数量","一点、一些与若干","今天、昨天与明天","昼夜与时辰","星期与周次","月份与年月","季节、节日与纪念日","从前、过去与以前","以后、未来与随后","经常、偶尔与反复","时间经过与持续表达","前后、持续与频率","尺度、大小与测量","量词、份数与计数","日期、周月与年份"]]
for _i, _subnames in enumerate(ORIGINAL_SUBGROUPS_FIRST_11):
    SUBGROUPS[_i] = _subnames
# The original paper classification includes 179 secondary semantic groups.
assert sum(map(len, SUBGROUPS)) == 179
_ref_path = Path(__file__).resolve().parent.parent / "data/classification_original_first1000.b64"
_ref_raw = zlib.decompress(base64.b64decode(_ref_path.read_text("ascii").strip()))
if len(_ref_raw) != 1826 * 3:
    raise RuntimeError("Original classification reference is malformed")
ORIGINAL_CLASSIFICATION = {}
for _origin in range(1,1826):
    _cat,_sub,_stars = _ref_raw[_origin*3:_origin*3+3]
    if _cat:
        if _cat > 11 or not 1 <= _sub <= len(SUBGROUPS[_cat-1]):
            raise RuntimeError("Invalid original category/subgroup at " + str(_origin))
        ORIGINAL_CLASSIFICATION[str(_origin)] = (_cat-1, _sub-1, _stars)
assert len(ORIGINAL_CLASSIFICATION) == 997

# Website words have priority. Anchors merely decide a *category*, never
# replace the spelling or silently apply a different source's meanings.
WORD_CATEGORY = {}
def anchors(category: int, words: str):
    for w in words.split():
        WORD_CATEGORY[w] = category

anchors(0, "مەن سەن سىز بىز ئۇ بۇ شۇ كىم نېمە نە قايسى قانداق قاچان قانچە نەچچە بار ئەمەس ھەئە ياق كېرەك لازىم بىلەن ۋە لېكىن ئەمما بىراق چۈنكى شۇڭا ئەگەر ياكى ھەم ھەمدە")
anchors(1, "ئانا ئاتا ئاپا دادا ئوغۇل قىز ئاكا ھەدە ئىنى ئۇكا سىڭىل")
anchors(5, "سۇ نان چاي پولۇ لەڭمەن مانتا سامسا ئالما")
anchors(10, "بىر ئىككى ئۈچ تۆت بەش ئالتە يەتتە سەككىز توققۇز ئون بۈگۈن تۈنۈگۈن ئەتە ھازىر بۇلتۇر")
anchors(16, "بار- كەل- كەت- ئال- بەر- قىل- كۆر- تۇر- ئولتۇر- ئۇخلا-")
anchors(17, "ياخشى يامان چوڭ كىچىك يېڭى كونا ئۇزۇن قىسقا")
anchors(18, "بەك ئىنتايىن ناھايىتى ئەڭ تېخىمۇ")

# Order is significant, since textbook glosses can contain multiple senses.
RULES = [
 (12, r"国名|地名|人名|男名|女名|（姓|首都|新疆|乌鲁木齐|阿克苏|北京|上海|深圳|中国|俄罗斯|美国|日本|印度|民族|维吾尔|哈萨克|柯尔克孜|州名|县名|市名|（女名|（男名"),
 (0,  r"代词|指示词|疑问词|助词|语气词|连词|介词|否定词|肯定词|谁|什么|哪个|哪里|哪儿|为何|为什么|疑问|是否|不是|所以|因此|因为|虽然|但是|如果|或者|要么|并且|一起|跟随|与……|有的|每个|没有谁|无论谁|无需|没有必要"),
 (1,  r"父母|父亲|母亲|爸爸|妈妈|儿子|女儿|家人|家庭|爷爷|奶奶|哥哥|姐姐|弟弟|妹妹|舅舅|伯父|亲戚|祖父|祖母|姑姑|嫂子|丈夫|妻子|夫妻|亲属|同胞|朋友|熟人"),
 (2,  r"教师|医生|教授|工人|农民|干部|局长|主任|领导|经理|律师|演员|科学家|作家|劳动者|售货员|消防员|服务员|厨师|学生代表|工作人员|职员|职业|岗位|从事|就业|退休|上班|工作者"),
 (3,  r"身体|眼睛|鼻子|耳朵|嘴巴|牙齿|牙|脚|手臂|手指|头发|胡须|膝盖|脸|面孔|心脏|血|疾病|生病|头痛|治疗|医疗|药|健康|病人|伤口|身体|发烧|疼痛|睡觉|休息|残疾|医院|大夫"),
 (4,  r"服装|衣服|外衣|内衣|衬衣|毛衣|裤|裙|袜|鞋|帽|腰带|围巾|手套|穿着|洗脸|梳头|洗澡|起床|美容|打扮|仪容|睡衣"),
 (5,  r"食物|食材|吃饭|饮食|饭|米|肉|馕|羊肉|牛肉|鸡肉|烤肉|水饺|包子|饺子|面条|拉面|馄饨|水果|苹果|葡萄|西瓜|蔬菜|馓子|抓饭|奶茶|牛奶|咖啡|果汁|饮料|烹饪|厨房|点心|饼干|鸡蛋|小麦|胡萝卜|黄瓜|番茄|西红柿|美味|可口|饭馆|饭店|餐厅|饮水|喝茶"),
 (6,  r"房子|房间|住房|客厅|卧室|家具|窗|门|屋|沙发|桌子|椅子|床|被子|枕头|钥匙|锅|碗|盘子|勺|筷子|电视|冰箱|空调|家电|电器|家居|建筑物|住宅|洗衣机"),
 (7,  r"学校|学习|学科|学生|班级|校园|课堂|教室|教材|课程|课文|课本|考试|作业|书|字|写字|读书|语言|语文|拼写|语法|翻译|词语|词汇|图书|学位|大学|学院|研究|知识|教育|阅读|计算机|文具|铅笔|钢笔|讲解"),
 (8,  r"经济|市场|买|卖|商店|价格|钱|元钱|贸易|货币|商业|企业|工厂|生产|产业|公司|商场|商品|产品|经营|制造|金融|金融机构|农业|农作物|工业|种植|机器|技术|营业|存款|贷款|投资|收入|工资|销售|货物|超市"),
 (9,  r"汽车|公交|火车|飞机|自行车|摩托|交通|公路|道路|街|广场|车站|机场|地铁|路口|旅行|旅馆|酒店|宾馆|邮局|城市|村庄|城市|方向|方位|左边|右边|前面|后面|上面|下面|旁边|里面|外面|中间|距离|远|近|进入|离开|到达|回家|出门|沿着|坐落|地图"),
 (10, r"数|一；|二；|三；|四；|五；|六；|七；|八；|九；|十；|百|千|万|亿|数字|次数|第一|第二|第三|第八|第十|百分|一半|多少个|多于|少于|几次|星期|周末|今天|明天|昨天|前天|后天|早晨|上午|中午|下午|傍晚|晚上|夜晚|年|月|日|日期|时刻|小时|分钟|秒钟|时间|季节|年龄|年度|度量|千克|米；|公斤|升；|岁|刚才|以前|今年|去年|明年"),
 (11, r"自然|天气|气候|晴|下雨|雪|太阳|月亮|星星|天空|云|风|沙漠|树林|森林|草原|植物|动物|鸟|昆虫|花朵|花卉|树木|果园|草|河流|河水|大海|湖泊|山|大地|土壤|地理|地形|环境|地球|生态|岩石|矿物|野生|山谷"),
 (13, r"政府|人民|社会|政治|法律|法规|行政|法院|律师事务所|司法|国家制度|自治区|机关|警察|公安|派出所|公民|政党|党|政策|革命|组织|协会|会议|公共|服务社会|民族团结|地方政府|政权|民主|历史事件|公用|规章"),
 (14, r"文学|艺术|小说|诗|歌|唱歌|音乐|作曲|画家|绘画|美术|电影|电视剧|影视|演员表演|舞台|运动员|体育|足球|篮球|比赛|游戏|娱乐|文化活动|节日|节庆|舞蹈|剧院|戏剧|杂技|展览"),
 (15, r"感情|心情|高兴|快乐|悲伤|伤心|想念|思考|思想|认为|觉得|理解|认识|记忆|回忆|意思|意义|了解|知识见解|观点|意见|想法|尊敬|尊重|礼貌|喜欢|热爱|爱好|希望|愿望|祝福|担心|害怕|生气|激动|交流|聊天|说话|沟通|谈话|交往|互相|合作|关系|信任|相信"),
 (18, r"非常|特别|很；|十分|极其|更加|更；|最；|最为|稍微|逐渐|越来越|程度|有时|偶尔|偶然|不断地|一直|频繁|经常|常常|马上|立即|突然|仍然|而且|无论|各种各样|好不容易|从头到尾|一边……|按照|根据|这样|那样|如此|方法|方式|习惯用语|谚语|惯用|副词"),
 (17, r"形容词|漂亮|美丽|英俊|寒冷|炎热|温暖|干燥|潮湿|大；|小；|多；|少；|长的|短的|高的|低的|宽阔|狭窄|厚|薄|软|硬|黑色|白色|红色|蓝色|黄色|绿色|颜色|圆形|方形|扁平|锋利|优秀|良好|低劣|强壮|无力|清楚|模糊|安静|吵闹|整洁|安全|危险|真实|错误|正确|方便|容易|困难|复杂|简单|特殊|重要|相同|不一样|相反|亲切|勤奋|认真|特别的"),
 (16, r"动作|行为|走|跑|来；|去；|回；|送；|带；|拿；|放；|给；|收；|做；|干；|开始|结束|停止|变化|改变|增长|提高|降低|起立|坐下|移动|前进|离去|走路|活动|开；|关；|用；|找到|发现|发生|进行"),
]

# Limited exact aliases to keep frequently confused near-words in one pocket.
WORD_SUBGROUP = {
    "مەن":0,"سەن":0,"سىز":0,"بىز":0,"ئۇ":0,
    "بۇ":1,"ماۋۇ":1,"مۇشۇ":1,"شۇ":2,"ئاۋۇ":2,
    "كىم":3,"نېمە":3,"نە":3,"قايسى":3,"قانداق":3,"قاچان":3,
    "بار":4,"ئەمەس":4,"ھەئە":4,"ياق":4,
    "لېكىن":6,"بىراق":6,"ئەمما":6,"ياكى":6,
    "چۈنكى":7,"شۇڭا":7,
}
NUMBER_SUBGROUP = {
    "بىر":0,"ئىككى":0,"ئۈچ":0,"تۆت":0,"بەش":0,
    "ئالتە":0,"يەتتە":0,"سەككىز":0,"توققۇز":0,"ئون":0,
    "بۈگۈن":7,"تۈنۈگۈن":7,"ئەتە":7,"بۇلتۇر":11,
}

def _gloss_text(row: dict) -> str:
    return "；".join(row["senses"]).replace("①","").replace("②","").replace("③","").replace("④","")

def category_for(row: dict) -> int:
    w=row["uy"]
    if w in WORD_CATEGORY:
        return WORD_CATEGORY[w]
    zh=_gloss_text(row)
    # Explicit names and place names should not be misclassified as food,
    # time or common objects merely because one character overlaps.
    for cat,pattern in RULES:
        if re.search(pattern,zh):
            return cat
    if w.endswith("-"):
        return 16
    if any(x in zh for x in ("的","得","颜色","状","形","不良","丰富","稀","浓","浅","深")):
        return 17
    if any(x in zh for x in ("怎么","怎样","极","总是","一向","每","突然","刚","已经")):
        return 18
    if any(x in zh for x in ("事情","情况","心","想","意识","经验","认识","变化")):
        return 15
    return 16 if w.endswith(("ماق","مەك")) else 15

def subgroup_for(row: dict, cat: int) -> int:
    w=row["uy"]
    if cat==0 and w in WORD_SUBGROUP:
        return WORD_SUBGROUP[w]
    if cat==10 and w in NUMBER_SUBGROUP:
        return NUMBER_SUBGROUP[w]
    zh=_gloss_text(row)
    groups=SUBGROUPS[cat]
    best_idx=len(groups)-1
    best_score=0
    for i,name in enumerate(groups):
        label=re.sub(r"^[^｜]*｜","",name)
        parts=[p.strip() for p in re.split(r"[、，,与及和／｜·\s]+",label) if len(p.strip())>=2]
        score=sum((2 if len(p)>=3 else 1) for p in parts if p in zh)
        if score>best_score:
            best_score=score
            best_idx=i
    return best_idx

def order_by_semantics(dataset: list[dict], difficulty_fn):
    """Stable semantic ordering; same website cards and source glosses."""
    notes=[]
    for row in dataset:
        original_number=str(row["sources"][0][0])
        historical=ORIGINAL_CLASSIFICATION.get(original_number)
        if historical:
            cat,sub,priority=historical
            source="original_classification"
        else:
            cat=category_for(row)
            sub=subgroup_for(row,cat)
            priority=0
            source="inferred_from_site_gloss"
        row["semantic_category"]=cat
        row["semantic_subgroup"]=sub
        row["semantic_subgroup_name"]=SUBGROUPS[cat][sub]
        row["semantic_match_source"]=source
        row["semantic_priority"]=priority
        # Smaller score = easier, and the actual vocabulary remains the website's.
        row["difficulty"]=difficulty_fn(row)[0]
        notes.append(row)
    # Group by category, then meaning pocket, THEN difficulty.
    result=sorted(notes,key=lambda r:(
        r["semantic_category"],r["semantic_subgroup"],
        -r["semantic_priority"],r["difficulty"],r["seq"]
    ))
    assert len(result)==len(dataset)==1813
    assert len({r["seq"] for r in result})==1813
    groups=Counter(r["semantic_category"] for r in result)
    if set(groups)!=set(range(19)):
        raise RuntimeError(f"Not all 19 categories have words: {groups}")
    return result
