#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""平行付费选项生成器。"""
import argparse, json, os, re, sys, urllib.error, urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(SCRIPT_DIR, "gen_config.json"), encoding="utf-8"))
LOCAL_CFG = os.path.join(SCRIPT_DIR, "gen_config.local.json")
if os.path.exists(LOCAL_CFG):
    try:
        CFG.update({k: v for k, v in json.load(open(LOCAL_CFG, encoding="utf-8")).items() if not k.startswith("_")})
    except Exception:
        pass

def resolve_project(path):
    path = path or CFG.get("default_project") or "."
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(SCRIPT_DIR, path))

def api_key():
    env = CFG.get("api_key_env", "OPENROUTER_API_KEY")
    key = os.environ.get(env, "").strip() or str(CFG.get("api_key", "")).strip()
    if not key:
        sys.exit(f"❌ 未找到 OpenRouter key（export {env} 或填 gen_config.local.json 的 api_key）")
    return key

def text_gen(prompt):
    req = urllib.request.Request(
        CFG["base_url"].rstrip("/") + "/chat/completions",
        data=json.dumps({"model": CFG["text_model"], "messages": [{"role": "user", "content": prompt}]}).encode("utf-8"),
        method="POST",
    )
    req.add_header("Authorization", "Bearer " + api_key())
    req.add_header("Content-Type", "application/json")
    req.add_header("HTTP-Referer", CFG.get("referer", ""))
    req.add_header("X-Title", CFG.get("title", ""))
    try:
        with urllib.request.urlopen(req, timeout=CFG.get("timeout_sec", 120)) as res:
            return json.loads(res.read().decode("utf-8"))["choices"][0]["message"].get("content", "")
    except urllib.error.HTTPError as err:
        sys.exit(f"❌ OpenRouter HTTP {err.code}: {err.read().decode('utf-8')[:300]}")

def gen_one(point):
    prompt = (
        "你在为一款互动读书游戏设计选择点。基于剧情上下文，给出 2 个不同应对选项。\n"
        "要求：每个选项≤14字，贴合上下文；两个选项体现不同性格取向；每个选项只改 1 个属性 +5。\n"
        "只返回JSON：{\"title\":\"一句提问\",\"options\":[{\"text\":\"...\",\"effects\":{\"属性\":5}}]}\n"
        f"可用属性：{point.get('attributes') or []}\n可用角色：{point.get('characters') or []}\n剧情上下文：{point.get('context', '')}"
    )
    m = re.search(r"\{.*\}", text_gen(prompt), re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser(description="平行付费选项生成器")
    parser.add_argument("--project")
    parser.add_argument("--only")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    project = resolve_project(args.project)
    template_path = os.path.join(project, "choices.template.json")
    output_path = os.path.join(project, "choices.json")
    if not os.path.exists(template_path):
        sys.exit(f"缺 {template_path}，先跑 convert.py")
    points = json.load(open(template_path, encoding="utf-8")).get("points", [])
    existing = json.load(open(output_path, encoding="utf-8")) if os.path.exists(output_path) else {}
    todo = [p for p in points if (not args.only or p["id"] == args.only) and (args.force or p["id"] not in existing)]
    if args.limit:
        todo = todo[:args.limit]
    print(f"[{project}] 选择点 {len(points)} 个，待生成 {len(todo)} 个")
    done = 0
    for point in todo:
        print(f"● {point['id']} ctx: {point.get('context', '')[:34]}…")
        if args.dry_run:
            continue
        spec = gen_one(point)
        if not spec or not spec.get("options"):
            print("  ⚠️ 解析失败，跳过")
            continue
        existing[point["id"]] = spec
        done += 1
        json.dump(existing, open(output_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  ✅ {spec.get('title', '')}")
    print(f"完成：写入 {done} 个 -> choices.json（再跑 convert.py 生效）")

if __name__ == "__main__":
    main()
