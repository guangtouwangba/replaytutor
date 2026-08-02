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
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "多头仓位计划" }));
    fireEvent.click(screen.getByRole("button", { name: "空头仓位计划" }));

    expect(onSelect).toHaveBeenNthCalledWith(1, "long_position");
    expect(onSelect).toHaveBeenNthCalledWith(2, "short_position");
    expect(screen.getByRole("button", { name: "关闭磁吸" })).toHaveAttribute("aria-pressed", "true");

    fireEvent.mouseEnter(screen.getByRole("button", { name: "多头仓位计划" }));
    expect(screen.getByRole("tooltip")).toHaveTextContent("依次点击入场、止损、目标价");
    fireEvent.mouseLeave(screen.getByRole("button", { name: "多头仓位计划" }));
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
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "线类工具" }));
    expect(screen.getByRole("menu", { name: "线类工具" })).toBeVisible();
    expect(onSelect).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("menuitemradio", { name: /^射线点击/ }));
    expect(onSelect).toHaveBeenLastCalledWith("trend_ray");
    expect(screen.queryByRole("menu", { name: "线类工具" })).not.toBeInTheDocument();
  });
});
