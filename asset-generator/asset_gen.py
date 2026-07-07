#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片素材生成器（OpenRouter）· 独立工具，可对任意小说游戏项目运行
------------------------------------------------------------------
缺什么图片素材就生成什么；产物直接落盘到 <project>/game/assets/ 并回写 manifest。
小说/文本生成模型属于 ../novel-generator；本工具只读取 image_model 出图。
依赖：仅 Python 标准库(urllib)。

用法：
  export OPENROUTER_API_KEY=sk-or-...
  python3 asset_gen.py --project /path/to/命运币的代价 list
  python3 asset_gen.py --project ... gen --only char_shenmo
  python3 asset_gen.py --project ... gen --all [--dry-run] [--force]
  (省略 --project 用 gen_config.json 的 default_project)
"""
import os, re, sys, json, glob, base64, argparse, urllib.request, urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(SCRIPT_DIR, "gen_config.json"), encoding="utf-8"))
# 可选：本地私密覆盖文件(不提交)，用于放 api_key 等敏感项
_local = os.path.join(SCRIPT_DIR, "gen_config.local.json")
if os.path.exists(_local):
    try: CFG.update({k: v for k, v in json.load(open(_local, encoding="utf-8")).items() if not k.startswith("_")})
    except Exception: pass

# 由 main() 按 --project 设定
PROJECT = GAME = ART_PATH = None

def resolve_project(cli_project):
    p = cli_project or CFG.get("default_project") or "."
    if not os.path.isabs(p):
        p = os.path.normpath(os.path.join(SCRIPT_DIR, p))
    return p

def load_json(p, default=None):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return default

def save_json(p, obj):
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def story():
    files = glob.glob(os.path.join(GAME, "story.*.json"))
    return load_json(files[0], {}) if files else {}

def manifest():
    m = load_json(os.path.join(GAME, "assets", "manifest.json"), {})
    return m.get("assets", m), m

def art():
    return load_json(ART_PATH, {}) or {}

def kind_of(key):
    if key.startswith("cover"):  return "cover"
    if key.startswith("avatar"): return "avatar"
    if key.startswith("char"):   return "char"
    if key.startswith("scene"):  return "scene"
    if key.startswith("cg"):     return "cg"
    return "misc"

DEFAULT_CHAR_PROMPT = (
    "单个人类角色全身/半身立绘，必须清楚画出一个活人角色的头部、脸、身体和服装，人物是唯一主体；"
    "人物必须居中构图，左右留白均衡，主体占画面高度约85%，不要偏左、不要偏右、不要为对话框预留大空白；"
    "PNG透明背景，alpha通道，背景必须完全透明；不要非人物主体，不要物品单独成图，不要钟、契约、文书、印章、建筑或场景作为主体；"
    "不要纯色背景、不要渐变背景、不要室内外场景、不要街景、不要建筑、不要墙面、不要地面、不要烟雾、不要光效背景、不要装饰性背景元素；"
    "不要裁掉头发、手、脚或衣摆"
)

def char_rules(A):
    return ((A.get("rules") or {}).get("char") or {})

def excluded_char_ids(A):
    return set(char_rules(A).get("excludeCharacterIds") or [])

def is_excluded_char(key, A):
    return kind_of(key) == "char" and key.split("_", 1)[1] in excluded_char_ids(A)

def char_prompt_rule(A):
    return char_rules(A).get("prompt") or DEFAULT_CHAR_PROMPT

def file_exists(path):
    if not path: return False
    base = re.sub(r"\.(webp|png|jpg|jpeg)$", "", path, flags=re.I)
    for e in (".webp", ".png", ".jpg", ".jpeg"):
        if os.path.exists(os.path.join(GAME, base + e)): return True
    return os.path.exists(os.path.join(GAME, path))

def missing_assets():
    assets, _ = manifest()
    return [(k, v) for k, v in assets.items() if not file_exists(v)]

# ---------------- OpenRouter ----------------
def api_key():
    # 优先级: 环境变量 > gen_config(.local).json 的 api_key 字段
    env = CFG.get("api_key_env", "OPENROUTER_API_KEY")
    k = os.environ.get(env, "").strip() or str(CFG.get("api_key", "")).strip()
    if not k:
        sys.exit(f"❌ 未找到 OpenRouter key。三选一：\n"
                 f"   1) export {env}=sk-or-...\n"
                 f"   2) 在 gen_config.local.json 填 \"api_key\"（推荐，不提交）\n"
                 f"   3) 在 gen_config.json 填 \"api_key\"")
    return k

def call(model, messages, image=False, image_config=None):
    url = CFG["base_url"].rstrip("/") + "/chat/completions"
    body = {"model": model, "messages": messages}
    if image:
        body["modalities"] = ["image", "text"]
        if image_config:
            body["image_config"] = image_config
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST")
    req.add_header("Authorization", "Bearer " + api_key())
    req.add_header("Content-Type", "application/json")
    req.add_header("HTTP-Referer", CFG.get("referer", ""))
    req.add_header("X-Title", CFG.get("title", ""))
    try:
        with urllib.request.urlopen(req, timeout=CFG.get("timeout_sec", 120)) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"❌ OpenRouter HTTP {e.code}: {e.read().decode('utf-8')[:500]}")
    except Exception as e:
        sys.exit(f"❌ 请求失败: {e}")

def text_gen(prompt):
    sys.exit("❌ 文本/小说生成模型已移到 ../novel-generator。请在那里生成 BG 标记、choices 和美术设定，再回到 asset-generator 出图。")

def extract_image(resp):
    try: msg = resp["choices"][0]["message"]
    except Exception: msg = {}
    for im in (msg.get("images") or []):
        u = (im.get("image_url") or {}).get("url") or im.get("url") or ""
        if u.startswith("data:image"): return u
    c = msg.get("content")
    if isinstance(c, list):
        for part in c:
            u = (part.get("image_url") or {}).get("url", "") if isinstance(part, dict) else ""
            if u.startswith("data:image"): return u
    m = re.search(r"data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/=]+", json.dumps(resp))
    return m.group(0) if m else None

def save_data_uri(data_uri, key, assets, raw_manifest):
    mime = re.search(r"data:image/([a-zA-Z]+);base64,", data_uri)
    ext = "." + (mime.group(1).lower().replace("jpeg", "jpg") if mime else CFG.get("save_ext", "png"))
    b64 = data_uri.split("base64,", 1)[1]
    rel = assets.get(key, f"assets/{kind_of(key)}s/{key}.png")
    rel = re.sub(r"\.(webp|png|jpg|jpeg)$", "", rel, flags=re.I) + ext
    out = os.path.join(GAME, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(base64.b64decode(b64))
    tgt = raw_manifest.get("assets", raw_manifest); tgt[key] = rel
    save_json(os.path.join(GAME, "assets", "manifest.json"), raw_manifest)
    return rel

# ---------------- 提示词 ----------------
def subject_for(key, A, S):
    k = kind_of(key); chars = A.get("characters", {}); scenes = A.get("scenes", {})
    if k == "cover":
        lead = next((c for c in chars.values() if c.get("appearance")), None)
        who = ("，主角：" + lead["appearance"]) if lead else ""
        first = (S.get("intro", "").splitlines() or [""])[0]
        return f"小说《{S.get('name','')}》封面，含书名留白{who}。题材：{first}"
    if k in ("char", "avatar"):
        cid = key.split("_", 1)[1]; c = chars.get(cid, {})
        appr = c.get("appearance") or (c.get("name", "") + " 角色")
        role = "圆形头像特写" if k == "avatar" else char_prompt_rule(A)
        return f"{role}：{c.get('name','')}，{appr}"
    if k == "scene":
        sc = scenes.get(key, {})
        return f"场景背景（无人物）：{sc.get('name','')}，{sc.get('desc') or '按剧情氛围'}"
    return key

def build_prompt(key, A, S):
    st = A.get("style", {}); asp = A.get("aspect", {}).get(kind_of(key), "")
    parts = [st.get("global", ""), subject_for(key, A, S)]
    if asp: parts.append(f"构图：{asp}")
    if st.get("quality"): parts.append(st["quality"])
    p = "；".join([x for x in parts if x])
    if st.get("negative"): p += f"。避免：{st['negative']}"
    return p

def image_config_for(key):
    ratios = {
        "cover": "3:4",
        "char": "3:4",
        "avatar": "1:1",
        "scene": "16:9",
        "cg": "16:9",
    }
    ratio = ratios.get(kind_of(key))
    return {"aspect_ratio": ratio, "image_size": "1K"} if ratio else None

# ---------------- deprecated text side ----------------
def read_settings_text():
    txt = ""
    for name in ("核心设定.md", "关系.md"):
        p = os.path.join(PROJECT, "设定", name)
        if os.path.exists(p): txt += open(p, encoding="utf-8").read() + "\n\n"
    return txt[:6000]

def scene_context(key, S):
    n = key.replace("scene_ch", "")
    node = (S.get("nodes") or {}).get(f"ch{n}", {})
    return " ".join(c.get("text", "") for c in (node.get("chats") or [])[:6])[:400]

def load_json_str(s):
    try: return json.loads(s)
    except Exception: return {}

def cmd_draft_spec(args):
    sys.exit("❌ draft-spec 已停用：文本/小说生成模型不能和图片生成模型混用。请使用 ../novel-generator 生成/维护文本侧设定。")
    A = art(); S = story(); settings = read_settings_text(); changed = 0
    empties = [cid for cid, c in A.get("characters", {}).items()
               if not c.get("appearance") and (not args.only or args.only == f"char_{cid}")]
    if empties:
        names = {cid: A["characters"][cid]["name"] for cid in empties}
        prompt = ("根据以下小说设定，为每个角色写一句**外貌描述**(发型/脸/身形/典型服装/气质，30字内，"
                  "用于AI绘图保持一致)，只返回JSON：{\"角色id\":\"外貌\"}。\n"
                  f"角色: {json.dumps(names, ensure_ascii=False)}\n\n设定:\n{settings}")
        print(f"🧠 文本模型补 {len(empties)} 个角色外貌…")
        out = text_gen(prompt)
        m = re.search(r"\{.*\}", out, re.S)
        data = load_json_str(m.group(0)) if m else {}
        for cid in empties:
            v = (data or {}).get(cid) or (data or {}).get(names[cid])
            if v: A["characters"][cid]["appearance"] = v.strip(); changed += 1
    for key, sc in A.get("scenes", {}).items():
        if sc.get("desc") or (args.only and args.only != key): continue
        out = text_gen(f"用一句(25字内)描述这段剧情的**场景背景**(地点/时间/氛围/色调，无人物)，只回描述本身：\n{sc.get('name','')}\n{scene_context(key, S)}")
        sc["desc"] = out.strip().strip('"「」'); changed += 1
    save_json(ART_PATH, A)
    print(f"✅ 已写回 设定/美术设定.json（更新 {changed} 项）")

# ---------------- gen ----------------
def select_keys(args):
    miss = dict(missing_assets()); assets, _ = manifest()
    if args.only:
        return [args.only] if (args.force or args.only in miss) else []
    keys = list(assets.keys()) if args.force else list(miss.keys())
    if args.kind: keys = [k for k in keys if kind_of(k) == args.kind]
    return keys

def cmd_gen(args):
    A = art(); S = story(); assets, raw = manifest()
    keys = select_keys(args)
    skipped = [k for k in keys if is_excluded_char(k, A)]
    keys = [k for k in keys if not is_excluded_char(k, A)]
    if skipped:
        print(f"跳过 {len(skipped)} 个非人物 char 立绘：{', '.join(skipped)}")
    if not keys:
        print("✅ 没有需要生成的素材（都齐了，或用 --force 重生成）。"); return
    print(f"目标 {len(keys)} 个素材：{', '.join(keys)}\n")
    for key in keys:
        prompt = build_prompt(key, A, S)
        print(f"● {key} [{kind_of(key)}]\n  提示词: {prompt}")
        if args.dry_run: print("  (dry-run，跳过)\n"); continue
        uri = extract_image(call(CFG["image_model"], [{"role": "user", "content": prompt}], image=True, image_config=image_config_for(key)))
        if not uri:
            print(f"  ⚠️ 未解析到图片（模型可能不支持图像输出）。\n"); continue
        print(f"  ✅ 保存 -> {save_data_uri(uri, key, assets, raw)}\n")
    print("完成。刷新游戏即可看到新素材。")

def cmd_list(args):
    miss = missing_assets(); A = art(); S = story()
    skipped = [k for k, _ in miss if is_excluded_char(k, A)]
    miss = [(k, v) for k, v in miss if not is_excluded_char(k, A)]
    print(f"[{PROJECT}]\n缺失素材 {len(miss)} 个：")
    if skipped:
        print(f"  （已按 rules.char.excludeCharacterIds 跳过非人物立绘：{', '.join(skipped)}）")
    for k, v in miss:
        print(f"  - {k:20s} -> {v}\n      主体: {subject_for(k, A, S)[:60]}")

def main():
    global PROJECT, GAME, ART_PATH
    ap = argparse.ArgumentParser(description="素材生成器 (OpenRouter)")
    ap.add_argument("--project", help="小说项目根目录")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    g = sub.add_parser("gen")
    g.add_argument("--only"); g.add_argument("--kind", choices=["char","avatar","scene","cover","cg"])
    g.add_argument("--all", action="store_true"); g.add_argument("--force", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    PROJECT = resolve_project(args.project)
    GAME = os.path.join(PROJECT, "game")
    ART_PATH = os.path.join(PROJECT, "设定", "美术设定.json")
    {"list": cmd_list, "gen": cmd_gen}[args.cmd](args)

if __name__ == "__main__":
    main()
