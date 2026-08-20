# T014B — Remove Pydantic workflow gates: execution record

Date: 2026-08-20. Scope: production capability surface only; benchmark assets
demoted, not deleted.

## 1. EditorialControl moved off the production capability surface

| What | Before | After |
|---|---|---|
| Capability module | `plugins/zuaef-ace-writing/zuaef_ace_writing/editorial.py` | `benchmarks/editorial-learning/legacy/editorial_capability.py` (docstring marked LEGACY/BENCHMARK-ONLY) |
| Production factory | `editorial_control = true` composed `EditorialControlCapability` | every `editorial_*` config key raises `CompositionError` pointing at the legacy location |
| Plugin exports | `__init__` re-exported the editorial names | removed |
| Profiles | `ace-writing-editorial.toml` (experimental ON side) | deleted; `ace-writing*.toml` carry no `editorial_*` keys |
| Authority note | — | `benchmarks/editorial-learning/legacy/README.md` records QUALITY_LOOP §11 rules |

Rationale: Phase 9 blind A/B showed no stable advantage of editorial control
ON over OFF, and the save veto is a regex-drift-driven machine gate on taste —
exactly the semantic-authority pattern v1.2 removes. The production writing
path is now model-driven through the toolset instructions and skills only.

## 2. Sensors / veto / evidence weight demoted to benchmark/legacy

- `run_trajectory_sensors`, `combined_drift`, the save veto, and
  `EditorialEvidence.weight` / `approved_by` survive only inside
  `benchmarks/editorial-learning/legacy/` and are imported exclusively by
  benchmark scripts, benchmark experiments, and their tests.
- `benchmarks/editorial-learning/evidence/human_patches.jsonl` and
  `compiled/evidence.jsonl` rows (`trigger_signals`, `action`, `weight`,
  `approved_by`) are legacy derived features, not human truth. The
  authoritative learning record is the document-first case packet under
  `learning/cases/`.
- Static guard added (`test_editorial_control_is_not_on_the_production_surface`):
  no editorial-control identifier may appear in the production plugin package,
  and no production profile may carry an `editorial_*` key.

## 3. Per-tool cognitive budget re-audit (writing tools)

Audited `BudgetedWritingToolset` (`writing_toolset.py`):

| Mechanism | Verdict | Why |
|---|---|---|
| `retrieve_exemplars` cap 6 / run | KEEP | Resource cap counted from ACE receipts (durable, resume-safe) + in-process counter. Protects an external engine from runaway pulls. |
| `retrieve_knowledge` cap 4 / run | KEEP | Same basis. |
| `check_claim` cap 8 / run | KEEP | Same basis; exhausted tool returns a bounded skip note. |
| Action-space withdrawal via `get_tools` | KEEP | The blessed Toolset-local call policy (AGENTS.md layer model: budgets + tool withdrawal belong to the toolset). |
| `retries=3` on observe tools | KEEP | Retry policy for transport flakiness, not a workflow gate. |
| Per-call `budget: int = 3` args | KEEP | ACE retrieval width passed through to the engine, not agent-process control. |

Conclusion: these are operational resource caps against a real external
system, not cognitive/workflow gates — no field-driven process logic, no
phase/status progression, no semantic completeness booleans. Nothing to
remove. The audit record lives here so the freeze (T015) can cite it.

## 4. Pydantic-not-workflow architecture guard

Added `test_kernel_pydantic_models_are_not_workflow_gates`
(`tests/test_architecture_guards.py`):

- kernel Pydantic models (BaseModel/BaseSettings) must not declare
  workflow-gate fields (`phase`, `stage`, `next_stage`, `next_action`,
  `quality_*`, `evidence_passed/weight`, `truth_score`, `completeness`,
  `is_complete`, `ready`, `validated`, `approved_by`, …);
- no drafting-process progression words as `Literal` members of a kernel
  model field (a field-gated writing workflow in disguise);
- Pydantic stays allowed where it models real data/config/API/persistence
  contracts (receipts, settings, profiles, gateway envelopes) — audited: all
  current kernel model fields are operational/persistence facts.

## 5. Test surface after T014B

- `tests/test_editorial_control.py` — Gate A inverted (production factory
  rejects `editorial_*` loudly, tool surface unchanged); capability behavior
  tests now import the legacy module; config-wiring tests replaced by
  rejection tests; composition tests use `code_mode = true` as the
  capability-carrying example.
- `tests/test_editorial_benchmark.py`, `tests/test_learning_pack_compiler.py`
  — imports retargeted to the legacy module; assertions unchanged.
- `benchmarks/editorial-learning/**` scripts — sys.path bootstraps extended
  with the legacy dir; all compile.
