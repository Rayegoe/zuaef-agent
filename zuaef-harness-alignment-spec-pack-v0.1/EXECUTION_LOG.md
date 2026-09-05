# Harness Alignment Lane — Execution Log (v0.1)

Executed: 2026-09-05. Lane: `zuaef-harness-alignment-spec-pack-v0.1` H000–H014.
Authority: repository `AGENTS.md`, `zuaef-runtime-coach`, `docs/runtime-refoundation/*`,
and this pack. This lane is a **compatibility lane, not a capability promotion**.

## H000 — Read authority & freeze scope ✅

Read: `AGENTS.md`, `zuaef-runtime-coach/SKILL.md`,
`docs/runtime-refoundation/CAPABILITY_ADMISSION.md`, `docs/runtime-refoundation/TASKS.md`,
this pack. Next unfinished runtime-refoundation task recorded: **T007 (still deferred)**;
the queue's next causal boundary is the shared-evidence-interpretation experiment
(specified, not started). Lane did not alter that order. No production change at this step.

## H001 — Version matrix ✅

| | Declared | Resolved |
|---|---|---|
| Production | `pydantic-ai>=2.35.3,<3`; `pydantic-ai-harness[skills,code-mode]>=0.27,<0.28` | 2.35.3 / 0.27.0 |
| Candidate | `pydantic-ai>=2.38,<3`; `harness>=0.29,<0.30` | **2.40.0 / 0.29.0** |

Upstream truth (fetched from upstream `pyproject.toml` @ v0.29.0):
`pydantic-ai-slim>=2.38.0` floor, `code-mode` extra = `pydantic-ai-slim[duckduckgo]>=2.38.0`
+ `pydantic-monty>=0.0.19`. 0.27.x is the ZUAEF production line, **not** upstream latest
(upstream latest = 0.29.0 as of 2026-09-05).

## H002 — Baseline focused tests ✅

68 passed on current dependency set (2.12s), no pre-existing failures in the focused set.
Files: generalist_activation, phase2_generalist_policy, phase2_deferred_tools,
plugin_composition, continuation, execute_run_seam, writing_codemode_skills.

## H003 — Disposable 0.29 worktree ✅

`git worktree add -b harness-029-compat /tmp/zuaef-harness-029 HEAD` (HEAD `eb0fe84`).
Candidate deps resolved cleanly. Lock diff = 8 packages, all floor-driven
(harness, pydantic-ai, slim, evals, graph, anthropic, openai, genai-prices); no
gratuitous unrelated upgrade. `uv sync` OK; candidate imports OK. **Not**
`HOLD_0_27_DEPENDENCY_CONFLICT`.

## H004 — Candidate focused tests, no repair ✅

Same 68 tests on candidate, unchanged: **68/68 pass**. Zero failures → nothing to classify.

## H005 — Private harness test coupling

Closed **NOT_NEEDED_CANDIDATE_UNBROKEN** (zero production change): the pack makes this
conditional on the candidate demonstrating the need; 0.29 did **not** break
`Skills._deferred_capabilities` (`test_writing_codemode_skills.py` passes unchanged).
The private coupling remains a recorded future-maintenance item — revisit when an
upstream release actually moves it.

## H006 — Pause/resume compatibility proof ✅

`tests/test_continuation.py` (real `execute_run` → `resume_paused_run` seam) all pass
on candidate, both approve and deny paths:
approve-executes-and-settles, deny-no-execution, non-paused-rejected,
**frozen-composition-ignores-mutable-profile (process-boundary simulation)**,
version-drift-fails-before-model-request. `test_execute_run_seam.py` 15/15.
`ContinuableSnapshot`/`FileStepStore` assumptions hold; no code change needed.

## H007 — Capability/tool surface diff ✅

`EXECUTION/surface_diff.py` (deterministic FunctionModel capture of
`AgentInfo.function_tools`, same technique as the repo's own tests). Five surfaces:
`ace-writing` (22), `stillevo-fde` (26), `quant-decision` (32), host repo+shell (25),
host toolsearch (20) — **125 tool names byte-identical** between baseline (0.27) and
candidate (0.29). No unexplained new production-visible tools; no surface naming/schema
drift observed.

## H008 — FileSystem / ToolOutputLimits / context-control proof ✅

Candidate: `test_knowledge_invariants.py` (protects knowledge area, symlink-escape
rejected, atomic write), `test_context_management_baseline.py` (oversized-return spill,
clear-tool-results, context controls ready / not composed on narrow surface) — all pass.
Behavior flows through upstream primitives; no local clones added.

## H009 — CJK ToolSearch compatibility proof ✅

`test_phase2_deferred_tools.py` (5) + `test_p3b3_tool_surface.py` (5, includes Chinese
intent discovery) all pass on candidate. Only the documented strategy extension point is
used (`cjk_keywords_search_fn` → `ToolSearch(strategy=...)`); no fork/registry.

## H010 — CodeMode compatibility proof ✅

`test_writing_codemode_skills.py` 5/5 on candidate: selector wraps context and excludes
save, legacy tagging, plugin capability when configured, profile composes, deferred
skills. No production default change.

## H011 — Full repository regression ✅ (promoted stack)

Candidate (0.29.0 / 2.40.0), after promotion changeset: **1007 passed, 2 skipped**
(2 skips = `data/derived` absent, CI standard). `uv run ruff check .` clean both trees.

Failure classification (pre-promotion run, 3 failures):
- `test_deepseek_v4_does_not_force_tool_choice` → **EXPECTED_UPSTREAM_BEHAVIOR_CHANGE**:
  pydantic-ai ≥2.38 official DeepSeek profile now reports
  `openai_supports_tool_choice_required=True` for deepseek-v4 / v4-flash (was False on
  2.35.3; the test passes on the baseline). ZUAEF mirrors the official profile, so the
  assertion follows upstream truth (test updated with rationale).
- `test_manifest_integrity.py` ×2 → **UNRELATED_PREEXISTING** (also fail on baseline `main`:
  `BUILD_MANIFEST.json` stale — missing `tests/test_quant_v31.py`/`tools/quant_v31.py` and
  toolset.py byte drift from `eb0fe84`). Fixed as part of the promotion changeset by the
  canonical `tools/regen_manifest.py` (uv.lock is manifest-scoped, so regen is required by
  the promotion anyway). In the lane worktree there was an additional pyproject size-drift
  entry caused by the lane's own dependency edit — disappeared after the canonical regen.

## H012 — Optional live canary

Not executed in this lane (deterministic gates + full regression green; canary is
optional and adds real-model quota). Recorded recommendation: run one read-only
analysis task in the real gateway session **after** deployment sync, and specifically
watch deepseek-v4 `tool_choice` behavior given the upstream profile change (H011).

## H013 — Promotion decision ✅

Verdict: **PROMOTE_0_29**

All acceptance gates pass (architecture A, dependency B, public-behavior C1–C7,
test-quality D, runtime-complexity E, promotion rule F). No architecture expansion;
no new global capability; no new hash/checksum machinery; no second runtime/approval/
durable store/registry.

Promotion changeset (main checkout, uncommitted pending review):
1. `pyproject.toml` — `pydantic-ai>=2.38,<3`; `pydantic-ai-harness[skills,code-mode]>=0.29,<0.30` (comment documents lane).
2. `uv.lock` — refreshed (`uv lock`); 8 floor-driven package moves.
3. `tests/test_cli_and_providers.py` — deepseek-v4 test follows new upstream truth (with rationale).
4. `BUILD_MANIFEST.json` — regenerated via `tools/regen_manifest.py` (canonical tool).

Deployment note (not done by this lane): main `.venv` is not yet synced; the next
`uv run` (e.g. gateway restart via systemd `Restart=on-failure`) will auto-sync the
environment to 0.29.0 / 2.40.0. Verify live behavior after that sync (see H012).

Recorded caveat: the deepseek-v4 profile change is an intentional upstream claim; if
production routes deepseek-v4 requests, forced-`tool_choice` request behavior may change.
Tracked in H012 recommendation, not a promotion blocker (upstream states support).

## H014 — New-capability watchlist (audit only) ✅

No reproduced ZUAEF failure or deployment contract requires any of these in this lane:

| Capability | Verdict |
|---|---|
| PromptInjectionDefender | `EXPERIMENTAL_CANDIDATE` — not admitted (needs reproduced indirect-injection failure on a real research surface) |
| Guardrails | `NOT_ADMITTED` |
| DynamicWorkflow | `EXPERIMENTAL` only, never default topology |
| Spend | `NOT_ADMITTED` (run-local `UsageLimits` remains; no cross-window USD-budget requirement) |
| Researcher / Coder | `DELEGATE_OR_PROFILE_CANDIDATE` — no demonstrated task-class benefit; do not replace core |
| durable-execution backends (Temporal/DBOS/…) | `NOT_ADMITTED` — StepPersistence seam passed the H006 pause/resume gates on 0.29 |
| CapabilityCreation | `QUARANTINED_FROM_PRODUCTION_CORE` — conflicts with frozen composition/authority |

Watchlist unchanged. The 0.28/0.29 upstream additions introduced no admitted candidates.

## Lane closeout

- Evidence artifacts: `EXECUTION/surface_diff.py`; this log; the disposable worktree
  `/tmp/zuaef-harness-029` (kept for inspection; `git worktree remove` after commit).
- `.env` copy made in the worktree for symmetric profile composition was local-only
  and removed after the lane.
- The promotion decision record above is the pack's required
  "markdown decision record + tests + dependency diff"; no new ceremony was added.
