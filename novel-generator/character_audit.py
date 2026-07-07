#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""角色审计工具：扫描小说正文/设定/大纲，找出 book.config.json roster 缺失的重要人物。"""
import argparse, glob, json, os, re
from collections import Counter, defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ROLE_PATTERNS = [
    ("jimu", "季母", ["季母", "母亲", "娘", "他母亲", "季暮舟的母亲"], "家庭核心，主角药钱压力来源", "high"),
    ("jideng", "季灯", ["季灯", "妹妹", "他妹妹"], "主角妹妹，星灯学舍与家庭压力来源", "high"),
    ("teahouse_owner", "茶铺老板娘", ["茶铺老板娘", "老板娘", "茶铺老板"], "灰檐区人情网，帮助逃脱", "medium"),
    ("congee_vendor", "粥铺阿婆", ["粥铺阿婆", "卖粥的阿婆", "卖粥的"], "街坊代表，灰檐区代入点", "medium"),
    ("bell_guard", "钟卫", ["钟卫", "守卫"], "鸣钟司执行层，泛用敌方群体", "medium"),
    ("wang_widow", "王寡妇", ["王寡妇"], "过往求助案例，低频 NPC", "low"),
    ("umbrella_craftsman", "修伞匠", ["修伞匠"], "街坊氛围 NPC", "low"),
    ("cloud_tier_official", "云阶区官员", ["云阶区来的人", "云阶区官员"], "高层权力象征", "medium"),
]

def resolve_project(path):
    if path:
        return path if os.path.isabs(path) else os.path.normpath(os.path.join(SCRIPT_DIR, path))
    cfg_path = os.path.join(SCRIPT_DIR, "gen_config.json")
    try:
        cfg = json.load(open(cfg_path, encoding="utf-8"))
        default = cfg.get("default_project") or "."
    except Exception:
        default = "."
    return default if os.path.isabs(default) else os.path.normpath(os.path.join(SCRIPT_DIR, default))

def iter_text_files(project):
    roots = ["正文", "设定", "大纲"]
    for root in roots:
        for path in sorted(glob.glob(os.path.join(project, root, "**", "*.md"), recursive=True)):
            yield path

def line_hits(path, aliases):
    hits = []
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except Exception:
        return hits
    for lineno, line in enumerate(lines, 1):
        matched = [alias for alias in aliases if alias in line]
        if matched:
            hits.append((lineno, line.strip(), matched))
    return hits

def current_roster(project):
    cfg = json.load(open(os.path.join(project, "book.config.json"), encoding="utf-8"))
    roster = cfg.get("roster", [])
    aliases = set()
    ids = set()
    for item in roster:
        ids.add(item.get("id"))
        aliases.add(item.get("name", ""))
        aliases.update(item.get("aliases", []))
    return roster, aliases, ids

def audit(project):
    roster, known_aliases, known_ids = current_roster(project)
    files = list(iter_text_files(project))
    report = []
    summary = []
    for suggested_id, name, aliases, note, priority in ROLE_PATTERNS:
        all_hits = []
        counter = Counter()
        for path in files:
            hits = line_hits(path, aliases)
            if hits:
                rel = os.path.relpath(path, project)
                for lineno, text, matched in hits:
                    all_hits.append((rel, lineno, text, matched))
                    counter.update(matched)
        is_known = suggested_id in known_ids or any(alias in known_aliases for alias in aliases)
        if all_hits:
            summary.append({
                "id": suggested_id,
                "name": name,
                "aliases": aliases,
                "hits": len(all_hits),
                "known": is_known,
                "priority": priority,
                "note": note,
                "examples": all_hits[:5],
            })
    return roster, summary

def write_report(project, roster, summary):
    out_dir = os.path.join(project, "追踪")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "角色审计报告.md")
    lines = ["# 角色审计报告", "", f"项目：`{project}`", "", "## 当前 roster", ""]
    for item in roster:
        lines.append(f"- `{item.get('id')}` · {item.get('name')} · aliases={item.get('aliases', [])}")
    lines += ["", "## 候选/缺失角色", "", "| 优先级 | 状态 | 建议 id | 名称 | 命中 | 建议 aliases | 说明 |", "|---|---|---|---|---:|---|---|"]
    for item in summary:
        status = "已在 roster" if item["known"] else "缺失"
        lines.append(f"| {item['priority']} | {status} | `{item['id']}` | {item['name']} | {item['hits']} | `{item['aliases']}` | {item['note']} |")
    lines += ["", "## 缺失角色建议配置", ""]
    missing = [item for item in summary if not item["known"] and item["priority"] in ("high", "medium")]
    if missing:
        lines.append("```json")
        for item in missing:
            lines.append(json.dumps({"id": item["id"], "name": item["name"], "lead": False, "aliases": item["aliases"]}, ensure_ascii=False) + ",")
        lines.append("```")
    else:
        lines.append("无高/中优先级缺失角色。")
    lines += ["", "## 证据样例", ""]
    for item in summary:
        lines.append(f"### {item['name']} · `{item['id']}`")
        for rel, lineno, text, matched in item["examples"]:
            lines.append(f"- `{rel}:{lineno}` · matched={matched} · {text}")
        lines.append("")
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    return out

def main():
    parser = argparse.ArgumentParser(description="审计小说项目 roster 缺失角色")
    parser.add_argument("--project")
    args = parser.parse_args()
    project = resolve_project(args.project)
    roster, summary = audit(project)
    out = write_report(project, roster, summary)
    missing = [item for item in summary if not item["known"]]
    print(f"✅ 角色审计完成：{out}")
    print(f"   当前 roster {len(roster)} 人 · 命中候选 {len(summary)} · 缺失 {len(missing)}")
    for item in missing:
        print(f"   - [{item['priority']}] {item['name']} -> {item['id']} ({item['hits']} hits)")

if __name__ == "__main__":
    main()
