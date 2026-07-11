/**
 * stripePattern.ts — the generated diagonal-stripe pattern atlas for the contested-county
 * fill (DESIGN_BIBLE.md §2.1 layer 3, "striped/hatched fill (CK3 convention)"; §6 names a
 * `contest-stripe` role). This is the TRUE striping that architecture.md §7 / the
 * integration-ledger Juice-Pass queue flagged as "deferred to the design phase" —
 * `@deck.gl/extensions`' `FillStyleExtension` (already a dependency) tiles a polygon fill
 * with a bitmap pattern, and this module supplies that bitmap.
 *
 * NO binary asset: the tile is encoded to a `data:image/png;base64,…` URI at first use
 * (memoized) rather than checked into `public/`. A tiny hand-rolled RGBA-PNG encoder
 * (stored/uncompressed DEFLATE — no zlib dependency) keeps the whole thing pure,
 * regenerable, and unit-testable, which a checked-in sprite is not (User CLAUDE.md:
 * verifiability + reuse-over-recreation; the encoder deliberately reuses no runtime
 * `<canvas>`, so it works identically in jsdom, Node, and the browser).
 *
 * MASK SEMANTICS (verified against the extension's shader, `fill-style/shader-module.js`):
 * with `fillPatternMask` (default `true`) the fragment shader does `color.a *=
 * patternColor.a` and keeps the layer's own `getFillColor` rgb — i.e. the pattern's
 * ALPHA channel is a stencil, the fill colour comes from the layer. So stripe pixels are
 * alpha 255 and gap pixels alpha 0; rgb is a constant white that the mask never shows.
 *
 * WORLD SIZE: the same shader scales the pattern by `FILL_UV_SCALE = 512/40_000_000`, so
 * one tile spans ≈ `getFillPatternScale × tilePx` metres (deck's documented "24px @ scale
 * 1 ≈ 24 m"). `STRIPE_PATTERN_SCALE` below is tuned so the hatch reads at the regional
 * (county) register; it is a world-anchored value, so the hatch densifies on zoom-out and
 * coarsens on zoom-in exactly as CK3's does. Adjust if live tuning wants a different pitch.
 */

/** Tile is square; must be an integer multiple of `STRIPE_PERIOD` to tile seamlessly. */
const STRIPE_TILE_PX = 16;
/** Full light+dark cycle of the 45° hatch, in tile pixels. */
const STRIPE_PERIOD = 8;
/** Opaque (stripe) span within each period; the remainder is the transparent gap. */
const STRIPE_DUTY = 4;

/** Pattern-name key shared by the atlas mapping and the layer's `getFillPattern`. */
export const STRIPE_PATTERN_NAME = "contest-diagonal";

/** Tile edge length in atlas pixels (exported for `getFillPatternScale` world-size math). */
export const STRIPE_PATTERN_SIZE = STRIPE_TILE_PX;

/**
 * `getFillPatternScale` value for the contested layer. World tile size ≈ scale × tilePx
 * metres; 300 × 16 px ≈ 4.8 km per tile → ~2.4 km stripe pitch, legible at the county
 * register. Tunable — see module docstring.
 */
export const STRIPE_PATTERN_SCALE = 300;

/** `fillPatternMapping` entry locating the single tile within the (1-tile) atlas. */
export const STRIPE_PATTERN_MAPPING: Record<
  string,
  { x: number; y: number; width: number; height: number }
> = {
  [STRIPE_PATTERN_NAME]: { x: 0, y: 0, width: STRIPE_TILE_PX, height: STRIPE_TILE_PX },
};

/**
 * Render the raw RGBA bytes of one hatch tile. Stripe pixels are opaque white
 * (255,255,255,255); gaps are fully transparent (0,0,0,0). `(x + y) % STRIPE_PERIOD`
 * yields a 45° diagonal; seamless because `STRIPE_TILE_PX % STRIPE_PERIOD === 0`.
 */
export function renderStripeTileRGBA(): Uint8Array {
  const px = new Uint8Array(STRIPE_TILE_PX * STRIPE_TILE_PX * 4);
  for (let y = 0; y < STRIPE_TILE_PX; y++) {
    for (let x = 0; x < STRIPE_TILE_PX; x++) {
      const opaque = (x + y) % STRIPE_PERIOD < STRIPE_DUTY;
      const i = (y * STRIPE_TILE_PX + x) * 4;
      const a = opaque ? 255 : 0;
      px[i] = 255;
      px[i + 1] = 255;
      px[i + 2] = 255;
      px[i + 3] = a;
    }
  }
  return px;
}

let cachedAtlas: string | null = null;

/**
 * The hatch tile as a `data:image/png;base64,…` URI, suitable for
 * `FillStyleExtension`'s `fillPatternAtlas`. Encoded once, then memoized: repeat calls
 * return the identical string, so the layer's `fillPatternAtlas` reference is stable and
 * deck.gl never re-uploads the texture.
 */
export function stripePatternAtlas(): string {
  if (cachedAtlas === null) {
    cachedAtlas = encodePngRGBA(STRIPE_TILE_PX, STRIPE_TILE_PX, renderStripeTileRGBA());
  }
  return cachedAtlas;
}

// ---------------------------------------------------------------------------
// Minimal RGBA-PNG encoder (8-bit, colour-type 6, no interlace). DEFLATE is emitted as a
// single stored (uncompressed) block — valid zlib, no compression dependency. Sufficient
// because the tile is < 2 KiB. Loops are all bounded by fixed sizes or the tiny byte
// buffer (Power-of-10 rule 2).
// ---------------------------------------------------------------------------

const PNG_SIGNATURE = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]);

const CRC_TABLE: Uint32Array = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(bytes: Uint8Array): number {
  let crc = 0xffffffff;
  // `for…of` over a Uint8Array yields `number` (not `number | undefined`),
  // so no per-byte index guard is needed under noUncheckedIndexedAccess. The
  // table lookup is a `& 0xff`-masked read of a fixed 256-entry table — always
  // in bounds — but tsc can't prove it, so `?? 0` satisfies the checker without
  // an assertion (the fallback is provably unreachable).
  for (const byte of bytes) {
    crc = (CRC_TABLE[(crc ^ byte) & 0xff] ?? 0) ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function adler32(bytes: Uint8Array): number {
  const MOD = 65521;
  let a = 1;
  let b = 0;
  for (const byte of bytes) {
    a = (a + byte) % MOD;
    b = (b + a) % MOD;
  }
  return ((b << 16) | a) >>> 0;
}

/** Wrap raw bytes in a zlib stream with one stored DEFLATE block. */
function zlibStore(data: Uint8Array): Uint8Array {
  if (data.length >= 0xffff) {
    throw new Error(`stripePattern: tile too large for a single stored block (${data.length} B)`);
  }
  const len = data.length;
  const nlen = ~len & 0xffff;
  const out = new Uint8Array(2 + 5 + len + 4);
  out[0] = 0x78; // zlib CMF
  out[1] = 0x01; // zlib FLG (no dict, fastest); 0x7801 % 31 === 0
  out[2] = 0x01; // DEFLATE block header: BFINAL=1, BTYPE=00 (stored)
  out[3] = len & 0xff;
  out[4] = (len >>> 8) & 0xff;
  out[5] = nlen & 0xff;
  out[6] = (nlen >>> 8) & 0xff;
  out.set(data, 7);
  const adler = adler32(data);
  writeUint32BE(out, 7 + len, adler);
  return out;
}

function writeUint32BE(buf: Uint8Array, offset: number, value: number): void {
  buf[offset] = (value >>> 24) & 0xff;
  buf[offset + 1] = (value >>> 16) & 0xff;
  buf[offset + 2] = (value >>> 8) & 0xff;
  buf[offset + 3] = value & 0xff;
}

/** Assemble one PNG chunk: length + type + data + CRC(type+data). */
function pngChunk(type: string, data: Uint8Array): Uint8Array {
  const body = new Uint8Array(4 + data.length);
  body[0] = type.charCodeAt(0);
  body[1] = type.charCodeAt(1);
  body[2] = type.charCodeAt(2);
  body[3] = type.charCodeAt(3);
  body.set(data, 4);
  const out = new Uint8Array(4 + body.length + 4);
  writeUint32BE(out, 0, data.length);
  out.set(body, 4);
  writeUint32BE(out, 4 + body.length, crc32(body));
  return out;
}

function encodePngRGBA(width: number, height: number, rgba: Uint8Array): string {
  const ihdr = new Uint8Array(13);
  writeUint32BE(ihdr, 0, width);
  writeUint32BE(ihdr, 4, height);
  ihdr[8] = 8; // bit depth
  ihdr[9] = 6; // colour type: truecolour + alpha
  // ihdr[10..12] already 0: default compression / filter / interlace.

  const stride = width * 4;
  const raw = new Uint8Array(height * (stride + 1));
  for (let y = 0; y < height; y++) {
    const rowStart = y * (stride + 1);
    raw[rowStart] = 0; // per-scanline filter type: none
    raw.set(rgba.subarray(y * stride, (y + 1) * stride), rowStart + 1);
  }

  const chunks = [
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", zlibStore(raw)),
    pngChunk("IEND", new Uint8Array(0)),
  ];
  const total = PNG_SIGNATURE.length + chunks.reduce((sum, c) => sum + c.length, 0);
  const png = new Uint8Array(total);
  let offset = 0;
  png.set(PNG_SIGNATURE, offset);
  offset += PNG_SIGNATURE.length;
  for (const chunk of chunks) {
    png.set(chunk, offset);
    offset += chunk.length;
  }
  return `data:image/png;base64,${bytesToBase64(png)}`;
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}
