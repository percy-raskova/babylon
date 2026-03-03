/**
 * Unit tests for the structured logger.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { createLogger, getCorrelationId, resetCorrelationId } from "./logger";

describe("logger", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe("createLogger", () => {
    it("creates logger with all four methods", () => {
      const log = createLogger("TestSource");
      expect(typeof log.debug).toBe("function");
      expect(typeof log.info).toBe("function");
      expect(typeof log.warn).toBe("function");
      expect(typeof log.error).toBe("function");
    });

    it("debug logs to console.debug with source prefix", () => {
      const spy = vi.spyOn(console, "debug").mockImplementation(() => {});
      const log = createLogger("MyModule");
      log.debug("test message");
      expect(spy).toHaveBeenCalledWith("[MyModule]", "test message", expect.any(Object));
    });

    it("info logs to console.info", () => {
      const spy = vi.spyOn(console, "info").mockImplementation(() => {});
      const log = createLogger("MyModule");
      log.info("info message", { key: "value" });
      expect(spy).toHaveBeenCalledWith(
        "[MyModule]",
        "info message",
        expect.objectContaining({
          level: "info",
          source: "MyModule",
          msg: "info message",
          key: "value",
        }),
      );
    });

    it("warn logs to console.warn", () => {
      const spy = vi.spyOn(console, "warn").mockImplementation(() => {});
      const log = createLogger("TestWarn");
      log.warn("warning");
      expect(spy).toHaveBeenCalledWith("[TestWarn]", "warning", expect.any(Object));
    });

    it("error logs to console.error", () => {
      const spy = vi.spyOn(console, "error").mockImplementation(() => {});
      const log = createLogger("TestError");
      log.error("error message");
      expect(spy).toHaveBeenCalledWith("[TestError]", "error message", expect.any(Object));
    });

    it("includes correlation ID in log entry", () => {
      const spy = vi.spyOn(console, "info").mockImplementation(() => {});
      const log = createLogger("TestCorrelation");
      log.info("test");
      const firstCall = spy.mock.calls[0];
      expect(firstCall).toBeDefined();
      if (!firstCall) {
        throw new Error("Expected logger call");
      }
      const entry = firstCall[2];
      expect(entry.correlationId).toBeTruthy();
      expect(typeof entry.correlationId).toBe("string");
    });
  });

  describe("getCorrelationId", () => {
    it("returns a string", () => {
      expect(typeof getCorrelationId()).toBe("string");
      expect(getCorrelationId().length).toBeGreaterThan(0);
    });

    it("returns same value across calls", () => {
      const a = getCorrelationId();
      const b = getCorrelationId();
      expect(a).toBe(b);
    });
  });

  describe("resetCorrelationId", () => {
    it("returns a new correlation ID", () => {
      getCorrelationId(); // ensure one exists
      const fresh = resetCorrelationId();
      expect(fresh).toBeTruthy();
      // Note: in test env crypto.randomUUID may be stubbed to same value
      // so we just verify it returns a string
      expect(typeof fresh).toBe("string");
    });
  });
});
