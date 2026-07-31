import type { ChartAnnotation } from "@replaytutor/contracts";

export type DrawingTool = "select" | "line" | "zone" | "marker";

export function overlayName(tool: Exclude<DrawingTool, "select">): string {
  if (tool === "line") return "segment";
  if (tool === "zone") return "rect";
  return "simpleAnnotation";
}

export function annotationShape(
  tool: Exclude<DrawingTool, "select">,
): ChartAnnotation["shape"] {
  return tool;
}
