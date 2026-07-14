/**
 * API client for communicating with the Django backend.
 *
 * Handles CSRF tokens, session cookies, and the standard response envelope.
 */

import type { ApiResponse } from "@/types/game";
import { endpoints } from "@/api/endpoints";
import type { ExplainResponse } from "@/types/inspection";
import { getCorrelationId, createLogger } from "@/utils/logger";

const log = createLogger("ApiClient");

/** Extract the CSRF token from the cookie jar. */
function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match?.[1] ?? "";
}

/** Ensure Django has issued a CSRF cookie before unsafe requests. */
async function ensureCsrfCookie(): Promise<void> {
  if (getCsrfToken()) {
    return;
  }

  await fetch("/accounts/login/", {
    method: "GET",
    credentials: "include",
  });
}

/** Base fetch wrapper with CSRF and credentials. */
async function request<T>(url: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-CSRFToken": getCsrfToken(),
    "X-Request-ID": getCorrelationId(),
    ...(options.headers as Record<string, string> | undefined),
  };

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch (error) {
    log.warn("Network error", { url, error });
    return {
      status: "error",
      data: null as T,
      message: "Network error",
    };
  }

  let body: ApiResponse<T>;
  try {
    body = (await response.json()) as ApiResponse<T>;
  } catch (error) {
    log.warn("Non-JSON response", { url, status: response.status, error });
    return {
      status: "error",
      data: null as T,
      message: !response.ok ? `HTTP ${response.status}` : "Invalid server response",
      http_status: response.status,
    };
  }

  if (!response.ok && body.status !== "error") {
    log.warn("HTTP error", { url, status: response.status });
    return {
      status: "error",
      data: body.data,
      message: `HTTP ${response.status}`,
      http_status: response.status,
    };
  }

  if (body.status === "error") {
    log.warn("API error", { url, message: body.message });
    // Only enrich the already-error-shaped envelope with the raw HTTP
    // status (needed to distinguish e.g. 409 from 5xx — Django's `_error()`
    // envelope carries no status code of its own). Deliberately NOT done
    // for "ok" bodies: some endpoints return a flat, unenveloped body on
    // success (no `status` field at all — see `fetchVerbTargets`'s
    // `res.data ?? res` fallback), and splicing an extra key onto that
    // flat body would corrupt it.
    return { ...body, http_status: response.status };
  }

  return body;
}

/** GET request. */
export async function get<T>(url: string): Promise<ApiResponse<T>> {
  return request<T>(url, { method: "GET" });
}

/** POST request with JSON body. */
export async function post<T>(url: string, data?: unknown): Promise<ApiResponse<T>> {
  return request<T>(url, {
    method: "POST",
    body: data !== undefined ? JSON.stringify(data) : undefined,
  });
}

/** POST form-encoded data (for Django login). */
export async function postForm<T>(
  url: string,
  data: Record<string, string>,
): Promise<ApiResponse<T>> {
  await ensureCsrfCookie();

  const formBody = new URLSearchParams(data).toString();
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-CSRFToken": getCsrfToken(),
    },
    credentials: "include",
    body: formBody,
  });

  return response.json();
}

/**
 * `GET /api/games/{id}/explain/?metric=<name>&scope=<scope>` — formula
 * provenance for one metric (spec-113 Lane C/D, architecture.md §2.4).
 * `scope` grammar: `"global"` | `"hex:<h3>"` | `"org:<id>"`.
 */
export async function fetchExplain(
  gameId: string,
  metric: string,
  scope: string,
): Promise<ApiResponse<ExplainResponse>> {
  return get<ExplainResponse>(
    `${endpoints.explain.path({ id: gameId })}?metric=${encodeURIComponent(metric)}&scope=${encodeURIComponent(scope)}`,
  );
}
