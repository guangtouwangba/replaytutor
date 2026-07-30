import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const healthyResponse = {
  schema_version: "1.0",
  status: "healthy",
  request_id: "request-test",
  api: { status: "healthy", version: "0.1.0" },
  database: {
    status: "healthy",
    path: "/tmp/app.db",
    journal_mode: "wal",
    foreign_keys: true,
    migration_current: "0001",
    migration_head: "0001",
  },
  data: { status: "healthy", path: "/tmp/data", writable: true },
  agents: [],
};

afterEach(() => vi.restoreAllMocks());

describe("startup state", () => {
  it("shows the API version when health is compatible", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify(healthyResponse)))));
    render(<App />);
    expect(screen.getByText("正在连接本地 API")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("API 0.1.0")).toBeInTheDocument());
  });

  it("shows an incompatible state for an unknown schema", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ ...healthyResponse, schema_version: "2.0" })))));
    render(<App />);
    await waitFor(() => expect(screen.getByText(/API 版本不兼容/)).toBeInTheDocument());
  });

  it("shows an offline state when the API cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));
    render(<App />);
    await waitFor(() => expect(screen.getByText(/API 不可用/)).toBeInTheDocument());
  });
});
