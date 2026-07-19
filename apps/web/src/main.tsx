import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { KLineChartSpike } from "./spikes/KLineChartSpike";
import "./styles.css";

const showKLineSpike = new URLSearchParams(window.location.search).get("spike") === "kline";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {showKLineSpike ? <KLineChartSpike /> : <App />}
  </StrictMode>,
);
