#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键小说生成入口：可选自动 BG 打标，然后转换为游戏数据。"""
import argparse, os, subprocess, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def run(args):
    print("$ " + " ".join(args))
    subprocess.run(args, cwd=SCRIPT_DIR, check=True)

def main():
    parser = argparse.ArgumentParser(description="小说生成器一键入口")
    parser.add_argument("--project", help="小说项目根目录")
    parser.add_argument("--tag", action="store_true", help="先自动插入 BG 转场标记")
    parser.add_argument("--tag-mode", choices=["heuristic", "llm"], default="heuristic")
    parser.add_argument("--only", type=int, help="只处理某章 BG 打标")
    parser.add_argument("--max-per-chapter", type=int, default=4)
    parser.add_argument("--force-tags", action="store_true")
    args = parser.parse_args()

    if args.tag:
        cmd = [sys.executable, "bg_tag_gen.py", "--mode", args.tag_mode, "--max-per-chapter", str(args.max_per_chapter), "--apply"]
        if args.project:
            cmd += ["--project", args.project]
        if args.only:
            cmd += ["--only", str(args.only)]
        if args.force_tags:
            cmd.append("--force")
        run(cmd)

    cmd = [sys.executable, "convert.py"]
    if args.project:
        cmd += ["--project", args.project]
    run(cmd)

if __name__ == "__main__":
    main()
