/**
 * Renders a `VerbConfig`'s `paramFields` (number/select/text) driving the
 * params object handed to `buildPayload`.
 */

import type { ParamField } from "@/lib/verbs";

interface ParamFieldsProps {
  fields: ParamField[];
  values: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
}

export function ParamFields({ fields, values, onChange }: ParamFieldsProps): React.JSX.Element {
  return (
    <div className="flex flex-col gap-2" data-testid="param-fields">
      {fields.map((field) => (
        <label key={field.key} className="flex flex-col gap-1">
          <span className="text-[9px] uppercase tracking-widest text-ash">{field.label}</span>
          {field.type === "select" && (
            <select
              value={String(values[field.key] ?? field.defaultValue)}
              onChange={(e) => onChange(field.key, e.target.value)}
              className="rounded border border-wet-steel bg-void px-2 py-1 text-[11px] text-bone"
            >
              {field.options?.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          )}
          {field.type === "number" && (
            <input
              type="number"
              min={field.min}
              max={field.max}
              value={Number(values[field.key] ?? field.defaultValue)}
              onChange={(e) => onChange(field.key, Number(e.target.value))}
              className="rounded border border-wet-steel bg-void px-2 py-1 text-[11px] text-bone"
            />
          )}
          {field.type === "text" && (
            <input
              type="text"
              value={String(values[field.key] ?? field.defaultValue)}
              onChange={(e) => onChange(field.key, e.target.value)}
              className="rounded border border-wet-steel bg-void px-2 py-1 text-[11px] text-bone"
            />
          )}
        </label>
      ))}
    </div>
  );
}
