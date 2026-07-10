/**
 * VerbForm preview — one verb's TargetPicker + ParamFields + submit
 * button. `config`/`snapshot`/`submitting` are props, but eligible
 * targets for endpoint-sourced verbs (everything except campaign) come
 * from a live `fetchVerbTargets` call inside `useVerbTargets` — there is
 * no store slice to seed past it (unlike the panels), and the fetch
 * outcome against this static capture harness isn't something a preview
 * should depend on (rule 9/10: in-flight or race-y fetch states are
 * skipped, seeding past preferred). So every cell here uses `campaign`
 * (`targetsSource: "snapshot"`, a pure `useMemo` over the snapshot — no
 * effect, no fetch) — the ONE verb whose full form is deterministic to
 * render statically — config object ported verbatim from
 * `@/lib/verbs/campaign.ts`.
 *
 * SelfTargetNoPicker demonstrates the `targetRequired: false` branch
 * (real production value on `reproduce`) via a config ported verbatim
 * from `@/lib/verbs/reproduce.ts` with ONE deliberate override:
 * `targetsSource: "snapshot"` in place of reproduce's real endpoint fetch
 * — same rationale as above, swapping the network dependency for the
 * synchronous snapshot path so "zero eligible self-targets" renders
 * deterministically instead of racing a live request. Flagged in
 * learnings.
 */
import { VerbForm } from "babylon-cockpit";

function Frame({ children }: { children?: unknown }) {
  return <div className="w-[380px] bg-void p-3">{children as never}</div>;
}

const WAYNE_COUNTY_SNAPSHOT = {
  tick: 104,
  territories: [
    { id: "territory-26163-hamtramck", name: "Hamtramck" },
    { id: "territory-26163-river-rouge", name: "River Rouge" },
  ],
  hyperedges: [{ id: "hx-uaw-tenants", label: "Auto Workers ↔ Tenants Union" }],
};

const CAMPAIGN_CONFIG = {
  verb: "campaign",
  label: "Campaign",
  description: "Launch a political campaign to build mass support and influence public discourse.",
  targetsSource: "snapshot",
  parseTargets: () => [],
  paramFields: [
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
  ],
  buildPayload: (orgId: string, targetId: string | null, params: Record<string, unknown>) => ({
    org_id: orgId,
    target_id: targetId ?? "",
    campaign_type: String(params.campaign_type ?? "PUBLIC_PRESSURE"),
  }),
};

export function FullFormCampaign() {
  return (
    <Frame>
      <VerbForm
        gameId="g-wayne-county"
        orgId="org-uaw-local-600"
        verb="campaign"
        config={CAMPAIGN_CONFIG}
        snapshot={WAYNE_COUNTY_SNAPSHOT}
        submitting={false}
        onSubmit={() => {}}
      />
    </Frame>
  );
}

export function Submitting() {
  return (
    <Frame>
      <VerbForm
        gameId="g-wayne-county"
        orgId="org-uaw-local-600"
        verb="campaign"
        config={CAMPAIGN_CONFIG}
        snapshot={WAYNE_COUNTY_SNAPSHOT}
        submitting={true}
        onSubmit={() => {}}
      />
    </Frame>
  );
}

const REPRODUCE_CONFIG_SNAPSHOT_OVERRIDE = {
  verb: "reproduce",
  label: "Reproduce",
  description: "Maintain and reproduce organizational capacity through internal development.",
  targetRequired: false,
  // Override — see file docstring. Real reproduce.ts has no targetsSource
  // (defaults to the live endpoint fetch).
  targetsSource: "snapshot",
  parseTargets: () => [],
  paramFields: [
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
  ],
  buildPayload: (orgId: string, targetId: string | null, params: Record<string, unknown>) => ({
    org_id: orgId,
    ...(targetId ? { target_id: targetId } : {}),
    params: {
      mode: String(params.mode ?? "cadre_training"),
      cl_committed: Number(params.cl_committed ?? 0),
      sl_committed: Number(params.sl_committed ?? 0),
    },
  }),
};

export function SelfTargetNoPicker() {
  return (
    <Frame>
      <VerbForm
        gameId="g-wayne-county"
        orgId="org-uaw-local-600"
        verb="reproduce"
        config={REPRODUCE_CONFIG_SNAPSHOT_OVERRIDE}
        snapshot={{ tick: 104, territories: [], hyperedges: [] }}
        submitting={false}
        onSubmit={() => {}}
      />
    </Frame>
  );
}
