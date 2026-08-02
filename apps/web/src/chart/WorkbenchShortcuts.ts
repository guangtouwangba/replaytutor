import type { DrawingTool } from "./DrawingController";

export type WorkbenchShortcutCommand =
  | { readonly kind: "drawing"; readonly tool: Exclude<DrawingTool, "select"> }
  | { readonly kind: "command_palette" }
  | { readonly kind: "indicator_search" }
  | { readonly kind: "shortcut_help" }
  | { readonly kind: "undo" }
  | { readonly kind: "redo" }
  | { readonly kind: "copy" }
  | { readonly kind: "paste" }
  | { readonly kind: "delete" }
  | { readonly kind: "toggle_drawings" }
  | { readonly kind: "save_layout" }
  | { readonly kind: "reset_chart" }
  | { readonly kind: "zoom_in" }
  | { readonly kind: "zoom_out" }
  | { readonly kind: "play_pause" }
  | { readonly kind: "advance"; readonly bars: number }
  | { readonly kind: "order_draft"; readonly side: "BUY" | "SELL"; readonly orderType: "MARKET" | "LIMIT" }
  | { readonly kind: "cancel" };

export const DRAWING_SHORTCUT_LABELS: Partial<Record<DrawingTool, string>> = {
  trend_line: "⌥/Alt + T",
  horizontal_line: "⌥/Alt + H",
  vertical_line: "⌥/Alt + V",
  cross_line: "⌥/Alt + C",
  fibonacci_retracement: "⌥/Alt + F",
  zone: "⌥/Alt + Shift + R",
};

export function isEditableShortcutTarget(target: EventTarget | null): boolean {
  return target instanceof Element
    && Boolean(target.closest("input, textarea, select, [contenteditable='true']"));
}

export function resolveWorkbenchShortcut(event: KeyboardEvent): WorkbenchShortcutCommand | null {
  if (isEditableShortcutTarget(event.target)) return event.key === "Escape" ? { kind: "cancel" } : null;
  const primary = event.metaKey || event.ctrlKey;
  const key = event.key.toLowerCase();

  if (event.key === "Escape") return { kind: "cancel" };
  if (event.key === "?" && !primary && !event.altKey) return { kind: "shortcut_help" };
  if (event.key === "/" && !primary && !event.altKey) return { kind: "indicator_search" };
  if (primary && key === "k") return { kind: "command_palette" };
  if (primary && key === "s") return { kind: "save_layout" };
  if (primary && event.altKey && key === "h") return { kind: "toggle_drawings" };
  if (primary && key === "z" && event.shiftKey) return { kind: "redo" };
  if (primary && key === "z") return { kind: "undo" };
  if (primary && key === "y") return { kind: "redo" };
  if (primary && key === "c") return { kind: "copy" };
  if (primary && key === "v") return { kind: "paste" };
  if (event.key === "Delete" || event.key === "Backspace") return { kind: "delete" };
  if (event.altKey && event.shiftKey && key === "r") return { kind: "drawing", tool: "zone" };
  if (event.altKey && !event.shiftKey && key === "t") return { kind: "drawing", tool: "trend_line" };
  if (event.altKey && !event.shiftKey && key === "h") return { kind: "drawing", tool: "horizontal_line" };
  if (event.altKey && !event.shiftKey && key === "v") return { kind: "drawing", tool: "vertical_line" };
  if (event.altKey && !event.shiftKey && key === "c") return { kind: "drawing", tool: "cross_line" };
  if (event.altKey && !event.shiftKey && key === "f") return { kind: "drawing", tool: "fibonacci_retracement" };
  if (event.altKey && !event.shiftKey && key === "r") return { kind: "reset_chart" };
  if (primary && event.key === "ArrowUp") return { kind: "zoom_in" };
  if (primary && event.key === "ArrowDown") return { kind: "zoom_out" };
  if (primary && event.key === "ArrowRight") return { kind: "advance", bars: 10 };
  if (!primary && !event.altKey && event.key === "ArrowRight") return { kind: "advance", bars: 1 };
  if (!primary && !event.altKey && event.code === "Space") return { kind: "play_pause" };
  if (event.shiftKey && event.altKey && key === "b") return { kind: "order_draft", side: "BUY", orderType: "LIMIT" };
  if (event.shiftKey && event.altKey && key === "s") return { kind: "order_draft", side: "SELL", orderType: "LIMIT" };
  if (event.shiftKey && !event.altKey && key === "b") return { kind: "order_draft", side: "BUY", orderType: "MARKET" };
  if (event.shiftKey && !event.altKey && key === "s") return { kind: "order_draft", side: "SELL", orderType: "MARKET" };
  return null;
}

export const TIMEFRAME_SHORTCUTS = {
  "1": "1m",
  "5": "5m",
  "15": "15m",
  "60": "1h",
  "240": "4h",
} as const;

export type ShortcutTimeframe = typeof TIMEFRAME_SHORTCUTS[keyof typeof TIMEFRAME_SHORTCUTS];

export function timeframeFromDigits(value: string): ShortcutTimeframe | null {
  return TIMEFRAME_SHORTCUTS[value as keyof typeof TIMEFRAME_SHORTCUTS] ?? null;
}

export function isTimeframePrefix(value: string): boolean {
  return Object.keys(TIMEFRAME_SHORTCUTS).some((item) => item.startsWith(value));
}
