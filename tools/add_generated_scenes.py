#!/usr/bin/env python3
"""Place six specially generated pictorial scenes into the textbook deck.
Generated sheet has three columns and two rows, all illustrations intentionally
match specific ORIGINAL Chinese textbook meanings, with no fabricated translations.
"""
import base64,io,json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent.parent
ATLAS=ROOT/"upstream/public/atlas"
SOURCE=ROOT/"data/generated_six_scenes.b64"
MAPPINGS=[
 ("ئاپتونوم رايون","自治区","自治区：天山脚下城市及区域景观"),
 ("ئاتا-ئانا","父母","父母：一家三口在院中相伴"),
 ("ئارتۇق","多；多余","多余：比所需多出的一张绿色椅子"),
 ("ئاسارئەتىقە","名胜古迹","名胜古迹：古老塔楼与历史建筑"),
 ("ئاش","饭","饭：一碗米饭和蔬菜肉类"),
 ("تاماق ئەت-","做饭","做饭：厨师在厨房烹饪"),
]
def main():
    data=base64.b64decode(SOURCE.read_text("ascii").strip(),validate=True)
    im=Image.open(io.BytesIO(data)).convert("RGB")
    w,h=im.size
    if w%3 or h%2:raise RuntimeError("Unexpected spritesheet dimensions")
    idxp=ATLAS/"index.json"
    idx=json.loads(idxp.read_text("utf8"))
    by_word={row[1]:row for row in idx["words"]}
    mapping={}
    for n,(uy,zh,description) in enumerate(MAPPINGS):
        row=by_word.get(uy)
        if row is None:raise RuntimeError("Source textbook word missing: "+uy)
        if zh not in row[2]:raise RuntimeError("Source textbook sense changed: "+uy)
        # User preference: if the original author already has a meaning-related
        # image, keep it rather than covering it with a generated scene.
        if row[6] & 1:
            print("KEEP_ORIGINAL_SCENE",uy,zh,flush=True)
            continue
        # Generate a special scene only if no licensed original match exists.
        x=n%3;y=n//3
        tile=im.crop((x*w//3,y*h//2,(x+1)*w//3,(y+1)*h//2))
        for size in ("img","thumb"):
            file=ATLAS/size/(row[0]+".webp")
            (ATLAS/size).mkdir(parents=True,exist_ok=True)
            img=tile if size=="img" else tile.resize((96,96))
            img.save(file,"WEBP",quality=78,method=6)
        row[6]|=1
        mapping[row[0]]={"uy":uy,"meaning":zh,"generated_description":description,
                         "origin":"ImageGen-generated visual, not a reused source image"}
    idx["illustrated"]=sum(bool(r[6]&1) for r in idx["words"])
    idxp.write_text(json.dumps(idx,ensure_ascii=False,separators=(",",":")),"utf8")
    for file in sorted((ATLAS/"entries").glob("*.json"),key=lambda p:int(p.stem)):
        entries=json.loads(file.read_text("utf8"))
        for e in entries:
            if e["id"] in mapping:e["m"] |= 1
        file.write_text(json.dumps(entries,ensure_ascii=False,separators=(",",":")),"utf8")
    (ATLAS/"generated-image-attributions.json").write_text(
        json.dumps({"count":len(mapping),"images":mapping},ensure_ascii=False,indent=2),"utf8")
    print("AI_GENERATED_IMAGES_ADDED",len(mapping),"TOTAL_ILLUSTRATED",idx["illustrated"],flush=True)
if __name__=="__main__":main()
