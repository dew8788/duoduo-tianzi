/*!
 * 生成本游戏 PWA 图标（纯 Node，无外部依赖，可在 Linux CI 上跑）
 *   橙圆角方块 + 白色小花（四片花瓣 + 金黄花心） = 「乐园/花」意象
 * 用法：node tools/make-icons.mjs
 */
import { deflateSync } from 'node:zlib';
import { writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, '..', 'assets');

/* ---------- PNG 编码 ---------- */
const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const typeBuf = Buffer.from(type, 'ascii');
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])));
  return Buffer.concat([len, typeBuf, data, crc]);
}
function encodePNG(w, h, rgba) {
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0);
  ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8; ihdr[9] = 6; // 8-bit RGBA
  const stride = w * 4 + 1;
  const raw = Buffer.alloc(stride * h);
  for (let y = 0; y < h; y++) {
    raw[y * stride] = 0; // filter none
    const s = y * w * 4, d = y * stride + 1;
    for (let x = 0; x < w * 4; x++) raw[d + x] = rgba[s + x];
  }
  return Buffer.concat([
    sig,
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw, { level: 9 })),
    chunk('IEND', Buffer.alloc(0))
  ]);
}

/* ---------- 像素绘制 ---------- */
function blendPixel(px, S, x, y, color, a) {
  if (x < 0 || y < 0 || x >= S || y >= S || a <= 0) return;
  const r = color[0], g = color[1], b = color[2];
  const i = (y * S + x) * 4;
  const dstA = px[i + 3] / 255, srcA = a;
  const outA = srcA + dstA * (1 - srcA);
  if (outA <= 0) return;
  px[i]     = Math.round((r * srcA + px[i]     * dstA * (1 - srcA)) / outA);
  px[i + 1] = Math.round((g * srcA + px[i + 1] * dstA * (1 - srcA)) / outA);
  px[i + 2] = Math.round((b * srcA + px[i + 2] * dstA * (1 - srcA)) / outA);
  px[i + 3] = Math.round(outA * 255);
}

function roundedRect(px, S, cx, cy, halfW, halfH, radius, color, alpha) {
  const r = Math.max(radius, 0.5);
  for (let y = Math.floor(cy - halfH - 1); y <= Math.ceil(cy + halfH + 1); y++) {
    for (let x = Math.floor(cx - halfW - 1); x <= Math.ceil(cx + halfW + 1); x++) {
      const dxp = Math.abs(x + 0.5 - cx), dyp = Math.abs(y + 0.5 - cy);
      const qx = Math.max(dxp - (halfW - r), 0);
      const qy = Math.max(dyp - (halfH - r), 0);
      const dist = Math.hypot(qx, qy) - r;
      const cov = Math.max(0, Math.min(1, 1 - dist));
      if (cov > 0) blendPixel(px, S, x, y, color, alpha * cov);
    }
  }
}

function ellipse(px, S, cx, cy, rx, ry, color, alpha) {
  for (let y = Math.floor(cy - ry - 1); y <= Math.ceil(cy + ry + 1); y++) {
    for (let x = Math.floor(cx - rx - 1); x <= Math.ceil(cx + rx + 1); x++) {
      if (x < 0 || y < 0 || x >= S || y >= S) continue;
      const dx = x + 0.5 - cx, dy = y + 0.5 - cy;
      const val = (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry);
      const cov = Math.max(0, Math.min(1, 1.15 - val));
      if (cov > 0) blendPixel(px, S, x, y, color, alpha * cov);
    }
  }
}

/* ---------- 花朵图标 ---------- */
function buildIcon(size) {
  const S = size;
  const px = new Uint8Array(S * S * 4);
  // 背景：橙色圆角方块（几乎铺满）
  roundedRect(px, S, S * 0.5, S * 0.5, S * 0.5, S * 0.5, S * 0.20, [247, 111, 46, 255], 1);
  // 底部深橙厚边（做成按钮的立体下缘）
  roundedRect(px, S, S * 0.5, S * 0.925, S * 0.5, S * 0.075, S * 0.06, [208, 72, 30, 255], 1);
  // 白花：4 片竖长椭圆花瓣 + 金黄+白色花心
  const cx = S * 0.5, cy = S * 0.46;
  const pRx = S * 0.225, pRy = S * 0.30;
  const off = S * 0.25;
  const white = [255, 255, 255, 255];
  ellipse(px, S, cx, cy - off, pRx, pRy, white, 1);
  ellipse(px, S, cx, cy + off, pRx, pRy, white, 1);
  ellipse(px, S, cx - off, cy, pRx, pRy, white, 1);
  ellipse(px, S, cx + off, cy, pRx, pRy, white, 1);
  // 花心
  ellipse(px, S, cx, cy, S * 0.17, S * 0.17, [255, 199, 60, 255], 1);
  ellipse(px, S, cx, cy, S * 0.07, S * 0.07, [255, 250, 230, 255], 1);
  return px;
}

/* ---------- 写文件 ---------- */
mkdirSync(OUT, { recursive: true });
const SIZES = [
  [180, 'icon-180.png'],
  [192, 'icon-192.png'],
  [512, 'icon-512.png']
];
for (const [s, name] of SIZES) {
  const rgba = buildIcon(s);
  const buf = encodePNG(s, s, rgba);
  writeFileSync(path.join(OUT, name), buf);
  console.log('✓ assets/' + name + ' (' + s + 'px, ' + (buf.length / 1024).toFixed(1) + ' KB)');
}