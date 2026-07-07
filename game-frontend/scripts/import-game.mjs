import { cp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const args = process.argv.slice(2);

function arg(name, fallback = '') {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] || fallback : fallback;
}

const projectArg = arg('--project');
if (!projectArg) {
  console.error('Usage: npm run import:game -- --project ../罪钟代理人 [--id custom-id]');
  process.exit(1);
}

const project = path.resolve(root, projectArg);
const gameDir = path.join(project, 'game');
const booksPath = path.join(gameDir, 'books.json');
const manifestPath = path.join(gameDir, 'assets', 'manifest.json');

if (!existsSync(booksPath) || !existsSync(manifestPath)) {
  console.error(`Invalid game package: ${gameDir} must contain books.json and assets/manifest.json`);
  process.exit(1);
}

const books = JSON.parse(await readFile(booksPath, 'utf8'));
const firstBook = books[0];
if (!firstBook?.bookId || !firstBook?.file) {
  console.error('books.json must contain at least one { bookId, name, file } entry');
  process.exit(1);
}

const id = arg('--id', firstBook.bookId);
const target = path.join(root, 'public', 'games', id);
await rm(target, { recursive: true, force: true });
await mkdir(target, { recursive: true });

for (const file of await readdir(gameDir)) {
  if (file === 'books.json' || /^story\..+\.json$/.test(file)) {
    await cp(path.join(gameDir, file), path.join(target, file));
  }
}
await cp(path.join(gameDir, 'assets'), path.join(target, 'assets'), { recursive: true });

const registryPath = path.join(root, 'public', 'games', 'index.json');
const registry = existsSync(registryPath) ? JSON.parse(await readFile(registryPath, 'utf8')) : [];
const entry = {
  id,
  bookId: firstBook.bookId,
  name: firstBook.name,
  basePath: `/games/${id}`,
  sourceProject: path.relative(root, project),
};
const nextRegistry = [entry, ...registry.filter((item) => item.id !== id)];
await writeFile(registryPath, JSON.stringify(nextRegistry, null, 2) + '\n');

console.log(`Imported ${firstBook.name} (${firstBook.bookId}) -> public/games/${id}`);
