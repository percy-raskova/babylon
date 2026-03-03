/**
 * Custom render helper — wraps components with any required providers.
 *
 * Currently no global providers are needed (Zustand stores are module-level),
 * but this provides a single place to add them when needed.
 */

import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";

export function renderWithProviders(ui: ReactElement, options?: Omit<RenderOptions, "wrapper">) {
  return render(ui, { ...options });
}

export { render };
