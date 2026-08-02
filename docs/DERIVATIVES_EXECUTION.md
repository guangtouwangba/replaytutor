# Derivatives execution contract

ReplayTutor keeps market facts, execution facts, and AI review separate. The
matching engine and ledger are the only authorities allowed to create fills,
margin changes, funding transfers, or liquidations.

## Supported account modes

- Spot and linear USDT-margined perpetual futures.
- Isolated and cross margin.
- One-way positions (`BOTH`) and hedge positions (`LONG` / `SHORT`).
- Session leverage from 1x to 125x.
- Maker/taker fees, maintenance margin, configurable funding interval/rate,
  unrealized and realized P&L, available margin, and liquidation price.

The account mode is fixed when a replay session is created. A perpetual account
requires a `crypto_perpetual` Snapshot, so spot candles cannot silently be
presented as futures market evidence.

## Supported order lifecycle

- Market, limit, stop-market, stop-limit, take-profit-market,
  take-profit-limit, and trailing-stop-market.
- GTC, IOC, FOK, and GTD.
- Reduce-only, close-position, post-only, amend, cancel, bracket, and OCO.
- Partial fills use a deterministic 10% participation cap against each
  one-minute bar's base-asset volume.

Orders activate on the next bar. Stop-limit orders become eligible on the bar
after their trigger because OHLC data cannot establish whether the limit was
reachable after the trigger within the same candle. Trailing stops likewise use
the prior anchor before considering a new intrabar extreme.

## Risk and evidence boundaries

- Funding defaults to zero. A non-zero session rate is an explicit simulation
  parameter until historical funding-rate events are imported alongside the
  Snapshot.
- Liquidation is evaluated against the visible bar's adverse extreme and the
  configured maintenance margin. The current model is a single-symbol replay
  account; portfolio margin and multi-asset collateral are outside this
  contract.
- Bar-volume participation is a replay model, not an order-book reconstruction.
  It must be shown as simulated liquidity in reviews.
- Options, dated futures, inverse/coin-margined contracts, ADL, insurance-fund
  settlement, and exchange-specific risk tiers are not represented yet.

AI review may cite these facts and annotate the chart, but it cannot submit,
amend, cancel, fill, fund, or liquidate an order.
