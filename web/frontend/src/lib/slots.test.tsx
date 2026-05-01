/**
 * Tests for the Slot composition primitive.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Slots, Slot } from "./slots";

describe("Slots / Slot", () => {
  it("renders provided content for a named slot", () => {
    render(
      <Slots title={<h1>Hello</h1>}>
        <Slot name="title" />
      </Slots>,
    );
    expect(screen.getByRole("heading", { name: "Hello" })).toBeInTheDocument();
  });

  it("renders fallback when no content for that slot name", () => {
    render(
      <Slots>
        <Slot name="missing" fallback={<span>Default</span>} />
      </Slots>,
    );
    expect(screen.getByText("Default")).toBeInTheDocument();
  });

  it("renders nothing when no content and no fallback", () => {
    const { container } = render(
      <Slots>
        <Slot name="empty" />
      </Slots>,
    );
    expect(container.textContent).toBe("");
  });

  it("nested Slots: inner overrides outer for matching key", () => {
    render(
      <Slots header={<span>Outer Header</span>} footer={<span>Outer Footer</span>}>
        <Slots header={<span>Inner Header</span>}>
          <div>
            <Slot name="header" />
            <Slot name="footer" />
          </div>
        </Slots>
      </Slots>,
    );
    expect(screen.getByText("Inner Header")).toBeInTheDocument();
    expect(screen.getByText("Outer Footer")).toBeInTheDocument();
    expect(screen.queryByText("Outer Header")).not.toBeInTheDocument();
  });

  it("outer keys remain available in nested scope", () => {
    render(
      <Slots sidebar={<span>Sidebar Content</span>}>
        <Slots main={<span>Main Content</span>}>
          <div>
            <Slot name="sidebar" />
            <Slot name="main" />
          </div>
        </Slots>
      </Slots>,
    );
    expect(screen.getByText("Sidebar Content")).toBeInTheDocument();
    expect(screen.getByText("Main Content")).toBeInTheDocument();
  });
});
