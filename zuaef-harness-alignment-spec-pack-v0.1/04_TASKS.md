# TASKS — Harness Alignment / Compatibility Lane

Rule: execute in order. A task may close with zero production code change.

## H000 — Read authority and freeze scope

Read:

- `AGENTS.md`
- `.agents/skills/zuaef-runtime-coach/SKILL.md`
- `docs/runtime-refoundation/CAPABILITY_ADMISSION.md`
- current `docs/runtime-refoundation/TASKS.md`
- this spec pack

Record the next unfinished runtime-refoundation task. Do not alter its order.

Acceptance:

- scope explicitly says "compatibility lane, not capability promotion";
- no production change yet.

## H001 — Record version matrix

Capture from current branch/environment:

- declared `pydantic-ai` range;
- declared Harness range;
- resolved versions from `uv.lock`/environment;
- candidate Harness 0.29.x requirements.

Expected declared baseline:

```text
pydantic-ai >=2.35.3,<3
pydantic-ai-harness[skills,code-mode] >=0.27,<0.28
```

Candidate upstream floor:

```text
pydantic-ai-slim >=2.38.0
pydantic-ai-harness 0.29.x
```

Acceptance:

- production and candidate versions are separately named;
- no claim that 0.27.x is upstream latest.

## H002 — Baseline focused tests on current dependency set

Run the smallest current tests that cover the public Harness boundary, including at least:

```text
tests/test_generalist_activation.py
tests/test_phase2_generalist_policy.py
tests/test_phase2_deferred_tools.py
tests/test_plugin_composition.py
tests/test_continuation.py
tests/test_execute_run_seam.py
tests/test_writing_codemode_skills.py
```

Also include any existing focused FileSystem/protected-path and ToolOutputLimits tests discovered in the repository.

Acceptance:

- current baseline is green or pre-existing failures are recorded before candidate testing.

## H003 — Create disposable 0.29 compatibility branch/worktree

In a disposable branch/worktree only:

- move Harness range to `>=0.29,<0.30`;
- ensure PydanticAI resolves to a compatible `>=2.38,<3` version;
- refresh lock for the candidate environment;
- do not merge dependency changes yet.

Acceptance:

- candidate environment resolves cleanly, or close `HOLD_0_27_DEPENDENCY_CONFLICT` with the exact conflict.

## H004 — Run focused candidate tests without repair

Run the H002 focused set unchanged first.

Classify every failure:

- `PUBLIC_API_BREAK`
- `PRIVATE_TEST_COUPLING`
- `EXPECTED_UPSTREAM_BEHAVIOR_CHANGE`
- `DEPENDENCY_RESOLUTION`
- `ZUAEF_BUG_EXPOSED`
- `UNRELATED_PREEXISTING`

Do not edit code before this classification.

Acceptance:

- each failure has one class and one concrete reproduction.

## H005 — Remove private Harness test coupling where behavior can be observed publicly

Primary known target:

```text
tests/test_writing_codemode_skills.py
```

Replace reliance on `Skills._deferred_capabilities` with a public/observable proof of the actual contract, if the candidate demonstrates this is needed.

Do not alter production runtime merely because a private test member moved.

Acceptance:

- the test proves deferred skill catalog/loading behavior through supported observable behavior;
- no new wrapper around Harness internals is introduced.

## H006 — Pause/resume compatibility proof

Exercise the real ZUAEF continuation seam using local deterministic fixtures:

```text
initial run
  -> DeferredToolRequests
  -> pause receipt/frontier persisted
  -> simulate process boundary by rebuilding from stores
  -> continue_run(include_interrupted=True)
  -> DeferredToolResults(approve or deny)
  -> new run id / same conversation / frozen composition & bindings
  -> terminal result
```

Prove both approve and deny paths.

Acceptance:

- no fresh-prompt substitution;
- no lost binding/composition authority;
- no duplicated external effect fixture;
- terminal/paused receipts remain internally consistent.

If the candidate breaks `ContinuableSnapshot` or `FileStepStore` assumptions, record the exact public/private seam before changing code.

## H007 — Capability/tool surface diff

For representative profiles/tasks, capture model-visible tools/capabilities under baseline and candidate.

At minimum:

- narrow writing profile;
- repo + shell authorized profile;
- tool-search/deferred-tool profile;
- subagent authorized profile.

Acceptance:

- no unexplained new production-visible tools;
- any upstream naming/schema change is explicitly reviewed;
- no capability is promoted simply to regain a prior test shape.

## H008 — FileSystem / ToolOutputLimits / context-control compatibility proof

Prove:

- protected patterns still block the intended writes;
- no path traversal regression;
- oversized output is still bounded/spilled as intended;
- configured context controls compose without changing default profile admission.

Acceptance:

- behavior passes through upstream primitives; no local clones added.

## H009 — CJK ToolSearch compatibility proof

Prove:

- ASCII tool discovery behavior remains compatible with upstream intent;
- Chinese queries still discover intended deferred domains;
- unrelated Chinese queries do not broadly activate unrelated domains.

Acceptance:

- only the documented strategy extension point is used;
- no ToolSearch fork or registry is introduced.

## H010 — CodeMode compatibility proof

Use the existing ACE-writing experimental path.

Prove:

- only intended tool definitions carry CodeMode metadata/selection;
- write/submit/external actions remain outside CodeMode where current policy requires;
- CodeMode remains profile-explicit.

Acceptance:

- no production default change.

## H011 — Full repository regression

Run ordinary repository gates after focused compatibility passes:

```text
uv run pytest
uv run ruff check .
```

Use the repository's canonical commands if they differ.

Acceptance:

- full regression passes, or candidate is held with exact unrelated vs candidate-caused failures separated.

## H012 — Optional read-only live canary

Only after deterministic gates pass, run one small real model canary that exercises existing behavior without external mutation.

Preferred shape:

- one ordinary analysis/repository task or existing read-only profile;
- no new capability;
- no live publish/send/trade action.

Compare:

- outcome adequacy;
- requests;
- tool calls;
- visible tool surface;
- context/token behavior where available.

Acceptance:

- no material regression attributable to dependency promotion.

## H013 — Promotion decision

Produce one verdict:

- `PROMOTE_0_29`
- `HOLD_0_27_PUBLIC_BREAK`
- `HOLD_0_27_DEPENDENCY_CONFLICT`
- `HOLD_0_27_BEHAVIOR_REGRESSION`
- `REFINE_TEST_PRIVATE_API_ONLY`

If `PROMOTE_0_29`:

- update production dependency range and lock;
- keep the same architecture/capability defaults;
- record the compatibility evidence.

If hold:

- revert candidate dependency edits;
- leave production behavior unchanged;
- record the smallest blocking fact.

## H014 — New-capability watchlist (audit only)

Review upstream additions only as candidates, not tasks to implement:

- PromptInjectionDefender
- Guardrails
- DynamicWorkflow
- Spend
- Researcher/Coder combined capabilities
- durable-execution backends
- CapabilityCreation

For each, answer only:

```text
Is there a reproduced ZUAEF failure or deployment contract that requires this now?
```

If no: record `NOT_ADMITTED` and stop.
