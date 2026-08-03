import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DrawingToolbar } from "./DrawingToolbar";

afterEach(cleanup);

describe("DrawingToolbar", () => {
  it("exposes explicit long and short position planning tools", () => {
    const onSelect = vi.fn();
    render(
      <DrawingToolbar
        activeTool="select"
        annotationsLocked={false}
        annotationsVisible
        canDelete={false}
        canRedo={false}
        canUndo={false}
        disabled={false}
        continuousDrawing={false}
        historyPending={false}
        magnetEnabled
        onSelect={onSelect}
        onDelete={vi.fn()}
        onToggleAnnotations={vi.fn()}
        onToggleMagnet={vi.fn()}
        onToggleContinuous={vi.fn()}
        onToggleLock={vi.fn()}
        onRedo={vi.fn()}
        onUndo={vi.fn()}
        onZoomIn={vi.fn()}
        onZoomOut={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "预测与测量" }));
    fireEvent.click(screen.getByRole("menuitemradio", { name: /^多头仓位计划/ }));
    fireEvent.click(screen.getByRole("button", { name: "预测与测量" }));
    fireEvent.click(screen.getByRole("menuitemradio", { name: /^空头仓位计划/ }));

    expect(onSelect).toHaveBeenNthCalledWith(1, "long_position");
    expect(onSelect).toHaveBeenNthCalledWith(2, "short_position");
    expect(screen.getByRole("button", { name: "关闭磁吸" })).toHaveAttribute("aria-pressed", "true");

    fireEvent.mouseEnter(screen.getByRole("button", { name: "预测与测量" }));
    expect(screen.getByRole("tooltip")).toHaveTextContent("多空仓位、盈亏比");
    fireEvent.mouseLeave(screen.getByRole("button", { name: "预测与测量" }));
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("opens a grouped line menu and selects extended line tools", () => {
    const onSelect = vi.fn();
    render(
      <DrawingToolbar
        activeTool="select"
        annotationsLocked={false}
        annotationsVisible
        canDelete={false}
        canRedo={false}
        canUndo={false}
        disabled={false}
        continuousDrawing={false}
        historyPending={false}
        magnetEnabled
        onSelect={onSelect}
        onDelete={vi.fn()}
        onToggleAnnotations={vi.fn()}
        onToggleMagnet={vi.fn()}
        onToggleContinuous={vi.fn()}
        onToggleLock={vi.fn()}
        onRedo={vi.fn()}
        onUndo={vi.fn()}
        onZoomIn={vi.fn()}
        onZoomOut={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "线类工具" }));
    expect(screen.getByRole("menu", { name: "线类工具" })).toBeVisible();
    expect(onSelect).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("menuitemradio", { name: /^射线点击/ }));
    expect(onSelect).toHaveBeenLastCalledWith("trend_ray");
    expect(screen.queryByRole("menu", { name: "线类工具" })).not.toBeInTheDocument();
  });

  it("separates prediction, measurement, patterns, and chart zoom controls", () => {
    const onSelect = vi.fn();
    const onZoomIn = vi.fn();
    const onZoomOut = vi.fn();
    render(
      <DrawingToolbar
        activeTool="select"
        annotationsLocked={false}
        annotationsVisible
        canDelete={false}
        canRedo={false}
        canUndo={false}
        disabled={false}
        continuousDrawing={false}
        historyPending={false}
        magnetEnabled
        onDelete={vi.fn()}
        onRedo={vi.fn()}
        onSelect={onSelect}
        onToggleAnnotations={vi.fn()}
        onToggleContinuous={vi.fn()}
        onToggleLock={vi.fn()}
        onToggleMagnet={vi.fn()}
        onUndo={vi.fn()}
        onZoomIn={onZoomIn}
        onZoomOut={onZoomOut}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "预测与测量" }));
    const predictionMenu = screen.getByRole("menu", { name: "预测与测量" });
    expect(predictionMenu).toHaveTextContent("预测");
    expect(predictionMenu).toHaveTextContent("多头仓位计划");
    expect(predictionMenu).toHaveTextContent("锚定 VWAP");
    expect(predictionMenu).toHaveTextContent("价格范围");
    fireEvent.click(screen.getByRole("menuitemradio", { name: /^日期与价格测量/ }));
    expect(onSelect).toHaveBeenLastCalledWith("measure");

    fireEvent.click(screen.getByRole("button", { name: "图形形态" }));
    expect(screen.getByRole("menu", { name: "图形形态" })).toHaveTextContent("头肩形态");

    fireEvent.click(screen.getByRole("button", { name: "放大当前图表" }));
    fireEvent.click(screen.getByRole("button", { name: "缩小当前图表" }));
    expect(onZoomIn).toHaveBeenCalledOnce();
    expect(onZoomOut).toHaveBeenCalledOnce();
  });
});
