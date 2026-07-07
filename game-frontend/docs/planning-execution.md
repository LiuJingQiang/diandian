# 点点式互动读书 · 策划 / 经济 / UI 执行文档

> 目的：把 `game-frontend` 从“线性文本 + 选项扣点”的原型，升级为点点式“剧情分叉 + 经济卡点 + 固定移动端 UI”的可执行前端规范。

## 0. 资料来源与访问说明

用户指定的线上页面：

```text
https://fa-html-viewer-660547.stg.g123.jp/research/hbjmtlhbddrz-flow.html
```

当前环境访问会跳转 Auth0 登录，因此执行时使用仓库根目录已归档的同源资料。**根目录 `研究资料/` 是主来源**：

```text
研究资料/README.md
研究资料/点点游戏架构规范.md
研究资料/全站存档/hbjmtlhbddrz-flow.md
研究资料/hbjmtlhbddrz_flow_data.json
研究资料/apk解析/raw_unzip/assets/flutter_assets/assets/images/
```

旧路径 `命运币的代价/game/研究资料/` 里也有副本，但后续以前者为准。

关键统计：

| 指标 | 数值 |
|---|---:|
| 章节 | 49 |
| paragraph | 897 |
| 选项 | 557 |
| 付费选项面 | 555 |
| 衣橱锁 | 11 |
| 章节锁信号 | 27 |
| 全局选项成本 | 12 能量 |
| 视觉章节解锁 | 17 能量 |
| 潜在选项成本 | 6660 能量 / ¥66.6 |
| 精简展示图 | 39 节点 / 23 边 |
| 被裁剪伪分支 | 268 组 / 536 边 |

结论：真实点点书不是简单线性选择，而是“多 paragraph 图 + 大量付费选项面 + 少量有意义结构分支 + 伪分支裁剪 + 章节/衣橱/属性锁”。

## 1. 当前前端缺口

当前 `src/App.jsx` 已支持：

- 加载多小说资源；
- 顺序播放 chats；
- 显示背景和立绘；
- 选项扣 energy；
- handlers / conditions；
- 简单 next/divert。

但缺少：

1. **有意义分叉模型**：没有 branch history / convergence / route flags / endings。
2. **卡点层级**：没有 chapter unlock、visual unlock、free-card gate、wardrobe lock、attribute lock、VIP lock。
3. **经济层**：只有 energy；没有 stardust / wishing star / love / VIP / items 的钱包和 sink/faucet。
4. **固定移动端 UI**：原型曾让文本长短影响面板高度；已修为固定框，但仍需 APK 资源化。
5. **固定图标布局**：缺 back / auto / shop / wardrobe / menu / reward timer 的真实动作栏。
6. **主题系统**：CSS 仍偏《罪钟代理人》；需要按小说分类切换 userall / xiuxian / ai_chat / horror / eastern-steam。
7. **埋点**：缺 node enter / option show / select_option / energy insufficient / ad play / paywall show。

## 2. 分支策划模型

### 2.1 节点类型

```ts
type NodeKind =
  | 'story'          // 普通剧情
  | 'choice'         // 决策点
  | 'paywall'        // 付费/广告/限免卡卡点
  | 'wardrobe_lock'  // 衣橱/立绘锁
  | 'attribute_lock' // 属性门槛
  | 'chapter_gate'   // 章节/视觉章节解锁
  | 'ending';
```

### 2.2 边类型

```ts
type EdgeKind =
  | 'auto'
  | 'free_option'
  | 'energy_paid'
  | 'ad_option'
  | 'free_card'
  | 'wardrobe_lock'
  | 'attribute_lock'
  | 'vip_lock';
```

### 2.3 选择必须产生至少一种后果

每个正式选项必须满足至少一项：

- `next` 指向不同后续节点；
- 修改变量，未来有条件引用；
- 增加/消耗道具；
- 改变 branch flag；
- 解锁 CG/立绘/章节/结局；
- 进入付费/广告/衣橱/属性门槛。

如果两个选项只改一个无后续使用的装饰变量，应归为伪分支并裁剪或合并。

## 3. 经济模型

### 3.1 平台层货币

| 货币 | 作用 | 来源 | 消耗 |
|---|---|---|---|
| energy 能量 | 阅读/选项硬闸 | 签到、广告、充值、VIP、星尘兑换 | 章节/选项/视觉解锁 |
| stardust 星尘 | 软产出 | 任务、签到、活动、广告 | 兑能量、混池祈愿 |
| wishingStar 祈愿星 | 抽卡 | 充值、活动、返还 | 单抽/十连/立绘卡 |
| love 爱心 | 社交/角色榜 | 互动、活动 | 送心/排行 |
| virtualCoin 虚拟币 | 商城硬币 | RMB 充值 | 礼包/VIP积分 |

### 3.2 书内层变量

按小说配置，至少支持：

- 好感/信任；
- 黑化/圣母/道德轴；
- 战斗/境界四维；
- 剧情道具；
- branch flags；
- replay round / ending flags。

### 3.3 卡点默认数值

来源：`hbjmtlhbddrz_flow_data.json` 与本地经济分析。

| 卡点 | 默认 |
|---|---:|
| 普通付费选项 | 12 energy |
| 普通章节解锁 | 12 energy |
| 视觉章节解锁 | 17 energy |
| 广告奖励 | 15 energy 起步，可配置 |
| RMB 估值 | ¥1 ≈ 100 energy |

## 4. UI 执行规范

### 4.1 固定阅读区

- 底部对话框固定高度。
- 文本区域固定高度。
- 长文本内部滚动或分页，不改变布局。
- 内容生成层必须优先避免超长文本：`novel-generator` 默认把每条 `chat.text` 控制在 46 字以内，按完整句/语义片段切分。
- 选项区域固定高度，超过时内部滚动。

当前已落地：

- `.dialog-card { height: 292px; }`
- `.dialog-scroll { height: 118px; overflow-y: auto; }`
- `.options-block { max-height: 204px; overflow-y: auto; }`

### 4.1.1 选项与人物互斥

当进入选项分叉状态时：

- 必须隐藏人物立绘；
- 必须隐藏左下角头像/好感卡；
- 选项浮层放在对话框上方，并留出足够 margin；
- 对话框保持固定位置，只显示“请选择你的回应”等轻提示；
- 不允许“选项 + 人物 + 头像卡”三者同时挤在下半屏。

原因：真实 Android 点点阅读器在选项状态会突出选择面，角色立绘若继续压在同一区域，会造成视觉噪声和误触风险。

### 4.2 说话人样式

必须按角色类型改变 UI：

| role | UI |
|---|---|
| narration | 旁白标签，纸质正文框 |
| lead | 主角名牌，偏深色 / 金色强调 |
| secondary | 配角名牌，红铜/次级强调 |
| system | 深色/冷色系统框 |

当前已落地 class：

```text
speaker-narration
speaker-lead
speaker-secondary
speaker-system
```

### 4.3 固定 icon 布局

必须补齐：

- 左上/左侧：back；
- 底部或右侧动作栏：auto、shop、wardrobe、menu；
- 顶部钱包：energy、stardust、wishing star、love；
- 右侧/中上：阅读时长奖励或广告补能量入口；
- 弹窗右上：close。

资源优先级：

1. `diandian_apk_art_resources` 或已导入 `assets/ui/` 切图；
2. 项目主题自绘 SVG；
3. 临时 emoji 只允许用于开发占位。

## 5. React/Vite 实施路线

### Phase 1：UI 基线修复

- 固定对话框高度。✅
- 角色/旁白/系统样式分流。✅
- 补真实 icon action bar。
- ChoiceButton 增加 free/paid/ad/locked 状态。

### Phase 2：Runtime 抽象

新增模块：

```text
src/branchRuntime.js
src/economyRuntime.js
src/unlockRuntime.js
src/eventBus.js
src/telemetry.js
src/themeRuntime.js
```

### Phase 3：Schema 扩展

story 节点增加：

```json
{
  "kind": "choice",
  "gates": [{ "type": "energy", "cost": 12 }],
  "branchTags": ["protect_bailing"],
  "events": [{ "type": "changeBackground", "bgKey": "scene_ch1_court" }]
}
```

option 增加：

```json
{
  "text": "替白铃承罪",
  "kind": "energy_paid",
  "cost": { "energy": 12 },
  "next": "ch1_branch_bailing",
  "branchSet": ["protect_bailing"],
  "handlers": []
}
```

### Phase 4：生成器联动

`novel-generator` 不应只生成平行付费选项。它需要生成：

- 真实 branch outline；
- convergence node；
- ending flags；
- gates；
- economy config；
- UI theme hint。

## 6. Android 模拟器 10 本书采样计划

当前已有逆向文档，但用户要求“手机模拟器找 10 款不同小说”。执行时按以下采集模板：

### 每本书必须截图/记录

1. 书籍详情页。
2. 阅读器首屏。
3. 旁白样式。
4. 主角说话样式。
5. 配角说话样式。
6. 选项弹出样式。
7. 付费选项 / 广告选项 / 限免卡卡点。
8. 能量不足弹窗。
9. 菜单弹窗。
10. 衣橱/换装入口。
11. 福利/广告补能入口。
12. 若有特殊题材 UI：聊天本、修仙本、恐怖本、AI 对话本。

### 输出文档

```text
game-frontend/docs/android-ui-sampling/<bookId>.md
game-frontend/docs/android-ui-sampling/summary.md
```

### 10 本书总结字段

- `bookId / title / category / visual_type`
- 固定 icon 位置
- 对话框尺寸和位置
- 姓名牌样式
- 选项按钮状态
- 钱包栏货币种类
- 卡点弹窗类型
- 主题资源路径
- 与当前 React UI 差距
