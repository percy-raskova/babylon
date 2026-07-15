/**
 * NetworkGraphCanvas — thin imperative wrapper mounting a sigma.js renderer
 * over a pre-built graphology `Graph` (AW4-R2). Sigma has no React binding
 * in this repo's dependency set (`@react-sigma/*` is not installed; only
 * bare `sigma` + `graphology` were pre-provisioned) so this follows the
 * same imperative-construct-in-a-`useEffect`/`kill()`-on-cleanup pattern
 * any non-React-native canvas/WebGL library needs (mirrors deck.gl's own
 * React binding internally, just without one supplied for us here).
 *
 * `graph` already carries its own `x`/`y`/`size`/`color` node attributes
 * and `color`/`size` edge attributes (`buildOrgNetworkGraph.ts`) — sigma
 * renders exactly that static, pre-laid-out picture. No sigma settings
 * here enable camera auto-animation or force-simulation ticking
 * (DESIGN_BIBLE §11 law 2/3: qualities cut, one motion budget per tick —
 * this lens isn't the principal contradiction, so it stays static/settled).
 */

import { useEffect, useRef } from "react";
import Sigma from "sigma";
import type Graph from "graphology";

interface Props {
  graph: Graph;
}

export function NetworkGraphCanvas({ graph }: Props): React.JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const renderer = new Sigma(graph, container);
    return () => renderer.kill();
  }, [graph]);

  return <div ref={containerRef} className="h-full w-full" data-testid="network-graph-canvas" />;
}
