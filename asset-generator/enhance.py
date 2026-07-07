#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
素材增强：提高像素 + 精修
------------------------------------------------
OpenRouter 图像模型只出 1024² PNG。这里做：
  · 场景/封面：2x LANCZOS 放大 + UnsharpMask 锐化 → 更高像素、更清晰
  · 立绘/头像：先用原图(或 _raw 备份)放大锐化，再 rembg(alpha_matting) 精修抠成透明 PNG
原图备份在 assets/_raw/。需在 venv 运行：
  ./.venv/bin/python enhance.py [--project P] [--scale 2]
"""
import os, io, json, argparse
from PIL import Image, ImageFilter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
def resolve_project(p):
    try: cfg = json.load(open(os.path.join(SCRIPT_DIR,"gen_config.json"),encoding="utf-8"))
    except Exception: cfg = {}
    p = p or cfg.get("default_project") or "."
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(SCRIPT_DIR, p))

def kind_of(k):
    for pre,kd in (("avatar","avatar"),("char","char"),("scene","scene"),("cover","cover"),("cg","cg")):
        if k.startswith(pre): return kd
    return "other"

def real_path(game, rel):
    base = os.path.splitext(rel)[0]
    for e in (".png",".webp",".jpg",".jpeg"):
        if os.path.exists(os.path.join(game, base+e)): return base+e
    return None

def upsharp(im, scale):
    im = im.convert("RGBA")
    w,h = im.size
    im = im.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=90, threshold=2))

def main():
    ap = argparse.ArgumentParser(description="素材增强(放大+锐化+立绘抠图)")
    ap.add_argument("--project"); ap.add_argument("--scale", type=float, default=2.0)
    args = ap.parse_args()
    PROJECT = resolve_project(args.project); GAME = os.path.join(PROJECT,"game")
    mpath = os.path.join(GAME,"assets","manifest.json")
    manifest = json.load(open(mpath,encoding="utf-8")); assets = manifest.get("assets",manifest)
    raw = os.path.join(GAME,"assets","_raw"); os.makedirs(raw, exist_ok=True)

    from rembg import remove, new_session
    session = new_session("u2net")
    done = 0
    for k, rel in list(assets.items()):
        kd = kind_of(k)
        if kd == "other": continue
        # 立绘/头像优先用原始备份(未抠图)做增强，边缘更干净
        srcbak = os.path.join(raw, os.path.basename(os.path.splitext(rel)[0])+".src.png")
        cur = real_path(GAME, rel)
        if kd in ("char","avatar") and os.path.exists(srcbak):
            im = Image.open(srcbak)
        elif cur:
            im = Image.open(os.path.join(GAME, cur))
            bak = os.path.join(raw, os.path.basename(os.path.splitext(cur)[0])+".src.png")
            if not os.path.exists(bak): im.convert("RGBA").save(bak)
        else:
            continue
        im = upsharp(im, args.scale)
        outrel = os.path.splitext(rel)[0] + ".png"
        if kd in ("char","avatar"):
            buf = io.BytesIO(); im.save(buf, "PNG")
            out = remove(buf.getvalue(), session=session, alpha_matting=True,
                         alpha_matting_foreground_threshold=245, alpha_matting_background_threshold=8,
                         alpha_matting_erode_size=6)
            open(os.path.join(GAME, outrel),"wb").write(out)
        else:
            im.save(os.path.join(GAME, outrel), "PNG")
        if cur and cur != outrel:
            try: os.remove(os.path.join(GAME, cur))
            except Exception: pass
        assets[k] = outrel; done += 1
        print(f"  ✅ {k} -> {outrel} [{kd}] {im.size[0]}x{im.size[1]}")
    json.dump(manifest, open(mpath,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"完成：增强 {done} 张（原图备份 assets/_raw/）。")

if __name__ == "__main__":
    main()
