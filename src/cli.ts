import { readFile, writeFile, mkdir, rename } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawnSync, spawn } from 'node:child_process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { entries, plan } from './planner.ts';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
interface Config { family: string; postscriptName: string; version: string; base: {path: string; url: string; sha256: string; license: string}; vocabulary: string; protection: string; outDir: string; annotationScale: number; annotationBaseline: number; buildEpoch: number }
const config: Config = JSON.parse(await readFile(resolve(root, 'font.config.json'), 'utf8'));
if (!/^[A-Za-z][A-Za-z0-9-]*$/.test(config.postscriptName) || !config.family || !(config.annotationScale > 0 && config.annotationScale <= 1) || !Number.isFinite(config.annotationBaseline) || !Number.isSafeInteger(config.buildEpoch)) throw new Error('Invalid font configuration');
const base = resolve(root, config.base.path), out = resolve(root, config.outDir);
const python = process.env.PYTHON ?? (existsSync(resolve(root, '.venv/bin/python')) ? resolve(root, '.venv/bin/python') : 'python3');
function run(script: string, args: string[] = [], capture = false) {
  const result = spawnSync(python, [resolve(root, 'scripts', script), ...args], { cwd: root, encoding: 'utf8', stdio: capture ? 'pipe' : 'inherit', maxBuffer: 16 * 1024 * 1024 });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(result.stderr || `${script} failed (${result.status})`);
  return result.stdout;
}
function checkBase(bytes: Uint8Array) {
  if (createHash('sha256').update(bytes).digest('hex') !== config.base.sha256) throw new Error('Base font checksum mismatch; review source before updating config');
}
async function fetchBase() {
  if (existsSync(base)) { checkBase(await readFile(base)); console.log('Verified cached open-source base font'); return; }
  const response = await fetch(config.base.url, { signal: AbortSignal.timeout(300_000) });
  if (!response.ok) throw new Error(`Base download failed: ${response.status}`);
  const bytes = new Uint8Array(await response.arrayBuffer()); checkBase(bytes);
  await mkdir(dirname(base), { recursive: true });
  await writeFile(base + '.tmp', bytes); await rename(base + '.tmp', base);
  console.log(`Downloaded and verified ${config.base.license} base font`);
}
async function makePlan() {
  if (!existsSync(base)) throw new Error('Base font missing. Run npm run font:fetch first.');
  checkBase(await readFile(base));
  const info = JSON.parse(run('compiler.py', ['inspect', '--base', base], true));
  const vocab = entries(JSON.parse(await readFile(resolve(root, config.vocabulary), 'utf8')));
  const protect = entries(JSON.parse(await readFile(resolve(root, config.protection), 'utf8')), true);
  const rules = plan(vocab, protect, new Set<number>(info.codepoints), info.glyphs);
  await mkdir(out, { recursive: true });
  await writeFile(resolve(out, 'plan.json'), JSON.stringify({ schema: 1, config, baseSha256: config.base.sha256, rules }, null, 2) + '\n');
  console.log(`Planned ${vocab.length} annotations and ${protect.length} protected forms`);
}
const cmd = process.argv[2];
switch (cmd) {
  case 'fetch': await fetchBase(); break;
  case 'plan': await makePlan(); break;
  case 'build':
    await makePlan(); run('compiler.py', ['build', '--base', base, '--plan', resolve(out, 'plan.json'), '--out', out]);
    run('verify.py', ['--base', base, '--out', out]); break;
  case 'verify': run('verify.py', ['--base', base, '--out', out]); break;
  case 'package':
    run('verify.py', ['--base', base, '--out', out]);
    run('package_release.py', ['--out', out]); break;
  case 'demo': {
    if (!existsSync(resolve(out, 'preview-font.woff2'))) throw new Error('Build fonts first: npm run build');
    const child = spawn(python, ['-m', 'http.server', '8765', '--bind', '127.0.0.1', '--directory', root], { stdio: 'inherit' });
    console.log('Preview: http://127.0.0.1:8765/demo/');
    child.on('error', e => { console.error(e); process.exitCode = 1; }); break;
  }
  default: throw new Error('Usage: node src/cli.ts fetch|plan|build|verify|package|demo');
}
