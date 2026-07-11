import { describe, it, expect } from "vitest";
import { createDomainMemo } from "./domainMemo";

describe("createDomainMemo", () => {
  it("adopts the first observed domain for a key", () => {
    const memo = createDomainMemo();
    const { domain, changed } = memo.resolve("heat", { min: 0, max: 1 });
    expect(domain).toEqual({ min: 0, max: 1 });
    expect(changed).toBe(false);
  });

  it("keeps returning the SAME domain object reference across calls with unchanged data (deck.gl updateTriggers stability)", () => {
    const memo = createDomainMemo();
    const first = memo.resolve("heat", { min: 0, max: 1 });
    const second = memo.resolve("heat", { min: 0, max: 1 });
    expect(second.domain).toBe(first.domain);
  });

  it("never silently rescales — a wider natural domain does not change the returned domain", () => {
    const memo = createDomainMemo();
    memo.resolve("heat", { min: 0, max: 1 });
    const { domain, changed } = memo.resolve("heat", { min: -5, max: 10 });
    expect(domain).toEqual({ min: 0, max: 1 });
    expect(changed).toBe(true);
  });

  it("reports changed:false when new data stays within the cached domain", () => {
    const memo = createDomainMemo();
    memo.resolve("heat", { min: 0, max: 10 });
    const { domain, changed } = memo.resolve("heat", { min: 2, max: 8 });
    expect(domain).toEqual({ min: 0, max: 10 });
    expect(changed).toBe(false);
  });

  it("tracks each lens key's domain independently", () => {
    const memo = createDomainMemo();
    memo.resolve("heat", { min: 0, max: 1 });
    memo.resolve("metric:imperial_rent", { min: 0, max: 100 });
    expect(memo.resolve("heat", { min: 0, max: 1 }).domain).toEqual({ min: 0, max: 1 });
    expect(memo.resolve("metric:imperial_rent", { min: 0, max: 100 }).domain).toEqual({
      min: 0,
      max: 100,
    });
  });

  it("reset() clears every cached domain, re-adopting the next natural domain", () => {
    const memo = createDomainMemo();
    memo.resolve("heat", { min: 0, max: 1 });
    memo.reset();
    const { domain, changed } = memo.resolve("heat", { min: 5, max: 9 });
    expect(domain).toEqual({ min: 5, max: 9 });
    expect(changed).toBe(false);
  });
});
