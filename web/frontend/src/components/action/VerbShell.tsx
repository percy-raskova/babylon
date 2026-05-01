/**
 * VerbShell — generic action form layout driven by VerbConfig.
 *
 * Uses Slots for chrome areas (title, preview, status).
 * Renders org picker, target picker, param fields, and submit button.
 */

import type { ReactNode } from "react";
import { Slots, Slot } from "@/lib/slots";
import type { VerbConfig, VerbTarget, ParamField } from "@/lib/verbs";
import type { OrgState } from "@/types/game";

interface VerbShellProps {
  config: VerbConfig;
  orgs: OrgState[];
  orgsLoaded: boolean;
  selectedOrgId: string;
  onOrgChange: (id: string) => void;
  targets: VerbTarget[];
  loadingTargets: boolean;
  selectedTargetId: string;
  onTargetChange: (id: string) => void;
  params: Record<string, unknown>;
  onParamChange: (key: string, value: unknown) => void;
  submitting: boolean;
  onSubmit: (e: React.FormEvent) => void;
  error?: string | null;
  children?: ReactNode;
}

export function VerbShell({
  config,
  orgs,
  orgsLoaded,
  selectedOrgId,
  onOrgChange,
  targets,
  loadingTargets,
  selectedTargetId,
  onTargetChange,
  params,
  onParamChange,
  submitting,
  onSubmit,
  error,
  children,
}: VerbShellProps) {
  const needsTarget = config.verb !== "reproduce";

  return (
    <Slots>
      <form onSubmit={onSubmit} className="flex flex-col gap-6">
        {error && <p className="text-crimson">{error}</p>}

        {/* Org Picker */}
        <OrgPicker
          orgs={orgs}
          orgsLoaded={orgsLoaded}
          selectedOrgId={selectedOrgId}
          onOrgChange={onOrgChange}
          disabled={submitting}
        />

        {/* Target Picker */}
        {needsTarget && (
          <TargetPicker
            config={config}
            targets={targets}
            loadingTargets={loadingTargets}
            selectedTargetId={selectedTargetId}
            onTargetChange={onTargetChange}
            disabled={submitting}
          />
        )}

        {/* Dynamic Param Fields */}
        {config.paramFields.map((field) => (
          <ParamFieldInput
            key={field.key}
            field={field}
            value={params[field.key] ?? field.defaultValue}
            onChange={(val) => onParamChange(field.key, val)}
            disabled={submitting}
          />
        ))}

        {/* Slot: preview area */}
        <Slot name="preview" />

        {/* Submit */}
        <button
          type="submit"
          disabled={submitting || !selectedOrgId || (needsTarget && !selectedTargetId)}
          className="mt-4 rounded bg-gold py-2 font-bold text-void hover:bg-yellow-600 disabled:opacity-50"
        >
          {submitting ? "Submitting..." : "Submit Action"}
        </button>
      </form>
      {children}
    </Slots>
  );
}

// -----------------------------------------------------------------------
// OrgPicker — organization selector
// -----------------------------------------------------------------------

function OrgPicker({
  orgs,
  orgsLoaded,
  selectedOrgId,
  onOrgChange,
  disabled,
}: {
  orgs: OrgState[];
  orgsLoaded: boolean;
  selectedOrgId: string;
  onOrgChange: (id: string) => void;
  disabled: boolean;
}) {
  return (
    <div>
      <label
        htmlFor="org-select"
        className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
      >
        Select Organization
      </label>
      {!orgsLoaded ? (
        <p className="text-sm text-silver">Loading...</p>
      ) : (
        <select
          id="org-select"
          value={selectedOrgId}
          onChange={(e) => onOrgChange(e.target.value)}
          className="w-full rounded border border-wet-concrete bg-void p-2 text-bone"
          disabled={disabled}
        >
          {orgs.map((org) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------
// TargetPicker — target selector with optgroup support
// -----------------------------------------------------------------------

function TargetPicker({
  config,
  targets,
  loadingTargets,
  selectedTargetId,
  onTargetChange,
  disabled,
}: {
  config: VerbConfig;
  targets: VerbTarget[];
  loadingTargets: boolean;
  selectedTargetId: string;
  onTargetChange: (id: string) => void;
  disabled: boolean;
}) {
  const suffix = config.verb === "educate" ? " Territory (Community)" : "";

  // Group targets for optgroup rendering
  const groups = groupTargets(targets);
  const hasGroups = groups.size > 1 || (groups.size === 1 && !groups.has(""));

  if (loadingTargets) {
    return (
      <div>
        <label
          htmlFor="target-select"
          className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
        >
          Select Target{suffix}
        </label>
        <p className="text-sm text-silver">Loading targets...</p>
      </div>
    );
  }

  if (targets.length === 0) {
    return (
      <div>
        <label
          htmlFor="target-select"
          className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
        >
          Select Target{suffix}
        </label>
        <p className="text-sm text-silver">No targets available.</p>
      </div>
    );
  }

  return (
    <div>
      <label
        htmlFor="target-select"
        className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
      >
        Select Target{suffix}
      </label>
      <select
        id="target-select"
        value={selectedTargetId}
        onChange={(e) => onTargetChange(e.target.value)}
        className="w-full rounded border border-wet-concrete bg-void p-2 text-bone"
        disabled={disabled}
      >
        {hasGroups ? <GroupedOptions groups={groups} /> : <FlatOptions targets={targets} />}
      </select>
    </div>
  );
}

function GroupedOptions({ groups }: { groups: Map<string, VerbTarget[]> }) {
  return (
    <>
      {Array.from(groups.entries()).map(([group, items]) => (
        <optgroup key={group} label={group}>
          {items.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </optgroup>
      ))}
    </>
  );
}

function FlatOptions({ targets }: { targets: VerbTarget[] }) {
  return (
    <>
      {targets.map((t) => (
        <option key={t.id} value={t.id}>
          {t.label}
        </option>
      ))}
    </>
  );
}

function groupTargets(targets: VerbTarget[]): Map<string, VerbTarget[]> {
  const groups = new Map<string, VerbTarget[]>();
  for (const t of targets) {
    const g = t.group ?? "";
    const list = groups.get(g) ?? [];
    list.push(t);
    groups.set(g, list);
  }
  return groups;
}

// -----------------------------------------------------------------------
// ParamFieldInput — renders a form field from a ParamField definition
// -----------------------------------------------------------------------

function ParamFieldInput({
  field,
  value,
  onChange,
  disabled,
}: {
  field: ParamField;
  value: unknown;
  onChange: (val: unknown) => void;
  disabled: boolean;
}) {
  const id = `param-${field.key}`;
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-2 block text-sm font-semibold tracking-wider text-ash uppercase"
      >
        {field.label}
      </label>
      <ParamFieldControl
        id={id}
        field={field}
        value={value}
        onChange={onChange}
        disabled={disabled}
      />
    </div>
  );
}

function ParamFieldControl({
  id,
  field,
  value,
  onChange,
  disabled,
}: {
  id: string;
  field: ParamField;
  value: unknown;
  onChange: (val: unknown) => void;
  disabled: boolean;
}) {
  const inputClass = "w-full rounded border border-wet-concrete bg-void p-2 text-bone";

  if (field.type === "select") {
    return (
      <select
        id={id}
        value={String(value)}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
        disabled={disabled}
      >
        {field.options?.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    );
  }

  if (field.type === "number") {
    return (
      <input
        id={id}
        type="number"
        min={field.min}
        max={field.max}
        value={Number(value) || 0}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className={inputClass}
        disabled={disabled}
      />
    );
  }

  return (
    <input
      id={id}
      type="text"
      value={String(value)}
      onChange={(e) => onChange(e.target.value)}
      className={inputClass}
      disabled={disabled}
    />
  );
}
