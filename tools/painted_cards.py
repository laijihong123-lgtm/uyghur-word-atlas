#!/usr/bin/env python3
"""Deterministic low-resolution storybook illustrations for vocabulary fallback cards.

The intended treatment is vintage illustrated flashcards: warm paper, muted
watercolor washes, scenery, a large recognizable subject and no pictogram frame.
This is procedural artwork, not individually generated AI paintings. The source
word/gloss remain untouched and attribution remains explicit.
"""
from __future__ import annotations

import hashlib
import math
import random
import re
from PIL import Image, ImageDraw, ImageFilter, ImageOps

SIDE = 384
PALETTES = {
    "objects": ((245, 219, 177), (187, 119, 80), (76, 94, 108)),
    "food": ((244, 208, 169), (186, 114, 78), (118, 145, 113)),
    "people": ((239, 211, 174), (163, 118, 102), (112, 147, 118)),
    "school": ((235, 209, 169), (157, 111, 83), (96, 124, 130)),
    "work": ((236, 208, 174), (146, 111, 90), (112, 145, 142)),
    "commerce": ((244, 214, 175), (170, 120, 97), (120, 147, 131)),
    "health": ((233, 219, 184), (156, 127, 124), (106, 148, 145)),
    "abstract": ((235, 213, 180), (144, 128, 124), (113, 144, 139)),
    "emotion": ((243, 211, 172), (183, 119, 119), (123, 143, 145)),
    "nature": ((238, 213, 176), (184, 139, 92), (112, 140, 127)),
    "weather": ((235, 219, 188), (150, 151, 161), (112, 143, 148)),
    "travel": ((238, 213, 173), (170, 128, 105), (102, 144, 145)),
    "transport": ((233, 210, 177), (156, 116, 96), (114, 148, 154)),
    "city": ((241, 214, 176), (173, 125, 107), (115, 144, 146)),
    "civic": ((239, 211, 178), (170, 128, 108), (111, 144, 145)),
    "sport": ((229, 214, 182), (170, 118, 90), (96, 148, 162)),
    "art": ((239, 210, 177), (163, 117, 116), (112, 148, 147)),
    "time": ((241, 215, 185), (165, 127, 104), (113, 148, 146)),
}
INK = (82, 82, 77)
SKY = (193, 213, 221)
CREAM = (251, 240, 213)

def mix(a, b, t):
    return tuple(round(a[i] * (1-t) + b[i]*t) for i in range(3))

def stable_seed(value):
    return int(hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12], 16)

def wash(im, a, b):
    d=ImageDraw.Draw(im)
    for y in range(SIDE):
        t=(y/SIDE)**0.8
        d.line((0,y,SIDE,y),fill=mix(a,b,t))

def hill(d, rng, base, color, height=14):
    points=[]
    for x in range(-4,SIDE+12,10):
        points.append((x,base+round(math.sin(x/65 + height)*height/2) + rng.randrange(-4,5)))
    points.extend([(SIDE,SIDE),(0,SIDE)])
    d.polygon(points,fill=color)

def foliage(d,rng,x,y,color,scale=1):
    for dx,dy,rad in [(-19,-5,17),(0,-14,21),(21,-3,17),(-7,7,20),(14,9,16)]:
        a=(x+dx*scale,y+dy*scale);r=rad*scale
        d.ellipse((a[0]-r,a[1]-r,a[0]+r,a[1]+r),fill=color)
    d.line((x,y+18*scale,x,y+54*scale),fill=(103,96,77),width=max(2,round(6*scale)))

def sky_scene(im,d,rng,kind,accent):
    wash(im,(205,219,222),(236,213,176))
    d=ImageDraw.Draw(im)
    # Clouds and distant layered mountains borrow the muted, broad-paint
    # storytelling composition of educational picture cards.
    for x,y in [(55,76),(278,47)]:
        c=(236,231,208)
        d.ellipse((x,y,x+57,y+23),fill=c)
        d.ellipse((x+13,y-11,x+45,y+20),fill=c)
    if kind in {"nature","travel","weather","transport","sport"}:
        d.polygon([(0,240),(77,165),(137,210),(217,139),(316,218),(384,180),(384,328),(0,328)],
                  fill=mix((129,160,178),accent,.20))
        d.polygon([(0,268),(104,208),(209,263),(315,209),(384,241),(384,350),(0,350)],
                  fill=mix(accent,(210,210,181),.57))
        hill(d,rng,299,mix(accent,(236,208,151),.53),12)
        hill(d,rng,333,mix((212,176,120),accent,.35),8)
    elif kind in {"city","civic"}:
        for x,y,w in [(-10,193,71),(70,167,75),(153,196,90),(254,174,83),(340,204,77)]:
            col=mix(accent,(245,224,179),rng.uniform(.4,.62))
            d.rectangle((x,y,x+w,316),fill=col)
            for xx in range(x+12,x+w-10,24):
                for yy in range(y+20,293,34):
                    d.rectangle((xx,yy,xx+10,yy+15),fill=(185,198,185))
        d.polygon([(0,313),(384,309),(384,384),(0,384)],fill=(194,166,129))
    else:
        hill(d,rng,291,mix(accent,(222,199,154),.67))
        hill(d,rng,331,mix(accent,(190,169,120),.66))
    if kind in {"nature","people","sport","weather"}:
        foliage(d,rng,28,249,(138,161,114),.67)
        foliage(d,rng,355,249,(144,156,104),.57)
    for x in (18,112,303,367):
        y=rng.randint(307,349)
        d.ellipse((x,y,x+23,y+7),fill=mix(accent,(135,148,99),.57))

def tabletop(im,d,rng,kind,accent):
    wash(im, (244,220,181), (229,193,150))
    d=ImageDraw.Draw(im)
    # Simplified desk/table setting, like a small hand-painted illustration
    # rather than a free-floating interface glyph.
    d.polygon([(0,236),(384,234),(384,384),(0,384)],fill=mix(accent,(240,182,120),.49))
    for x in (29,178,311):
        d.line((x,252,x+9,378),fill=mix(accent,(191,138,96),.48),width=3)
    d.ellipse((40,249,347,347),fill=(173,138,105))
    d.ellipse((45,239,342,330),fill=(233,204,163))
    if kind in {"school","work","abstract","time","civic","commerce"}:
        d.polygon([(43,243),(195,222),(338,252),(192,279)],fill=(247,237,211))
        d.line((58,249,185,231),fill=(196,183,158),width=2)
        d.line((209,233,320,255),fill=(196,183,158),width=2)
    if kind in {"food","health"}:
        d.ellipse((62,227,327,319),fill=(192,154,123))
        d.ellipse((68,217,321,306),fill=(242,235,213))
        d.ellipse((89,230,300,286),outline=(134,156,177),width=5)

def pool_scene(im,rng):
    d=ImageDraw.Draw(im)
    wash(im,(196,219,224),(169,209,216))
    d=ImageDraw.Draw(im)
    d.rectangle((0,136,384,384),fill=(75,161,186))
    d.rectangle((0,116,384,143),fill=(226,208,173))
    d.rectangle((0,137,384,150),fill=(177,180,163))
    for i in range(40):
        x=rng.randrange(-30,390);y=rng.randrange(157,388)
        d.arc((x,y,x+46,y+13),8,170,fill=(142,201,209),width=3)
    for x in (32,96,289,358):
        foliage(d,rng,x,98,(130,161,116),.45)

def shadowed_icon(im,icon,seed,accent,kind):
    if icon is None:return im
    # Repaint monochrome line art as a slightly irregular, two-tone gouache
    # silhouette so the fallback doesn't look like a Lucide UI icon sticker.
    source=icon.convert("RGBA")
    source.thumbnail((235,235),Image.Resampling.LANCZOS)
    mask=source.getchannel("A")
    thick=mask.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.GaussianBlur(.8))
    x=(SIDE-source.width)//2
    y=68 if kind not in {"abstract","civic","work"} else 65
    rgba=im.convert("RGBA")
    under=Image.new("RGBA",(source.width,source.height),mix(accent,INK,.28)+(255,))
    under.putalpha(thick)
    drop=Image.new("RGBA",(source.width,source.height),(100,81,66,130))
    drop.putalpha(thick.point(lambda v:round(v*.26)))
    rgba.alpha_composite(drop,(x+7,y+10))
    rgba.alpha_composite(under,(x,y))
    core=Image.new("RGBA",(source.width,source.height),mix(accent,(250,229,171),.40)+(255,))
    core.putalpha(mask.point(lambda v:round(v*.86)))
    rgba.alpha_composite(core,(x-1,y-2))
    # A fine dark outline balances the softer painted fill.
    detail=Image.new("RGBA",(source.width,source.height),INK+(255,))
    detail.putalpha(mask.point(lambda v:round(v*.43)))
    rgba.alpha_composite(detail,(x,y))
    return rgba.convert("RGB")

def draw_pen(im):
    d=ImageDraw.Draw(im)
    d.ellipse((53,233,343,292),fill=(184,134,95))
    d.line((81,289,304,105),fill=(95,105,114),width=41)
    d.line((89,285,302,108),fill=(36,63,84),width=30)
    d.line((154,226,320,90),fill=(219,175,91),width=5)
    d.line((105,270,153,228),fill=(219,171,82),width=26)
    d.polygon([(73,297),(112,276),(145,242),(135,234),(98,266)],fill=(236,190,98))
    d.ellipse((90,271,101,281),fill=(96,76,54))

def draw_dumplings(im):
    d=ImageDraw.Draw(im)
    d.ellipse((40,144,339,324),fill=(184,123,93))
    d.ellipse((42,127,334,305),fill=(239,231,212))
    d.ellipse((59,139,322,283),outline=(115,142,163),width=6)
    for cx,cy in [(133,181),(202,172),(265,197),(166,245),(244,249)]:
        d.ellipse((cx-42,cy-23,cx+44,cy+25),fill=(221,173,122))
        d.pieslice((cx-39,cy-45,cx+41,cy+20),0,180,fill=(247,222,174))
        for n in (-15,0,15):
            d.line((cx+n,cy-10,cx+n+6,cy+4),fill=(215,182,137),width=2)
    d.ellipse((278,59,364,135),fill=(215,203,180))
    d.ellipse((286,64,359,124),fill=(157,65,46))

def draw_camel(im):
    d=ImageDraw.Draw(im)
    d.ellipse((60,280,320,313),fill=(185,153,117))
    for x in (102,151,235,271):
        d.line((x,238,x-9,300),fill=(165,101,65),width=25)
        d.ellipse((x-27,289,x+11,306),fill=(120,88,65))
    d.polygon([(67,222),(89,181),(105,134),(120,178),(140,177),(168,122),(193,182),(245,193),
               (260,145),(288,115),(303,150),(290,214),(274,254),(120,260)],fill=(204,137,76))
    d.ellipse((271,101,338,158),fill=(208,146,82))
    d.ellipse((310,118,355,145),fill=(210,148,87))
    d.ellipse((303,119,310,126),fill=INK)
    d.line((320,138,338,139),fill=(97,75,62),width=3)
    d.ellipse((275,109,300,134),fill=(182,111,64))

def draw_swim(im):
    d=ImageDraw.Draw(im)
    d.ellipse((155,160,219,225),fill=(222,167,119))
    d.ellipse((177,157,219,181),fill=(53,81,104))
    d.line((176,225,100,172),fill=(221,165,124),width=29)
    d.line((101,169,67,219),fill=(224,167,123),width=18)
    d.line((216,238,270,187),fill=(221,165,124),width=24)
    for x,y in [(52,239),(103,270),(275,254),(328,218)]:
        d.arc((x-32,y-13,x+33,y+14),0,180,fill=(236,243,227),width=7)
    d.ellipse((210,186,218,194),fill=(73,77,79))

def texture(im,seed):
    rng=random.Random(seed)
    # Cheap deterministic paper-grain pass; low output resolution is intended.
    noise=Image.effect_noise((SIDE,SIDE),24)
    paper=ImageOps.colorize(noise,(185,158,132),(255,250,230))
    im=Image.blend(im,paper,.115)
    d=ImageDraw.Draw(im,"RGBA")
    for _ in range(220):
        x=rng.randint(0,SIDE);y=rng.randint(0,SIDE);w=rng.randint(1,13)
        d.ellipse((x,y,x+w,y+rng.randint(1,4)),fill=(249,233,196,rng.randrange(9,39)))
    return im

def draw_card(row,icon_name,kind,icon_img):
    uid,word,gloss=row[0],row[1],row[2]
    seed=stable_seed(uid)
    rng=random.Random(seed)
    bg,accent,green=PALETTES.get(kind, PALETTES["abstract"])
    im=Image.new("RGB",(SIDE,SIDE),bg)
    is_swim=("游泳" in gloss or "游水" in gloss)
    if is_swim:
        pool_scene(im,rng)
    elif kind in {"food","objects","school","work","commerce","abstract","health","art","time"}:
        tabletop(im,ImageDraw.Draw(im),rng,kind,accent)
    else:
        sky_scene(im,ImageDraw.Draw(im),rng,kind,green)
    if "骆驼" in gloss:
        draw_camel(im)
    elif "钢笔" in gloss:
        draw_pen(im)
    elif "饺子" in gloss or "馄饨" in gloss:
        draw_dumplings(im)
    elif is_swim:
        draw_swim(im)
    else:
        im=shadowed_icon(im,icon_img,seed,accent,kind)
    # Only an ambiguous/abstract idea needs the source language as a cue;
    # avoid large picture-caption panels on recognizable concrete subjects.
    broad = kind in {"abstract","emotion"} or icon_name in {"hash","circle-help","notebook-pen"}
    if broad:
        from PIL import ImageFont
        fonts=["/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
               "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]
        f=next((ImageFont.truetype(p,19) for p in fonts if __import__("os").path.isfile(p)),None)
        if f is not None:
            text=re.split(r"[；;,，、/／（(]",gloss)[0].strip()
            if text:
                d=ImageDraw.Draw(im,"RGBA")
                text=text[:12]
                while len(text)>2 and d.textbbox((0,0),text,font=f)[2] > 310:
                    text=text[:-1]
                bb=d.textbbox((0,0),text,font=f)
                width=bb[2]-bb[0]
                d.rounded_rectangle(((SIDE-width)//2-20,335,(SIDE+width)//2+20,368),
                                    radius=12,fill=(252,239,209,190))
                d.text(((SIDE-width)//2,339),text,font=f,fill=INK+(255,))
    im=texture(im,seed)
    return im
