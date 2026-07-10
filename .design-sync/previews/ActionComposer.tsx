/**
 * ActionComposer preview — Right Dock tab 1: acting-org selector + the
 * flat 9-verb grid + the selected verb's form. Store-driven (reads
 * `world.snapshot.organizations` + `actions.{pending,submitting,error}`);
 * each cell seeds the store inside its own wrapper, always spreading the
 * existing slice.
 *
 * `verb`/`orgId` selection is internal `useState` with no prop override —
 * a real mount always starts with no verb selected, and this capture
 * harness has no click simulation (screenshots only) — so the three
 * store-only cells below show every state reachable via props+store on a
 * real `<ActionComposer/>` mount (empty / multi-org+grid / pending queue).
 *
 * FullFormComposed depicts "org selected, verb selected, targets visible"
 * — the state ActionComposer reaches only after a click — by composing
 * its own real children (`VerbGrid` + `VerbForm`, verb="campaign", the
 * one verb whose targets resolve synchronously from the snapshot — see
 * VerbForm.tsx's docstring) inside the same container classes
 * ActionComposer itself renders. This is NOT a literal `<ActionComposer/>`
 * mount (its internal verb state can't be seeded from outside); it's the
 * compound scene built from the real constituent components, which is the
 * only way to show this reachable state statically.
 *
 * needs cfg.overrides.ActionComposer = {cardMode: "single", primaryStory:
 * "FullFormComposed"} — see learnings (store-driven, cells seed different
 * world/actions state, so the combined default card would lie).
 */
import { ActionComposer, VerbGrid, VerbForm, useStore } from "babylon-cockpit";

function Frame({ children }: { children?: unknown }) {
  return <div className="w-[380px] bg-void p-3">{children as never}</div>;
}

export function NoPlayerOrgs() {
  useStore.setState((s: any) => ({
    world: {
      ...s.world,
      snapshot: {
        tick: 104,
        organizations: [
          { id: "org-motor-city-holdings", name: "Motor City Holdings", player_controlled: false },
        ],
      },
    },
    actions: { ...s.actions, pending: [], submitting: false, error: null },
  }));
  return (
    <Frame>
      <ActionComposer gameId="g-wayne-county" />
    </Frame>
  );
}

export function MultiOrgSelector() {
  useStore.setState((s: any) => ({
    world: {
      ...s.world,
      snapshot: {
        tick: 104,
        organizations: [
          { id: "org-uaw-local-600", name: "UAW Local 600", player_controlled: true },
          { id: "org-48210-block-club", name: "48210 Block Club", player_controlled: true },
        ],
      },
    },
    actions: { ...s.actions, pending: [], submitting: false, error: null },
  }));
  return (
    <Frame>
      <ActionComposer gameId="g-wayne-county" />
    </Frame>
  );
}

export function PendingQueued() {
  useStore.setState((s: any) => ({
    world: {
      ...s.world,
      snapshot: {
        tick: 104,
        organizations: [{ id: "org-uaw-local-600", name: "UAW Local 600", player_controlled: true }],
      },
    },
    actions: {
      ...s.actions,
      pending: [
        {
          id: "pact-1",
          verb: "educate",
          orgId: "org-uaw-local-600",
          targetId: "comm-hamtramck-tenants",
          submittedAtTick: 104,
        },
        {
          id: "pact-2",
          verb: "aid",
          orgId: "org-uaw-local-600",
          targetId: "org-detroit-dsa",
          submittedAtTick: 104,
        },
      ],
      submitting: false,
      error: null,
    },
  }));
  return (
    <Frame>
      <ActionComposer gameId="g-wayne-county" />
    </Frame>
  );
}

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

export function FullFormComposed() {
  return (
    <Frame>
      <div className="flex flex-col gap-3 p-2">
        <VerbGrid selectedVerb="campaign" onSelect={() => {}} />
        <VerbForm
          gameId="g-wayne-county"
          orgId="org-uaw-local-600"
          verb="campaign"
          config={CAMPAIGN_CONFIG}
          snapshot={{
            tick: 104,
            territories: [
              { id: "territory-26163-hamtramck", name: "Hamtramck" },
              { id: "territory-26163-river-rouge", name: "River Rouge" },
            ],
            hyperedges: [{ id: "hx-uaw-tenants", label: "Auto Workers ↔ Tenants Union" }],
          }}
          submitting={false}
          onSubmit={() => {}}
        />
      </div>
    </Frame>
  );
}
