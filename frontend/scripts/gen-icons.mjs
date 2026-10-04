/**
 * Generate BioTerrace Sentinel PWA icons — pure Node.js, zero dependencies.
 * Uses only the built-in `zlib` module to write valid PNG files.
 *
 * Outputs:
 *   public/icons/icon-512.png
 *   public/icons/icon-192.png
 *   public/icons/icon-96.png
 *
 * Run:  node scripts/gen-icons.mjs
 */

import { deflateSync } from 'zlib';
import { writeFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR   = join(__dirname, '..', 'public', 'icons');

// ── Brand colours (RGB) ──────────────────────────────────────────────────────
const FOREST  = [0x0f, 0x1f, 0x0f];   // #0f1f0f  background
const CANOPY  = [0x1a, 0x3a, 0x1a];   // #1a3a1a  card bg
const SAGE    = [0x4a, 0x9a, 0x4a];   // #4a9a4a  mountain body
const MIST    = [0xa8, 0xd5, 0xa2];   // #a8d5a2  snow / peak highlight
const LEAF    = [0x2d, 0x6a, 0x2d];   // #2d6a2d  accent ring

// ── PNG helpers ──────────────────────────────────────────────────────────────

function crc32(buf) {
  let crc = 0xffffffff;
  const table = crc32.table ??= (() => {
    const t = new Uint32Array(256);
    for (let i = 0; i < 256; i++) {
      let c = i;
      for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
      t[i] = c;
    }
    return t;
  })();
  for (let i = 0; i < buf.length; i++) crc = table[(crc ^ buf[i]) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const typeBytes = Buffer.from(type, 'ascii');
  const len       = Buffer.alloc(4); len.writeUInt32BE(data.length);
  const crcInput  = Buffer.concat([typeBytes, data]);
  const crcBuf    = Buffer.alloc(4); crcBuf.writeUInt32BE(crc32(crcInput));
  return Buffer.concat([len, typeBytes, data, crcBuf]);
}

function encodePng(pixels, size) {
  // pixels: Uint8Array of size*size*3 (RGB, row-major)
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8;   // bit depth
  ihdr[9] = 2;   // color type: RGB
  ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;

  // Build filtered scanlines (filter byte 0 = None per row)
  const raw = Buffer.alloc(size * (1 + size * 3));
  for (let y = 0; y < size; y++) {
    raw[y * (1 + size * 3)] = 0; // filter type None
    for (let x = 0; x < size; x++) {
      const src = (y * size + x) * 3;
      const dst = y * (1 + size * 3) + 1 + x * 3;
      raw[dst]     = pixels[src];
      raw[dst + 1] = pixels[src + 1];
      raw[dst + 2] = pixels[src + 2];
    }
  }

  const compressed = deflateSync(raw, { level: 9 });
  return Buffer.concat([
    sig,
    chunk('IHDR', ihdr),
    chunk('IDAT', compressed),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

// ── Pixel drawing helpers ────────────────────────────────────────────────────

function makeCanvas(size, bg) {
  const px = new Uint8Array(size * size * 3);
  for (let i = 0; i < size * size; i++) {
    px[i * 3]     = bg[0];
    px[i * 3 + 1] = bg[1];
    px[i * 3 + 2] = bg[2];
  }
  return px;
}

function setPixel(px, size, x, y, colour) {
  if (x < 0 || x >= size || y < 0 || y >= size) return;
  const i = (y * size + x) * 3;
  px[i] = colour[0]; px[i + 1] = colour[1]; px[i + 2] = colour[2];
}

/** Filled circle */
function fillCircle(px, size, cx, cy, r, colour) {
  for (let y = cy - r; y <= cy + r; y++) {
    for (let x = cx - r; x <= cx + r; x++) {
      if ((x - cx) ** 2 + (y - cy) ** 2 <= r * r) setPixel(px, size, x, y, colour);
    }
  }
}

/** Filled triangle (flat-bottom) using barycentric test */
function fillTriangle(px, size, x0, y0, x1, y1, x2, y2, colour) {
  const minX = Math.max(0, Math.floor(Math.min(x0, x1, x2)));
  const maxX = Math.min(size - 1, Math.ceil(Math.max(x0, x1, x2)));
  const minY = Math.max(0, Math.floor(Math.min(y0, y1, y2)));
  const maxY = Math.min(size - 1, Math.ceil(Math.max(y0, y1, y2)));

  function sign(ax, ay, bx, by, cx, cy) {
    return (ax - cx) * (by - cy) - (bx - cx) * (ay - cy);
  }

  for (let y = minY; y <= maxY; y++) {
    for (let x = minX; x <= maxX; x++) {
      const d0 = sign(x, y, x0, y0, x1, y1);
      const d1 = sign(x, y, x1, y1, x2, y2);
      const d2 = sign(x, y, x2, y2, x0, y0);
      const hasNeg = d0 < 0 || d1 < 0 || d2 < 0;
      const hasPos = d0 > 0 || d1 > 0 || d2 > 0;
      if (!(hasNeg && hasPos)) setPixel(px, size, x, y, colour);
    }
  }
}

/** Filled rounded rectangle */
function fillRoundRect(px, size, x, y, w, h, r, colour) {
  for (let py = y; py < y + h; py++) {
    for (let px_ = x; px_ < x + w; px_++) {
      const dx = Math.max(0, Math.max(x + r - px_, px_ - (x + w - r - 1)));
      const dy = Math.max(0, Math.max(y + r - py, py - (y + h - r - 1)));
      if (dx * dx + dy * dy <= r * r) setPixel(px, size, px_, py, colour);
    }
  }
}

// ── Draw the icon at `size` pixels ───────────────────────────────────────────

function drawIcon(size) {
  const s = size / 512;   // scale factor
  const px = makeCanvas(size, FOREST);

  // Background rounded rectangle (card-like)
  const pad = Math.round(24 * s);
  const r   = Math.round(80 * s);
  fillRoundRect(px, size, pad, pad, size - pad * 2, size - pad * 2, r, CANOPY);

  // Outer ring accent
  const ringW = Math.round(10 * s);
  for (let i = 0; i < ringW; i++) {
    const rr = Math.round((80 - i) * s);
    const p  = pad + i;
    const ww = size - p * 2;
    // Draw outline only (draw filled then overdraw inside)
    fillRoundRect(px, size, p, p, ww, ww, rr, LEAF);
  }
  fillRoundRect(px, size, pad + ringW, pad + ringW,
    size - (pad + ringW) * 2, size - (pad + ringW) * 2,
    Math.max(1, r - ringW), CANOPY);

  // Mountain body — large triangle
  const midX  = Math.round(size / 2);
  const peakY = Math.round(110 * s);
  const baseY = Math.round(370 * s);
  const baseL = Math.round(100 * s);
  const baseR = Math.round(412 * s);
  fillTriangle(px, size, midX, peakY, baseL, baseY, baseR, baseY, SAGE);

  // Snow cap — smaller bright triangle at peak
  const snowH = Math.round(90 * s);
  const snowW = Math.round(60 * s);
  fillTriangle(px, size,
    midX, peakY,
    midX - snowW, peakY + snowH,
    midX + snowW, peakY + snowH,
    MIST,
  );

  // Ground/terrace band below mountain base
  const terraceY = Math.round(370 * s);
  const terraceH = Math.round(40 * s);
  fillRoundRect(px, size,
    Math.round(80 * s), terraceY,
    Math.round(352 * s), terraceH,
    Math.round(8 * s), LEAF,
  );

  // Small dot above peak — "sentinel eye"
  fillCircle(px, size, midX, Math.round(78 * s), Math.round(14 * s), MIST);

  return px;
}

// ── Resize (box downsample) ──────────────────────────────────────────────────

function resize(src, srcSize, dstSize) {
  const dst   = new Uint8Array(dstSize * dstSize * 3);
  const scale = srcSize / dstSize;
  for (let dy = 0; dy < dstSize; dy++) {
    for (let dx = 0; dx < dstSize; dx++) {
      let r = 0, g = 0, b = 0, count = 0;
      const x0 = Math.floor(dx * scale);
      const x1 = Math.ceil((dx + 1) * scale);
      const y0 = Math.floor(dy * scale);
      const y1 = Math.ceil((dy + 1) * scale);
      for (let sy = y0; sy < y1 && sy < srcSize; sy++) {
        for (let sx = x0; sx < x1 && sx < srcSize; sx++) {
          const i = (sy * srcSize + sx) * 3;
          r += src[i]; g += src[i + 1]; b += src[i + 2];
          count++;
        }
      }
      const di = (dy * dstSize + dx) * 3;
      dst[di] = r / count; dst[di + 1] = g / count; dst[di + 2] = b / count;
    }
  }
  return dst;
}

// ── Generate & write ─────────────────────────────────────────────────────────

mkdirSync(OUT_DIR, { recursive: true });

const base512 = drawIcon(512);
const px192   = resize(base512, 512, 192);
const px96    = resize(base512, 512, 96);

const files = [
  { name: 'icon-512.png', px: base512, size: 512 },
  { name: 'icon-192.png', px: px192,   size: 192 },
  { name: 'icon-96.png',  px: px96,    size: 96  },
];

for (const { name, px, size } of files) {
  const path = join(OUT_DIR, name);
  writeFileSync(path, encodePng(px, size));
  console.log(`  ✓ ${name}  (${size}×${size})`);
}

console.log(`\nIcons written to ${OUT_DIR}`);
