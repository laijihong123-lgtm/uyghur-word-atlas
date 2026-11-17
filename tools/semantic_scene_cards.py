#!/usr/bin/env python3
"""Meaning-first, low-resolution illustrated flashcards.

Pictures are drawn with Pillow as small retro scene studies, not as separate
ImageGen paintings. An explicit meaning table selects a recognizable subject
or two-person action scene. Unknown grammatical / ambiguous vocabulary gets
a non-misleading typographic meaning card, never an unrelated generic icon.
The source Chinese gloss and Uyghur card text are not modified.
"""
from __future__ import annotations
import hashlib, math, random, re, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

SIZE=384
INK=(73,80,84)
PEACH=(242,208,169)
WALL=(249,224,187)
EARTH=(200,155,115)
GREEN=(125,157,116)
BLUE=(116,165,185)
DARKBLUE=(77,110,132)
YELLOW=(230,181,95)
CREAM=(247,234,205)
PALETTE=[(202,128,86),(98,143,139),(202,159,93),(117,143,173),(140,122,150)]
FUNCTION_EXACT={
  "بولىدۇ":"permission","ماقۇل":"permission","ماقۇل بول-":"permission",
  "مەيلى":"permission","ياق":"refuse","ھەئە":"permission",
  "لېكىن":"contrast","بىراق":"contrast","ئەمما":"contrast",
  "چۈنكى":"reason","شۇڭا":"reason","ئەگەر":"condition","ياكى":"choice",
  "ئەمەس":"refuse","كېرەك":"need","لازىم":"need",
}
# First matching gloss term wins. Avoid accidental punctuation and near-word
# token collisions by checking for the strongest, longest keys before generic.
SCENES=[
 ("骆驼|驼","camel"),
 ("饺子|水饺|馄饨|包子|面片","dumplings"),
 ("钢笔|圆珠笔|铅笔|毛笔","pen"),
 ("茶叶|喝茶|红茶|绿茶|奶茶|茶水|茶","tea"),
 ("咖啡","coffee"),
 ("蛋糕|糕点|点心","cake"),
 ("米饭|抓饭|饭菜|饭","rice"),
 ("拉面|面条|烩面|凉面|面食","noodles"),
 ("馕|面包|烤饼","bread"),
 ("牛奶|酸奶|奶酪","milk"),
 ("烤肉|羊肉|牛肉|肉类","meat"),
 ("苹果","apple"),("香蕉","banana"),("梨子|梨","pear"),
 ("水果|石榴|橘子|橙子|葡萄|西瓜|哈密瓜|桃子|杏","fruit"),
 ("洋葱|白菜|蔬菜|胡萝卜|番茄|西红柿|黄瓜|土豆|茄子|萝卜|青菜","vegetables"),
 ("鱼","fish"),
 ("骏马|骑马|马匹|马","horse"),("奶牛|黄牛|牛","cow"),
 ("羊","sheep"),("鸡","chicken"),("鸭","duck"),("鹅","goose"),
 ("猫","cat"),("狗","dog"),("兔","rabbit"),
 ("鸟|麻雀|鸽子","bird"),("蜜蜂|昆虫|蚂蚁","bug"),
 ("花|玫瑰","flower"),("树|树林|森林|柏树","tree"),
 ("草|苗|植物|种植","sprout"),("山|高山|山脉","mountain"),
 ("河流|湖泊|海洋|池塘|河水","river"),
 ("沙漠|沙丘","desert"),("下雪|冰雪|雪","snow"),
 ("下雨|雨天|雨水|暴雨","rain"),
 ("天气|阳光|太阳|晴朗","sun"),
 ("月亮|星空|夜晚|星星","night"),
 ("飞机|航空|机场","airplane"),("火车|铁路|列车","train"),
 ("公共汽车|公交车|巴士","bus"),("自行车|骑车","bicycle"),
 ("摩托车","motorcycle"),("轮船|游船|船舶|小船","boat"),
 ("出租车|小汽车|汽车|轿车","car"),
 ("道路|公路|路口|桥梁|马路","road"),
 ("住房|住宅|房子|房屋|家里|家","house"),
 ("教室|课堂|学校|小学|中学|大学|学院|校园|教学楼","school"),
 ("医院|诊所|医务|医疗","hospital"),
 ("商店|超市|商场|买卖|市场","shop"),
 ("饭店|食堂|餐厅|饭馆|餐馆","restaurant"),
 ("银行|金融|贷款|存款","bank"),
 ("政府|税务局|办公厅|派出所|公安局|行政局|机关","office"),
 ("城市|县城|城镇|街道","town"),
 ("村庄|村落|农村|乡村","village"),
 ("书|教材|课本|词典|报纸|小说|阅读","book"),
 ("纸|文书|资料|文件|信件","letter"),
 ("手机|电话|打电话|通话","phone"),
 ("笔记本电脑|计算机|电脑|键盘","computer"),
 ("钥匙","key"),("行李|箱子|书包|背包|钱包|提包","bag"),
 ("钟表|时钟|手表|时间","clock"),
 ("桌子|课桌|书桌","table"),("椅子|凳子","chair"),
 ("窗户|窗帘","window"),("开门|关门|房门|门口|门","door"),
 ("床|睡觉|被子|枕头","bed"),
 ("衣服|衬衫|毛衣|大衣|裙子|裤子|外套|穿衣","clothing"),
 ("帽子|头巾|花帽","hat"),("鞋|靴子|袜子","shoes"),
 ("水杯|杯子|喝水|饮水|矿泉水","water"),
 ("碗|盘|餐具","plate"),("锅|做饭|煮饭|炒菜|烹饪|厨房","cooking"),
 ("教师|老师|授课|讲课|教学","teach"),
 ("医生|治疗|诊疗|护士|护士长|医师","doctor"),
 ("工人|劳动|上班|工作|打工","work"),
 ("记者|采访|报道|新闻","reporter"),
 ("写字|写作|书写|填表|签字","writing"),
 ("学习|读书|复习|备考|做作业","studying"),
 ("问候|你好|您好|见面|相逢|再见|告别","greeting"),
 ("帮助|援助|协助|合作|互助|互相","helping"),
 ("同意|答应|允许|可以|行；|行，|好吧","permission"),
 ("拒绝|不允许|不能|不要|禁止|否定","refuse"),
 ("可能|也许","possibility"),
 ("因为|原因|由于|缘故|因此|所以","reason"),
 ("如果|假如|条件","condition"),
 ("但是|然而|可是|尽管|虽然","contrast"),
 ("或者|还是|选择","choice"),
 ("完成|结束|已经|做好|结束了","finished"),
 ("开始|初次|第一次|最初","beginning"),
 ("需要|必要|必须|应该|要求","need"),
 ("思考|考虑|认为|决定|想法","thinking"),
 ("问|询问|提问|问题","asking"),
 ("说话|聊天|交流|讨论|谈话","talking"),
 ("微笑|高兴|快乐|愉快|幸福","happy"),
 ("悲伤|伤心|难过|哭","sad"),
 ("担心|紧张|害怕|恐惧|焦虑","worry"),
 ("生气|愤怒|恼怒","angry"),
 ("游泳|游水","swim"),
 ("跑步|奔跑|跑","running"),
 ("步行|散步|走路|走","walking"),
 ("到达|回来|回家|返回","arriving"),
 ("出发|离开|送去|前往","leaving"),
 ("跳跃|跳高|跳远|跳","jumping"),
 ("拿|给予|递给|送给|交给|接受|收下|收到","giving"),
 ("购买|买东西|购物|买","buying"),
 ("卖|出售|售货","selling"),
 ("唱歌|音乐|歌曲|歌手","music"),
 ("摄影|照相|拍照","camera"),
 ("画画|绘画|艺术|画家","painting"),
 ("足球|踢球","football"),
 ("篮球|排球|乒乓球|网球|球赛","ball"),
 ("数字|数学|计算|加法|减法","numbers"),
 ("钱|货币|价格|费用|工资","money"),
 ("年|月|日|星期|周末|日期","calendar"),
 ("头|脸|嘴巴|鼻子|眼睛|耳朵|牙齿","face"),
 ("手|胳膊|手臂|指头|手指","hand"),
 ("脚|腿|膝盖","feet"),
 ("家人|父母|亲属|家庭|亲戚","family"),
 ("朋友|伙伴|同学|邻居","friends"),
 ("男人|女人|孩子|儿童|老人|人们|人","people"),
 ("病|疼痛|头疼|生病|感冒|发烧","sick"),
 ("成功|胜利|赢|获胜","winner"),
 ("失败|输了|输|失误","loss"),
]
# For function words that are not naturally depictable, a legible meaning card
# is preferable to inventing a false semantic image.
GRAMMAR_REGEX=re.compile(
  r"代词|连接词|连词|介词|语气|助词|副词|虚词|感叹词|"
  r"指示词|疑问词|形容词|量词|词尾|词缀|时态|"
  r"按照|不论|无论|尚且|甚至|何况|一边|仅仅|只要|其次|总之|至于"
)

def meaning_text(zh):
    s=re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", "", zh)
    s=re.sub(r"（[^）]*）|\([^)]*\)", "", s)
    return re.split(r"[；;，,／/、]",s)[0].strip() or zh.strip()

def pick_scene(word, zh):
    if word in FUNCTION_EXACT:
        return FUNCTION_EXACT[word], "explicit"
    main=meaning_text(zh)
    if GRAMMAR_REGEX.search(main) and len(main)>12:
        return "meaning", "grammar"
    # Concrete and scene-specific meanings have priority over the broad sense.
    for phrase,scene in SCENES:
        if any(p in main for p in phrase.split("|")):
            return scene, "semantic"
    # Extended meanings sometimes have the only picturable sense.
    for phrase,scene in SCENES:
        if any(len(p)>=2 and p in zh for p in phrase.split("|")):
            return scene,"secondary"
    return "meaning", "safe_fallback"

def seed_from(uid):
    return int(hashlib.sha256(uid.encode("utf-8")).hexdigest()[:12], 16)

def mix(a,b,t):
    return tuple(round(a[i]*(1-t)+b[i]*t) for i in range(3))

def ellipse(d,x,y,rx,ry,color,stroke=None,width=2):
    d.ellipse((x-rx,y-ry,x+rx,y+ry),fill=color,outline=stroke,width=width)

def line(d,coords,color,width=4):
    d.line(coords, fill=color, width=width, joint="curve")

def roundbox(d,box,color,r=12,outline=None,width=2):
    d.rounded_rectangle(tuple(round(n) for n in box),radius=r,fill=color,outline=outline,width=width)

def backdrop(outdoor,uid):
    rng=random.Random(seed_from(uid))
    im=Image.new("RGB",(SIZE,SIZE),CREAM)
    d=ImageDraw.Draw(im)
    top=(192,213,219) if outdoor else (252,225,187)
    bottom=(237,217,179) if outdoor else (237,194,149)
    for y in range(SIZE):
        d.line((0,y,SIZE,y),fill=mix(top,bottom,y/SIZE))
    if outdoor:
        d.polygon([(0,258),(91,178),(152,230),(256,154),(344,225),(384,191),(384,311),(0,311)],
                  fill=(177,193,187))
        d.polygon([(0,288),(110,239),(229,283),(345,236),(384,249),(384,384),(0,384)],
                  fill=(199,198,165))
        d.polygon([(0,314),(384,310),(384,384),(0,384)],fill=(216,187,143))
        for x in (29,354):
            ellipse(d,x,309,24,10,(149,165,118))
    else:
        d.rectangle((0,278,384,384),fill=(179,127,91))
        line(d,(0,278,384,278),(151,107,85),5)
        d.rectangle((22,61,94,196),fill=(214,198,166))
        d.rectangle((28,67,88,190),fill=(187,215,225))
        line(d,(57,67,57,190),(239,225,198),5)
    return im

def person(d,x,y,pose="standing",shirt=(179,111,84),scale=1,face=(223,170,124)):
    # x,y = torso center. All characters have a warm painterly silhouette.
    s=scale
    ellipse(d,x,y-75*s,24*s,27*s,face)
    ellipse(d,x-9*s,y-83*s,15*s,5*s,(99,73,63))
    ellipse(d,x+8*s,y-79*s,2*s,2*s,INK)
    roundbox(d,(x-27*s,y-46*s,x+28*s,y+34*s),shirt,max(5,round(17*s)))
    if pose=="point":
        line(d,(x-24*s,y-26*s,x-73*s,y-50*s),face,max(3,round(13*s)))
        line(d,(x+24*s,y-23*s,x+45*s,y+7*s),face,max(3,round(13*s)))
    elif pose=="wave":
        line(d,(x-23*s,y-29*s,x-53*s,y-73*s),face,max(3,round(13*s)))
        line(d,(x+23*s,y-29*s,x+41*s,y+6*s),face,max(3,round(13*s)))
    elif pose=="hand":
        line(d,(x-22*s,y-26*s,x+5*s,y+15*s),face,max(3,round(12*s)))
        line(d,(x+23*s,y-26*s,x-5*s,y+15*s),face,max(3,round(12*s)))
    else:
        line(d,(x-22*s,y-24*s,x-40*s,y+15*s),face,max(3,round(12*s)))
        line(d,(x+23*s,y-24*s,x+41*s,y+15*s),face,max(3,round(12*s)))
    line(d,(x-14*s,y+27*s,x-18*s,y+86*s),(78,109,128),max(3,round(16*s)))
    line(d,(x+15*s,y+27*s,x+20*s,y+86*s),(78,109,128),max(3,round(16*s)))
    return x,y

def sign(d,x,y,symbol,fill=(247,242,209)):
    ellipse(d,x,y,26,26,fill,INK,2)
    if symbol=="ok":
        line(d,(x-10,y,x-1,y+10,x+13,y-12),(85,142,103),7)
    elif symbol=="no":
        line(d,(x-10,y-10,x+10,y+10),(171,91,86),6)
        line(d,(x+10,y-10,x-10,y+10),(171,91,86),6)
    elif symbol=="?":
        d.arc((x-11,y-15,x+12,y+6),180,348,fill=INK,width=5)
        d.ellipse((x-2,y+13,x+4,y+19),fill=INK)
    elif symbol=="!":
        line(d,(x,y-14,x,y+5),INK,5)
        ellipse(d,x,y+15,3,3,INK)

def scene_people(d,scene):
    if scene in {"permission","refuse","choice","contrast","reason","condition","possibility","need","finished","beginning"}:
        person(d,119,209,"point",(199,119,91),.85)
        person(d,265,209,"wave" if scene=="permission" else "standing",(106,140,129),.85)
        if scene=="permission":
            sign(d,252,77,"ok")
        elif scene=="refuse":
            sign(d,252,77,"no")
        elif scene=="choice":
            sign(d,254,81,"?")
            d.rectangle((66,275,140,313),fill=(238,229,203))
            d.ellipse((72,285,100,306),fill=(181,114,80))
            d.rectangle((243,274,312,314),fill=(238,229,203))
            d.ellipse((270,282,300,309),fill=(126,161,116))
        elif scene in {"reason","condition"}:
            d.arc((150,60,228,114),0,170,fill=DARKBLUE,width=5)
            d.polygon([(214,103),(229,109),(213,118)],fill=DARKBLUE)
            sign(d,189,79,"?" if scene=="condition" else "!")
        elif scene=="contrast":
            ellipse(d,182,71,17,17,YELLOW)
            d.polygon([(219,57),(266,57),(250,93),(232,93)],fill=BLUE)
        else:
            sign(d,253,78,"ok" if scene in {"finished","beginning"} else "?")
    elif scene in {"talking","greeting","asking","helping","giving","friends","family","people","buying","selling","teach","studying","reporter","doctor"}:
        person(d,106,210,"point" if scene in {"giving","asking","teach","buying","selling"} else "wave",
               (185,111,93),.82)
        person(d,278,210,"point" if scene in {"helping","reporter","doctor"} else "standing",
               (107,138,132),.82)
        if scene in {"talking","asking","greeting","reporter","teach"}:sign(d,193,82,"?" if scene=="asking" else "ok")
        if scene in {"giving","helping","buying","selling"}:
            d.rectangle((177,183,210,220),fill=(219,186,112),outline=(121,92,70),width=2)
    elif scene in {"running","walking","leaving","arriving","jumping","winner","loss","work","happy","sad","worry","angry"}:
        person(d,194,201,"wave" if scene in {"winner","happy"} else "standing",(180,112,91),1.0)
        if scene=="winner":sign(d,292,77,"ok")
        if scene in {"sad","worry","angry"}:sign(d,293,77,"?")
        if scene=="leaving":
            line(d,(256,267,331,267),DARKBLUE,7);d.polygon([(336,266),(319,254),(319,279)],fill=DARKBLUE)
    else:
        person(d,194,207,"standing",(190,120,91),1)
def draw_book(d):
    d.polygon([(78,205),(194,181),(305,205),(305,288),(192,265),(78,288)],fill=(245,236,210),outline=(151,121,99))
    line(d,(192,187,192,266),EARTH,3)
    for x in (101,219):
        for y in (216,234,250):
            line(d,(x,y,x+65,y-7), (195,171,140),2)

def draw_item(d,scene,rng):
    x=192
    if scene in {"book","letter","writing","studying","reading"}:draw_book(d)
    if scene=="pen":
        line(d,(98,286,299,105),DARKBLUE,37)
        line(d,(99,286,287,117),YELLOW,7)
        d.polygon([(72,308),(103,271),(133,260),(102,289)],fill=(239,198,102))
    elif scene in {"noodles","rice","dumplings","vegetables","fruit","meat","cake","bread","water","milk","tea","coffee","plate"}:
        ellipse(d,194,237,124,61,(219,185,151))
        ellipse(d,190,224,116,52,(245,237,213),DARKBLUE,3)
        if scene=="dumplings":
            for a,b in [(123,205),(191,197),(260,212),(150,239),(226,245)]:
                ellipse(d,a,b,34,15,(244,213,160),EARTH,2)
                d.arc((a-30,b-21,a+30,b+20),178,340,fill=EARTH,width=2)
        elif scene=="noodles":
            for j in range(6):
                d.arc((104+j*15,188,213+j*11,257),12,168,fill=YELLOW,width=5)
        elif scene=="bread":
            ellipse(d,193,227,98,37,(214,169,100))
            for j in range(4):
                d.arc((124+j*31,205,154+j*29,236),200,330,fill=(155,111,75),width=3)
        elif scene in {"tea","coffee","water","milk"}:
            roundbox(d,(136,169,249,277),(251,239,216),17,EARTH)
            ellipse(d,193,171,55,17, (133,83,66) if scene=="coffee" else
                    (164,115,70) if scene=="tea" else (245,244,234) if scene=="milk" else BLUE)
            d.arc((243,188,292,256),250,104,fill=EARTH,width=9)
        elif scene in {"fruit","apple","vegetables"}:
            for a,b,col in [(139,215,(175,89,72)),(200,210,(209,166,87)),(257,233,GREEN)]:
                ellipse(d,a,b,28,30,col)
        else:
            for a,b in [(143,207),(192,224),(239,200)]:
                ellipse(d,a,b,35,22,(202,149,86))
    elif scene in {"camel","cow","horse","sheep","cat","dog","rabbit","bird","duck","chicken","goose","fish","bug"}:
        # Mammals: clearly identifiable silhouettes with the relevant feature.
        if scene=="bird" or scene in {"duck","chicken","goose"}:
            ellipse(d,191,216,75,52,(209,151,88))
            ellipse(d,238,165,28,30,(215,168,113))
            d.polygon([(258,165),(293,173),(260,182)],fill=(218,151,74))
            for xx in (154,207):line(d,(xx,252,xx,292),EARTH,8)
        elif scene=="fish":
            ellipse(d,175,225,91,49,BLUE)
            d.polygon([(247,222),(305,176),(303,278)],fill=DARKBLUE)
            ellipse(d,117,212,7,7,INK)
        elif scene=="bug":
            ellipse(d,192,215,42,60,(178,125,72))
            ellipse(d,192,152,25,20,INK)
            for dy in (180,215,248):
                line(d,(159,dy,132,dy-14),INK,5)
                line(d,(225,dy,252,dy-14),INK,5)
        else:
            body=(204,148,90) if scene in {"camel","horse","cow"} else (183,161,130)
            ellipse(d,183,218,95,54,body)
            ellipse(d,269,178,30,37,body)
            for ax in (124,173,223,250):line(d,(ax,252,ax-6,303),(151,115,83),13)
            if scene=="camel":
                for ax in (139,212):
                    d.polygon([(ax-25,200),(ax,134),(ax+35,200)],fill=body)
            elif scene=="horse":
                d.polygon([(269,151),(285,132),(296,168)],fill=(119,100,80))
            elif scene=="cow":
                for ax in (142,214):ellipse(d,ax,216,18,13,(251,236,209))
                d.polygon([(244,147),(235,125),(252,141)],fill=CREAM)
                d.polygon([(281,147),(295,125),(290,157)],fill=CREAM)
            elif scene=="sheep":
                for ax in (131,161,197,229):ellipse(d,ax,194,35,31,(249,238,213))
            elif scene=="rabbit":
                for ax in (255,279):ellipse(d,ax,129,10,37,body)
            elif scene in {"cat","dog"}:
                for ax in (253,284):d.polygon([(ax-14,150),(ax,125),(ax+15,149)],fill=body)
    elif scene in {"tree","sprout","flower"}:
        line(d,(191,289,191,121),EARTH,19)
        for xx,yy,rr in [(146,171,55),(211,137,56),(258,196,40)]:
            ellipse(d,xx,yy,rr,rr*.8,GREEN)
        if scene=="flower":ellipse(d,204,153,25,25,(209,109,103))
    elif scene in {"sun","night","snow","rain","mountain","river","desert"}:
        if scene=="sun":ellipse(d,274,119,40,40,YELLOW)
        if scene=="night":
            ellipse(d,270,104,38,38,(230,217,166))
            ellipse(d,286,98,35,35,(198,216,217))
        if scene in {"rain","snow"}:
            for _ in range(23):
                xx=rng.randrange(35,351);yy=rng.randrange(101,281)
                if scene=="rain":line(d,(xx,yy,xx-7,yy+16),BLUE,3)
                else:ellipse(d,xx,yy,4,4,CREAM)
        if scene=="river":
            d.polygon([(0,268),(384,268),(384,384),(0,384)],fill=BLUE)
            for yy in (286,323,354):line(d,(75,yy,308,yy+5),CREAM,4)
    elif scene in {"car","bus","train","motorcycle","bicycle","boat","airplane"}:
        if scene in {"car","bus","train"}:
            color=(198,120,94) if scene=="car" else BLUE
            roundbox(d,(66,183,318,264),color,14)
            d.polygon([(110,181),(158,139),(260,139),(292,183)],fill=color)
            for xx in (134,253):roundbox(d,(xx,152,xx+47,193),(198,222,227),4)
            for xx in (116,279):ellipse(d,xx,268,23,24,INK)
        elif scene in {"bicycle","motorcycle"}:
            for xx in (123,278):ellipse(d,xx,265,42,42,None,INK,8)
            line(d,(123,265,191,188,278,265,123,265),DARKBLUE,8)
            line(d,(191,188,217,265),DARKBLUE,8)
        elif scene=="airplane":
            d.polygon([(43,239),(168,216),(190,112),(219,111),(224,205),(340,217),(341,243),(219,261),(167,312),(144,313),(162,255)],fill=(114,146,165))
        else:
            d.polygon([(79,236),(301,236),(275,286),(108,286)],fill=(117,147,153))
            d.polygon([(189,136),(190,234),(266,231)],fill=CREAM)
    elif scene in {"house","school","hospital","bank","office","shop","restaurant","town","village"}:
        d.rectangle((88,144,299,312),fill=(228,186,143),outline=EARTH,width=3)
        d.polygon([(67,149),(191,76),(323,149)],fill=(162,103,84))
        for xx in (121,255):roundbox(d,(xx,182,xx+48,234),(185,209,214),4)
        roundbox(d,(176,243,222,311),(130,104,94),5)
        if scene in {"school","hospital","bank","office","shop","restaurant"}:
            roundbox(d,(120,157,264,181),(244,225,184),6)
            if scene=="hospital":
                line(d,(192,158,192,182),(184,83,72),6)
                line(d,(180,170,205,170),(184,83,72),6)
    elif scene in {"key","bag","clock","table","chair","window","door","bed","clothing","hat","shoes","computer","phone","cooking","money","numbers","calendar","face","hand","feet","ball","football","camera","music","painting","road","letter","water"}:
        # Real object compositions, not generic Lucide icons.
        if scene=="phone":
            roundbox(d,(143,107,238,296),DARKBLUE,18)
            roundbox(d,(153,129,230,271),(190,218,223),11)
            ellipse(d,189,284,6,6,CREAM)
        elif scene=="computer":
            roundbox(d,(83,124,302,251),DARKBLUE,9)
            roundbox(d,(95,137,290,233),(176,210,215),4)
            d.polygon([(73,270),(314,270),(330,298),(54,298)],fill=(159,165,159))
        elif scene in {"table","chair","bed"}:
            d.polygon([(82,180),(296,177),(324,209),(67,211)],fill=EARTH)
            for xx in (103,282):line(d,(xx,207,xx,315),(133,101,81),13)
        elif scene in {"window","door"}:
            roundbox(d,(106,108,275,305),EARTH,8)
            roundbox(d,(122,122,256,289),(192,213,213),4)
            if scene=="window":
                line(d,(189,124,189,289),CREAM,7)
                line(d,(121,197,258,197),CREAM,7)
            else:ellipse(d,245,218,6,6,YELLOW)
        elif scene=="clock":
            ellipse(d,191,196,93,91,CREAM,EARTH,9)
            line(d,(190,196,191,139),INK,8);line(d,(190,196,244,211),INK,8)
        elif scene=="key":
            ellipse(d,138,185,34,33,YELLOW,INK,4)
            line(d,(160,199,279,276),YELLOW,19)
            line(d,(243,255,264,237),YELLOW,12)
        elif scene=="bag":
            roundbox(d,(110,170,274,290),(178,126,92),17)
            d.arc((153,131,231,200),181,360,fill=INK,width=11)
        elif scene=="cooking":
            roundbox(d,(108,196,288,281),(145,153,148),26)
            d.arc((142,165,255,218),174,360,fill=(188,203,196),width=8)
            line(d,(127,179,272,179),INK,11)
        elif scene in {"calendar","numbers","money"}:
            roundbox(d,(112,117,276,296),(247,234,209),12,EARTH,5)
            d.rectangle((113,117,275,158),fill=(183,118,89))
            for a in range(3):
                for b in range(3):
                    roundbox(d,(132+a*45,182+b*31,156+a*45,199+b*31),(198,182,150),3)
        elif scene in {"clothing","hat","shoes"}:
            d.polygon([(134,139),(171,115),(216,114),(257,139),(290,193),(247,217),(244,294),(133,294),(135,217),(92,193)],fill=(183,114,86))
        else:
            # Explicit generic-but-understandable physical object background.
            d.rectangle((110,157,273,279),fill=(234,207,167),outline=EARTH,width=5)
            ellipse(d,193,217,37,35,GREEN)
    else:
        draw_book(d)

def text_fallback(im,zh,word):
    # If an image cannot depict the precise meaning, display a meaning card:
    # NO false notebook/pen icon. No unverified inferred situation.
    d=ImageDraw.Draw(im)
    roundbox(d,(26,52,358,332),(250,237,210),19,(180,150,119),3)
    d.rectangle((48,78,335,87),fill=GREEN)
    fonts=["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
           "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]
    fpath=next((p for p in fonts if os.path.isfile(p)),None)
    if fpath:
        small=ImageFont.truetype(fpath,17)
        d.text((53,112),"语义提示",font=small,fill=(127,112,93))
        text=meaning_text(zh).strip()
        if not text:text=zh
        lines=[]
        while text and len(lines)<4:
            chunk=text[:9]
            while len(chunk)>1 and d.textbbox((0,0),chunk,font=small)[2]>258:
                chunk=chunk[:-1]
            lines.append(chunk)
            text=text[len(chunk):]
        large=ImageFont.truetype(fpath,29 if max((len(x) for x in lines),default=0)<7 else 23)
        for k,row in enumerate(lines):
            d.text((55,159+k*39),row,font=large,fill=INK)
    return im

def paint(row):
    uid,word,zh=row[0],row[1],row[2]
    scene,source=pick_scene(word,zh)
    people={"permission","refuse","choice","contrast","reason","condition","possibility","need",
            "finished","beginning","talking","greeting","asking","helping","giving","friends",
            "family","people","buying","selling","teach","studying","reporter","doctor",
            "running","walking","leaving","arriving","jumping","winner","loss","work",
            "happy","sad","worry","angry"}
    outdoor=scene in people or scene in {"camel","cow","horse","sheep","cat","dog","rabbit","bird","duck","chicken","goose","fish","bug",
                        "tree","sprout","flower","sun","night","snow","rain","mountain","river","desert",
                        "car","bus","train","motorcycle","bicycle","boat","airplane",
                        "house","school","hospital","bank","office","shop","restaurant","town","village"}
    im=backdrop(outdoor,uid)
    d=ImageDraw.Draw(im)
    if scene=="meaning":
        text_fallback(im,zh,word)
    elif scene in people:
        scene_people(d,scene)
    else:
        draw_item(d,scene,random.Random(seed_from(uid)))
    # All images share a subtle low-resolution printed-paper finish.
    rng=random.Random(seed_from(uid)+17)
    noise=Image.effect_noise((SIZE,SIZE),18)
    grain=ImageOps.colorize(noise,(181,154,131),(251,244,226))
    im=Image.blend(im,grain,.11)
    return im,scene,source
