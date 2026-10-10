import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { Barcode } from "./barcode";

afterEach(() => {
  cleanup();
});

describe("Barcode", () => {
  it("renders an EAN-13 with its human-readable digits", () => {
    render(<Barcode value="4006381333931" />);

    expect(screen.getByRole("img", { name: /4006381333931/ })).toBeTruthy();
    expect(screen.getByText("4006381333931")).toBeTruthy();
  });

  it("renders an internal code as Code 128", () => {
    render(<Barcode value="BEAN-1KG" />);
    expect(screen.getByRole("img", { name: /BEAN-1KG/ })).toBeTruthy();
  });

  it("renders a fallback instead of throwing on an unencodable value", () => {
    render(<Barcode value="café" />);
    expect(screen.getByText("Unsupported barcode")).toBeTruthy();
  });

  it("hides the human-readable text when asked", () => {
    render(<Barcode value="4006381333931" showText={false} />);
    expect(screen.queryByText("4006381333931")).toBeNull();
  });
});
