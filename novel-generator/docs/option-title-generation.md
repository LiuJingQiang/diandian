# optionTitle 生成逻辑规范

> 本文只定义 `optionTitle` 的生成位置、优先级和数据流。本次不执行生成命令。

## 1. 基本原则

`optionTitle` 属于**小说内容生成层**，不属于前端 UI 层。

前端只能读取并显示：

```jsx
node.optionTitle
```

前端不得硬编码：

```text
这一步，你怎么应对？
```

也不应该在运行时根据文本临时编一个问题。运行时只能做最低限度兜底，例如：

```text
请选择
```

真正的剧情化问题必须在 `novel-generator/` 阶段生成并写入 story JSON。

---

## 2. 正确生成阶段

`optionTitle` 的长期正确来源是：

```text
<project>/choices.json
```

推荐流程：

```text
正文/第00X章.md
    ↓
convert.py 第一次运行
    ↓
choices.template.json
    ↓
choice_gen.py 或未来 branch_gen.py
    ↓
choices.json
    ↓
convert.py 第二次运行
    ↓
game/story.<bookId>.json
    ↓
game-frontend 显示 node.optionTitle
```

---

## 3. 当前代码位置

当前 `optionTitle` 写入位置在：

```text
novel-generator/convert.py
```

函数：

```python
build_story()
  └─ make_choice()
```

当前逻辑应保持以下优先级：

```python
spec = choices.get(cp_id) or fallback_choice(attrs, ci)
title = spec.get("title") or contextual_option_title(seg_chats)
node["optionTitle"] = title
```

解释：

1. 如果 `choices.json` 中有 `title`，必须优先使用。
2. 如果没有 `title`，才使用 `contextual_option_title(seg_chats)` 作为临时兜底。
3. 不允许再返回固定文案 `这一步，你怎么应对？`。

---

## 4. choices.template.json 的职责

`convert.py` 第一次运行时会生成：

```text
<project>/choices.template.json
```

模板中每个选择点至少要包含：

```json
{
  "id": "ch1_s3",
  "context": "韩照抬眼。季代书，记录。罪钟将落印。",
  "attributes": ["隐忍", "锋芒", "城府", "赤诚"],
  "characters": ["白铃", "韩照", "陆青萝"]
}
```

这个文件只提供上下文，不直接进入前端。

---

## 5. choices.json 的目标结构

`choice_gen.py` 或未来 `branch_gen.py` 应生成：

```json
{
  "ch1_s3": {
    "title": "韩照催你记录罪名，你要不要继续沉默？",
    "options": [
      {
        "text": "按规矩写下罪名",
        "effects": { "鸣钟司警觉": -1 }
      },
      {
        "text": "把代理认罪状压上案桌",
        "effects": {
          "承罪层数": 1,
          "白铃信任": 1
        }
      }
    ]
  }
}
```

要求：

- `title` 必须贴合当前剧情。
- `title` 不能是泛用问题。
- `title` 必须让玩家知道当前矛盾是什么。
- `options` 必须带来变量、分支、卡点或剧情后果。

---

## 5.1 输出结构总览

`optionTitle` 相关生成链路需要产出三层结构。

### A. choices.template.json：选择点上下文模板

由 `convert.py` 初次扫描正文生成。用于给 `choice_gen.py / branch_gen.py` 提供上下文，不直接进入前端。

```json
{
  "_note": "convert 产出的选择点上下文；choice_gen.py 据此生成 choices.json。",
  "points": [
    {
      "id": "ch1_s3",
      "context": "韩照抬眼。季代书，记录。罪钟将落印。",
      "attributes": ["隐忍", "锋芒", "城府", "赤诚"],
      "characters": ["白铃", "韩照", "陆青萝"],
      "sceneName": "鸣钟司大堂",
      "bgKey": "scene_ch1_court"
    }
  ]
}
```

字段说明：

| 字段 | 含义 |
|---|---|
| `id` | 选择点节点 id，对应未来 story node id |
| `context` | 当前选择点前 3–6 条剧情文本 |
| `attributes` | 可用属性池 |
| `characters` | 当前书中关键角色 |
| `sceneName` | 当前场景名，辅助生成具体问题 |
| `bgKey` | 当前背景 key，辅助识别场景 |

### B. choices.json：可编译选择点

由 `choice_gen.py` 或未来 `branch_gen.py` 生成。`convert.py` 第二次运行时读取它并写入 story。

```json
{
  "ch1_s3": {
    "title": "韩照催你记录罪名，你要不要继续沉默？",
    "kind": "branch_minor",
    "options": [
      {
        "text": "按规矩写下罪名",
        "cost": 0,
        "effects": { "鸣钟司警觉": -1 },
        "next": "ch1_s4"
      },
      {
        "text": "把代理认罪状压上案桌",
        "cost": 8,
        "effects": {
          "承罪层数": 1,
          "白铃信任": 1,
          "回钟权柄": 1
        },
        "branchSet": ["protect_bailing"],
        "next": "ch1_proxy_confession"
      }
    ]
  }
}
```

字段说明：

| 字段 | 必填 | 含义 |
|---|---|---|
| `title` | 是 | 剧情化选择问题，即最终 `node.optionTitle` |
| `kind` | 建议 | `branch_major / branch_minor / gate_energy / gate_ad / ending` |
| `options[].text` | 是 | 玩家可见选项文案 |
| `options[].cost` | 可选 | 能量消耗；可为数字或 `{ energy: 12 }` |
| `options[].effects` | 可选 | 变量变化，转换为 handlers |
| `options[].next` | 可选 | 真分支目标节点；无则默认汇回下一段 |
| `options[].branchSet` | 可选 | 设置路线 flag |
| `options[].conditions` | 可选 | 出现条件 |

### C. story.<bookId>.json：前端运行结构

由 `convert.py` 编译生成，前端只读这个结构。

```json
{
  "nodes": {
    "ch1_s3": {
      "id": "ch1_s3",
      "name": "第001章 代理认罪状",
      "bgKey": "scene_ch1_court",
      "sceneName": "鸣钟司大堂",
      "chats": [],
      "optionTitle": "韩照催你记录罪名，你要不要继续沉默？",
      "options": [
        {
          "text": "按规矩写下罪名",
          "cost": { "energy": 0 },
          "isAd": false,
          "handlers": [
            {
              "var": "鸣钟司警觉",
              "method": 5,
              "ops": ["+"],
              "list": [
                { "name": "鸣钟司警觉", "num": 0, "str": "", "vType": 1 },
                { "name": "const", "num": -1, "str": "", "vType": 1 }
              ]
            }
          ],
          "conditions": [],
          "next": "ch1_s4"
        }
      ],
      "diverts": []
    }
  }
}
```

前端只允许显示：

```jsx
node.optionTitle
```

不得再自行生成标题。

---

## 5.2 未来 branch_plan.json 结构

当进入真正多分支/多结局生成时，新增：

```text
<project>/branch_plan.json
```

推荐结构：

```json
{
  "bookId": "jinlanchengzui",
  "routes": [
    {
      "id": "protect_bailing",
      "name": "护白铃线",
      "entry": "ch1_proxy_confession",
      "merge": "ch2_s0",
      "endingFlags": ["bailing_trust_path"]
    }
  ],
  "endings": [
    {
      "id": "be_alley_burned",
      "name": "BE · 檐灯成灰",
      "conditions": [
        { "var": "檐灯巷存亡", "op": 4, "target": 1 }
      ]
    },
    {
      "id": "te_bell_agent",
      "name": "TE · 夺钟代理人",
      "conditions": [
        { "var": "回钟权柄", "op": 3, "target": 5 },
        { "var": "白铃信任", "op": 3, "target": 3 }
      ]
    }
  ],
  "choiceOverrides": {
    "ch1_s3": {
      "title": "罪钟将落，你要不要替白铃承罪？",
      "options": []
    }
  }
}
```

职责划分：

- `choices.json`：局部选择点。
- `branch_plan.json`：全局路线、汇流、结局和关键节点覆盖。
- `story.<bookId>.json`：前端最终运行数据。

---

## 6. optionTitle 文案标准

### 好的 optionTitle

```text
韩照催你记录罪名，你要不要继续沉默？
罪钟将落，你要不要替白铃承罪？
檐灯巷被逼交人，你先护谁？
旧契写着你的名字，你要追问韩照吗？
陆青萝开出活价，你要拿什么抵押？
```

### 不合格 optionTitle

```text
这一步，你怎么应对？
请选择
你要怎么办？
做出选择
继续吗？
```

这些文案太泛，不包含剧情冲突，不能作为生成结果进入 `choices.json`。

---

## 7. contextual_option_title 的定位

`contextual_option_title(seg_chats)` 只是**临时兜底**。

它可以根据关键词生成较具体的问题，例如：

```python
if "韩照" in text or "钟卫" in text:
    return "韩照逼近，你要如何破局？"
```

但它不是最终策划方案。

正式项目中，关键选择点必须由 `choices.json` 或未来 `branch_plan.json` 提供明确标题。

---

## 8. 后续重构方向

后续应新增：

```text
branch_gen.py
```

职责：

1. 读取 `choices.template.json`。
2. 识别关键矛盾和当前场景。
3. 生成剧情化 `optionTitle`。
4. 生成真正分支：`next`、`branchSet`、`endingFlag`、`gate`。
5. 写入 `choices.json` 或 `branch_plan.json`。

最终 `convert.py` 只负责把这些结构编译进 story JSON。
