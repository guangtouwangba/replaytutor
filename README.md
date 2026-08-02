# ReplayTutor

**Train decisions, not hindsight.**

[简体中文](README.zh-CN.md) · [Architecture](docs/ARCHITECTURE.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)

> Alpha software for local research and deliberate practice. ReplayTutor is not a broker, does not place live orders, and does not promise trading returns.

[![ReplayTutor English demo](apps/web/public/media/replaytutor-demo-readme.gif)](apps/web/public/media/replaytutor-demo-en.mp4)

[Watch the English demo (MP4)](apps/web/public/media/replaytutor-demo-en.mp4) · [观看中文演示 (MP4)](apps/web/public/media/replaytutor-demo-zh.mp4)

ReplayTutor is a local-first, multi-market trading replay and AI review workbench. It hides future market data, computes simulated execution deterministically, and gives an AI Tutor a read-only evidence package tied to the exact replay frame.

## Why ReplayTutor

- **No look-ahead:** the server owns `frame_id` and `visible_at`; future bars never enter the replay UI or Tutor context.
- **Deterministic execution:** matching, fees, P&L, MFE/MAE, and ledger entries are application code—not model guesses.
- **Auditable AI:** Tutor observations cite bars, orders, fills, notes, and chart annotations from the current evidence bundle.
- **Local first:** market data, SQLite metadata, Parquet snapshots, reports, and Agent runs stay on your machine.
- **Useful on day one:** a bundled BTCUSDT 1-minute snapshot runs without an API key.

## Three-minute quick start

Requirements: macOS or Linux, Node.js 24 with Corepack, Python 3.12, `uv`, and GNU Make. WSL is experimental.

```bash
git clone https://github.com/guangtouwangba/replaytutor.git
cd replaytutor
make setup
make doctor
make demo
```

Open [http://127.0.0.1:5174](http://127.0.0.1:5174). The demo uses an isolated data directory and the bundled BTCUSDT fixture. For normal development, run `make dev` and open port 5173.

If startup reports a busy port, `make dev` now prints the owning process before exiting. Stop only the process you recognize, then retry.

## Automatic market data

Training setup supports BTCUSDT and ETHUSDT spot or USDT perpetual contracts.

- Local snapshots are reused when they cover the requested range.
- Missing coverage is downloaded from Binance public market-data endpoints.
- The default range is 30 days; one-year downloads are available.
- No Binance key is required for public OHLCV history.
- Every successful import creates a new immutable Parquet snapshot.

Private Binance fills are an optional, read-only review workflow. Never grant ReplayTutor trading, withdrawal, leverage, or account-management permissions.

## Demo video

The homepage lazily loads a bilingual Remotion demo. Its source lives in `apps/demo-video`; Playwright prepares an isolated session and records browser footage.

- [English demo](apps/web/public/media/replaytutor-demo-en.mp4) — English UI and captions.
- [Chinese demo](apps/web/public/media/replaytutor-demo-zh.mp4) — Chinese UI and captions.

```bash
make demo-video
```

Individual stages are also available:

```bash
pnpm demo:prepare
pnpm demo:record -- --locale en-US
pnpm demo:render
pnpm demo:verify
```

Raw recordings are ignored. Only reviewed posters, captions, and optimized release videos belong in Git.

The ReplayTutor application code is Apache-2.0. Remotion tooling is distributed under the separate [Remotion License](https://www.remotion.dev/license); check its eligibility terms before using the video workspace for a company.

## Architecture at a glance

```text
React/Vite UI
  └─ versioned JSON contracts
       └─ FastAPI application
            ├─ immutable Parquet + DuckDB market snapshots
            ├─ SQLite metadata and event ledger
            ├─ deterministic replay/execution/rules modules
            └─ read-only isolated Coding Agent adapters
```

Market-specific behavior goes through adapters. AI output cannot modify orders, fills, the ledger, or market data. See [Architecture](docs/ARCHITECTURE.md), [Security model](docs/SECURITY_MODEL.md), and [Agent binding](docs/AGENT_BINDING.md).

## Development

```bash
make setup       # locked JS/Python dependencies, migration, hooks
make doctor      # local dependency and port diagnostics
make dev         # API :8788 + Web :5173
make verify      # contracts, lint, types, unit tests, build, artifact scan
make e2e         # isolated browser acceptance tests
```

The contract flow is Pydantic → JSON Schema → generated TypeScript/Ajv. After changing a public model, run:

```bash
pnpm contracts:update
```

## Internationalization

The public UI supports `en-US` and `zh-CN`; English is the fallback. Language choice is stored in local preferences and sent through `Accept-Language`. Stable API error codes remain language-independent.

User-authored playbooks, notes, and historical Tutor output are never silently machine-translated.

## Status and roadmap

`v0.1.0-alpha.1` focuses on a trustworthy local loop: data → hidden-future replay → paper execution → evidence-linked review. See [ROADMAP.md](ROADMAP.md) and [CHANGELOG.md](CHANGELOG.md).

Not in Alpha: live trading, cloud accounts, collaboration, mobile trading, arbitrary strategy scripts, or return claims.

## Contributing

Bug reports, reproducible fixtures, market-rule adapters, accessibility fixes, and contract tests are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md) first.

Security issues should follow [SECURITY.md](SECURITY.md), not a public issue.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

ReplayTutor does not copy TradingView branding, proprietary icons, text, pixel-level layouts, or its closed-source Charting Library.
