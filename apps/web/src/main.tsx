import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { KLineChartSpike } from "./spikes/KLineChartSpike";
import "./styles.css";

const showKLineSpike = new URLSearchParams(window.location.search).get("spike") === "kline";

// KLineChart updates several stacked canvases from ResizeObserver callbacks.
// Move those updates across a frame boundary so Chromium never detects a
// resize-write loop in the same observer delivery cycle.
const NativeResizeObserver = window.ResizeObserver;
window.ResizeObserver = class FrameBoundaryResizeObserver extends NativeResizeObserver {
  constructor(callback: ResizeObserverCallback) {
    super((entries, observer) => {
      window.requestAnimationFrame(() => callback(entries, observer));
    });
  }
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {showKLineSpike ? <KLineChartSpike /> : <App />}
  </StrictMode>,
);
