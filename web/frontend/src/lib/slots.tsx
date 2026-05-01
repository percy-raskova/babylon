/**
 * Slot composition primitive — named content slots with fallback support.
 *
 * <Slots> provides named content; <Slot> renders the named content or a fallback.
 * Nested <Slots> providers compose: inner overrides outer for matching keys.
 */

import { createContext, useContext, type ReactNode } from "react";

type SlotMap = Record<string, ReactNode>;

const SlotContext = createContext<SlotMap>({});

/**
 * Provide named content to descendant <Slot> components.
 * Nested providers merge with inner keys taking precedence.
 */
export function Slots({ children, ...slots }: { children: ReactNode } & SlotMap) {
  const parent = useContext(SlotContext);
  const merged = { ...parent, ...slots };
  return <SlotContext.Provider value={merged}>{children}</SlotContext.Provider>;
}

/**
 * Render the content for a named slot, or `fallback` if no content was provided.
 */
export function Slot({ name, fallback = null }: { name: string; fallback?: ReactNode }) {
  const slots = useContext(SlotContext);
  return <>{slots[name] ?? fallback}</>;
}
