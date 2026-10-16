import { copyFile, cp, mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const root = new URL('../', import.meta.url);
const site = new URL('dist/site/', root);
await mkdir(new URL('dist/', site), { recursive: true });
await mkdir(new URL('data/', site), { recursive: true });
await cp(new URL('demo/', root), new URL('demo/', site), { recursive: true });
await copyFile(new URL('data/vocabulary.json', root), new URL('data/vocabulary.json', site));
await copyFile(new URL('dist/preview-font.woff2', root), new URL('dist/preview-font.woff2', site));
for (const name of ['LICENSE', 'LICENSES.md', 'OFL.txt', 'wordfreq-attribution.md']) {
  await copyFile(new URL(name, root), new URL(name, site));
}
await writeFile(new URL('index.html', site), `<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url=./demo/">
<title>Common Chinese English Sans</title>
<a href="./demo/">打开字体演示 / Open demo</a>
</html>
`);
await writeFile(new URL('.nojekyll', site), '');
console.log(`GitHub Pages site: ${fileURLToPath(site)}`);
