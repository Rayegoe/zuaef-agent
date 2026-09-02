# 09 — Codex Implementation Prompt

Implement the attached **ZUAEF Quant Business Dashboard + Candidate Discovery Spec v1.0** against the current repository state.

## Intent

The current quant work has enough engineering proof. This change must shift operator attention from software progress to market/strategy evidence.

The existing four-stock `user_watchlist` is a set of legacy holdings, not an adequate opportunity universe. Separate it from a broader deterministic candidate pool.

## Hard constraints

1. **Do not create a new framework, manager, DB, scheduler, daemon, broker integration, or workflow engine.**
2. Preserve the existing engineering/audit dashboard. Add a business dashboard rather than stuffing more sections into the old page.
3. Candidate discovery is deterministic. The LLM does not screen the full market.
4. Live actions still require the existing deterministic trigger evidence.
5. Candidate rank is not a buy order or profitability claim.
6. Empty/failed universe must fail closed; never convert `0 scanned / 0 trigger` into a legitimate `NO_TRADE` market conclusion.
7. Use file-native JSON/TOML artifacts and existing cache conventions.
8. Unit tests must not depend on live network.
9. Network source failures must be explicit. The deployment has already observed EastMoney transport failures; accepted fallback/cached sources need provenance/freshness.
10. Stop after the acceptance checklist passes.

## Required implementation order

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010.

Do not opportunistically refactor unrelated ZUAEF core code.

## Required final report

Return:
- changed files;
- commands run;
- test/lint results;
- candidate coverage and count from one real refresh if network permits;
- screenshot-free textual summary of the first business dashboard result;
- any degraded source path;
- explicit confirmation that engineering dashboard remains available;
- explicit confirmation that no scheduler/broker/DB/framework was added.

Do not commit or push unless explicitly instructed by the operator.
