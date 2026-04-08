/**
 * Color Scale Utility for HexMap
 * Maps metric values to the constitutional palette colors.
 */

// Constitutional Palette Colors
const COLORS = {
  CRIMSON: "#8b0000",
  GOLD: "#daa520",
  ASH: "#808080",
  SILVER: "#c0c0c0",
  BLOOD_VOID: "#1a0005",
};

/**
 * Converts a hex code to an RGB array.
 */
function hexToRgb(hex: string): [number, number, number] {
  let parsedHex = hex.replace(/^#/, "");
  if (parsedHex.length === 3) {
    parsedHex = parsedHex
      .split("")
      .map((c) => c + c)
      .join("");
  }
  const num = parseInt(parsedHex, 16);
  return [num >> 16, (num >> 8) & 255, num & 255];
}

/**
 * Converts an RGB array to a hex code.
 */
function rgbToHex(rgb: number[]): string {
  return (
    "#" +
    rgb
      .map((x) => {
        const hex = Math.round(x).toString(16);
        return hex.length === 1 ? "0" + hex : hex;
      })
      .join("")
  );
}

/**
 * Interpolates between two colors given a fraction (0 to 1).
 */
function interpolateColor(color1: string, color2: string, factor: number): string {
  if (factor <= 0) return color1;
  if (factor >= 1) return color2;
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);
  const result = rgb1.map((c, i) => c + factor * ((rgb2[i] ?? 0) - c));
  return rgbToHex(result);
}

/**
 * Interpolates over a gradient array of colors.
 */
function interpolateGradient(colors: string[], factor: number): string {
  if (!colors.length) return "#808080";
  if (colors.length === 1) return colors[0]!;
  if (factor <= 0) return colors[0]!;
  if (factor >= 1) return colors[colors.length - 1]!;

  const numSegments = colors.length - 1;
  const segment = Math.floor(factor * numSegments);
  const startColor = colors[segment] || "#808080";
  const endColor = colors[segment + 1] || "#808080";
  const segmentFactor = factor * numSegments - segment;

  return interpolateColor(startColor, endColor, segmentFactor);
}

/**
 * metricToColor
 * @param {number} value - The actual metric value.
 * @param {number} min - The absolute minimum observed metric.
 * @param {number} max - The absolute maximum observed metric.
 * @param {string} metricName - The identifier of the metric field.
 * @returns {string} Hex color string.
 */
export function metricToColor(value: number, min: number, max: number, metricName: string): string {
  // Edge case: min == max avoids division by block
  let factor = 0;
  if (max > min) {
    factor = (value - min) / (max - min);
  } else {
    factor = 0.5; // If all values are the same, pick the midpoint of the gradient
  }

  // Bound factor between 0.0 and 1.0 just in case
  factor = Math.max(0, Math.min(1, factor));

  switch (metricName) {
    case "profit_rate":
      // CRIMSON (#8b0000) at low → GOLD (#daa520) at high
      return interpolateGradient([COLORS.CRIMSON, COLORS.GOLD], factor);

    case "exploitation_rate":
      // GOLD at low → CRIMSON at high (inverted)
      return interpolateGradient([COLORS.GOLD, COLORS.CRIMSON], factor);

    case "heat":
      // ASH (#808080) at low → CRIMSON at mid → GOLD at high
      return interpolateGradient([COLORS.ASH, COLORS.CRIMSON, COLORS.GOLD], factor);

    case "occ":
    case "imperial_rent":
      // ASH at low → SILVER (#c0c0c0) at high
      return interpolateGradient([COLORS.ASH, COLORS.SILVER], factor);

    case "org_presence":
      // BLOOD_VOID (#1a0005) at 0 → GOLD at max
      return interpolateGradient([COLORS.BLOOD_VOID, COLORS.GOLD], factor);

    default:
      return COLORS.ASH; // Safe fallback
  }
}
