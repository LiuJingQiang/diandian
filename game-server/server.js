import express from 'express';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const PORT = Number(process.env.PORT || 666);
const DEFAULT_PACKAGES = ['../罪钟代理人/game', '../命运币的代价/game'];
const GAME_PACKAGES = (process.env.GAME_PACKAGES || DEFAULT_PACKAGES.join(','))
  .split(',')
  .map((item) => item.trim())
  .filter(Boolean)
  .map((item) => path.resolve(__dirname, item));

const DB_FILE = path.join(__dirname, 'data', 'db.json');
let DB = { users: {}, assetOverrides: {}, gmLog: [] };
try { DB = JSON.parse(fs.readFileSync(DB_FILE, 'utf8')); } catch {}

function saveDb() {
  fs.mkdirSync(path.dirname(DB_FILE), { recursive: true });
  fs.writeFileSync(DB_FILE, JSON.stringify(DB, null, 2));
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function relToRoot(file) {
  return path.relative(ROOT, file).split(path.sep).join('/');
}

function loadContentPackages(paths) {
  const books = [];
  const stories = new Map();
  const manifests = new Map();
  const packageByBook = new Map();

  for (const gameDir of paths) {
    const booksPath = path.join(gameDir, 'books.json');
    const manifestPath = path.join(gameDir, 'assets', 'manifest.json');
    if (!fs.existsSync(booksPath) || !fs.existsSync(manifestPath)) {
      console.warn(`[content] skip invalid game package: ${gameDir}`);
      continue;
    }
    const localBooks = readJson(booksPath);
    const manifestRaw = readJson(manifestPath);
    const manifest = manifestRaw.assets || manifestRaw;
    for (const book of localBooks) {
      const storyPath = path.join(gameDir, book.file);
      if (!fs.existsSync(storyPath)) {
        console.warn(`[content] missing story file: ${storyPath}`);
        continue;
      }
      const story = readJson(storyPath);
      const bookId = book.bookId || story.bookId;
      const publicManifest = Object.fromEntries(Object.entries(manifest).map(([key, value]) => {
        if (!value || /^(https?:|data:|\/)/.test(value)) return [key, value];
        return [key, `/content/${bookId}/${value}`];
      }));
      books.push({ ...book, bookId, id: bookId, name: story.name || book.name });
      stories.set(bookId, story);
      manifests.set(bookId, publicManifest);
      packageByBook.set(bookId, gameDir);
    }
  }
  return { books, stories, manifests, packageByBook };
}

let CONTENT = loadContentPackages(GAME_PACKAGES);
const sessions = new Map();

function newUser(uid, isGuest = true) {
  return {
    uid,
    is_guest: isGuest,
    is_vip: false,
    energy: 100,
    stardust: 0,
    wish_star: 0,
    love: 0,
    items: { '选项限免卡': 1, '衣橱兑换券': 0, '卡碎片': 0 },
  };
}

function getUser(uid = 'guest') {
  if (!DB.users[uid]) {
    DB.users[uid] = newUser(uid, true);
    saveDb();
  }
  return DB.users[uid];
}

const OPERATORS = {
  0: (a, b) => a === b,
  1: (a, b) => a !== b,
  2: (a, b) => a > b,
  3: (a, b) => a >= b,
  4: (a, b) => a < b,
  5: (a, b) => a <= b,
};

function themeForStory(story) {
  const tags = [...(story.categories || []), story.book_theme, story.theme].filter(Boolean).join(' ');
  if (/仙侠|玄幻|修仙|古风|古代/.test(tags)) return { ui_theme: 0, theme: 'xianxia', book_theme: 'xianxia' };
  if (/AI|聊天|角色/.test(tags)) return { ui_theme: 2, theme: 'ai_chat', book_theme: 'ai_chat' };
  return { ui_theme: 1, theme: 'urban', book_theme: 'urban' };
}

function baseDialogStyle(story) {
  const theme = themeForStory(story);
  return {
    ...theme,
    display_mode: story.display_mode || 'visual_novel',
    app_display_mode: story.app_display_mode || 'visual_reader',
    content_variant: theme.theme === 'xianxia' ? 'xianxia_multi' : 'userall',
    option_variant: theme.theme === 'xianxia' ? 'xianxia' : 'userall',
    name_variant: theme.theme === 'xianxia' ? 'xianxia_left' : 'main',
    text_color: theme.theme === 'xianxia' ? '#4a2e19' : '#ffffff',
    frame_alpha: theme.theme === 'xianxia' ? 0.98 : 0.68,
  };
}

function styleForChat(story, chat) {
  const base = baseDialogStyle(story);
  const character = chat.char ? story.characters?.[chat.char] : null;
  const isNarration = !character;
  const isSystem = chat.char === 'system' || character?.name?.includes('系统') || character?.name?.includes('平台');
  return {
    ...base,
    speaker_role: isNarration ? 'narration' : isSystem ? 'system' : character?.lead ? 'lead' : 'secondary',
    content_variant: isSystem ? 'ai_chat' : isNarration ? (base.theme === 'xianxia' ? 'xianxia_multi' : 'narration') : base.content_variant,
    name_variant: isSystem ? 'ai_chat' : character?.lead ? 'main' : character ? 'secondary' : base.name_variant,
    show_name: !isNarration,
  };
}

function storyOf(session) { return CONTENT.stories.get(session.bookId); }
function currentNode(session) { return storyOf(session).nodes[session.nodeId]; }

function operand(session, item) {
  if (!item) return 0;
  if (item.vType === 3) return item.str || '';
  if (item.name === 'const') return Number(item.num) || 0;
  if (item.name === 'random') return Math.floor(Math.random() * 10) + 1;
  if (!item.name && item.str) return item.str;
  return session.variables[item.name] ?? (Number(item.num) || 0);
}

function applyHandlers(session, handlers = []) {
  for (const handler of handlers || []) {
    if (!handler.var || !handler.list?.length) continue;
    let acc = operand(session, handler.list[0]);
    for (let i = 1; i < handler.list.length; i += 1) {
      const right = operand(session, handler.list[i]);
      const op = (handler.ops || [])[i - 1] || '+';
      if (typeof acc === 'string' || typeof right === 'string') acc = `${acc}${right}`;
      else if (op === '-') acc -= right;
      else if (op === '*') acc *= right;
      else if (op === '/') acc = right ? acc / right : acc;
      else acc += right;
    }
    session.variables[handler.var] = typeof acc === 'number' ? Math.round(acc) : acc;
  }
}

function cond1(session, condition) {
  const compare = OPERATORS[condition.op] || OPERATORS[0];
  let right;
  if (condition.right?.length) right = condition.right.reduce((sum, item) => sum + operand(session, item), 0);
  else if (condition.target !== '' && condition.target != null) {
    const parsed = Number(condition.target);
    right = Number.isNaN(parsed) ? condition.target : parsed;
  } else return true;
  let left = condition.left?.length ? condition.left.reduce((sum, item) => sum + operand(session, item), 0) : (session.variables[condition.var] ?? 0);
  if (typeof right === 'string') left = String(session.variables[condition.var] ?? '');
  return compare(left, right);
}

function passConds(session, conditions = [], relation = 'and') {
  if (!conditions.length) return true;
  const results = conditions.map((condition) => cond1(session, condition));
  return relation === 'or' ? results.some(Boolean) : results.every(Boolean);
}

function fill(session, text = '') {
  const hero = session.variables['主角名字'];
  return hero ? text.replaceAll('主角名字', hero) : text;
}

function visibleOptions(session) {
  return (currentNode(session).options || [])
    .map((option, index) => ({ index, option }))
    .filter(({ option }) => option.text && passConds(session, option.conditions, 'and'))
    .map(({ index, option }) => ({ index, text: fill(session, option.text), cost: option.cost || {}, isAd: Boolean(option.isAd) }));
}

function publicBook(book) {
  const story = CONTENT.stories.get(book.bookId);
  return {
    id: book.bookId,
    book_id: book.bookId,
    bookId: book.bookId,
    name: story?.name || book.name,
    book_name: story?.name || book.name,
    author: story?.author,
    categories: story?.categories || [],
    intro: story?.intro || '',
    coverKey: story?.coverKey,
    image_key: story?.coverKey,
    ui_theme: themeForStory(story || {}).ui_theme,
    book_theme: themeForStory(story || {}).book_theme,
    dialog_style: story ? baseDialogStyle(story) : null,
    online_chapter_sum: Object.keys(story?.nodes || {}).length,
    ad_mod: 'Option',
  };
}

function bookDesc(bookId) {
  const story = CONTENT.stories.get(bookId);
  if (!story) return null;
  return {
    id: bookId,
    book_id: bookId,
    name: story.name,
    book_name: story.name,
    author: story.author,
    intro: story.intro,
    categories: story.categories || [],
    image_key: story.coverKey,
    coverKey: story.coverKey,
    ...themeForStory(story),
    display_mode: 'visual_novel',
    app_display_mode: 'visual_reader',
    dialog_style: baseDialogStyle(story),
    book_character_list: Object.entries(story.characters || {}).map(([id, item]) => ({ id, character_id: id, ...item })),
    chapters: [{ id: story.start, chapter_id: story.start, name: '主线剧情', index: 0, is_have_energy_unlock: false }],
    is_free_book: false,
    is_use_ticket_book: true,
    book_permissions: ['Visual'],
  };
}

function createSession(bookId, uid = 'guest') {
  const story = CONTENT.stories.get(bookId);
  if (!story) throw new Error(`Unknown bookId: ${bookId}`);
  const session = {
    id: `${bookId}_${uid}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    uid,
    bookId,
    nodeId: story.start,
    chatIndex: 0,
    variables: Object.fromEntries((story.variables || []).map((key) => [key, 0])),
    energy: story.startEnergy ?? getUser(uid).energy ?? 60,
    items: { ...getUser(uid).items },
    paidOptions: {},
  };
  applyHandlers(session, currentNode(session).handlers);
  sessions.set(session.id, session);
  return session;
}

function statePayload(session, extra = {}) {
  const story = storyOf(session);
  const node = currentNode(session);
  return {
    sessionId: session.id,
    bookId: session.bookId,
    nodeId: session.nodeId,
    nodeName: node.name,
    bgKey: node.bgKey,
    sceneName: node.sceneName,
    characters: story.characters || {},
    ...themeForStory(story),
    display_mode: baseDialogStyle(story).display_mode,
    app_display_mode: baseDialogStyle(story).app_display_mode,
    dialog_style: baseDialogStyle(story),
    variables: session.variables,
    energy: session.energy,
    items: session.items,
    ...extra,
  };
}

function advance(session) {
  const node = currentNode(session);
  const chats = (node.chats || []).filter((chat) => passConds(session, chat.conditions, 'and'));
  if (session.chatIndex < chats.length) {
    const chat = chats[session.chatIndex++];
    applyHandlers(session, chat.handlers);
    const bgKey = chat.bgKey || node.bgKey;
    return statePayload(session, { type: 'chat', bgKey, sceneName: chat.sceneName || node.sceneName, chat: { ...chat, text: fill(session, chat.text), dialog_style: styleForChat(storyOf(session), chat) } });
  }
  const options = visibleOptions(session);
  if (options.length) return statePayload(session, { type: 'options', options, optionTitle: node.optionTitle || '', option_style: baseDialogStyle(storyOf(session)) });
  return autoDivert(session);
}

function autoDivert(session) {
  const node = currentNode(session);
  const diverts = (node.diverts || []).slice();
  if (!diverts.length || node.isEnd) return statePayload(session, { type: 'end', message: '你走完了当前分支。' });
  const pick = diverts.find((divert) => passConds(session, divert.conditions, divert.relation)) || diverts[0];
  if (pick.isEnd || !pick.next) return statePayload(session, { type: 'end', message: '你走完了当前分支。' });
  session.nodeId = pick.next;
  session.chatIndex = 0;
  applyHandlers(session, currentNode(session).handlers);
  return advance(session);
}

function choose(session, optionIndex) {
  const node = currentNode(session);
  const option = (node.options || [])[optionIndex];
  if (!option) return statePayload(session, { type: 'options', options: visibleOptions(session), error: '选项不存在' });
  if (!passConds(session, option.conditions, 'and')) return statePayload(session, { type: 'options', options: visibleOptions(session), error: '条件未满足' });
  const cost = option.cost?.energy || 0;
  const paidKey = `${session.nodeId}:${optionIndex}`;
  if (option.isAd && !session.paidOptions[paidKey]) return statePayload(session, { type: 'needAd', optionIndex, cost });
  if (cost > 0 && !session.paidOptions[paidKey]) {
    if (session.items['选项限免卡'] > 0) session.items['选项限免卡'] -= 1;
    else if (session.energy >= cost) session.energy -= cost;
    else return statePayload(session, { type: 'needEnergy', optionIndex, cost, options: visibleOptions(session) });
    session.paidOptions[paidKey] = true;
  }
  applyHandlers(session, option.handlers);
  const next = option.next || option.diverts?.[0]?.next;
  if (!next) return statePayload(session, { type: 'end', message: '你走完了当前分支。' });
  session.nodeId = next;
  session.chatIndex = 0;
  applyHandlers(session, currentNode(session).handlers);
  return advance(session);
}

const app = express();
app.use(express.json());
app.use((req, res, next) => {
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type');
  res.set('Cache-Control', req.path.startsWith('/api/') ? 'no-store' : 'no-cache, must-revalidate');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  return next();
});

for (const [bookId, gameDir] of CONTENT.packageByBook.entries()) {
  app.use(`/content/${bookId}`, express.static(gameDir));
}

app.post('/api/login_guest', (req, res) => {
  const uid = req.body.device_id || req.body.uid || `guest_${Math.random().toString(36).slice(2, 10)}`;
  const user = getUser(uid);
  user.is_guest = true;
  saveDb();
  res.json({ code: 0, data: { access_token: `mock.${Buffer.from(uid).toString('base64')}`, user_id: uid, uid, is_guest: true } });
});
app.post('/account/device_login', (req, res) => {
  const uid = req.body?.device_id || req.body?.uid || `guest_${Math.random().toString(36).slice(2, 10)}`;
  getUser(uid);
  res.json({ code: 0, data: { uid, user_id: uid, token: `mock.${Buffer.from(uid).toString('base64')}`, is_guest: true } });
});
app.get('/api/user/currency', (req, res) => res.json({ code: 0, data: getUser(req.query.uid || 'guest') }));
app.post('/api/gm/grant', (req, res) => {
  const user = getUser(req.body.uid || 'guest');
  const item = req.body.item || '能量';
  const count = Number(req.body.count || 0);
  if (item === '能量') user.energy += count;
  else if (item === '星辰') user.stardust += count;
  else if (item === '祈愿星') user.wish_star += count;
  else if (item === '爱心') user.love += count;
  else user.items[item] = (user.items[item] || 0) + count;
  DB.gmLog.unshift({ uid: user.uid, item, count, ts: new Date().toISOString() });
  DB.gmLog = DB.gmLog.slice(0, 100);
  saveDb();
  res.json({ code: 0, data: user, log: DB.gmLog.slice(0, 20) });
});
app.get('/api/gm/state', (req, res) => res.json({ code: 0, users: DB.users, log: DB.gmLog.slice(0, 20) }));
app.post('/api/gm/asset-override', (req, res) => {
  if (req.body.from) {
    if (req.body.to) DB.assetOverrides[req.body.from] = req.body.to;
    else delete DB.assetOverrides[req.body.from];
    saveDb();
  }
  res.json({ code: 0, data: DB.assetOverrides });
});
app.get('/api/gm/asset-overrides', (req, res) => res.json({ code: 0, data: DB.assetOverrides }));

app.get('/api/books', (req, res) => res.json({ code: 0, data: CONTENT.books }));
app.get('/api/story/:id', (req, res) => {
  const story = CONTENT.stories.get(req.params.id);
  story ? res.json({ code: 0, data: story }) : res.status(404).json({ code: 1, msg: 'story not found' });
});
app.get('/api/game/assets', (req, res) => {
  const bookId = req.query.book_id || req.query.bookId || CONTENT.books[0]?.bookId;
  res.json({ code: 0, data: CONTENT.manifests.get(bookId) || {} });
});
app.get('/api/config', (req, res) => res.json({ code: 0, data: { book_count: CONTENT.books.length, packages: GAME_PACKAGES.map(relToRoot) } }));
app.get('/api/health', (req, res) => res.json({ code: 0, ok: true, books: CONTENT.books.length, users: Object.keys(DB.users).length }));

app.get('/home_page_book/guess_you_like_book_list', (req, res) => res.json({ code: 0, data: { book_list: CONTENT.books.map(publicBook) } }));
app.get('/step1/book_desc', (req, res) => {
  const desc = bookDesc(req.query.book_id || req.query.bookId || CONTENT.books[0]?.bookId);
  desc ? res.json({ code: 0, data: desc }) : res.status(404).json({ code: 1, msg: 'book not found' });
});
app.get('/step1/book_chapter_detail', (req, res) => {
  const bookId = req.query.book_id || req.query.bookId || CONTENT.books[0]?.bookId;
  const uid = req.query.uid || req.get('x-user-id') || 'web-dev';
  try {
    res.json({ code: 0, data: statePayload(createSession(bookId, uid), { type: 'ready', chapter_id: req.query.chapter_id || req.query.chapterId || bookId, chapter_index: Number(req.query.chapter_index || 0) }) });
  } catch (error) {
    res.status(400).json({ code: 1, msg: error.message });
  }
});
app.post('/step1/book_chapter_detail/advance', (req, res) => {
  const session = sessions.get(req.body.sessionId);
  if (!session) return res.status(404).json({ code: 1, msg: 'session not found' });
  return res.json({ code: 0, data: advance(session) });
});
app.post('/book/energy_consume', (req, res) => {
  const session = sessions.get(req.body.sessionId);
  if (!session) return res.status(404).json({ code: 1, msg: 'session not found' });
  return res.json({ code: 0, data: choose(session, Number(req.body.optionIndex)) });
});
app.post('/bonus/ad_finish', (req, res) => {
  const session = sessions.get(req.body.sessionId);
  if (!session) return res.status(404).json({ code: 1, msg: 'session not found' });
  session.energy += Number(req.body.amount || 15);
  if (req.body.optionIndex != null) session.paidOptions[`${session.nodeId}:${req.body.optionIndex}`] = true;
  return res.json({ code: 0, data: statePayload(session, { type: 'reward', add: Number(req.body.amount || 15) }) });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[game-server] listening on :${PORT}`);
  console.log(`[game-server] loaded ${CONTENT.books.length} books from ${GAME_PACKAGES.map(relToRoot).join(', ')}`);
});
