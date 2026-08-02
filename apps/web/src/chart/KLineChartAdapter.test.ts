import type { Chart, OverlayCreate } from "klinecharts";
import { describe, expect, it, vi } from "vitest";
import { KLineChartAdapter } from "./KLineChartAdapter";

describe("KLineChartAdapter order line", () => {
  it("supports create, select, drag, programmatic move, and delete", () => {
    let createdOverlay: OverlayCreate | undefined;
    const chart = {
      createOverlay: vi.fn((overlay: OverlayCreate) => {
        createdOverlay = overlay;
        return overlay.id ?? null;
      }),
      overrideOverlay: vi.fn(() => true),
      removeOverlay: vi.fn(() => true),
    } as unknown as Chart;
    const onSelect = vi.fn();
    const onMove = vi.fn();
    const onDelete = vi.fn();
    const adapter = new KLineChartAdapter(chart);

    const id = adapter.createOrderLine(67_420, { onSelect, onMove, onDelete });
    expect(createdOverlay?.name).toBe("horizontalStraightLine");
    expect(createdOverlay?.points).toEqual([{ value: 67_420 }]);

    createdOverlay?.onSelected?.({ chart, overlay: { points: [{ value: 67_420 }] } } as never);
    expect(onSelect).toHaveBeenCalledWith(id);

    createdOverlay?.onPressedMoveEnd?.({
      chart,
      overlay: { points: [{ value: 67_550 }] },
    } as never);
    expect(onMove).toHaveBeenCalledWith(id, 67_550);

    adapter.moveOrderLine(id, 67_600);
    expect(chart.overrideOverlay).toHaveBeenCalledWith({ id, points: [{ value: 67_600 }] });

    createdOverlay?.onRemoved?.({ chart, overlay: { points: [] } } as never);
    expect(onDelete).toHaveBeenCalledWith(id);
    adapter.deleteOrderLine(id);
    expect(chart.removeOverlay).toHaveBeenCalledWith({ id });
  });
});
