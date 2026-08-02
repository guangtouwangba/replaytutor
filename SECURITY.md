# Security policy

## Supported version

Only the latest Alpha release and the current default branch receive security fixes.

## Reporting

Use GitHub private vulnerability reporting. Do not open a public issue for a suspected vulnerability or include credentials, private fills, database files, or Agent workspaces in a report.

## Trust boundaries

- ReplayTutor binds locally by default and does not provide live-trading endpoints.
- Public Binance market data requires no key.
- Private trade review must use read-only credentials with no trading, withdrawal, leverage, or account-management permissions.
- Coding Agents run in isolated directories with read-only evidence and structured output validation.
- AI output cannot update market data, orders, fills, ledger events, or deterministic metrics.

See [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md) for the full model.
