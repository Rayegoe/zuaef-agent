# 19 — Runtime Questions Codex Must Verify

These are intentionally **not** answered by assumption.

1. What exact local branch/tree is currently running relative to GitHub `main`?
2. What service/timer units own the Quant loop and Telegram bridge today?
3. What is the canonical state/evidence store format and directory?
4. What command currently implements `status`, `once`, candidate build, live monitor, settlement, and report rendering?
5. What exact trigger vocabulary is present in code today (`READY/NEAR/...`)?
6. What is the actual intraday polling cadence?
7. Which current data providers supply daily bars, intraday data, financials, index membership, and corporate actions?
8. Which fields have trustworthy `available_at`/announcement timestamps today?
9. What exactly is included in the current 5 “true trade records” and how are they distinguished from replay/backtest records?
10. What code produces the reported PIT verdict and trust aggregation?
11. Is current position/cost basis sourced from system state, manual acknowledgement, or a broker/account source?
12. What is the exact production scoring config currently active?
13. Which prior fixes are already in the running tree but not yet pushed to Git?
14. Are there any uncommitted changes that would be overwritten by a checkout/reset?

Codex must create `BASELINE_RUNTIME.md` with answers before modifying files. A missing answer should be marked unknown, not guessed.
