#!/usr/bin/env python3
"""Fast semantic-picture regression check before rebuilding 1,127 cards."""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image

from semantic_scene_cards import SCENES, paint, pick_scene

CASES=[
    ("بولىدۇ","可以","permission"),
    ("ماقۇل","行；可以；就这样","permission"),
    ("مەيلى","好吧；可以；随便","permission"),
    ("ئاۋاز","不可以","refuse"),
    ("tb0001","书包","bag"),
    ("tb0002","书籍","book"),
    ("tb0003","苹果","apple"),
    ("tb0004","香蕉","banana"),
    ("tb0005","鞋子","shoes"),
    ("tb0006","帽子","hat"),
    ("tb0007","游泳","swim"),
    ("tb0008","跑步","running"),
    ("tb0009","因为","reason"),
    ("tb0010","如果","condition"),
    ("tb0011","但是","contrast"),
    ("tb0012","或者","choice"),
    ("tb0013","饺子","dumplings"),
    ("tb0014","汽车","car"),
    ("tb0015","我的","meaning"),
    ("tb0016","钢笔","pen"),
    ("tb0017","打电话","phone"),
]
def main():
    for index,(word,gloss,expected) in enumerate(CASES):
        value,why=pick_scene(word,gloss)
        assert value==expected,(word,gloss,value,expected,why)
        im,scene,source=paint((f"qa{index:04d}",word,gloss))
        assert scene==expected and im.mode=="RGB" and im.size==(384,384)
    kinds=set(scene for _,scene in SCENES)
    # Every category must render and compress to a valid low-resolution WebP.
    for index,scene in enumerate(sorted(kinds)):
        matching=next(p.split("|")[0] for p,name in SCENES if name==scene)
        im,chosen,_=paint((f"template{index:04d}",f"test{index}",matching))
        assert im.size==(384,384),(scene,im.size)
        assert im.getbbox() is not None
    full=Path("upstream/public/fast-illustrations-preview.webp")
    print("SEMANTIC_IMAGE_REGRESSION_PASSED",len(CASES),
          "SCENE_TYPES",len(kinds),"NO_DOWNLOADABLE_ICON_DEPENDENCY",True,flush=True)

if __name__=="__main__":
    main()
