/** `edge`-kind resolver adapter — `GET /api/games/:id/edge/:id/`. */

import type { InspectionNode, InspectionRef } from "@/types/inspection";
import { adaptGenericEntity } from "./genericEntity";
import type { RawEntity } from "./fields";

export function adaptEdge(ref: InspectionRef, data: RawEntity): InspectionNode {
  return adaptGenericEntity(ref, data);
}
