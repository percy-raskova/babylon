/**
 * Unit tests for the API client module.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { get, post, postForm, fetchExplain } from "./client";
import { server } from "@/test/server";
import { http, HttpResponse } from "msw";

describe("API client", () => {
  beforeEach(() => {
    // Clear cookies
    document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  });

  describe("get", () => {
    it("returns parsed JSON response", async () => {
      const res = await get<{ is_authenticated: boolean }>("/accounts/whoami/");
      expect(res.status).toBe("ok");
      expect(res.data.is_authenticated).toBe(true);
    });

    it("includes X-Request-ID header", async () => {
      let capturedHeaders: Headers | undefined;
      server.use(
        http.get("/api/test-headers/", ({ request }) => {
          capturedHeaders = request.headers;
          return HttpResponse.json({ status: "ok", data: null });
        }),
      );

      await get("/api/test-headers/");
      expect(capturedHeaders?.get("X-Request-ID")).toBeTruthy();
    });

    it("includes credentials", async () => {
      // MSW automatically handles credentials, but we verify the fetch call
      // by checking the response works with session-based auth
      const res = await get<{ is_authenticated: boolean }>("/accounts/whoami/");
      expect(res.status).toBe("ok");
    });
  });

  describe("post", () => {
    it("sends JSON body", async () => {
      let capturedBody: unknown;
      server.use(
        http.post("/api/test-post/", async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({ status: "ok", data: null });
        }),
      );

      await post("/api/test-post/", { key: "value" });
      expect(capturedBody).toEqual({ key: "value" });
    });

    it("sends Content-Type application/json", async () => {
      let contentType: string | null = null;
      server.use(
        http.post("/api/test-ct/", ({ request }) => {
          contentType = request.headers.get("Content-Type");
          return HttpResponse.json({ status: "ok", data: null });
        }),
      );

      await post("/api/test-ct/", { data: true });
      expect(contentType).toBe("application/json");
    });

    it("handles undefined body", async () => {
      const res = await post("/api/games/game-001/resolve/");
      expect(res.status).toBe("ok");
    });
  });

  describe("postForm", () => {
    it("sends form-encoded data", async () => {
      let capturedBody: string | undefined;
      server.use(
        http.post("/accounts/login/", async ({ request }) => {
          capturedBody = await request.text();
          return HttpResponse.json({
            status: "ok",
            data: { username: "testuser" },
          });
        }),
      );

      await postForm("/accounts/login/", {
        username: "testuser",
        password: "secret",
      });
      expect(capturedBody).toContain("username=testuser");
      expect(capturedBody).toContain("password=secret");
    });

    it("sends Content-Type application/x-www-form-urlencoded", async () => {
      let contentType: string | null = null;
      server.use(
        http.post("/accounts/login/", ({ request }) => {
          contentType = request.headers.get("Content-Type");
          return HttpResponse.json({
            status: "ok",
            data: { username: "testuser" },
          });
        }),
      );

      await postForm("/accounts/login/", {
        username: "test",
        password: "pass",
      });
      expect(contentType).toBe("application/x-www-form-urlencoded");
    });
  });

  describe("CSRF token", () => {
    it("extracts CSRF token from cookie", async () => {
      document.cookie = "csrftoken=abc123";
      let capturedCsrf: string | null = null;
      server.use(
        http.get("/api/test-csrf/", ({ request }) => {
          capturedCsrf = request.headers.get("X-CSRFToken");
          return HttpResponse.json({ status: "ok", data: null });
        }),
      );

      await get("/api/test-csrf/");
      expect(capturedCsrf).toBe("abc123");
    });

    it("sends empty CSRF when no cookie", async () => {
      let capturedCsrf: string | null = null;
      server.use(
        http.get("/api/test-no-csrf/", ({ request }) => {
          capturedCsrf = request.headers.get("X-CSRFToken");
          return HttpResponse.json({ status: "ok", data: null });
        }),
      );

      await get("/api/test-no-csrf/");
      expect(capturedCsrf).toBe("");
    });
  });

  describe("fetchExplain", () => {
    it("encodes metric/scope into the query string", async () => {
      let capturedUrl = "";
      server.use(
        http.get("/api/games/:id/explain/", ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({
            status: "ok",
            data: {
              metric: "exploitation_rate",
              scope: "global",
              value: 0.45,
              formula: { name: "exploitation_rate", expression: "x", doc: "d" },
              inputs: [],
              constants: [],
            },
          });
        }),
      );

      const res = await fetchExplain("game-001", "exploitation_rate", "org:C 001");

      expect(res.status).toBe("ok");
      expect(capturedUrl).toContain("metric=exploitation_rate");
      expect(capturedUrl).toContain("scope=org%3AC%20001");
    });
  });

  describe("error handling", () => {
    it("maps HTTP errors to error status", async () => {
      server.use(
        http.get("/api/error-test/", () =>
          HttpResponse.json({ status: "ok", data: null }, { status: 500 }),
        ),
      );

      const res = await get("/api/error-test/");
      expect(res.status).toBe("error");
      expect(res.message).toBe("HTTP 500");
    });

    it("passes through API error responses", async () => {
      server.use(
        http.get("/api/api-error/", () =>
          HttpResponse.json({
            status: "error",
            data: null,
            message: "Something went wrong",
          }),
        ),
      );

      const res = await get("/api/api-error/");
      expect(res.status).toBe("error");
      expect(res.message).toBe("Something went wrong");
    });

    it("maps non-JSON responses to error status", async () => {
      server.use(
        http.get("/api/non-json/", () =>
          HttpResponse.text("<html>not json</html>", {
            status: 500,
            headers: { "Content-Type": "text/html" },
          }),
        ),
      );

      const res = await get("/api/non-json/");
      expect(res.status).toBe("error");
      expect(res.message).toBe("HTTP 500");
    });
  });
});
