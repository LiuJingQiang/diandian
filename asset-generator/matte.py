#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
立绘/头像 背景去除（抠图成透明 PNG）
------------------------------------------------
AI 出的角色图带不透明背景（常与衣服同色，不能简单抠色）。
用 rembg(u2net) 做主体分割 → 透明 PNG，让立绘干净贴合场景。
只处理 char_* / avatar_*（场景/封面保留背景）。原图备份到 assets/_raw/。

需在本项目 venv 运行：
  ./.venv/bin/python matte.py [--project P] [--only char_shenmo] [--kind char|avatar] [--all]
"""
import os, io, sys, json, argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
def resolve_project(p):
    try: cfg = json.load(open(os.path.join(SCRIPT_DIR,"gen_config.json"),encoding="utf-8"))
    except Exception: cfg = {}
    p = p or cfg.get("default_project") or "."
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(SCRIPT_DIR, p))

def kind_of(k):
    return "avatar" if k.startswith("avatar") else "char" if k.startswith("char") else "other"

def main():
    ap = argparse.ArgumentParser(description="立绘/头像抠图成透明 PNG (rembg)")
    ap.add_argument("--project"); ap.add_argument("--only"); ap.add_argument("--kind", choices=["char","avatar"])
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    PROJECT = resolve_project(args.project); GAME = os.path.join(PROJECT,"game")
    manifest = json.load(open(os.path.join(GAME,"assets","manifest.json"),encoding="utf-8"))
    assets = manifest.get("assets", manifest)

    keys = [k for k in assets if kind_of(k) in ("char","avatar")]
    if args.only: keys = [args.only]
    elif args.kind: keys = [k for k in keys if kind_of(k)==args.kind]
    # 只处理磁盘上真实存在的文件
    def real(path):
        base = os.path.splitext(path)[0]
        for e in (".png",".webp",".jpg",".jpeg"):
            if os.path.exists(os.path.join(GAME, base+e)): return base+e
        return None

    from rembg import remove, new_session
    session = new_session("u2net")   # 首次会下载模型(~176MB)
    raw_dir = os.path.join(GAME,"assets","_raw"); os.makedirs(raw_dir, exist_ok=True)

    done = 0
    for k in keys:
        rel = real(assets.get(k,""))
        if not rel: print(f"  跳过 {k}（无文件）"); continue
        src = os.path.join(GAME, rel)
        inp = open(src,"rb").read()
        # 备份原图（仅首次）
        bak = os.path.join(raw_dir, os.path.basename(os.path.splitext(rel)[0])+".src.png")
        if not os.path.exists(bak): open(bak,"wb").write(inp)
        out = remove(inp, session=session)           # 透明 PNG bytes
        outrel = os.path.splitext(rel)[0] + ".png"
        open(os.path.join(GAME, outrel),"wb").write(out)
        if outrel != rel:
            try: os.remove(src)                       # 换扩展名则删旧
            except Exception: pass
            assets[k] = outrel
        done += 1
        print(f"  ✅ {k} -> {outrel} (透明)")
    json.dump(manifest, open(os.path.join(GAME,"assets","manifest.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"完成：抠图 {done} 张（原图备份在 assets/_raw/）。刷新游戏即可。")

if __name__ == "__main__":
    main()
