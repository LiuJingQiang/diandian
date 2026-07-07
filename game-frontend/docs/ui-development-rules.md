# game-frontend UI 开发规范（本 session 固化版）

> 目标：`game-frontend` 必须还原 Android 模拟器中点点原游戏阅读器的 UI 结构，不允许回退为普通 Web 阅读器或自定义风格稿。

## 1. 证据源优先级

UI 设计优先级：

1. Android 模拟器真实截图；
2. 根目录 `研究资料/apk解析/美术资源/flutter_images/` 中的 APK 原始 UI 切图；
3. `diandian_apk_art_resources/UI_STYLE_GUIDE.md`；
4. 当前 CSS fallback。

当前已采集真实截图：

```text
game-frontend/docs/android-ui-sampling/real-app-current.png
```

## 2. 竖屏手机画布

- 前端只做手机竖屏阅读器布局。
- 桌面浏览器中游戏画布居中，近似手机比例。
- 移动端占满 `100svh`。
- 不做横屏，不做桌面宽屏重排。

实现位置：

```text
src/styles.css -> .game-shell
```

## 3. 对话框规则

- 对话框固定高度，不能被文字撑开。
- 小说生成器必须保证 `chat.text <= 46` 中文字符。
- 对话文字不能被鼠标/长按选中。
- 对话框里不显示章节名。
- 纯旁白不默认显示主角。
- 旁白只有存在 `focusChar` 时才显示对应视觉焦点。

实现位置：

```text
src/styles.css -> .dialog-card / .dialog-scroll / .dialog-text
src/App.jsx    -> visualCharacter = character || focusCharacter || null
novel-generator/convert.py -> MAX_CHAT_CHARS = 46
```

## 4. 选项显示规则

- 选项不能写死为“这一步，你怎么应对？”；必须来自 story/node 的剧情化 `optionTitle`。若生成器兜底，也必须基于上下文生成具体问题。
- 选项浮层显示在对话框上方，并保留明显间距。
- 进入选项状态时，必须隐藏人物立绘。
- 进入选项状态时，必须隐藏左下角头像/好感卡。
- 选项、人物、头像卡不能同时挤在下半屏。

实现位置：

```text
src/App.jsx -> options-float / run.mode === 'options'
src/styles.css -> .options-float
```

## 5. 固定 UI 控件

阅读器固定控件必须接近 Android 原游戏：

- 左上返回按钮：必须使用原图 `back.webp`，不能用 CSS 画圆或文字箭头替代。
- 右侧悬浮奖励：`+50 / 立即领取`，位置在屏幕右侧偏上，不得压住对话框。
- 右下评论气泡：保留评论入口视觉。
- 底部操作栏：只显示 icon，不显示额外文字。
- 操作栏 icon：自动 / 商城 / 衣橱 / 菜单。

实现位置：

```text
src/App.jsx -> reader-back / reward-float / action-bar
src/styles.css -> .reader-back / .reward-float / .action-bar
```

## 6. 控件点击逻辑

- 返回：有弹窗时先关闭弹窗，否则浏览器后退；无历史时 toast。
- 自动：开启/关闭自动阅读。
- 自动倍速：支持 1–10 倍速。
- 商城：点击弹出“内容待续”弹框。
- 衣橱：点击弹出“内容待续”弹框。
- 菜单：打开功能按钮面板（目录/存档/设置/回看），具体逻辑待续。

实现位置：

```text
src/App.jsx -> handleBack / handleAction / GameModal / speed-panel
```

## 7. 自动阅读倍速

- 支持 1–10 倍速。
- 自动阅读只推进 chat，不自动跳过选项。
- 到达选项时暂停等待玩家选择。
- `speed-panel` 只在自动阅读开启时显示。
- Review 阶段可开启无限命运币，避免路线审查被付费点打断。

当前节奏：

```js
delay = Math.max(140, Math.round(1800 / autoSpeed))
```

## 8. 角色立绘与站位

- 角色不应永远出现在同一个位置。
- 两个不同角色连续出场时，不能使用同一侧。
- 同一个角色连续出现可以保持原位置。
- `zuizhong` 固定中位，只作为大立绘，不显示头像卡。
- 角色站位配置只放在：

```text
src/stageConfig.js
```

当前核心配置：

```js
stagingRules.alternateDifferentConsecutiveCharacters = true
zuizhong = { position: 'center', artOnly: true }
```

## 9. 素材引用规则

- 前端不直接写死小说资源路径。
- 通过 `public/games/<gameId>/assets/manifest.json` 解析素材。
- 小说资源通过导入脚本进入前端：

```bash
npm run import:game -- --project ../罪钟代理人
```

## 10. 验收清单

每次 UI 修改后必须检查：

1. `npm run build` 通过；
2. `lsp_diagnostics src` 0 errors；
3. 浏览器 console 0 errors；
4. 对话文字不能选中；
5. 对话框不因文字长短改变高度；
6. 选项出现时人物和头像卡隐藏；
7. 返回按钮使用原始 back icon；
8. 底部 icon 无文字；
9. 不同角色连续出场左右交替；
10. `zuizhong` 不显示头像卡。
