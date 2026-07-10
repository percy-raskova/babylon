/**
 * ParamFields preview — pure presentational renderer for a VerbConfig's
 * paramFields (fields/values/onChange all arrive as props). Field sets
 * are ported verbatim from the real registry (`@/lib/verbs/reproduce.ts`,
 * `campaign.ts`) to sweep number+select-together vs. select-only.
 *
 * No shipped verb currently declares a `type: "text"` field (the union
 * supports it, nothing in the registry uses it yet) — CodenameTextField
 * exercises that render branch with an invented-but-plausible field
 * rather than leaving it uncovered; flagged in learnings.
 *
 * No cell for an empty `fields` array: the parent (`VerbForm`) never
 * mounts this component when `config.paramFields.length === 0` — it has
 * no designed empty state of its own to capture.
 */
import { ParamFields } from "babylon-cockpit";

function Frame({ children }: { children?: unknown }) {
  return <div className="w-[380px] bg-void p-3">{children as never}</div>;
}

const REPRODUCE_FIELDS = [
  {
    key: "mode",
    label: "Mode",
    type: "select",
    defaultValue: "cadre_training",
    options: [
      { value: "cadre_training", label: "Cadre Training" },
      { value: "mass_recruitment", label: "Mass Recruitment" },
    ],
  },
  { key: "cl_committed", label: "Cadre Labor Committed", type: "number", defaultValue: 0, min: 0 },
  { key: "sl_committed", label: "Sympathizer Labor Committed", type: "number", defaultValue: 0, min: 0 },
];

export function ReproduceFields() {
  return (
    <Frame>
      <ParamFields
        fields={REPRODUCE_FIELDS}
        values={{ mode: "mass_recruitment", cl_committed: 4, sl_committed: 9 }}
        onChange={() => {}}
      />
    </Frame>
  );
}

const CAMPAIGN_FIELDS = [
  {
    key: "campaign_type",
    label: "Campaign Type",
    type: "select",
    defaultValue: "PUBLIC_PRESSURE",
    options: [
      { value: "ELECTORAL", label: "Electoral" },
      { value: "LEGISLATIVE", label: "Legislative" },
      { value: "PUBLIC_PRESSURE", label: "Public Pressure" },
    ],
  },
];

export function CampaignSelectOnly() {
  return (
    <Frame>
      <ParamFields
        fields={CAMPAIGN_FIELDS}
        values={{ campaign_type: "ELECTORAL" }}
        onChange={() => {}}
      />
    </Frame>
  );
}

const CODENAME_FIELD = [
  { key: "operation_codename", label: "Operation Codename", type: "text", defaultValue: "" },
];

export function CodenameTextField() {
  return (
    <Frame>
      <ParamFields
        fields={CODENAME_FIELD}
        values={{ operation_codename: "Red November" }}
        onChange={() => {}}
      />
    </Frame>
  );
}
