/**
 * API client for communicating with the Django backend.
 *
 * Handles CSRF tokens, session cookies, and the standard response envelope.
 */

import type { ApiResponse } from "@/types/game";

/** Extract the CSRF token from the cookie jar. */
function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match?.[1] ?? "";
}

/** Base fetch wrapper with CSRF and credentials. */
async function request<T>(
  url: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-CSRFToken": getCsrfToken(),
    ...(options.headers as Record<string, string> | undefined),
  };

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: "include",
  });

  const body: ApiResponse<T> = await response.json();

  if (!response.ok && body.status !== "error") {
    return {
      status: "error",
      data: body.data,
      message: `HTTP ${response.status}`,
    };
  }

  return body;
}

/** GET request. */
export async function get<T>(url: string): Promise<ApiResponse<T>> {
  return request<T>(url, { method: "GET" });
}

/** POST request with JSON body. */
export async function post<T>(
  url: string,
  data?: unknown,
): Promise<ApiResponse<T>> {
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
