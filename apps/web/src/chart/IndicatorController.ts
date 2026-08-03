import type { Chart, IndicatorCreate } from "klinecharts";
import { indicatorDefinition, type IndicatorInstance } from "./IndicatorCatalog";

export function syncChartIndicators(
  chart: Pick<Chart, "createIndicator" | "getIndicators" | "overrideIndicator" | "removeIndicator">,
  instances: readonly IndicatorInstance[],
): void {
  const requested = new Set(instances.map((item) => item.instanceId));
  for (const current of chart.getIndicators()) {
    if (current.id.startsWith("indicator-") && !requested.has(current.id)) {
      chart.removeIndicator({ id: current.id });
    }
  }

  const existing = new Set(chart.getIndicators().map((item) => item.id));
  for (const instance of instances) {
    const item = indicatorDefinition(instance.definitionId);
    const create: IndicatorCreate = {
      id: instance.instanceId,
      name: item.engineName,
      visible: instance.visible,
      ...(instance.params ? { calcParams: [...instance.params] } : {}),
      ...(item.placement === "main" ? { paneId: "candle_pane" } : {}),
    };
    if (existing.has(instance.instanceId)) chart.overrideIndicator(create);
    else chart.createIndicator(create, false);
  }
}
