import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import { CommandPalette, ShortcutHelp } from "./WorkbenchShortcutOverlay";

describe("Workbench shortcut overlays", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en-US");
  });

  it("renders the shortcut help entirely in English for en-US", () => {
    render(<ShortcutHelp onClose={vi.fn()} />);

    expect(screen.getByRole("dialog", { name: "ReplayTutor keyboard shortcuts" })).toBeVisible();
    expect(screen.getByText("Replay and chart")).toBeVisible();
    expect(screen.getByText("Replay safety boundary")).toBeVisible();
    expect(screen.queryByText("回放安全边界")).not.toBeInTheDocument();
  });

  it("switches the command palette copy to Simplified Chinese", async () => {
    await i18n.changeLanguage("zh-CN");
    render(<CommandPalette actions={[]} onClose={vi.fn()} />);

    expect(screen.getByRole("dialog", { name: "快速搜索功能和工具" })).toBeVisible();
    expect(screen.getByPlaceholderText("搜索工具、周期或操作…")).toBeVisible();
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "不存在" } });
    expect(screen.getByText(/没有匹配的可用操作/)).toBeVisible();
  });
});
