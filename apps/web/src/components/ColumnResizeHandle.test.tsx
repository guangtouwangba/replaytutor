import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  clampResizableValue,
  ColumnResizeHandle,
  readStoredResizableValue,
} from "./ColumnResizeHandle";

describe("ColumnResizeHandle", () => {
  it("clamps restored values to safe layout limits", () => {
    window.localStorage.removeItem("missing-resize-test");
    expect(readStoredResizableValue("missing-resize-test", 400, 320, 720)).toBe(400);
    window.localStorage.setItem("resize-test", "999");
    expect(readStoredResizableValue("resize-test", 400, 320, 720)).toBe(720);
    expect(clampResizableValue(120, 320, 720)).toBe(320);
  });

  it("supports physical keyboard resizing and reset", () => {
    const values: number[] = [];
    let reset = false;
    render(
      <ColumnResizeHandle
        direction={-1}
        label="调整右侧栏宽度"
        max={720}
        min={320}
        onChange={(value) => values.push(value)}
        onReset={() => { reset = true; }}
        value={400}
      />,
    );
    const separator = screen.getByRole("separator", { name: "调整右侧栏宽度" });
    fireEvent.keyDown(separator, { key: "ArrowLeft" });
    expect(values).toEqual([416]);
    fireEvent.doubleClick(separator);
    expect(reset).toBe(true);
  });
});
