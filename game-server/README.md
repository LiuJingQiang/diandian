# game-server · 通用互动读书 Express 服务

父级可复用服务器，抽取自：

- `reversed/mock-server/server.js` 的账号、货币、GM、素材替换 API 思路；
- `命运币的代价/game/server.js` 的 story session / advance / choose 状态机。

它不绑定某一本小说。启动时通过 `GAME_PACKAGES` 指定一个或多个小说 `game/` 目录。

## 运行

```bash
cd game-server
npm install
GAME_PACKAGES="../罪钟代理人/game,../命运币的代价/game" npm run dev
```

默认端口：

```text
http://127.0.0.1:666
```

## 内容包契约

每个小说 game 包需要包含：

```text
<novel>/game/
├── books.json
├── story.<bookId>.json
└── assets/manifest.json
```

## 主要 API

兼容两类调用风格：

### 点点式 mock / GM

```text
POST /api/login_guest
GET  /api/user/currency?uid=guest
POST /api/gm/grant
GET  /api/gm/state
POST /api/gm/asset-override
GET  /api/gm/asset-overrides
GET  /api/books
GET  /api/story/:bookId
GET  /api/game/assets?book_id=<bookId>
```

### 游戏运行时

```text
POST /account/device_login
GET  /home_page_book/guess_you_like_book_list
GET  /step1/book_desc?book_id=<bookId>
GET  /step1/book_chapter_detail?book_id=<bookId>&uid=<uid>
POST /step1/book_chapter_detail/advance
POST /book/energy_consume
POST /bonus/ad_finish
```

## 目录整理原则

- `game-server/`：通用 API/session/GM 服务；
- `game-frontend/`：通用 React/Vite 前端；
- `novel-generator/`：小说 → story/manifest；
- `asset-generator/`：manifest/art spec → 图片；
- `罪钟代理人/`、`命运币的代价/`：内容包。
