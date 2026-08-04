import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import i18n from "../i18n";
import { HomePage } from "./HomePage";

const api = vi.hoisted(() => ({
  fetchDatasets: vi.fn(),
  fetchSessions: vi.fn(),
  fetchTrainingReviews: vi.fn(),
}));

vi.mock("../api/datasets", () => ({ fetchDatasets: api.fetchDatasets }));
vi.mock("../api/sessions", () => ({
  fetchSessions: api.fetchSessions,
  fetchTrainingReviews: api.fetchTrainingReviews,
}));

describe("HomePage", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("zh-CN");
    api.fetchDatasets.mockResolvedValue({ datasets: [] });
    api.fetchSessions.mockResolvedValue({ sessions: [] });
    api.fetchTrainingReviews.mockResolvedValue({ reviews: [], recommendation: null });
  });

  it("keeps a compact state-aware action and removes onboarding or demo content", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter><HomePage /></MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("link", { name: /准备真实数据/ })).toHaveAttribute("href", "/data");
    expect(screen.getByRole("heading", { name: /用当时可见的信息/ })).toBeInTheDocument();
    expect(screen.queryByText("40 秒了解 REPLAYTUTOR")).not.toBeInTheDocument();
    expect(screen.queryByText("先用固定片段完成一场可核验训练")).not.toBeInTheDocument();
  });
});
