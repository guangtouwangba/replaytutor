import { dispose, type Chart, type OverlayCreate } from "klinecharts";
import type { ChartAdapter, OrderLineCallbacks } from "./ChartAdapter";

export class KLineChartAdapter implements ChartAdapter {
  constructor(
    private readonly chart: Chart,
    private readonly host?: HTMLElement,
  ) {}

  createOrderLine(price: number, callbacks: OrderLineCallbacks): string {
    const id = `order-line-${crypto.randomUUID()}`;
    const overlay: OverlayCreate = {
      id,
      name: "horizontalStraightLine",
      points: [{ value: price }],
      styles: {
        line: { color: "#f5a623", size: 1, style: "dashed" },
        point: { color: "#f5a623", borderColor: "#fff1d6" },
      },
      onSelected: () => callbacks.onSelect(id),
      onPressedMoveEnd: ({ overlay: movedOverlay }) => {
        const movedPrice = movedOverlay.points[0]?.value;
        if (typeof movedPrice === "number") callbacks.onMove(id, movedPrice);
      },
      onRemoved: () => callbacks.onDelete(id),
    };
    const created = this.chart.createOverlay(overlay);
    if (created !== id) throw new Error("KLineChart failed to create the order line");
    return id;
  }

  moveOrderLine(id: string, price: number): void {
    if (!this.chart.overrideOverlay({ id, points: [{ value: price }] })) {
      throw new Error(`Unknown order line: ${id}`);
    }
  }

  deleteOrderLine(id: string): void {
    if (!this.chart.removeOverlay({ id })) {
      throw new Error(`Unknown order line: ${id}`);
    }
  }

  destroy(): void {
    if (this.host) dispose(this.host);
  }
}
