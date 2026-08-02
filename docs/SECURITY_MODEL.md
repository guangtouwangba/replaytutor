# ReplayTutor security model

Protected assets include private trade history, market snapshots, local notes, SQLite metadata, Agent prompts/results, and optional read-only exchange credentials.

## Default posture

- Bind services to loopback and keep state under a configurable local directory.
- Do not expose live-trading endpoints.
- Treat imported files and Agent output as untrusted input.
- Keep credentials out of Git, logs, evidence bundles, reports, and videos.

## Agent isolation

Each Tutor run receives a new directory containing only a clipped context, allow-listed evidence, output schema, and audit manifest. The default environment is read-only, ephemeral, and has no broker credentials. Unsafe bypass flags are forbidden. Output must pass schema and evidence-ID validation.

## Exchange and recording boundaries

Public Binance OHLCV requires no credential. Optional private fill review must use the least-privileged read-only key; trading, withdrawal, leverage, margin, and account-management permissions are out of scope.

Demo recordings use an isolated temporary data directory, bundled fixture, UTC, and a fresh browser context. They do not reuse profiles, cookies, private datasets, or real Agent workspaces.
