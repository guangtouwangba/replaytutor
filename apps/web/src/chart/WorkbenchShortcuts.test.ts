import { describe, expect, it } from "vitest";
import { isTimeframePrefix, resolveWorkbenchShortcut, timeframeFromDigits } from "./WorkbenchShortcuts";

function keyboard(key: string, init: KeyboardEventInit = {}) {
  return new KeyboardEvent("keydown", { key, ...init });
}

describe("WorkbenchShortcuts", () => {
  it("maps professional drawing shortcuts", () => {
    expect(resolveWorkbenchShortcut(keyboard("t", { altKey: true }))).toEqual({ kind: "drawing", tool: "trend_line" });
    expect(resolveWorkbenchShortcut(keyboard("R", { altKey: true, shiftKey: true }))).toEqual({ kind: "drawing", tool: "zone" });
  });

  it("keeps order shortcuts as drafts", () => {
    expect(resolveWorkbenchShortcut(keyboard("B", { shiftKey: true }))).toEqual({ kind: "order_draft", side: "BUY", orderType: "MARKET" });
    expect(resolveWorkbenchShortcut(keyboard("S", { shiftKey: true, altKey: true }))).toEqual({ kind: "order_draft", side: "SELL", orderType: "LIMIT" });
  });

  it("supports platform primary modifiers", () => {
    expect(resolveWorkbenchShortcut(keyboard("k", { metaKey: true }))).toEqual({ kind: "command_palette" });
    expect(resolveWorkbenchShortcut(keyboard("z", { ctrlKey: true }))).toEqual({ kind: "undo" });
    expect(resolveWorkbenchShortcut(keyboard("Z", { metaKey: true, shiftKey: true }))).toEqual({ kind: "redo" });
  });

  it("resolves direct timeframe input without accepting unknown values", () => {
    expect(timeframeFromDigits("15")).toBe("15m");
    expect(timeframeFromDigits("60")).toBe("1h");
    expect(timeframeFromDigits("30")).toBeNull();
    expect(isTimeframePrefix("2")).toBe(true);
    expect(isTimeframePrefix("3")).toBe(false);
  });
});
