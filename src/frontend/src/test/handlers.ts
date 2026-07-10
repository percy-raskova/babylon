/**
 * MSW request handlers — scoped to what B2's ported modules actually
 * exercise (spec-110 B2). B1 kept this empty; B2 adds only the endpoints
 * `api/client.test.ts` and `fetchVerbTargets.test.ts` need. The full stateful
 * game-loop mock (`web/frontend/src/test/handlers.ts`) belongs to B3, once
 * stores/pages that need it are ported.
 */

import { http, HttpResponse } from "msw";

export const handlers = [
  // Auth — exercised by api/client.test.ts's `get()` happy-path tests.
  http.get("/accounts/whoami/", () =>
    HttpResponse.json({
      status: "ok",
      data: { is_authenticated: true, id: 1, username: "testuser" },
    }),
  ),

  http.post("/accounts/login/", () =>
    HttpResponse.json({
      status: "ok",
      data: { username: "testuser" },
    }),
  ),

  // GET /accounts/login/ — api/client's ensureCsrfCookie() hits this to
  // obtain a fresh CSRF cookie before postForm() when none is set yet.
  http.get("/accounts/login/", () =>
    HttpResponse.text("<html><body>login</body></html>", {
      headers: { "Content-Type": "text/html" },
    }),
  ),

  // Resolve tick — exercised by api/client.test.ts's `post()` undefined-body test.
  http.post("/api/games/game-001/resolve/", () =>
    HttpResponse.json({ status: "ok", data: { resolved: true }, tick: 1 }),
  ),
];
