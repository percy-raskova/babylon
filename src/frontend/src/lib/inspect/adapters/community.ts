/**
 * `community`-kind resolver adapter — `GET /api/games/:id/community/:id/`
 * (`api.inspector_community`, `web/game/urls.py` route name
 * `inspector-community`). Architecture.md §2.4 names the endpoint as the
 * plural `/communities/` dashboard list; the live route is actually the
 * singular per-hyperedge `/community/<id>/` inspector — `resolvers.ts`
 * hits the real route (verified against `web/game/urls.py`/`api.py`), not
 * the plural dashboard.
 */

import type { InspectionNode, InspectionRef } from "@/types/inspection";
import { adaptGenericEntity } from "./genericEntity";
import type { RawEntity } from "./fields";

export function adaptCommunity(ref: InspectionRef, data: RawEntity): InspectionNode {
  return adaptGenericEntity(ref, data);
}
