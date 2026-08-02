# ReplayTutor architecture

ReplayTutor is a local React/Vite client backed by FastAPI. SQLite stores business metadata and immutable events; Parquet stores market snapshots and DuckDB queries them. Pydantic models generate JSON Schema and TypeScript/Ajv contracts.

## Deterministic core

Replay state, matching, fees, positions, ledger journals, P&L, MFE/MAE, and market-rule checks are deterministic modules. Identical inputs and rule versions must reproduce identical events.

The server issues `frame_id` and `visible_at`. Every replay response, chart query, order command, account view, and Tutor context is clipped to that boundary. An order submitted after observing a completed bar cannot activate before the next bar.

## Adapters

- Market Data Adapter normalizes public or imported OHLCV into immutable snapshots.
- Market Rules Adapter owns venue calendars, tick/step sizes, settlement, limits, and fees.
- Chart Adapter maps visible bars and evidence into the open-source chart engine.
- Agent Adapter runs supported Coding Agents in isolated read-only workspaces.

Market-specific behavior must not be scattered through UI branches.

## AI and locale boundaries

Tutor consumes a versioned, stage-specific evidence bundle. Replay-stage bundles physically exclude future bars, later fills, final P&L, and after-action metrics. Output must validate against JSON Schema and reference only evidence IDs present in the bundle.

AI can explain evidence and propose annotations. It cannot submit orders, create fills, update the ledger, modify market data, or calculate canonical metrics.

`en-US` and `zh-CN` are supported public locales. Locale changes presentation and generated prose, never identifiers, numeric truth, timestamps, matching behavior, or evidence membership.
