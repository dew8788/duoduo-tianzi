/*!
 * 朵朵填字乐园 · 打包脚本
 * 用法：node build.mjs
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync, statSync, copyFileSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(__dirname, 'src');
const DIST = path.join(__dirname, 'dist');

function read(p) {
  const f = path.join(SRC, p);
  if (!existsSync(f)) {
    console.error('✗ 缺少源文件: ' + f);
    process.exit(1);
  }
  return readFileSync(f, 'utf8');
}

mkdirSync(DIST, { recursive: true });

const css = read('style.css');
const levels = read('puzzles.js');
const engine = read('engine.js');
const app = read('app.js');
let html = read('index.template.html');

function inline(tpl, marker, code, label) {
  const token = '/*{{' + marker + '}}*/';
  if (tpl.indexOf(token) < 0) {
    console.error('✗ 模板里找不到占位符 ' + token);
    process.exit(1);
  }
  console.log('  内联 ' + label.padEnd(8) + (code.length / 1024).toFixed(1).padStart(7) + ' KB');
  return tpl.replace(token, () => code);
}

console.log('打包 朵朵填字乐园 → dist/');
html = inline(html, 'CSS', css, 'style');
html = inline(html, 'LEVELS', levels, 'puzzles');
html = inline(html, 'ENGINE', engine, 'engine');
html = inline(html, 'APP', app, 'app');

if (/\{\{[A-Z]+\}\}/.test(html)) {
  console.error('✗ 仍有未替换的占位符');
  process.exit(1);
}

const outFile = path.join(DIST, 'index.html');
writeFileSync(outFile, html, 'utf8');

// 图标（从 assets/ 复制）
const ASSETS_DIR = path.join(__dirname, 'assets');
let iconCount = 0;
if (existsSync(ASSETS_DIR)) {
  for (const f of readdirSync(ASSETS_DIR)) {
    if (!/\.(png|ico|svg)$/i.test(f)) continue;
    copyFileSync(path.join(ASSETS_DIR, f), path.join(DIST, f));
    iconCount++;
  }
}
if (!iconCount) {
  console.error('✗ assets/ 里没有图标');
  process.exit(1);
}

// Service Worker（离线缓存，逻辑与 24 点同款，非阻塞）
const sw = `const CACHE = 'pz-v1';
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon-180.png', './icon-192.png', './icon-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(self.skipWaiting());
});
self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim());
  warmCache();
});
function warmCache() {
  caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .catch(() => {});
  caches.open(CACHE)
    .then((cache) => Promise.all(ASSETS.map((u) => cache.add(u).catch(() => {}))))
    .catch(() => {});
}
function isDoc(req) {
  const accept = req.headers.get('accept') || '';
  return req.mode === 'navigate' || accept.indexOf('text/html') >= 0;
}
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const req = e.request;
  if (isDoc(req)) {
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const hit = await cache.match(req);
      if (hit) {
        fetch(req).then((res) => { if (res && res.ok) cache.put(req, res.clone()); }).catch(() => {});
        return hit;
      }
      try {
        const res = await fetch(req);
        if (res && res.ok) cache.put(req, res.clone());
        return res;
      } catch (err) {
        const fb = (await cache.match('./index.html')) || (await cache.match('./'));
        if (fb) return fb;
        throw err;
      }
    })());
    return;
  }
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(req);
    if (hit) return hit;
    const res = await fetch(req);
    if (res && res.ok) cache.put(req, res.clone());
    return res;
  })());
});
`;
writeFileSync(path.join(DIST, 'sw.js'), sw, 'utf8');

const manifest = {
  name: '朵朵填字乐园',
  short_name: '朵朵填字',
  description: '朵朵填字乐园：看图拼字、填成语，认字的趣味小游戏。纯本地运行、离线可玩。',
  lang: 'zh-CN',
  start_url: './index.html',
  scope: './',
  display: 'standalone',
  display_override: ['standalone', 'fullscreen'],
  orientation: 'any',
  background_color: '#ffffff',
  theme_color: '#ffffff',
  categories: ['games', 'education'],
  icons: [
    { src: 'icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
    { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
    { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' }
  ]
};
writeFileSync(path.join(DIST, 'manifest.webmanifest'), JSON.stringify(manifest, null, 2) + '\n', 'utf8');

const size = statSync(outFile).size;
const hash = createHash('sha256').update(readFileSync(outFile)).digest('hex').slice(0, 12);
console.log('\n✓ dist/index.html  ' + (size / 1024).toFixed(1) + ' KB  sha256:' + hash);
console.log('✓ dist/sw.js / manifest.webmanifest / ' + iconCount + ' 个图标');
console.log('\n本机预览：node tools/serve.mjs');
console.log('发布：推到 main 后由 .github/workflows/pages.yml 自动部署');