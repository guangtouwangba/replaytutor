import type { MarketDepthResponse } from "@replaytutor/contracts";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { MarketDepthPanel } from "./MarketDepthPanel";

afterEach(cleanup);

describe("MarketDepthPanel", () => {
  it("does not disguise candle-only data as an order book", () => {
    render(
      <MarketDepthPanel
        depth={{
          schema_version: "1.0",
          session_id: "ses_00000000-0000-0000-0000-000000000001",
          frame_id: "frm_00000000-0000-0000-0000-000000000001",
          visible_at: "2025-01-01T00:19:59Z",
          status: "unavailable",
          reason: "historical_depth_not_captured",
          age_seconds: null,
          depth: null,
        }}
        english={false}
        error={null}
        loading={false}
        priceScale={2}
        quoteCurrency="USDT"
      />,
    );

    expect(screen.getByText("该时刻没有历史 L2 盘口")).toBeVisible();
    expect(screen.getByText(/不会用今天的实时盘口冒充历史盘口/)).toBeVisible();
  });

  it("renders timestamped levels, spread and stale status", () => {
    const response: MarketDepthResponse = {
      schema_version: "1.0",
      session_id: "ses_00000000-0000-0000-0000-000000000001",
      frame_id: "frm_00000000-0000-0000-0000-000000000001",
      visible_at: "2025-01-01T00:21:30Z",
      status: "stale",
      reason: "depth_snapshot_is_stale",
      age_seconds: 90,
      depth: {
        schema_version: "1.0",
        depth_id: "dpt_00000000-0000-0000-0000-000000000001",
        snapshot_id: "snp_00000000-0000-0000-0000-000000000001",
        instrument_id: "ins_00000000-0000-0000-0000-000000000001",
        captured_at: "2025-01-01T00:20:00Z",
        source_kind: "file_import",
        last_update_id: 42,
        bids: [{ price: "100", quantity: "2", cumulative_quantity: "2", notional: "200", cumulative_notional: "200" }],
        asks: [{ price: "101", quantity: "3", cumulative_quantity: "3", notional: "303", cumulative_notional: "303" }],
        best_bid: "100",
        best_ask: "101",
        spread: "1",
        midpoint: "100.5",
      },
    };
    render(
      <MarketDepthPanel
        depth={response}
        english={false}
        error={null}
        loading={false}
        priceScale={2}
        quoteCurrency="USDT"
      />,
    );

    expect(screen.getByText("盘口已陈旧 · 90s")).toBeVisible();
    expect(screen.getByText("100.50")).toBeVisible();
    expect(screen.getByText("价差 1.00")).toBeVisible();
  });
});
