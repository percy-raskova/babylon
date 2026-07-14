/**
 * `node`-kind resolver adapter — `GET /api/games/:id/node/:entityId/`
 * (architecture.md §2.4, `EngineBridge.get_inspector_node`). Every node type
 * other than `social_class` falls through to the honest generic field dump
 * (`adaptGenericEntity`) — the backend itself only special-cases
 * `social_class`, so this adapter mirrors that discrimination.
 *
 * Program 17 Wave 1 builds structured, labeled `InspectionSection`s for the
 * `social_class` case (following the exact pattern `org.ts` established for
 * orgs): the wage-pairing fields, an "Ideology" section adding (W1.4) the
 * per-class ternary consciousness (`readConsciousness`, reused verbatim from
 * `org.ts`'s pattern — same bridge-computed `{revolutionary, liberal,
 * fascist}` shape) plus agitation, an "Imperial Apologetics" section for the
 * narrative pair, and (W1.6) an "Imperial Circuit" section carrying the
 * 4-node mini-Sankey `circuit_flows` — attached ONLY when the backend sent a
 * non-empty circuit (a role/hop a scenario does not seed is honestly absent,
 * never a fabricated placeholder — Constitution III.11).
 */

import type {
  CircuitFlows,
  InspectionNode,
  InspectionRef,
  InspectionRow,
  InspectionSection,
} from "@/types/inspection";
import { adaptGenericEntity } from "./genericEntity";
import { readConsciousness, readNumberField, readStringField, type RawEntity } from "./fields";

const CONSCIOUSNESS_COLORS = {
  revolutionary: "text-laser",
  liberal: "text-cadre",
  fascist: "text-rupture",
} as const;

/** Narrow `data.circuit_flows` to a usable shape, or `null` (absent/malformed). */
function readCircuitFlows(data: RawEntity): CircuitFlows | null {
  const raw = data.circuit_flows;
  if (raw === null || raw === undefined || typeof raw !== "object") return null;
  const { nodes, links } = raw as RawEntity;
  if (!Array.isArray(nodes) || !Array.isArray(links)) return null;
  return { nodes, links } as CircuitFlows;
}

function socialClassSections(data: RawEntity): InspectionSection[] {
  const consciousness = readConsciousness(data);
  const circuitFlows = readCircuitFlows(data);

  const mainRows: InspectionRow[] = [
    { label: "Role", value: readStringField(data, "role"), format: "raw" },
    { label: "Wealth", value: readNumberField(data, "wealth"), format: "decimal2" },
    { label: "Core Wages", value: readNumberField(data, "core_wages"), format: "decimal2" },
    {
      label: "Imperial Rent Gap",
      value: readNumberField(data, "imperial_rent_gap"),
      format: "decimal2",
    },
    {
      label: "Unearned Increment",
      value: readNumberField(data, "unearned_increment"),
      format: "decimal2",
    },
    { label: "PPP Multiplier", value: readNumberField(data, "ppp_multiplier"), format: "decimal2" },
    {
      label: "Effective Wealth",
      value: readNumberField(data, "effective_wealth"),
      format: "decimal2",
    },
    { label: "Population", value: readNumberField(data, "population"), format: "integer" },
    { label: "Organization", value: readNumberField(data, "organization"), format: "decimal3" },
    {
      label: "Repression Faced",
      value: readNumberField(data, "repression_faced"),
      format: "decimal3",
    },
    {
      label: "Subsistence Threshold",
      value: readNumberField(data, "subsistence_threshold"),
      format: "decimal3",
    },
    { label: "Inequality", value: readNumberField(data, "inequality"), format: "decimal2" },
    {
      label: "Class Position",
      value: readStringField(data, "class_position"),
      format: "raw",
      mock: data.class_position_mock === true,
    },
  ];

  const ideologyRows: InspectionRow[] = [
    {
      label: "Consciousness",
      value: null,
      format: "raw",
      composition: consciousness
        ? [
            {
              key: "Revolutionary",
              value: consciousness.revolutionary,
              color: CONSCIOUSNESS_COLORS.revolutionary,
            },
            { key: "Liberal", value: consciousness.liberal, color: CONSCIOUSNESS_COLORS.liberal },
            { key: "Fascist", value: consciousness.fascist, color: CONSCIOUSNESS_COLORS.fascist },
          ]
        : undefined,
    },
    {
      label: "Class Consciousness",
      value: readNumberField(data, "class_consciousness"),
      format: "decimal3",
    },
    {
      label: "National Identity",
      value: readNumberField(data, "national_identity"),
      format: "decimal3",
    },
    { label: "Agitation", value: readNumberField(data, "agitation"), format: "decimal3" },
  ];

  const apologistRows: InspectionRow[] = [
    { label: "Apologist Claim", value: readStringField(data, "apologist_claim"), format: "raw" },
    {
      label: "Apologist Refutation",
      value: readStringField(data, "apologist_refutation"),
      format: "raw",
    },
  ];

  const sections: InspectionSection[] = [
    { rows: mainRows },
    { label: "Ideology", rows: ideologyRows },
    { label: "Imperial Apologetics", rows: apologistRows },
  ];

  if (circuitFlows !== null && circuitFlows.nodes.length > 0) {
    sections.push({
      label: "Imperial Circuit",
      rows: [{ label: "Value Flow", value: null, format: "raw", circuitFlows }],
    });
  }

  return sections;
}

export function adaptNode(ref: InspectionRef, data: RawEntity): InspectionNode {
  if (data.type !== "social_class") {
    return adaptGenericEntity(ref, data);
  }
  const name = readStringField(data, "name");
  return {
    ref,
    title: ref.label ?? name ?? ref.id,
    sections: socialClassSections(data),
  };
}
