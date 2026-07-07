# novel-generator 重构执行规范

目标：把 `novel-generator` 从“散文切 chats 的转换器”升级为“互动读书游戏内容生成器”。它必须在生成前理解人物、场景、分支、经济卡点和 UI 约束。

## 1. 当前问题

### 1.1 人物表是手写的

`book.config.json > roster` 是唯一人物来源。正文里出现但没写入 roster 的角色不会被识别：

- 季母 / 主角母亲；
- 季灯 / 妹妹；
- 茶铺老板娘；
- 粥铺阿婆；
- 钟卫；
- 云阶区官员；
- 其它街坊角色。

后果：

- `chat.char` 缺失；
- `focusChar` 缺失；
- 前端无法自动切换立绘；
- 美术设定不会生成对应角色槽位。

### 1.2 选择点仍偏“平行扣点”

当前 `fallback_choice()` 只是给出两个选项并修改变量，很多选项不会改变后续剧情结构。

真实点点式结构要求：

- 选择必须能改变量、改分支、进卡点、解锁剧情或导向结局；
- 不同场景的抉择必须有不同后果；
- 伪分支必须裁剪或折叠；
- 要支持多结局和分支汇流。

### 1.3 UI 约束必须前置到内容生成

前端是固定蓝色对话框，内容生成必须保证：

- `chat.text <= 46` 中文字符；
- 选项出现时隐藏人物立绘和头像卡；
- 旁白无 `focusChar` 时不显示人物；
- `focusChar` 用于视觉焦点，不等于说话人；
- `zuizhong` 为 art-only，不生成头像卡表现。

## 2. 新生成流水线

```text
正文/设定/大纲
  ↓
character_audit.py              # 审计 roster 缺失角色
  ↓
book.config.json roster 修正      # 人物/别名/是否需要立绘
  ↓
bg_tag_gen.py                    # 场景 BG 转场标记
  ↓
branch_plan.json / choices.json  # 多分支 / 多结局 / 卡点配置
  ↓
convert.py                       # 生成 story / manifest / 美术设定
  ↓
asset-generator                  # 生成立绘/背景/头像/封面
```

## 3. 人物审计规则

### 3.1 必须识别的类型

| 类型 | 是否进 roster | 是否需要立绘 |
|---|---|---|
| 主角 / 女主 / 反派 / 关键 NPC | 是 | 是 |
| 家庭成员（母亲、妹妹） | 是 | 是 |
| 关键街坊 / 帮助者 | 是 | 视出场频率 |
| 群体敌人（钟卫） | 是，可 generic | 可选 |
| 纯背景群众 | 否 | 否 |

### 3.2 输出格式

`character_audit.py` 输出 Markdown 报告：

```text
<project>/追踪/角色审计报告.md
```

并建议配置项：

```json
{ "id": "jimu", "name": "季母", "lead": false, "aliases": ["季母", "母亲", "娘", "他母亲"] }
```

## 4. 多分支生成规则

### 4.1 choice 必须剧情化

选项标题不能使用硬编码：

```text
这一步，你怎么应对？
```

必须来自当下剧情。例如：

```text
罪钟即将落印，你要如何落笔？
韩照堵住巷口，你要先护谁？
旧契写着你的名字，你要追问谁？
```

详细生成规则见：

```text
docs/option-title-generation.md
```

其中必须维护以下输出结构：

```text
choices.template.json  # 选择点上下文模板
choices.json           # 可编译选择点，含 title/options/effects/next
branch_plan.json       # 未来多分支/多结局路线图
story.<bookId>.json    # 前端最终运行结构，含 node.optionTitle
```

### 4.2 choice 必须有结构后果

每个选项至少满足一项：

- 跳到不同 `next`；
- 设置 branch flag；
- 改变未来条件；
- 进入不同结局线；
- 触发卡点：energy/ad/free_card/wardrobe/attribute；
- 解锁 CG/立绘/隐藏剧情。

### 4.3 分支类型

| 类型 | 说明 |
|---|---|
| `branch_major` | 改变后续节点或结局 |
| `branch_minor` | 改变量并在未来门槛使用 |
| `gate_energy` | 12/17 能量卡点 |
| `gate_ad` | 看广告替代付费 |
| `gate_attribute` | 属性/好感门槛 |
| `gate_wardrobe` | 衣橱/符册系统门槛 |
| `ending` | BE/NE/TE/隐藏结局 |

## 5. 《罪钟代理人》初步结局规划

| 结局 | 条件方向 | 说明 |
|---|---|---|
| BE · 檐灯成灰 | 檐灯巷存亡过低 / 黑雾侵蚀过高 | 救灾失败 |
| NE · 承罪小吏 | 只救白铃或只翻案局部 | 活下但制度未改 |
| HE · 代理复核 | 回钟权柄 + 白铃信任 + 陆青萝线达标 | 翻案成功 |
| TE · 夺钟代理人 | 承罪层数 / 罪钟真相 / 街坊支持达标 | 改写罪钟规则 |

## 6. 前端联动约束

- 角色站位规则不写进正文，统一由 `game-frontend/src/stageConfig.js` 控制。
- 但 `convert.py` 必须输出 `char` / `focusChar`，否则前端无法切换。
- 选项显示时人物隐藏，这是前端规范，生成器只负责给出正确 `options`。
