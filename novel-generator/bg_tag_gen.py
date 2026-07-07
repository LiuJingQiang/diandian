#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小说正文背景自动打标器。"""
import argparse, glob, json, os, re, sys, urllib.error, urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(SCRIPT_DIR, "gen_config.json"), encoding="utf-8"))
LOCAL_CFG = os.path.join(SCRIPT_DIR, "gen_config.local.json")
if os.path.exists(LOCAL_CFG):
    try:
        CFG.update({k: v for k, v in json.load(open(LOCAL_CFG, encoding="utf-8")).items() if not k.startswith("_")})
    except Exception:
        pass

BG_RE = re.compile(r'^\s*<!--\s*BG\s+([A-Za-z0-9_-]+)\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*-->\s*$')
CH_RE = re.compile(r'第(\d+)章')
UNSAFE_WORDS = ("人物", "人群", "行人", "女性", "孩子", "母亲", "韩照", "白铃", "季暮舟", "季灯", "钟卫", "一名", "一个孩子")

SCENE_RULES = [
    ("home", "季家屋内", ("母亲", "药碗", "药汤", "病榻"), "灰檐区狭窄旧屋，药碗、病榻、破窗纸、煤烟从窗缝渗入，清晨冷光，贫穷压抑，无人物"),
    ("alley", "檐灯巷", ("檐灯巷", "牌坊", "粥铺", "伞铺", "星灯学舍"), "烬岚城灰檐区檐灯巷，粥铺、伞铺、星灯学舍小祠堂、潮湿青石路、煤烟与檐灯，贫穷但有烟火气，无人物"),
    ("court", "鸣钟司大堂", ("鸣钟司", "大堂", "罪钟", "代书席", "代理认罪状"), "烬岚城鸣钟司大堂，东方屋脊与蒸汽管并存，黑铜罪钟高悬，代书席、状纸、红印、煤烟光束，庄严压迫，无人物"),
    ("back_alley", "鸣钟司后巷", ("后门", "放煤的小巷", "米行后门", "茶铺", "追捕铜哨"), "鸣钟司后门外的放煤窄巷，旧告示、红印、煤灰墙面、米行后门与茶铺布帘，追捕铜哨后的紧张气氛，无人物"),
    ("clinic", "黑市医铺", ("黑市药巷", "医铺", "诊椅", "黄铜义手"), "黑市药巷深处的医铺，青布灯笼、草药柜、蒸汽医疗器械、黄铜义手工具，阴冷但有烟火气，无人物"),
    ("rooftop", "东街屋顶", ("屋顶", "验罪点", "假案卷", "钟卫调动"), "烬岚城东街屋顶视角，远处验罪点与调动痕迹，蒸汽烟柱、灰瓦屋脊、飘落假案卷，暮色紧张，无人物"),
    ("bell_tower", "旧钟楼", ("旧钟楼", "西市尽头", "禁入木牌", "旧钟槌"), "西市旧钟楼，黑瓦木楼，被蒸汽管和封条缠绕，禁入木牌、灰尘、旧钟槌与家族旧痕，阴冷压抑，无人物"),
    ("hidden_room", "旧钟楼暗格", ("暗格", "黑色小钟", "旧契", "预备承罪人"), "旧钟楼暗格空镜，黑色小钟、发黄旧契、旧官印、灰尘木板，窗外夜色与后河冷光，命运揭露的压迫感，无人物"),
    ("river", "旧钟楼后河", ("后河", "河水", "跳进夜色", "冰冷河水"), "旧钟楼后方黑暗河道，冷雾、水面反光、远处钟楼剪影、夜色吞没一切，逃亡转场氛围，无人物"),
]

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

def chapter_no(path):
    m = CH_RE.search(os.path.basename(path))
    return int(m.group(1)) if m else 0

def title_and_start(lines):
    title, start = "", 0
    if lines and lines[0].strip().startswith("#"):
        title = re.sub(r'^#+\s*', '', lines[0].strip())
        start = 1
    short = re.sub(r'^第\s*\d+\s*章\s*', '', title).strip() or title or "本章"
    return short, start

def prose_paragraphs(lines, start):
    paras = []
    for i in range(start, len(lines)):
        text = lines[i].strip()
        if not text or BG_RE.match(text) or (text.startswith("<!--") and text.endswith("-->")):
            continue
        paras.append({"line": i, "text": text})
    return paras

def clean_suffix(text):
    return re.sub(r'[^A-Za-z0-9_-]+', '_', text.strip().lower()).strip('_')[:32] or "scene"

def existing_bg_keys(lines):
    keys = set()
    for line in lines:
        m = BG_RE.match(line.strip())
        if m:
            keys.add(m.group(1))
    return keys

def normalize_desc(desc):
    desc = str(desc or "").strip()
    if any(word in desc for word in UNSAFE_WORDS):
        desc += "。画面必须改为空镜，只保留地点、物件、光线和事件痕迹，不出现任何人物或人形"
    if "无人物" not in desc:
        desc += "，无人物"
    return desc

def dedupe_tags(tags, max_tags):
    seen_lines, seen_suffix, out = set(), set(), []
    for tag in sorted(tags, key=lambda item: item["line"]):
        if tag["line"] in seen_lines or tag["suffix"] in seen_suffix:
            continue
        seen_lines.add(tag["line"])
        seen_suffix.add(tag["suffix"])
        out.append(tag)
        if len(out) >= max_tags:
            break
    return out

def heuristic_tags(lines, start, max_tags):
    paras = prose_paragraphs(lines, start)
    tags = []
    for suffix, name, words, desc in SCENE_RULES:
        for para in paras:
            if any(word in para["text"] for word in words):
                tags.append({"line": para["line"], "suffix": suffix, "name": name, "desc": desc})
                break
    if not tags and paras:
        tags.append({"line": paras[0]["line"], "suffix": "opening", "name": "章节开场", "desc": normalize_desc(f"根据本章开场生成的空镜背景：{paras[0]['text'][:80]}，东方幻想蒸汽城邦风格")})
    return dedupe_tags(tags, max_tags)

def llm_tags(lines, start, ch_no, short, max_tags):
    paras = prose_paragraphs(lines, start)
    sampled = [{"i": i, "text": para["text"][:180]} for i, para in enumerate(paras[:80])]
    prompt = (
        "你是互动读书游戏的场景导演。请为章节自动插入背景转场点。\n"
        "只在地点/时间/视觉空间明显变化处打标；每章 2-5 个；背景必须是空镜、无人物，适合叠加立绘和对话框。\n"
        "严禁在 desc 中出现可见人物/人群/角色动作/母亲/孩子/韩照/白铃/季暮舟；只能描述地点、物件、光线、痕迹。\n"
        "key_suffix 必须用英文 snake_case，不要用拼音。\n"
        "返回 JSON 数组，不要解释。字段：paragraph(下方段落编号i), key_suffix, name(中文场景名), desc(中文绘图描述，必须以“无人物”结尾)。\n"
        f"章节：第{ch_no}章《{short}》；最多 {max_tags} 个。\n段落：{json.dumps(sampled, ensure_ascii=False)}"
    )
    m = re.search(r"\[.*\]", text_gen(prompt), re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except Exception:
        return []
    tags = []
    for item in data:
        try:
            idx = int(item.get("paragraph"))
        except Exception:
            continue
        if idx < 0 or idx >= len(paras):
            continue
        tags.append({
            "line": paras[idx]["line"],
            "suffix": clean_suffix(str(item.get("key_suffix", "scene"))),
            "name": str(item.get("name", "转场背景")).strip() or "转场背景",
            "desc": normalize_desc(item.get("desc", "")),
        })
    return dedupe_tags(tags, max_tags)

def marker_for(ch_no, tag):
    key = f"scene_ch{ch_no}_{clean_suffix(tag['suffix'])}"
    return key, f"<!-- BG {key} | {tag['name']} | {tag['desc']} -->"

def apply_tags(path, tags, dry_run, force):
    lines = open(path, encoding="utf-8").read().splitlines()
    existing = existing_bg_keys(lines)
    inserts = []
    for tag in tags:
        key, marker = marker_for(chapter_no(path), tag)
        if key in existing and not force:
            continue
        inserts.append((tag["line"], key, marker))
    if dry_run:
        return inserts
    by_line = {}
    for line_no, _, marker in inserts:
        by_line.setdefault(line_no, []).append(marker)
    out = []
    for i, line in enumerate(lines):
        out.extend(by_line.get(i, []))
        out.append(line)
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    return inserts

def main():
    parser = argparse.ArgumentParser(description="小说正文背景自动打标器")
    parser.add_argument("--project")
    parser.add_argument("--only", type=int)
    parser.add_argument("--mode", choices=["heuristic", "llm"], default="heuristic")
    parser.add_argument("--max-per-chapter", type=int, default=4)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    project = resolve_project(args.project)
    files = sorted(glob.glob(os.path.join(project, "正文", "第*章.md")), key=chapter_no)
    if args.only:
        files = [path for path in files if chapter_no(path) == args.only]
    if not files:
        raise SystemExit(f"未找到章节：{os.path.join(project, '正文')}")
    print(f"[{project}] BG 自动打标 mode={args.mode} action={'apply' if args.apply else 'dry-run'}")
    total = 0
    for path in files:
        lines = open(path, encoding="utf-8").read().splitlines()
        short, start = title_and_start(lines)
        tags = llm_tags(lines, start, chapter_no(path), short, args.max_per_chapter) if args.mode == "llm" else heuristic_tags(lines, start, args.max_per_chapter)
        inserts = apply_tags(path, tags, dry_run=not args.apply, force=args.force)
        total += len(inserts)
        print(f"● {os.path.basename(path)} {short}: {len(inserts)} 个")
        for _, key, marker in inserts:
            print(f"  - {key}: {marker}")
    print(f"完成：{'写入' if args.apply else '预览'} {total} 个 BG 标记。再跑 convert.py 生效。")

if __name__ == "__main__":
    main()
