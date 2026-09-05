# 13 — Observability, Dashboard & Telegram

## Current achievement

Latest report generation and Telegram delivery are operational. Preserve this path.

Dashboard/HTML is a **human projection** of underlying state. Agent should consume structured contracts directly.

## Attention model

Notifications should prioritize exceptions and actionability:

1. real `READY` trigger or exit attention;
2. `DO_NOT_PARTICIPATE`/regime change;
3. critical data/evidence degradation;
4. runtime/bridge failure;
5. experiment promotion/rejection summary;
6. routine no-action report.

## Daily brief

A compact machine/human brief should contain:

- market participation state;
- production decision;
- READY/NEAR counts;
- top attention candidates (bounded number);
- current positions/exit attention;
- data trust/PIT/freshness;
- live forward counts and settlements;
- replay/shadow experiment summary;
- runtime health.

## Zero-trigger report

Do not write “nothing happened.” Report whether:

- no true timing opportunity existed;
- market gate blocked participation;
- evidence gate blocked action;
- data was stale/insufficient;
- runtime failed.

## Delivery idempotency

A report delivery event is distinct from a trading decision. Retrying Telegram delivery must not create a new decision/evidence record.
