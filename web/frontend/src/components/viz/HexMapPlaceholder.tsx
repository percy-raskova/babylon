/**
 * HexMapPlaceholder — SVG placeholder for the deck.gl hex map.
 *
 * Renders a styled SVG grid with animated highlight cells, representing
 * the eventual geospatial territory view. Designed for the BriefingPage
 * map canvas slot.
 */

import { TERRITORIES } from "@/fixtures/v2-mock-data";

interface HexMapPlaceholderProps {
  className?: string;
}

export function HexMapPlaceholder({ className = "" }: HexMapPlaceholderProps) {
  // Generate hex grid coordinates for a small preview
  const hexSize = 28;
  const rows = 6;
  const cols = 8;

  const hexPoints = (cx: number, cy: number, r: number) => {
    const pts: string[] = [];
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i - Math.PI / 6;
      pts.push(`${cx + r * Math.cos(angle)},${cy + r * Math.sin(angle)}`);
    }
    return pts.join(" ");
  };

  const hexes: { cx: number; cy: number; idx: number }[] = [];
  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const offsetX = row % 2 === 0 ? 0 : hexSize * 0.87;
      const cx = 40 + col * hexSize * 1.74 + offsetX;
      const cy = 30 + row * hexSize * 1.5;
      hexes.push({ cx, cy, idx: row * cols + col });
    }
  }

  // Map some territories to hexes for visual fidelity
  const hotHexes = new Set([3, 5, 10, 11, 18, 19, 25, 33, 41]);
  const playerHexes = new Set([12, 13, 20, 21, 28, 29]);

  return (
    <div
      className={`relative flex items-center justify-center overflow-hidden rounded-lg border border-soot bg-void ${className}`}
    >
      <svg viewBox="0 0 440 300" className="h-full w-full" xmlns="http://www.w3.org/2000/svg">
        {/* Grid background */}
        <defs>
          <filter id="hexGlow">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <linearGradient id="heatGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#e04040" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#e04040" stopOpacity="0.08" />
          </linearGradient>
          <linearGradient id="playerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#80b0e0" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#80b0e0" stopOpacity="0.08" />
          </linearGradient>
        </defs>

        {hexes.map((h) => {
          const isHot = hotHexes.has(h.idx);
          const isPlayer = playerHexes.has(h.idx);
          let fill = "rgba(30,30,35,0.5)";
          let stroke = "#2a2a30";
          if (isHot) {
            fill = "url(#heatGrad)";
            stroke = "#e04040";
          } else if (isPlayer) {
            fill = "url(#playerGrad)";
            stroke = "#80b0e0";
          }
          return (
            <polygon
              key={h.idx}
              points={hexPoints(h.cx, h.cy, hexSize - 2)}
              fill={fill}
              stroke={stroke}
              strokeWidth={isHot || isPlayer ? 1 : 0.5}
              filter={isHot ? "url(#hexGlow)" : undefined}
              className={isHot ? "animate-pulse" : ""}
            />
          );
        })}

        {/* Territory labels */}
        {TERRITORIES.slice(0, 4).map((t, i) => {
          const hex = hexes[playerHexes.values().next().value! + i * 2];
          if (!hex) return null;
          return (
            <text
              key={t.id}
              x={hex.cx}
              y={hex.cy + 2}
              textAnchor="middle"
              className="fill-bone text-[7px] font-semibold"
            >
              {t.name.split(" ")[0]}
            </text>
          );
        })}

        {/* Legend */}
        <g transform="translate(340, 250)">
          <rect x="0" y="0" width="8" height="8" fill="#e04040" opacity="0.4" rx="1" />
          <text x="12" y="7" className="fill-ash text-[7px]">
            High Heat
          </text>
          <rect x="0" y="14" width="8" height="8" fill="#80b0e0" opacity="0.3" rx="1" />
          <text x="12" y="21" className="fill-ash text-[7px]">
            Player Presence
          </text>
        </g>

        {/* "Situation Map" watermark */}
        <text
          x="220"
          y="290"
          textAnchor="middle"
          className="fill-chassis text-[8px] uppercase tracking-[4px]"
        >
          Situation Map · deck.gl pending
        </text>
      </svg>
    </div>
  );
}
