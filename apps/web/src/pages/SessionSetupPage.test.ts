import type { DataSnapshot } from "@replaytutor/contracts";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import i18n from "../i18n";
import {
  automaticDownloadRange,
  selectLocalSnapshot,
  SessionSetupPage,
} from "./SessionSetupPage";

const api = vi.hoisted(() => ({
  createSession: vi.fn(() => new Promise(() => undefined)),
  fetchDatasetDownloadJobs: vi.fn(),
  fetchDatasets: vi.fn(),
  fetchPlaybooks: vi.fn(),
  startBinanceDatasetDownload: vi.fn(),
}));

vi.mock("../api/datasets", () => ({
  fetchDatasetDownloadJobs: api.fetchDatasetDownloadJobs,
  fetchDatasets: api.fetchDatasets,
  startBinanceDatasetDownload: api.startBinanceDatasetDownload,
}));
vi.mock("../api/playbooks", () => ({ fetchPlaybooks: api.fetchPlaybooks }));
vi.mock("../api/sessions", () => ({ createSession: api.createSession }));

function snapshot(
  snapshotId: string,
  symbol: string,
  assetClass: "crypto_spot" | "crypto_perpetual",
  createdAt: string,
): DataSnapshot {
  return {
    schema_version: "1.0",
    snapshot_id: snapshotId,
    instrument: {
      schema_version: "1.0",
      instrument_id: `ins_${snapshotId}`,
      asset_class: assetClass,
      market: "CRYPTO",
      venue: assetClass === "crypto_perpetual" ? "BINANCE_USDM" : "BINANCE",
      canonical_symbol: symbol,
      display_name: symbol,
      base_currency: symbol.replace("USDT", ""),
      quote_currency: "USDT",
      timezone: "UTC",
      tick_size: "0.01",
      lot_size: "0.00001",
      price_scale: 2,
      market_rule_set_id: assetClass === "crypto_perpetual"
        ? "binance_usdm_perpetual_v1"
        : "crypto_spot_v1",
    },
    timeframe: "1m",
    source_id: `binance:${symbol}`,
    source_kind: assetClass === "crypto_perpetual" ? "binance_usdm" : "binance_public",
    coverage_start: "2026-07-01T00:00:00Z",
    coverage_end: "2026-08-01T00:00:00Z",
    created_at: createdAt,
    content_hash: `content-${snapshotId}`,
    manifest_hash: `manifest-${snapshotId}`,
    immutable: true,
    quality: {
      status: "passed",
      row_count: 44_640,
      duplicate_count: 0,
      gap_count: 0,
      invalid_ohlc_count: 0,
      flags: [],
    },
    derived_timeframes: [],
  };
}

describe("automatic market data selection", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage("zh-CN");
  });

  it("reuses the newest local snapshot for the selected symbol and market", () => {
    const snapshots = [
      snapshot("old-perp", "BTCUSDT", "crypto_perpetual", "2026-07-01T00:00:00Z"),
      snapshot("eth-perp", "ETHUSDT", "crypto_perpetual", "2026-08-01T00:00:00Z"),
      snapshot("spot", "BTCUSDT", "crypto_spot", "2026-08-02T00:00:00Z"),
      snapshot("new-perp", "BTCUSDT", "crypto_perpetual", "2026-08-02T00:00:00Z"),
    ];

    expect(selectLocalSnapshot(snapshots, "BTCUSDT", "USDT_PERPETUAL", 30)?.snapshot_id)
      .toBe("new-perp");
    expect(selectLocalSnapshot(snapshots, "BTCUSDT", "SPOT", 30)?.snapshot_id)
      .toBe("spot");
    expect(selectLocalSnapshot(snapshots, "BTCUSDT", "USDT_PERPETUAL", 365))
      .toBeUndefined();
    expect(selectLocalSnapshot(
      snapshots,
      "BTCUSDT",
      "USDT_PERPETUAL",
      30,
      "old-perp",
    )?.snapshot_id).toBe("old-perp");
  });

  it("lets the user choose a snapshot and a specific replay time", async () => {
    const snapshots = [
      snapshot("old-perp", "BTCUSDT", "crypto_perpetual", "2026-07-01T00:00:00Z"),
      snapshot("new-perp", "BTCUSDT", "crypto_perpetual", "2026-08-02T00:00:00Z"),
    ];
    api.fetchDatasets.mockResolvedValue({ schema_version: "1.0", datasets: snapshots });
    api.fetchDatasetDownloadJobs.mockResolvedValue({ schema_version: "1.0", jobs: [] });
    api.fetchPlaybooks.mockResolvedValue({ schema_version: "1.0", playbooks: [] });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    render(createElement(
      QueryClientProvider,
      { client: queryClient },
      createElement(MemoryRouter, null, createElement(SessionSetupPage)),
    ));

    const snapshotGroup = await screen.findByRole("radiogroup", { name: "选择数据集 Snapshot" });
    expect(snapshotGroup).toBeVisible();
    expect(screen.queryByText("账户与风险引擎")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "请先选择数据集" })).toBeDisabled();
    fireEvent.click(screen.getByRole("radio", { name: /old-perp/ }));
    expect(screen.getByText("账户与风险引擎")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "选择日期" }));
    fireEvent.change(screen.getByLabelText("回放开始时间（UTC）"), {
      target: { value: "2026-07-15T12:30" },
    });
    fireEvent.click(screen.getByRole("button", { name: /使用所选数据开始/ }));

    await waitFor(() => expect(api.createSession).toHaveBeenCalledWith(
      expect.objectContaining({
        snapshot_id: "old-perp",
        start_mode: "specific",
        start_time: "2026-07-15T12:30:00.000Z",
        hidden_real_date: false,
      }),
    ));
  });

  it("downloads a closed-minute 30-day window when local data is absent", () => {
    expect(automaticDownloadRange(new Date("2026-08-02T10:23:42.123Z"))).toEqual({
      start_time: "2026-07-03T10:23:00.000Z",
      end_time: "2026-08-02T10:23:00.000Z",
    });
    expect(automaticDownloadRange(new Date("2026-08-02T10:23:42.123Z"), 365)).toEqual({
      start_time: "2025-08-02T10:23:00.000Z",
      end_time: "2026-08-02T10:23:00.000Z",
    });
  });
});
