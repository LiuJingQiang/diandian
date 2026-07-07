# novel-generator · 小说 → 互动读书游戏数据

独立小说生成器项目。负责把小说正文转换成互动读书游戏可消费的数据，并支持自动给正文插入背景转场标记。

它和 `asset-generator/` 的边界如下：

- `novel-generator/`：正文解析、自动 BG 打标、story JSON、choices 模板、manifest、美术设定脚手架。
- `asset-generator/`：根据 manifest / 美术设定调用图像模型出图、增强、抠图。

模型边界：`novel-generator/gen_config.json` 只配置 `text_model`；`asset-generator/gen_config.json` 只配置 `image_model`。两边可以共用 OpenRouter key/base URL，但不能共用同一个模型字段，也不要把小说生成和图片生成混在一个项目里。

## 项目输入

目标小说项目需要有：

```text
<project>/
├── 正文/第001章.md
├── 正文/第002章.md
├── 设定/核心设定.md
├── 设定/关系.md
└── book.config.json
```

## 产物

```text
<project>/game/story.<bookId>.json
<project>/game/books.json
<project>/game/assets/manifest.json
<project>/game/缺素材清单.md
<project>/设定/美术设定.json
<project>/choices.template.json
```

## 背景标记格式

正文中可写：

```md
<!-- BG scene_ch1_court | 鸣钟司大堂 | 烬岚城鸣钟司大堂，黑铜罪钟高悬，庄严压迫，无人物 -->

烬岚城是一栋老楼，屋脊像庙，墙里却埋着蒸汽管。
```

`convert.py` 会把这个标记附加到后面的第一条 chat：

```json
{
  "text": "烬岚城是一栋老楼，屋脊像庙，墙里却埋着蒸汽管。",
  "bgKey": "scene_ch1_court",
  "sceneName": "鸣钟司大堂"
}
```

同时会把 `scene_ch1_court` 写入 `manifest.json` 和 `设定/美术设定.json`，后续 `asset-generator/asset_gen.py` 可以直接生成这张背景。

## 命令

```bash
cd novel-generator

# 1. 预览自动 BG 打标（零成本启发式）
python3 bg_tag_gen.py --project ../罪钟代理人 --mode heuristic

# 2. 应用自动 BG 打标
python3 bg_tag_gen.py --project ../罪钟代理人 --mode heuristic --apply

# 3. 使用 LLM 做更细的场景导演打标（会调用 OpenRouter 文本模型）
python3 bg_tag_gen.py --project ../罪钟代理人 --mode llm --apply

# 4. 生成互动游戏数据
python3 convert.py --project ../罪钟代理人

# 4.1 审计 roster 缺失角色（生成 追踪/角色审计报告.md）
python3 character_audit.py --project ../罪钟代理人

# 5. 一键：打标 + 转换
python3 generate.py --project ../罪钟代理人 --tag --tag-mode heuristic
```

## 当前小说生成逻辑

1. 读取 `正文/第00X章.md`。
2. 识别 `# 第001章 标题` 作为章节名。
3. 识别 `<!-- BG key | name | desc -->` 为背景转场元信息，不进入正文显示。
4. 普通段落转成 `chats`：
   - `【角色】：台词` → 角色对话；
   - 段首引号 → 尝试按上下文识别说话人；
   - 其它 → 旁白。
5. **固定对话框容量约束**：每条 chat 默认不超过 46 个中文字符。超过时按句号/问号/感叹号/分号优先切分；单句过长再按逗号/顿号切分。切分后每次点击都显示完整一句或完整语义片段，不能让前端对话框被文字撑高。
6. 每 14 条 chat 切成一个节点：`ch1_s0`、`ch1_s1`。
7. 节点默认背景是 `scene_ch1`；如果 chat 上有 BG 标记，播放器播放到该 chat 时切换到对应背景。
8. 每个节点之间插入点点式平行选项；章末插入下一章解锁/广告选项。
9. 写出 story、manifest、缺素材清单和美术设定。

## 对话框文字规则

前端阅读框是固定高度，不允许因文本长短改变布局。因此生成器必须保证：

- 每条 `chat.text` 都能完整显示在固定对话框里，默认上限 46 个中文字符；
- 不把一整段长旁白塞进同一次点击；
- 切分优先保持完整句子；
- BG 转场和变量 `handlers` 只挂在切分后的第一条 chat 上，避免重复触发。
