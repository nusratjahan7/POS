import type * as React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { FullscreenToggle } from "./fullscreen-toggle";

const { toastError } = vi.hoisted(() => ({ toastError: vi.fn() }));

vi.mock("sonner", () => ({ toast: { error: toastError } }));

// Radix's tooltip needs layout APIs jsdom lacks; the toggle's behaviour is what
// matters here, so the primitives collapse to plain wrappers.
vi.mock("@radix-ui/react-tooltip", () => ({
  Provider: ({ children }: { children: React.ReactNode }) => children,
  Root: ({ children }: { children: React.ReactNode }) => children,
  Trigger: ({ children }: { children: React.ReactNode }) => children,
  Portal: ({ children }: { children: React.ReactNode }) => children,
  Content: () => null,
}));

function setFullscreenElement(element: Element | null) {
  Object.defineProperty(document, "fullscreenElement", {
    configurable: true,
    get: () => element,
  });
}

function setMethod(target: object, key: string, value: unknown) {
  Object.defineProperty(target, key, { configurable: true, writable: true, value });
}

function renderToggle() {
  return render(<FullscreenToggle />);
}

/** Simulates the browser reporting a fullscreen change (Esc, F11, OS, etc.). */
function emitFullscreenChange(element: Element | null) {
  act(() => {
    setFullscreenElement(element);
    document.dispatchEvent(new Event("fullscreenchange"));
  });
}

beforeEach(() => {
  setFullscreenElement(null);
  setMethod(document.documentElement, "requestFullscreen", vi.fn().mockResolvedValue(undefined));
  setMethod(document, "exitFullscreen", vi.fn().mockResolvedValue(undefined));
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("FullscreenToggle", () => {
  it("requests full screen for the application root", async () => {
    const user = userEvent.setup();
    renderToggle();

    await user.click(screen.getByRole("button", { name: "Full screen" }));

    expect(document.documentElement.requestFullscreen).toHaveBeenCalledTimes(1);
  });

  it("exits full screen when it is already active", async () => {
    setFullscreenElement(document.documentElement);
    const user = userEvent.setup();
    renderToggle();

    await user.click(screen.getByRole("button", { name: "Exit full screen" }));

    expect(document.exitFullscreen).toHaveBeenCalledTimes(1);
  });

  it("mirrors browser-driven changes, including leaving with Esc", () => {
    renderToggle();
    expect(screen.getByRole("button", { name: "Full screen" })).toBeTruthy();

    emitFullscreenChange(document.documentElement);
    expect(screen.getByRole("button", { name: "Exit full screen" })).toBeTruthy();

    emitFullscreenChange(null);
    expect(screen.getByRole("button", { name: "Full screen" })).toBeTruthy();
  });

  it("surfaces a rejected request instead of throwing", async () => {
    setMethod(document.documentElement, "requestFullscreen", vi.fn().mockRejectedValue(new Error("denied")));
    const user = userEvent.setup();
    renderToggle();

    await user.click(screen.getByRole("button", { name: "Full screen" }));

    await vi.waitFor(() => expect(toastError).toHaveBeenCalled());
  });

  it("surfaces an unsupported browser instead of throwing", async () => {
    setMethod(document.documentElement, "requestFullscreen", undefined);
    const user = userEvent.setup();
    renderToggle();

    await user.click(screen.getByRole("button", { name: "Full screen" }));

    await vi.waitFor(() => expect(toastError).toHaveBeenCalled());
  });
});
