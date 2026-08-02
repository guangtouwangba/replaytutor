# Contributing to ReplayTutor

Thanks for helping build a trustworthy trading-practice tool.

## Before opening a change

1. Read `DESIGN.md`, `docs/DESIGN.md`, `docs/SYSTEM_ARCHITECTURE.md`, and `docs/AGENT_BINDING.md`.
2. Open an issue for large behavior, contract, or architecture changes.
3. Never include credentials, private fills, personal paths, runtime databases, or generated Agent workspaces.

## Local workflow

```bash
make setup
make doctor
make verify
make e2e
```

Public contract changes must start in Pydantic and be regenerated with `pnpm contracts:update`.

## Non-negotiable invariants

- Do not expose data after `visible_at` to the replay UI or Tutor.
- Matching, fees, P&L, MFE/MAE, ledger updates, and rule checks stay deterministic.
- AI output is read-only and cannot modify orders, fills, ledger, or market data.
- Market differences belong in adapters, not scattered UI branches.
- New data-source and Agent adapters require shared contract tests.

## Pull requests

Keep PRs focused. Explain user-visible behavior, tests, screenshots for UI work, data provenance for fixtures, and any security or compatibility impact. Update English and Chinese public copy together.

By contributing, you agree that your contribution is licensed under Apache-2.0.
