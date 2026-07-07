# asset-generator · 图片素材生成器

独立图片素材生成器。它读取小说项目里已经生成好的 `game/assets/manifest.json` 与 `设定/美术设定.json`，调用图片模型出图并回写 manifest。
小说解析、自动 BG 打标、choices、story JSON 生成已经独立到同级项目 `../novel-generator/`。

```
asset-generator/            ← 图片素材生成工具
├── 需求分析.md              需求分析
├── README.md               本文件
├── asset_gen.py            OpenRouter 出图 -> 直接落盘进游戏
└── gen_config.json         base/image_model/default_project

<小说项目>/                  ← 数据(工具操作对象)
├── 设定/美术设定.json        novel-generator 生成/维护的美术输入
└── game/assets/manifest.json novel-generator 生成的素材槽位
```

## 快速开始

```bash
cd asset-generator
# 配 OpenRouter key（三选一，见下方「Key 配置」）
export OPENROUTER_API_KEY=sk-or-...

# 先在 ../novel-generator 里运行 convert.py / generate.py
python3 asset_gen.py list                     # 看缺哪些素材
python3 asset_gen.py gen --only cover_book    # 先出单张验证
python3 asset_gen.py gen --all                # 批量出图(直接进 game/assets/)
```

对别的小说：先用 `../novel-generator/convert.py --project /path/to/另一本书` 生成 manifest，再用本工具 `asset_gen.py --project /path/to/另一本书 gen --all` 出图。

## Key 配置（三选一，优先级从高到低）

| 方式 | 怎么配 | 说明 |
|---|---|---|
| ① 环境变量 | `export OPENROUTER_API_KEY=sk-or-...` | 最安全，CI/临时用 |
| ② 本地私密文件(推荐) | 复制 `gen_config.local.json.example` → `gen_config.local.json`，填 `api_key` | 已被 `.gitignore` 忽略，不会提交 |
| ③ 主配置字段 | 直接改 `gen_config.json` 的 `"api_key"` | 最方便，**但注意别泄露/别提交** |

环境变量存在则优先用它，否则读文件里的 `api_key`。变量名可在 `gen_config.json` 的 `api_key_env` 改。

## 其它配置

- **`gen_config.json`**：`default_project`(相对本目录) · `base_url` · `image_model`(须支持图像输出) · `save_ext`。
- 小说/文本生成模型只配置在 `../novel-generator/gen_config.json` 的 `text_model`，不要和图片模型共用一个字段或项目配置。
- **`<小说项目>/book.config.json`**：换书只改这里——`bookId/name/roster/variables/firstChapterChoice/chapterUnlockCost`。
- **`<小说项目>/设定/美术设定.json`**（convert 生成脚手架）：`style.global` 全局画风 + 每角色 `appearance` 最关键；`seed/refImage` 保一致。

## 命令速查

```bash
python3 asset_gen.py [--project P] list
python3 asset_gen.py [--project P] gen --only KEY | --kind char|scene|avatar|cover|cg | --all [--dry-run] [--force]
./.venv/bin/python matte.py [--project P] --kind char      # 立绘抠成透明 PNG
./.venv/bin/python center_char.py [--project P] --all     # 透明立绘居中，默认跳过已确认合格样张
```

## 立绘硬规则

`char_*` 只允许作为人物立绘使用，规则同时写在小说项目的 `设定/美术设定.json -> rules.char`，生成器会读取其中的 `prompt` 和 `excludeCharacterIds`：

- 只能生成单个人类人物，必须清楚看到头部、脸、身体和服装。
- 必须是 PNG 透明背景，保留 alpha 通道；生成后运行 `matte.py --kind char` 抠图。
- 人物必须居中，左右留白均衡，主体建议占画面高度约 85%；生成/抠图后运行 `center_char.py --all` 居中。
- 禁止非人物主体、物品单独成图、钟/契约/文书/印章/牌位/剪影作为主体。
- 禁止纯色/渐变/场景背景，禁止街景、建筑、墙面、地面、烟雾、光效背景或装饰性背景元素。
- `rules.char.excludeCharacterIds` 中的角色不会作为 `char_*` 生成；例如机械雀、审判钟这类非人物只能作为其它类型素材。
- `rules.char.approvedSamples` 是人工确认合格样张，后处理默认跳过，避免误覆盖。

## 工作原理 / 故障排查

- 出图：`POST {base}/chat/completions` 带 `modalities:["image","text"]`，回包按 `message.images → content[] → 正则` 解析 data URI → 落盘 → 回写 manifest。
- 引擎按 manifest 的 key 加载素材，缺失自动占位；把同名图丢进 `game/assets/对应目录` 也能直接生效。

| 现象 | 处理 |
|---|---|
| 未找到 API key | `export OPENROUTER_API_KEY=...` |
| HTTP 401/404 | key 无效 / 模型名错，检查 gen_config.json |
| 未解析到图片 | 选的模型不支持图像输出，换 image_model |
| 多图不一致 | 填 美术设定.json 的 appearance/seed |
| 省钱预览 | `gen --dry-run` |

> 换书就是新建一本书的 `正文/ 设定/ book.config.json`，然后先跑 `../novel-generator/convert.py --project 新书`，再跑 `asset_gen.py --project 新书 gen --all`。
> 对齐点点的进阶方向（段级图/衣橱闭环/平行付费选项）见 `../命运币的代价/game/研究资料/点点游戏架构规范.md` 第七节。
