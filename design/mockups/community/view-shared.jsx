// view-shared.jsx — chrome / shared atoms used across all four artboards
// Stays aesthetically aligned with The Map (Cold Collapse v8 / Bunker Constructivism).

// ─────────────────────────────────────────────────────────────
// Numeric formatting
// ─────────────────────────────────────────────────────────────
function fmtCount(n) {
  if (n >= 1_000_000) return (n/1_000_000).toFixed(2).replace(/\.?0+$/,"") + "M";
  if (n >=     1_000) return (n/    1_000).toFixed(1).replace(/\.?0+$/,"") + "k";
  return String(n);
}
function fmtPct(n, digits = 0) { return (n * 100).toFixed(digits) + "%"; }
function fmtSigned(n, digits = 3) { return (n >= 0 ? "+" : "") + n.toFixed(digits); }

// ─────────────────────────────────────────────────────────────
// CRT overlay — same recipe as map-shell so artboards feel unified
// ─────────────────────────────────────────────────────────────
function CRTOverlay({ scanlines = true }) {
  return (
    <div style={{
      position: "absolute", inset: 0, pointerEvents: "none", mixBlendMode: "overlay",
      backgroundImage: scanlines
        ? "repeating-linear-gradient(180deg, rgba(255,255,255,.025) 0 1px, transparent 1px 3px)"
        : undefined,
      boxShadow: "inset 0 0 180px 40px rgba(0,0,0,.75), inset 0 0 60px rgba(0,0,0,.4)",
      zIndex: 50,
    }}/>
  );
}

// ─────────────────────────────────────────────────────────────
// Top bar — tick / route / breadcrumbs / org switcher
// ─────────────────────────────────────────────────────────────
function TopBar({ route, tick = 42, orgName = "Detroit Revolutionary Assembly", orgShort = "DRA" }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "9px 16px",
      background: "var(--tar)", borderBottom: "1px solid var(--rebar)",
      fontFamily: "var(--font-mono)", fontSize: 10,
      letterSpacing: ".12em", color: "var(--fog)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
        <div style={{ fontFamily: "var(--font-sans)", fontSize: 13, fontWeight: 700, letterSpacing: ".18em", color: "var(--bone)" }}>
          BABYLON <span style={{ color: "var(--ash)", fontWeight: 400 }}>· spec-070</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, textTransform: "uppercase" }}>
          {route.map((r, i) => (
            <React.Fragment key={i}>
              <span style={{ color: i === route.length-1 ? "var(--spire)" : "var(--ash)" }}>{r}</span>
              {i < route.length-1 && <span style={{ color: "var(--shroud)" }}>›</span>}
            </React.Fragment>
          ))}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
          <span style={{ color: "var(--ash)" }}>TICK</span>
          <span style={{ color: "var(--bone)", fontSize: 14, fontWeight: 700, letterSpacing: ".02em" }}>{String(tick).padStart(3,"0")}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 10px",
          background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 3 }}>
          <span style={{ width: 6, height: 6, borderRadius: 9999, background: "var(--solidarity)", boxShadow: "0 0 6px var(--solidarity)" }}/>
          <span style={{ color: "var(--bone)" }}>{orgShort}</span>
          <span style={{ color: "var(--ash)", fontFamily: "var(--font-sans)", textTransform: "none", letterSpacing: ".02em" }}>· {orgName}</span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Status banner — Article VIII.9 anchor; appears on every artboard
// ─────────────────────────────────────────────────────────────
function ConstitutionBanner({ children, kind = "info" }) {
  const tone = {
    info:    { fg: "var(--spire)",      bg: "rgba(77,217,230,.04)",  bd: "rgba(77,217,230,.22)" },
    warning: { fg: "var(--rupture)",    bg: "rgba(212,160,44,.05)",  bd: "rgba(212,160,44,.28)" },
    forbid:  { fg: "var(--laser)",      bg: "rgba(255,51,68,.04)",   bd: "rgba(255,51,68,.25)" },
  }[kind];
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10, padding: "6px 12px",
      background: tone.bg, border: `1px solid ${tone.bd}`, borderRadius: 3,
      fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: ".06em",
      color: tone.fg,
    }}>
      <span style={{ fontWeight: 700, letterSpacing: ".18em", textTransform: "uppercase" }}>Article VIII.9</span>
      <span style={{ width: 1, height: 10, background: tone.bd }}/>
      <span style={{ color: "var(--fog)", letterSpacing: ".02em" }}>{children}</span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Pane — bordered card with section label
// ─────────────────────────────────────────────────────────────
function Pane({ label, badge, children, style }) {
  return (
    <div style={{
      background: "var(--concrete)", border: "1px solid var(--rebar)", borderRadius: 5,
      display: "flex", flexDirection: "column", minHeight: 0, ...style,
    }}>
      {label && (
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "8px 12px", borderBottom: "1px solid var(--rebar)",
          fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 600,
          letterSpacing: ".22em", textTransform: "uppercase", color: "var(--ash)",
        }}>
          <span>{label}</span>
          {badge && <span style={{ color: "var(--fog)", fontWeight: 400, letterSpacing: ".12em" }}>{badge}</span>}
        </div>
      )}
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Community swatch / chip / badge
// ─────────────────────────────────────────────────────────────
function CommSwatch({ id, size = 8 }) {
  const c = COMM_BY_ID[id]; if (!c) return null;
  return (
    <span style={{
      display: "inline-block", width: size, height: size,
      background: c.color, boxShadow: `0 0 ${size}px ${c.color}55`,
      borderRadius: 2, flexShrink: 0,
    }}/>
  );
}

function CommBadge({ id, share, dense = false }) {
  const c = COMM_BY_ID[id]; if (!c) return null;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      padding: dense ? "2px 6px" : "3px 8px",
      borderRadius: 3, border: `1px solid ${c.color}44`,
      background: `${c.color}11`,
      fontFamily: "var(--font-mono)", fontSize: dense ? 9 : 10, color: "var(--bone)",
      letterSpacing: ".08em",
    }}>
      <span style={{ width: 6, height: 6, background: c.color, borderRadius: 1, boxShadow: `0 0 6px ${c.color}` }}/>
      <span>{c.label}</span>
      {share != null && <span style={{ color: "var(--fog)" }}>{fmtPct(share)}</span>}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────
// Lens / sub-tab strip — for switching analysis lenses
// ─────────────────────────────────────────────────────────────
function SubTabs({ tabs, active }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 0,
      background: "var(--tar)", borderBottom: "1px solid var(--rebar)",
      padding: "0 16px",
    }}>
      {tabs.map(t => (
        <div key={t.id} style={{
          padding: "10px 14px",
          fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 600,
          letterSpacing: ".18em", textTransform: "uppercase",
          color: t.id === active ? "var(--spire)" : "var(--ash)",
          borderBottom: t.id === active ? "1px solid var(--spire)" : "1px solid transparent",
          background: t.id === active ? "rgba(77,217,230,.04)" : "transparent",
          cursor: "default",
        }}>{t.label}</div>
      ))}
      <div style={{ flex: 1 }}/>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--shroud)", letterSpacing: ".18em" }}>
        XGI · n-ary hyperedge layer
      </div>
    </div>
  );
}
