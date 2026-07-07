function normalizeBasePath(basePath) {
  return basePath.endsWith('/') ? basePath.slice(0, -1) : basePath;
}

export function requestedGameId() {
  const params = new URLSearchParams(window.location.search);
  return params.get('game') || '';
}

export function assetUrl(source, manifest, key) {
  if (!key) return '';
  const path = manifest[key] || key;
  if (/^(https?:|data:|\/)/.test(path)) return path;
  return `${source.basePath}/${path}`;
}

export async function loadRegistry() {
  const registryResponse = await fetch('/games/index.json');
  if (!registryResponse.ok) throw new Error('/games/index.json 加载失败，请先运行 npm run import:game');
  const registry = await registryResponse.json();
  if (!Array.isArray(registry) || registry.length === 0) throw new Error('没有已导入的小说资源，请运行 npm run import:game -- --project ../罪钟代理人');
  return registry.map((item) => ({ ...item, basePath: normalizeBasePath(item.basePath || `/games/${item.id}`) }));
}

export async function loadGameSummary(source) {
  const basePath = normalizeBasePath(source.basePath || `/games/${source.id}`);
  const books = await fetch(`${basePath}/books.json`).then((res) => {
    if (!res.ok) throw new Error(`${basePath}/books.json 加载失败`);
    return res.json();
  });
  const book = books.find((item) => item.bookId === source.bookId) || books[0];
  const [story, manifestRaw] = await Promise.all([
    fetch(`${basePath}/${book.file}`).then((res) => {
      if (!res.ok) throw new Error(`${basePath}/${book.file} 加载失败`);
      return res.json();
    }),
    fetch(`${basePath}/assets/manifest.json`).then((res) => {
      if (!res.ok) throw new Error(`${basePath}/assets/manifest.json 加载失败`);
      return res.json();
    }),
  ]);
  const manifest = manifestRaw.assets || manifestRaw;
  return {
    ...source,
    basePath,
    bookId: book.bookId,
    name: story.name || book.name || source.name,
    author: story.author || '',
    categories: story.categories || [],
    intro: story.intro || '',
    coverUrl: assetUrl({ ...source, basePath }, manifest, story.coverKey),
  };
}

export async function loadCatalog() {
  const registry = await loadRegistry();
  const games = await Promise.all(registry.map((source) => loadGameSummary(source)));
  return { registry, games };
}

export async function loadGameBundle(gameId) {
  const registry = await loadRegistry();

  const id = gameId || requestedGameId() || registry[0]?.id;
  const source = registry.find((item) => item.id === id || item.bookId === id) || registry[0];
  const basePath = normalizeBasePath(source.basePath || `/games/${source.id}`);
  const normalized = { ...source, basePath };
  localStorage.setItem('selectedGameId', normalized.id);

  const [books, manifestRaw] = await Promise.all([
    fetch(`${basePath}/books.json`).then((res) => {
      if (!res.ok) throw new Error(`${basePath}/books.json 加载失败`);
      return res.json();
    }),
    fetch(`${basePath}/assets/manifest.json`).then((res) => {
      if (!res.ok) throw new Error(`${basePath}/assets/manifest.json 加载失败`);
      return res.json();
    }),
  ]);
  const book = books.find((item) => item.bookId === source.bookId) || books[0];
  if (!book) throw new Error(`${source.id} 缺少 books.json 书籍条目`);
  const story = await fetch(`${basePath}/${book.file}`).then((res) => {
    if (!res.ok) throw new Error(`${basePath}/${book.file} 加载失败`);
    return res.json();
  });
  return { registry, source: normalized, books, book, story, manifest: manifestRaw.assets || manifestRaw };
}

export function switchGame(nextId) {
  const url = new URL(window.location.href);
  url.searchParams.set('game', nextId);
  window.location.href = url.toString();
}
