import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";
import i18n from "../i18n";

afterEach(cleanup);
beforeEach(async () => { await i18n.changeLanguage("zh-CN"); });

function renderShell(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<AppShell onRetry={vi.fn()} startup={{ kind: "loading" }} />}>
            <Route index element={<h1>首页内容</h1>} />
            <Route path="sessions/:sessionId" element={<h1>工作台内容</h1>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AppShell workspace layout", () => {
  it("keeps the global navigation on normal pages", () => {
    renderShell("/");
    expect(screen.getByRole("complementary", { name: "主要导航" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "跳到主要内容" })).toHaveAttribute("href", "#main-content");
  });

  it("releases the global rail space inside a training workbench", () => {
    renderShell("/sessions/ses_test");
    expect(screen.queryByRole("complementary", { name: "主要导航" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "工作台内容" })).toBeInTheDocument();
  });
});
