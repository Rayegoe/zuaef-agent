# Branch B — Delete Duplication (T003 + T005) — Verification Record

Status: **VERIFIED COMPLETE on `main`** — user chose "verify and report only; no new worktree/branch".

Verified at: 2026-08-19 ~13:4x CST, `git rev-parse HEAD` = the moving tip of `main`
(records below were re-checked against the live tree at each step; two T003/T005
commits are stable on `main` and untouched by later commits).

## Scope

| Task | Definition | Expected result |
|---|---|---|
| T003 | Delete ZUAEF custom tool-name conflict preflight; upstream composition owns collisions | `DELETE`, no replacement registry |
| T005 | Use official provider/profile behavior; delete duplicated DeepSeek/model capability flags; keep only deployment glue | `DELETE` duplicated flags, `KEEP` deployment glue |

## Evidence

### T003 — tool-conflict preflight deleted

Commit `08c10a9` (`refactor: remove duplicate substrate and private persistence coupling`):

- Deleted from `src/zuaef_agent/composition.py`: `_check_tool_conflicts`, `_tool_names`, `_claim`
  (the entire preflight: per-plugin tool enumeration + duplicate-name rejection via `CompositionError`).
- `resolve_profile` no longer calls the conflict check; a comment documents that tool-name
  collisions are owned by upstream composition (PydanticAI raises its own `UserError` at schema
  collection — no silent override), so ZUAEF runs no second preflight.
- No replacement registry/bridge/adapter was introduced.

Regression test: `tests/test_plugin_composition.py::test_duplicate_tool_fails_no_silent_override`
(lines 414–449). It proves: resolution SUCCEEDS (no preflight raise), then materializing the
composed agent's tool schema raises PydanticAI's own `UserError` matching "conflicts".

Static contract: `tests/test_core_contract_static.py` asserts `AgentRegistry` / `StateMachine`
are absent from `core.py`.

### T005 — provider profile duplicates deleted

Commit `9b98c9a` (`refactor: resolve models through official provider profiles (T005)`):

- `src/zuaef_agent/providers.py` now resolves DeepSeek models through the official
  `pydantic_ai.providers.deepseek.DeepSeekProvider` (whose `deepseek_model_profile` owns
  thinking-field/tool-choice/json-object flags) and generic OpenAI-compatible endpoints through
  `OpenAIProvider` with its official default profile.
- Deleted from `AgentSettings` (`src/zuaef_agent/config.py`): hand-copied capability flags
  `openai_strict_tool_definitions`, `multiple_system_messages`, `supports_max_completion_tokens`.
- Kept (deployment-specific transport/config only): base URL, api key, http(s) proxy
  resolution, timeouts, retries, explicit DeepSeek thinking toggle, optional
  `…/chat/completions` suffix normalization (added later by the main line as
  transport glue; consistent with the T005 rule).

Tests: `tests/test_cli_and_providers.py` — `test_deepseek_uses_official_provider_profile`,
`test_deepseek_v4_does_not_force_tool_choice`, `test_generic_endpoint_uses_official_default_profile`,
plus `assert not hasattr(settings, "openai_strict_tool_definitions")`.

## Constraint check

| Constraint | Result |
|---|---|
| No new AdapterManager / Registry / Bridge | PASS — none in `src/` (grep + static contract test) |
| Gateway untouched by T003/T005 | PASS — both commits touch only composition/verification/providers/config + tests + manifest |
| Memory / SubAgent / generalist composition untouched | PASS — generalist surface is separate T006+ work (`core.py`/`config.py`), not in these commits |
| plugin_api.py stays a thin contract | PASS — plugin contract types only, no runtime/preflight/registry |

## Test evidence (measured)

- Targeted: `test_plugin_composition.py` + `test_cli_and_providers.py` + `test_core_contract_static.py`
  → **41 passed** against the live tree at verification time.
- Full suite on the live tree: **497 passed, 1 failed** — the single failure is
  `test_manifest_integrity.py` (manifest hash/size drift for `tools/fde_two_turn_proof.py`,
  an untracked file belonging to concurrent in-flight T013 work). Not a stable `main` defect
  and outside Branch B scope.
- Ruff on HEAD-committed files: clean at T003/T005 commit time.

## Findings (cosmetic leftovers of the T003 deletion)

Three stale references still claim ZUAEF composition itself detects tool conflicts; they
contradict the implemented upstream-ownership behavior:

1. `src/zuaef_agent/composition.py:5` — module docstring "…detecting tool conflicts, …"
2. `src/zuaef_agent/composition.py:213` — `resolve_profile` docstring "enforce the capability
   policy and tool-conflict rules"
3. `src/zuaef_agent/cli.py:82` — `profile check` help "(loads factories, validates bundles,
   detects conflicts) without any model request"

Fixing them touches `BUILD_MANIFEST.json` (hash-locked delivery tree), so it was NOT done in
this verify-only pass. Safe to do later as a one-line strings commit + `tools/regen_manifest.py`.

Note: file names differ from the Branch B briefing's prediction — coverage lives in
`tests/test_plugin_composition.py` (not `tests/test_composition*.py`) and
`tests/test_cli_and_providers.py` (not `tests/test_provider*.py`). Coverage exists; names differ.

## Worktree decision

Per user's explicit choice: NO new worktree / git branch was created. The suggested
`worktree/upstream-delete-duplication` does not exist and is unnecessary — the complete
Branch B scope is already committed to `main` (`08c10a9` T003, `9b98c9a` T005) and tested.

## Verdict

```text
T003: DELETE confirmed (preflight removed, no replacement registry)
T005: DELETE confirmed (hand-copied capability flags removed, official profiles used)
Branch B: PASS
```