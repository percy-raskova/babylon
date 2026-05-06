/**
 * NavRail — left icon rail for in-game navigation.
 *
 * Groups: PLAY (Briefing, Orgs, Intel, Results),
 *         VERBS (9 verb shortcuts),
 *         ANALYZE (Analysis — post-MVP).
 *
 * Active route determined from useLocation().
 */

import { NavLink } from "react-router";
import { BblTooltip } from "@/components/bbl";

interface NavRailProps {
  gameId: string;
}

interface NavItem {
  to: string;
  label: string;
  glyph: string;
  /** Match path prefix for active detection. */
  matchPrefix?: string;
}

export function NavRail({ gameId }: NavRailProps) {
  const base = `/games/${gameId}`;

  const coreItems: NavItem[] = [
    { to: base, label: "Briefing", glyph: "◐", matchPrefix: "EXACT" },
    { to: `${base}/orgs`, label: "Orgs", glyph: "◇" },
    { to: `${base}/intel`, label: "Intel", glyph: "◉" },
    { to: `${base}/results`, label: "Results", glyph: "▦" },
  ];

  const verbItems: NavItem[] = [
    { to: `${base}/actions/educate`, label: "Educate", glyph: "◐" },
    { to: `${base}/actions/mobilize`, label: "Mobilize", glyph: "◈" },
    { to: `${base}/actions/campaign`, label: "Campaign", glyph: "◢" },
    { to: `${base}/actions/aid`, label: "Aid", glyph: "◇" },
    { to: `${base}/actions/attack`, label: "Attack", glyph: "▲" },
    { to: `${base}/actions/move`, label: "Move", glyph: "→" },
    { to: `${base}/actions/investigate`, label: "Investigate", glyph: "◉" },
    { to: `${base}/actions/reproduce`, label: "Reproduce", glyph: "⬡" },
    { to: `${base}/actions/negotiate`, label: "Negotiate", glyph: "⇄" },
  ];

  const postItems: NavItem[] = [{ to: `${base}/analysis`, label: "Analysis", glyph: "◊" }];

  return (
    <nav
      className="flex w-14 shrink-0 flex-col gap-1 overflow-y-auto border-r border-soot bg-void py-2"
      aria-label="Game navigation"
    >
      {/* PLAY group */}
      <div className="flex flex-col gap-0.5 px-1">
        <span className="mb-1 text-center text-[7px] uppercase tracking-[0.3em] text-chassis">
          Play
        </span>
        {coreItems.map((item) => (
          <NavRailItem key={item.label} item={item} exact={item.matchPrefix === "EXACT"} />
        ))}
      </div>

      <div className="mx-2 my-1 border-t border-soot" />

      {/* VERBS group */}
      <div className="flex flex-col gap-0.5 px-1">
        <span className="mb-1 text-center text-[7px] uppercase tracking-[0.3em] text-chassis">
          Verbs
        </span>
        {verbItems.map((item) => (
          <NavRailItem key={item.label} item={item} />
        ))}
      </div>

      <div className="mx-2 my-1 border-t border-soot" />

      {/* ANALYZE group */}
      <div className="flex flex-col gap-0.5 px-1">
        <span className="mb-1 text-center text-[7px] uppercase tracking-[0.3em] text-chassis">
          Analyze
        </span>
        {postItems.map((item) => (
          <NavRailItem key={item.label} item={item} />
        ))}
      </div>
    </nav>
  );
}

function NavRailItem({ item, exact = false }: { item: NavItem; exact?: boolean }) {
  return (
    <BblTooltip text={item.label}>
      <NavLink
        to={item.to}
        end={exact}
        aria-label={item.label}
        className={({ isActive }) =>
          `flex h-9 w-full items-center justify-center rounded text-base transition-colors ${
            isActive
              ? "border border-gold bg-gold/10 text-gold"
              : "border border-transparent text-ash hover:bg-soot hover:text-bone"
          }`
        }
        aria-current={undefined}
        // react-router sets aria-current="page" automatically on active NavLink
      >
        <span className="text-[16px]" aria-hidden="true">
          {item.glyph}
        </span>
      </NavLink>
    </BblTooltip>
  );
}
