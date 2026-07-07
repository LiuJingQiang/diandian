# game-frontend · 通用 React/Vite 互动读书前端

这一层只放**前端代码**，不绑定任何单本小说。多本小说都通过资源导入进入 `public/games/<gameId>/`，启动时用 `?game=<gameId>` 选择要播放的小说。

## 目录边界

```text
game-frontend/                 # 唯一前端代码项目
├── src/                        # React 播放器与状态机
├── scripts/import-game.mjs      # 从小说项目导入 game 资源
└── public/games/                # 可替换小说资源，不手写

罪钟代理人/game/                 # 小说内容包
├── books.json
├── story.jinlanchengzui.json
└── assets/manifest.json + 图片
```

## 导入小说资源

```bash
cd game-frontend
npm install
npm run import:game -- --project ../罪钟代理人
npm run import:game -- --project ../命运币的代价
```

导入后会生成：

```text
public/games/index.json
public/games/jinlanchengzui/books.json
public/games/jinlanchengzui/story.jinlanchengzui.json
public/games/jinlanchengzui/assets/manifest.json
```

## 运行

```bash
npm run dev
```

打开：

```text
http://127.0.0.1:8788/?game=jinlanchengzui
```

不带 `game` 参数时，默认使用 `public/games/index.json` 里的第一本。

## 架构原则

- 前端代码只有一套。
- 小说项目只产出 `game/books.json`、`story.*.json`、`assets/manifest.json` 和图片。
- 同一本小说可以替换素材，只要重新导入或替换对应 `public/games/<id>/assets/`。
- UI 风格默认按《罪钟代理人》的东方蒸汽 / 黑铜罪钟 / 案卷纸质感设计，后续可以从 story categories 或 manifest 增加主题变量。
