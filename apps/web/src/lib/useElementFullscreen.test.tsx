import { fireEvent, render, screen } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useElementFullscreen } from "./useElementFullscreen";

function Harness() {
  const targetRef = useRef<HTMLElement>(null);
  const fullscreen = useElementFullscreen(targetRef);
  return (
    <section className={fullscreen.fallback ? "is-immersive" : ""} ref={targetRef}>
      <span>{fullscreen.active ? "active" : "inactive"}</span>
      <button onClick={() => void fullscreen.toggle()} type="button">toggle</button>
    </section>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  Reflect.deleteProperty(HTMLElement.prototype, "requestFullscreen");
});

describe("useElementFullscreen", () => {
  it("falls back to an immersive layout and lets Escape exit", async () => {
    Object.defineProperty(HTMLElement.prototype, "requestFullscreen", {
      configurable: true,
      value: vi.fn().mockRejectedValue(new Error("denied")),
    });
    render(<Harness />);

    fireEvent.click(screen.getByRole("button", { name: "toggle" }));
    expect(await screen.findByText("active")).toBeInTheDocument();
    expect(screen.getByText("active").closest("section")).toHaveClass("is-immersive");

    fireEvent.keyDown(window, { key: "Escape" });
    expect(await screen.findByText("inactive")).toBeInTheDocument();
  });
});
