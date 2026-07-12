/**
 * stripePattern.test.ts — the generated hatch-tile atlas contract (spec-113 STRIPE lane,
 * DESIGN_BIBLE.md §2.1 layer 3). Verifies the tile bytes encode a seamless 45° mask and
 * that the PNG the encoder emits is well-formed (signature + IHDR dimensions decodable
 * without a WebGL/canvas context), so the atlas is a real regenerable asset, not opaque.
 */

import { describe, expect, it } from "vitest";
import {
  STRIPE_PATTERN_MAPPING,
  STRIPE_PATTERN_NAME,
  STRIPE_PATTERN_SIZE,
  renderStripeTileRGBA,
  stripePatternAtlas,
} from "./stripePattern";

/** Decode `data:image/png;base64,…` back to raw bytes for structural assertions. */
function decodeDataUriBytes(dataUri: string): Uint8Array {
  const base64 = dataUri.replace(/^data:image\/png;base64,/, "");
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function alphaAt(tile: Uint8Array, x: number, y: number): number {
  // In-bounds by construction (callers stay within the tile); `?? 0` only
  // satisfies noUncheckedIndexedAccess — the fallback is unreachable.
  return tile[(y * STRIPE_PATTERN_SIZE + x) * 4 + 3] ?? 0;
}

describe("renderStripeTileRGBA", () => {
  it("produces a square RGBA tile of the declared size", () => {
    const tile = renderStripeTileRGBA();
    expect(tile).toHaveLength(STRIPE_PATTERN_SIZE * STRIPE_PATTERN_SIZE * 4);
  });

  it("encodes stripes purely in the alpha channel (rgb is a constant white the mask hides)", () => {
    const tile = renderStripeTileRGBA();
    for (let i = 0; i < tile.length; i += 4) {
      expect(tile[i]).toBe(255);
      expect(tile[i + 1]).toBe(255);
      expect(tile[i + 2]).toBe(255);
      expect([0, 255]).toContain(tile[i + 3]);
    }
  });

  it("alpha runs along a 45° diagonal — a shifted row reproduces the row above", () => {
    const tile = renderStripeTileRGBA();
    // (x + y) hatch: alpha at (x, y) equals alpha at (x + 1, y - 1).
    for (let y = 1; y < STRIPE_PATTERN_SIZE; y++) {
      for (let x = 0; x < STRIPE_PATTERN_SIZE - 1; x++) {
        expect(alphaAt(tile, x + 1, y - 1)).toBe(alphaAt(tile, x, y));
      }
    }
  });

  it("has both opaque and transparent pixels (a real stripe, not a solid fill)", () => {
    const tile = renderStripeTileRGBA();
    const alphas = new Set<number>();
    for (let i = 3; i < tile.length; i += 4) {
      alphas.add(tile[i] ?? 0);
    }
    expect(alphas.has(0)).toBe(true);
    expect(alphas.has(255)).toBe(true);
  });

  it("tiles seamlessly — each row is periodic with a divisor of the tile width", () => {
    const tile = renderStripeTileRGBA();
    // The bitmap is texture-wrapped (repeat) by FillStyleExtension, so column 0 abuts
    // column SIZE-1. Seamlessness requires the row to be periodic with a period that
    // divides SIZE. Find the smallest such period from row 0 and assert it divides SIZE
    // (no seam) — decoupled from the private STRIPE_PERIOD constant.
    const row0 = Array.from({ length: STRIPE_PATTERN_SIZE }, (_, x) => alphaAt(tile, x, 0));
    let period = STRIPE_PATTERN_SIZE;
    for (let p = 1; p < STRIPE_PATTERN_SIZE; p++) {
      if (row0.every((v, x) => v === row0[(x + p) % STRIPE_PATTERN_SIZE])) {
        period = p;
        break;
      }
    }
    expect(STRIPE_PATTERN_SIZE % period).toBe(0);
    expect(period).toBeLessThan(STRIPE_PATTERN_SIZE); // an actual repeating stripe
  });
});

describe("stripePatternAtlas", () => {
  it("returns a base64 PNG data URI", () => {
    expect(stripePatternAtlas()).toMatch(/^data:image\/png;base64,[A-Za-z0-9+/]+=*$/);
  });

  it("emits a structurally valid PNG (signature + IHDR width/height = tile size)", () => {
    const bytes = decodeDataUriBytes(stripePatternAtlas());
    // 8-byte PNG signature.
    expect(Array.from(bytes.slice(0, 8))).toEqual([137, 80, 78, 71, 13, 10, 26, 10]);
    // First chunk is IHDR (bytes 12..16 are the ASCII type after the 4-byte length).
    expect(
      String.fromCharCode(bytes[12] ?? 0, bytes[13] ?? 0, bytes[14] ?? 0, bytes[15] ?? 0),
    ).toBe("IHDR");
    const view = new DataView(bytes.buffer);
    expect(view.getUint32(16)).toBe(STRIPE_PATTERN_SIZE); // width
    expect(view.getUint32(20)).toBe(STRIPE_PATTERN_SIZE); // height
    expect(bytes[24]).toBe(8); // bit depth
    expect(bytes[25]).toBe(6); // colour type RGBA
  });

  it("is memoized — repeat calls return the identical string reference", () => {
    expect(stripePatternAtlas()).toBe(stripePatternAtlas());
  });
});

describe("STRIPE_PATTERN_MAPPING", () => {
  it("maps the pattern name to the full single-tile atlas frame", () => {
    expect(STRIPE_PATTERN_MAPPING[STRIPE_PATTERN_NAME]).toEqual({
      x: 0,
      y: 0,
      width: STRIPE_PATTERN_SIZE,
      height: STRIPE_PATTERN_SIZE,
    });
  });
});
