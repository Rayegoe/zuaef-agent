# T014A — Capability-owned Result Contract proof: execution record

Date: 2026-08-20.

## Unit proof (offline, real plugins)

`tests/test_result_contract.py` (rewritten; 3 tests):

- **I1 one generic terminal**: the REAL `BudgetedWritingToolset`
  (ace-writing), the REAL budget toolset (zuaef-emtb-budget, deterministic
  budget_lib) and the REAL client-service toolset (over the synthetic corpus
  fixture) are each composed through `build_agent + execute_run`. All three
  settle as natural `str` presentations with one receipt schema
  (`RunReceipt`) and zero domain fields; the budget/client scripted models
  actually exercise the real domain tools (`parse_budget_csv`,
  `budget_variance`, `retrieve_client_context` visible in
  `tool_effect_facts`).
- **I2 kernel zero-diff**: a structure-only change owned by the budget
  capability (`BUDGET_RULES` instructions gain a clause) reaches the toolset
  surface while `models.py` / `runtime.py` / `plugin_api.py` stay
  byte-identical.
- **I3 no universal result schema**: no `BusinessResult`/`ResultSchema`/
  `ResultRegistry`/`DeliverableType` class in the kernel.

## Real-model proof

`tools/result_contract_proof.py` (mechanical driver; refuses to run without
credentials) — command:

```
uv run python tools/result_contract_proof.py [--only writing|budget|client]
```

Evidence under `workspace/artifacts/result-contract-proof/`:

| Domain | Deliverable | Real tools driven | Receipt |
|---|---|---|---|
| writing | 真文章：约 300 字公众号短文（结论前置、无价格、场景取自素材） | — (pasted-material rewrite path, natural terminal) | RunReceipt, completed |
| budget | 真预算分析：数字→偏差→含义，含百分比口径 | parse_budget_csv, budget_variance, budget_summary, significant_changes, budget_consistency, budget_health | RunReceipt, completed |
| client | 真客户回复：中文、面向李姐、说明改法与不变约束、无政策外承诺 | retrieve_client_context + harness search/memory/record_interaction | RunReceipt, completed |

All three settled through the SAME generic terminal (`str` presentation) and
one receipt schema; the runtime contributed the identical contract to all
domains and knew none of them.

## Verdict

PASS. Result shaping lives in capability toolset instructions + domain tools;
the Kernel's `str | DeferredToolRequests` terminal is unchanged and needs no
domain knowledge.
