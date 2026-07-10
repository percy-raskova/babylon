import { clsx, type ClassValue } from "clsx";

/**
 * Merge conditional class names.
 *
 * Ported from `web/frontend/src/lib/utils.ts` (spec-110 B2) minus
 * `tailwind-merge` — that package isn't among the deps B1 pinned for the
 * cockpit, and none of the ported components need Tailwind conflict
 * resolution (they don't combine variadic/conflicting utility classes on
 * the same element). Add `tailwind-merge` back only if a real conflict
 * shows up.
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}
