#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
透明人物立绘居中工具
--------------------
对 char_* 透明 PNG 按 alpha 外接框裁切，再放回同尺寸画布中央，解决模型生成时人物偏左/偏右、留白过大的问题。

用法：
  ./.venv/bin/python center_char.py [--project P] [--only char_jilinchuan] [--all]
"""
import argparse
import json
import os

from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_project(path):
    try:
        cfg = json.load(open(os.path.join(SCRIPT_DIR, "gen_config.json"), encoding="utf-8"))
    except Exception:
        cfg = {}
    path = path or cfg.get("default_project") or "."
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(SCRIPT_DIR, path))


def load_manifest(game):
    path = os.path.join(game, "assets", "manifest.json")
    data = json.load(open(path, encoding="utf-8"))
    return path, data, data.get("assets", data)


def approved_samples(project):
    art_path = os.path.join(project, "设定", "美术设定.json")
    try:
        art = json.load(open(art_path, encoding="utf-8"))
    except Exception:
        return set()
    return set(((art.get("rules") or {}).get("char") or {}).get("approvedSamples") or [])


def real_path(game, rel):
    base = os.path.splitext(rel)[0]
    for ext in (".png", ".webp", ".jpg", ".jpeg"):
        path = os.path.join(game, base + ext)
        if os.path.exists(path):
            return path, base + ext
    return None, None


def centered_image(image, target_fill):
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return image, None

    subject = image.crop(bbox)
    width, height = image.size
    subject_width, subject_height = subject.size
    scale = min(width * target_fill / subject_width, height * target_fill / subject_height, 1.0)
    new_size = (max(1, round(subject_width * scale)), max(1, round(subject_height * scale)))
    if new_size != subject.size:
        subject = subject.resize(new_size, Image.LANCZOS)

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left = (width - subject.width) // 2
    top = (height - subject.height) // 2
    canvas.alpha_composite(subject, (left, top))
    return canvas, {"before": bbox, "after": (left, top, left + subject.width, top + subject.height)}


def main():
    parser = argparse.ArgumentParser(description="透明人物立绘居中")
    parser.add_argument("--project")
    parser.add_argument("--only")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--target-fill", type=float, default=0.86, help="主体占画布宽/高上限比例，默认 0.86")
    parser.add_argument("--include-approved", action="store_true", help="默认跳过 rules.char.approvedSamples；此参数会包含它们")
    args = parser.parse_args()

    project = resolve_project(args.project)
    game = os.path.join(project, "game")
    manifest_path, manifest, assets = load_manifest(game)
    approved = set() if args.include_approved else approved_samples(project)

    if args.only:
        keys = [args.only]
    else:
        keys = [key for key in assets if key.startswith("char_")]
    keys = [key for key in keys if key not in approved]

    raw_dir = os.path.join(game, "assets", "_raw")
    os.makedirs(raw_dir, exist_ok=True)
    done = 0
    for key in keys:
        src, rel = real_path(game, assets.get(key, ""))
        if not src:
            print(f"  跳过 {key}（无文件）")
            continue
        image = Image.open(src).convert("RGBA")
        centered, boxes = centered_image(image, args.target_fill)
        if not boxes:
            print(f"  跳过 {key}（无 alpha 主体）")
            continue

        backup = os.path.join(raw_dir, os.path.basename(os.path.splitext(rel)[0]) + ".precenter.png")
        if not os.path.exists(backup):
            image.save(backup)
        out_rel = os.path.splitext(rel)[0] + ".png"
        centered.save(os.path.join(game, out_rel), "PNG")
        assets[key] = out_rel
        done += 1
        print(f"  ✅ {key} 居中 {boxes['before']} -> {boxes['after']}")

    json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"完成：居中 {done} 张。")


if __name__ == "__main__":
    main()
