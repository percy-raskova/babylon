/**
 * SelectorRegistry — global registry for ScriptValue selectors.
 *
 * Provides registration, lookup, and enumeration. Duplicate names throw.
 * Pure data structure — no React, no side effects.
 */

import type { ScriptValue } from "./types";

export class SelectorRegistry {
  private readonly _entries = new Map<string, ScriptValue>();

  /** Register a selector. Throws if name is already taken. */
  register(selector: ScriptValue): void {
    if (this._entries.has(selector.name)) {
      throw new Error(`Selector "${selector.name}" is already registered.`);
    }
    this._entries.set(selector.name, selector);
  }

  /** Get a selector by name. Throws if not found. */
  get(name: string): ScriptValue {
    const entry = this._entries.get(name);
    if (!entry) {
      throw new Error(`Selector "${name}" is not registered.`);
    }
    return entry;
  }

  /** Check if a selector with the given name exists. */
  has(name: string): boolean {
    return this._entries.has(name);
  }

  /** Return a sorted list of all registered selector names. */
  dump(): string[] {
    return Array.from(this._entries.keys()).sort();
  }

  /** Return the total number of registered selectors. */
  get size(): number {
    return this._entries.size;
  }
}

/** Global singleton registry. Import primitives/derived to auto-populate. */
export const selectors = new SelectorRegistry();
