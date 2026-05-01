/**
 * NavigationStrip — horizontal nav links to Orgs, Actions, and Intel pages.
 */

import { Link, useParams } from "react-router";

export function NavigationStrip() {
  const { id: gameId = "" } = useParams<{ id: string }>();

  const links = [
    { to: `/games/${gameId}/orgs`, label: "Organizations" },
    { to: `/games/${gameId}/actions/educate`, label: "Actions" },
    { to: `/games/${gameId}/intel`, label: "Intel" },
    { to: `/games/${gameId}/log`, label: "Log" },
  ];

  return (
    <nav className="flex shrink-0 gap-1 px-3 py-1" aria-label="Game navigation">
      {links.map(({ to, label }) => (
        <Link
          key={to}
          to={to}
          className="rounded border border-wet-concrete px-3 py-1 text-xs font-semibold uppercase tracking-wider text-silver transition-colors hover:border-gold hover:text-gold"
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}
