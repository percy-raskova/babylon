/** `node`-kind resolver adapter — `GET /api/games/:id/node/:id/`. */

import type { InspectionNode, InspectionRef } from "@/types/inspection";
import { adaptGenericEntity } from "./genericEntity";
import type { RawEntity } from "./fields";

export function adaptNode(ref: InspectionRef, data: RawEntity): InspectionNode {
  return adaptGenericEntity(ref, data);
}
