/**
 * MSW node server for Vitest — see `src/test/handlers.ts`.
 */

import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
