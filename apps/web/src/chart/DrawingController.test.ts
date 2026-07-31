import { describe, expect, it } from "vitest";
import { annotationShape, overlayName } from "./DrawingController";

describe("DrawingController", () => {
  it.each([
    ["line", "segment"],
    ["zone", "rect"],
    ["marker", "simpleAnnotation"],
  ] as const)("maps %s to a supported KLineChart overlay", (tool, overlay) => {
    expect(overlayName(tool)).toBe(overlay);
    expect(annotationShape(tool)).toBe(tool);
  });
});
