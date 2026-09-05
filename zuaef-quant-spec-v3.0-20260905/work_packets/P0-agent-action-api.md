# WP2 — Agent Action Surface

## Goal
Make Quant operable by Agent through stable structured actions rather than HTML scraping.

## Tasks
- L0: status, attention, candidates, decision, positions, observations.
- L1: once, settle, report, replay start/status.
- common envelope/version/mode/reason codes.
- idempotency for retriable controls.
- explicit domain outcomes vs runtime failures.
- register with ZUAEF-Agent using existing tool mechanism.

## Prohibited
No real broker order tool in this work packet.

## Acceptance
Agent can diagnose current 50-candidate/0-trigger state through structured data and trigger safe replay/settlement without writing production config.
