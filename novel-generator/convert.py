#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小说 -> 互动读书游戏数据生成器。"""
import argparse, glob, json, os, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
QUOTE_RE = re.compile(r'“[^”]*”|「[^」]*」|"[^"]*"')
STARTS_QUOTE_RE = re.compile(r'^\s*(“|「|")')
BG_RE = re.compile(r'^\s*<!--\s*BG\s+([A-Za-z0-9_-]+)\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*-->\s*$')
MAX_CHAT_CHARS = 46

def resolve_project(cli_project):
    cfg = load_json(os.path.join(SCRIPT_DIR, "gen_config.json"), {})
    p = cli_project or cfg.get("default_project") or "."
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(SCRIPT_DIR, p))

def load_json(path, default=None):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def const_num(n): return {"name": "const", "num": n, "str": "", "vType": 1}
def const_str(s): return {"name": "", "num": 0, "str": s, "vType": 3}
def var_ref(v): return {"name": v, "num": 0, "str": "", "vType": 1}
def set_str(var, s): return {"var": var, "method": 5, "ops": [], "list": [const_str(s)]}
def add_num(var, n): return {"var": var, "method": 5, "ops": ["+"], "list": [var_ref(var), const_num(n)]}

def alias_in(text, roster):
    best, best_pos = None, 10**9
    for r in roster:
        for a in r.get("aliases", []):
            if len(a) < 2:
                continue
            pos = text.find(a)
            if pos != -1 and pos < best_pos:
                best, best_pos = r, pos
    return best

def speaker_of(para, qstart, qend, roster):
    return alias_in(para[qend:qend + 12], roster) or alias_in(para[max(0, qstart - 12):qstart], roster)

def chat(char_id, text, msg_type="0", handlers=None, focus_char=None):
    data = {"char": char_id or "", "text": text, "msgType": msg_type, "imgKey": "", "conditions": [], "handlers": handlers or []}
    if focus_char and not char_id:
        data["focusChar"] = focus_char
    return data

def split_long_text(text, max_chars=MAX_CHAT_CHARS):
    """固定高度对话框约束：每条 chat 必须能完整放入阅读框。
    优先按中文句读切分；单句过长时再按逗号/语义停顿兜底切分。
    """
    text = (text or "").strip()
    if len(text) <= max_chars:
        return [text] if text else []
    sentences = re.findall(r'.+?[。！？!?；;…]+|.+$', text)
    chunks, buf = [], ""
    def push_buffer(value):
        value = value.strip()
        if value:
            chunks.append(value)
    for sent in [s.strip() for s in sentences if s.strip()]:
        if len(sent) > max_chars:
            if buf:
                push_buffer(buf); buf = ""
            parts = re.findall(r'.+?[，,、：:]+|.+$', sent)
            cur = ""
            for part in [p.strip() for p in parts if p.strip()]:
                if len(part) > max_chars:
                    if cur:
                        push_buffer(cur); cur = ""
                    for i in range(0, len(part), max_chars):
                        push_buffer(part[i:i + max_chars])
                elif len(cur) + len(part) <= max_chars:
                    cur += part
                else:
                    push_buffer(cur); cur = part
            if cur:
                push_buffer(cur)
        elif len(buf) + len(sent) <= max_chars:
            buf += sent
        else:
            push_buffer(buf); buf = sent
    if buf:
        push_buffer(buf)
    return chunks

def fit_chats_to_dialog(chats):
    fitted = []
    for item in chats:
        parts = split_long_text(item.get("text", ""))
        if not parts:
            continue
        for idx, part in enumerate(parts):
            next_item = dict(item)
            next_item["text"] = part
            # handlers / bgKey / sceneName must fire only once, on the first displayed slice.
            if idx:
                next_item["handlers"] = []
                next_item.pop("bgKey", None)
                next_item.pop("sceneName", None)
            fitted.append(next_item)
    return fitted

def split_paragraph_to_chats(para, roster, default_speaker=None):
    out = []
    m = re.match(r'^\s*【(.+?)】\s*[:：]?\s*(.*)$', para)
    if m:
        who, body = m.group(1).strip(), m.group(2).strip()
        r = next((r for r in roster if who == r.get("name") or who in r.get("aliases", [])), None)
        return fit_chats_to_dialog([chat(r["id"] if r else "", (body or para).strip())])
    focus = alias_in(para, roster)
    if QUOTE_RE.search(para):
        last = 0
        for mt in QUOTE_RE.finditer(para):
            pre = para[last:mt.start()].strip()
            if pre:
                pre_focus = alias_in(pre, roster) or focus
                out.append(chat("", pre, focus_char=pre_focus["id"] if pre_focus else None))
            spk = speaker_of(para, mt.start(), mt.end(), roster) or default_speaker
            out.append(chat(spk["id"] if spk else "", mt.group(0)))
            last = mt.end()
        tail = para[last:].strip()
        if tail:
            tail_focus = alias_in(tail, roster) or focus
            out.append(chat("", tail, focus_char=tail_focus["id"] if tail_focus else None))
        if out:
            return fit_chats_to_dialog(out)
    return fit_chats_to_dialog([chat("", para.strip(), focus_char=focus["id"] if focus else None)])

def read_chapters(prose_dir):
    files = sorted(glob.glob(os.path.join(prose_dir, "第*章.md")), key=lambda f: int(re.search(r'第(\d+)章', os.path.basename(f)).group(1)))
    chapters = []
    for f in files:
        n = int(re.search(r'第(\d+)章', os.path.basename(f)).group(1))
        lines = open(f, encoding="utf-8").read().splitlines()
        title = ""
        if lines and lines[0].strip().startswith("#"):
            title = re.sub(r'^#+\s*', '', lines[0]).strip()
            lines = lines[1:]
        short = re.sub(r'^第\s*\d+\s*章\s*', '', title).strip() or f"第{n}章"
        paras, bg_scenes = [], []
        for raw in lines:
            p = raw.strip()
            if not p:
                continue
            m = BG_RE.match(p)
            if m:
                scene = {"key": m.group(1).strip(), "name": m.group(2).strip(), "desc": m.group(3).strip()}
                paras.append({"type": "bg", **scene})
                bg_scenes.append(scene)
            elif p.startswith("<!--") and p.endswith("-->"):
                continue
            else:
                paras.append({"type": "text", "text": p})
        chapters.append({"n": n, "title": title or f"第{n}章", "short": short, "paras": paras, "bg_scenes": bg_scenes})
    return chapters

def collect_bg_scenes(chapters):
    scenes = {}
    for ch in chapters:
        for sc in ch.get("bg_scenes", []):
            scenes[sc["key"]] = sc
    return scenes

def chapter_chats(chapter, roster):
    out, pending_bg, last_actor = [], None, None
    for item in chapter.get("paras", []):
        if item.get("type") == "bg":
            pending_bg = item
            continue
        text = item.get("text", "")
        starts_quote = bool(STARTS_QUOTE_RE.match(text))
        chats = split_paragraph_to_chats(text, roster, default_speaker=last_actor if starts_quote else None)
        if pending_bg and chats:
            chats[0]["bgKey"] = pending_bg["key"]
            chats[0]["sceneName"] = pending_bg["name"]
            pending_bg = None
        out.extend(chats)
        actor = alias_in(text, roster)
        if actor:
            last_actor = actor
        elif not starts_quote and text.endswith(("。", "！", "？", "?", "!")):
            # Keep recent actor for immediate quote replies, but do not let it leak indefinitely.
            last_actor = None
    return out

def chunk(lst, k):
    return [lst[i:i + k] for i in range(0, len(lst), k)] or [[]]

def fallback_choice(attrs, idx):
    a = attrs or ["隐忍", "锋芒", "城府", "赤诚"]
    pairs = [
        [("不动声色，先看清局势", a[0 % len(a)]), ("寸步不让，当场回击", a[1 % len(a)])],
        [("留个心眼，暗中记下", a[2 % len(a)]), ("坦荡直言，问个明白", a[3 % len(a)])],
        [("忍住情绪，稳住阵脚", a[0 % len(a)]), ("锋芒毕露，先声夺人", a[1 % len(a)])],
    ][idx % 3]
    return {"options": [{"text": t, "effects": {attr: 5}} for t, attr in pairs]}

def contextual_option_title(seg_chats):
    text = "".join(c.get("text", "") for c in (seg_chats or [])[-3:])
    if "罪钟" in text or "落印" in text:
        return "罪钟将落，你要如何落笔？"
    if "韩照" in text or "钟卫" in text:
        return "韩照逼近，你要如何破局？"
    if "檐灯巷" in text or "街坊" in text:
        return "檐灯巷危在眼前，你先护哪一边？"
    if "白铃" in text:
        return "白铃就在身侧，你要如何回应？"
    if "陆青萝" in text or "黑市" in text or "药" in text:
        return "黑市药灯未灭，你要如何取信？"
    if "旧钟楼" in text or "旧契" in text:
        return "旧钟楼藏着真相，你要先查哪里？"
    return "此刻的抉择是——"

def build_story(chapters, cfg, choices=None):
    choices = choices or {}
    roster = cfg["roster"]
    characters = {r["id"]: {"name": r["name"], "lead": r["lead"], "drawingKey": f"char_{r['id']}", "avatarKey": f"avatar_{r['id']}"} for r in roster}
    attrs = cfg.get("attributes", [])
    variables = list(dict.fromkeys(list(cfg.get("variables", [])) + attrs))
    seg_size = cfg.get("segmentSize", 14)
    opt_cost = cfg.get("optionCost", 12)
    unlock_cost = cfg.get("chapterUnlockCost", 12)
    first_choice = cfg.get("firstChapterChoice")
    nodes, templates, first_start = {}, [], None

    def make_choice(cp_id, next_id, seg_chats, ci):
        spec = choices.get(cp_id) or fallback_choice(attrs, ci)
        opts = [{"text": o["text"], "cost": {"energy": opt_cost}, "isAd": False, "handlers": [add_num(k, v) for k, v in (o.get("effects") or {}).items()], "conditions": [], "next": next_id} for o in spec.get("options", [])]
        ctx = " ".join(c.get("text", "") for c in seg_chats[-6:])[:300]
        templates.append({"id": cp_id, "context": ctx, "attributes": attrs, "characters": [r["name"] for r in roster if not r.get("lead")]})
        return spec.get("title") or contextual_option_title(seg_chats), opts

    for ci, ch in enumerate(chapters):
        segs = chunk(chapter_chats(ch, roster), seg_size)
        for si, seg in enumerate(segs):
            nid = f"ch{ch['n']}_s{si}"
            if first_start is None:
                first_start = nid
            node = {"id": nid, "name": ch["title"], "bgKey": f"scene_ch{ch['n']}", "sceneName": ch["short"], "isEnd": False, "chats": seg, "options": [], "diverts": [], "handlers": []}
            if ci == 0 and si == 0 and cfg.get("leadName"):
                node["handlers"] = [set_str("主角名字", cfg["leadName"])]
            if si < len(segs) - 1:
                nxt = f"ch{ch['n']}_s{si + 1}"
                title, opts = make_choice(nid, nxt, seg, ci * 10 + si)
                node["optionTitle"], node["options"] = title, opts
            elif ci == len(chapters) - 1:
                node["isEnd"] = True
            else:
                nxt = f"ch{chapters[ci + 1]['n']}_s0"
                if ci == 0 and first_choice:
                    node["optionTitle"] = first_choice.get("title", "你的选择是——")
                    node["options"] = [{"text": o["text"], "cost": {"energy": o.get("cost", 0)}, "isAd": bool(o.get("isAd")), "handlers": [add_num(k, v) for k, v in (o.get("effects") or {}).items()], "conditions": [], "next": nxt} for o in first_choice.get("options", [])]
                else:
                    node["optionTitle"] = f"下一章《{chapters[ci + 1]['short']}》尚未解锁"
                    node["options"] = [{"text": "解锁下一章", "cost": {"energy": unlock_cost}, "isAd": False, "handlers": [], "conditions": [], "next": nxt}, {"text": "看广告免费解锁", "cost": {"energy": 0}, "isAd": True, "handlers": [], "conditions": [], "next": nxt}]
            nodes[nid] = node
    return {"bookId": cfg["bookId"], "name": cfg["name"], "author": cfg.get("author", ""), "categories": cfg.get("categories", []), "intro": cfg.get("intro", ""), "coverKey": "cover_book", "startEnergy": cfg.get("startEnergy", 60), "start": first_start, "variables": variables, "characters": characters, "nodes": nodes}, templates

def build_manifest(story, chapters):
    assets = {"cover_book": "assets/covers/cover_book.webp"}
    for c in story["characters"].values():
        assets[c["drawingKey"]] = f"assets/characters/{c['drawingKey']}.webp"
        assets[c["avatarKey"]] = f"assets/characters/{c['avatarKey']}.webp"
    for ch in chapters:
        assets[f"scene_ch{ch['n']}"] = f"assets/scenes/scene_ch{ch['n']}.webp"
    for key in collect_bg_scenes(chapters):
        assets[key] = f"assets/scenes/{key}.webp"
    return {"_note": "key -> 本地素材文件。空值或缺文件将显示占位图。", "assets": assets}

def build_art_spec(story, chapters, existing=None):
    existing = existing or {}
    spec = {"_note": "素材生成输入配置。convert 会合并保留作者已填写内容。", "style": {"global": "东方幻想蒸汽城邦 + 轻小说插画风，电影感冷暖对比，高细节，统一画风", "negative": "低质, 模糊, 畸形, 多余手指, 多余肢体, 水印, 文字乱码, 杂乱背景, 西式贵族过重, 现代电子设备", "quality": "masterpiece, best quality, highly detailed, cinematic lighting"}, "aspect": {"cover": "3:4 竖版", "char": "3:4 竖版半身/全身", "avatar": "1:1 方形", "scene": "16:9 横版", "cg": "16:9 横版"}, "characters": {}, "scenes": {}}
    for grp in ("style", "aspect"):
        if isinstance(existing.get(grp), dict):
            spec[grp].update(existing[grp])
    ex_chars = existing.get("characters", {}) or {}
    for cid, c in story["characters"].items():
        prev = ex_chars.get(cid, {})
        spec["characters"][cid] = {"name": c["name"], "appearance": prev.get("appearance", ""), "refImage": prev.get("refImage", ""), "seed": prev.get("seed"), "notes": prev.get("notes", "")}
    ex_scenes = existing.get("scenes", {}) or {}
    for ch in chapters:
        key, prev = f"scene_ch{ch['n']}", ex_scenes.get(f"scene_ch{ch['n']}", {})
        spec["scenes"][key] = {"name": ch["short"], "desc": prev.get("desc", "")}
    for key, sc in collect_bg_scenes(chapters).items():
        prev = ex_scenes.get(key, {})
        spec["scenes"][key] = {"name": sc["name"], "desc": prev.get("desc") or sc.get("desc", "")}
    return spec

def ai_prompt(kind, label):
    style = "国潮/东方蒸汽轻小说插画风，电影感光影"
    return f"{style}；{kind}：{label}"

def build_checklist(story, chapters, manifest, book_name):
    bg_scenes = collect_bg_scenes(chapters)
    scene_rows = [(f"scene_ch{ch['n']}", f"第{ch['n']}章《{ch['short']}》场景", manifest["assets"][f"scene_ch{ch['n']}"]) for ch in chapters]
    scene_rows += [(key, f"转场《{sc['name']}》背景", manifest["assets"][key]) for key, sc in bg_scenes.items()]
    lines = [f"# 缺素材清单 · {book_name}\n", "| 层级 | 游戏素材槽位 | 数量 |", "|---|---|---|", f"| 书 | `cover_book` | 1 |", f"| 人物 | `char_*` + `avatar_*` | {len(story['characters'])} 人 |", f"| 场景 | `scene_*` | {len(scene_rows)} 个 |\n"]
    lines += ["## ① 封面", "", f"| `cover_book` | 《{book_name}》封面 | `{manifest['assets']['cover_book']}` |", "", "## ② 人物立绘 / 头像", ""]
    for c in story["characters"].values():
        lines.append(f"| `{c['drawingKey']}` | {c['name']} 立绘 | `{manifest['assets'][c['drawingKey']]}` |")
        lines.append(f"| `{c['avatarKey']}` | {c['name']} 头像 | `{manifest['assets'][c['avatarKey']]}` |")
    lines += ["", "## ③ 场景背景", ""]
    for key, label, path in scene_rows:
        lines.append(f"| `{key}` | {label} | `{path}` |")
    return "\n".join(lines) + "\n"

def preserve_existing_asset_paths(game, manifest):
    assets = manifest.get("assets", manifest)
    for k, v in list(assets.items()):
        base = re.sub(r'\.(webp|png|jpg|jpeg)$', '', v, flags=re.I)
        for ext in ('.png', '.webp', '.jpg', '.jpeg'):
            if os.path.exists(os.path.join(game, base + ext)):
                assets[k] = base + ext
                break

def main():
    ap = argparse.ArgumentParser(description="小说 -> 互动读书游戏数据生成器")
    ap.add_argument("--project", help="小说项目根目录")
    args = ap.parse_args()
    project = resolve_project(args.project)
    game = os.path.join(project, "game")
    cfg_path = os.path.join(project, "book.config.json")
    cfg = load_json(cfg_path)
    if not cfg:
        raise SystemExit(f"缺 book.config.json：{cfg_path}")
    chapters = read_chapters(os.path.join(project, "正文"))
    if not chapters:
        raise SystemExit(f"未找到章节：{os.path.join(project, '正文')}")
    choices = load_json(os.path.join(project, "choices.json"), {}) or {}
    story, templates = build_story(chapters, cfg, choices)
    manifest = build_manifest(story, chapters)
    preserve_existing_asset_paths(game, manifest)

    for sub in ("assets", "assets/covers", "assets/characters", "assets/scenes", "assets/cg"):
        os.makedirs(os.path.join(game, sub), exist_ok=True)
    art_path = os.path.join(project, "设定", "美术设定.json")
    art_spec = build_art_spec(story, chapters, load_json(art_path, {}) or {})
    save_json(os.path.join(project, "choices.template.json"), {"_note": "convert 产出的选择点上下文；choice_gen.py 据此生成 choices.json。", "points": templates})
    save_json(art_path, art_spec)
    save_json(os.path.join(game, f"story.{cfg['bookId']}.json"), story)
    save_json(os.path.join(game, "books.json"), [{"bookId": cfg["bookId"], "name": cfg["name"], "file": f"story.{cfg['bookId']}.json"}])
    save_json(os.path.join(game, "assets", "manifest.json"), manifest)
    open(os.path.join(game, "缺素材清单.md"), "w", encoding="utf-8").write(build_checklist(story, chapters, manifest, cfg["name"]))
    total_chats = sum(len(n["chats"]) for n in story["nodes"].values())
    print(f"✅ {cfg['name']} 生成完成 (project: {project})")
    print(f"   节点 {len(story['nodes'])} · chats {total_chats} · 角色 {len(story['characters'])} · 素材槽 {len(manifest['assets'])}")
    print(f"   BG 转场 {len(collect_bg_scenes(chapters))} 个 · 美术设定: 设定/美术设定.json")

if __name__ == "__main__":
    main()
