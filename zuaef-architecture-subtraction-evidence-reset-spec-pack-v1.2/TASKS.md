# TASKS — Coding-Agent Execution List

## T000 — Baseline audit

**Goal:** establish exact current dependency surface.

Deliver:
- grep/inventory report;
- current full test result;
- list of files that consume old receipt evidence fields;
- list of Case-specific kernel usages;
- list of editorial derived-label consumers.

No code change.

PASS when the report is committed as a temporary implementation artifact or included in task notes.

---

## T001 — Introduce operational receipt v2

Refactor `models.py`.

Requirements:
- v2 terminal receipt describes execution only;
- pause receipt describes pending work only;
- add `bindings`;
- remove new-write support for semantic evidence/verification fields;
- neutrally rename artifact/tool facts if retained;
- remove semantic `partial` downgrade model.

Do not dual-write old + new semantic fields.

If old v1.2 reads are required, isolate legacy parsing.

Tests:
- serialize/deserialize v2;
- pause receipt round-trip;
- bindings round-trip.

---

## T002 — Delete semantic verification pipeline

Refactor/delete `verification.py`.

Keep only:
- path containment;
- hash/byte identity;
- changed-artifact detection;
- StepStore tool-event projection if consumed.

Delete:
- evidence-ref parser;
- knowledge evidence validation;
- tool-effect evidence lookup;
- model-claimed evidence loop.

Refactor `runtime.finalize_terminal()` accordingly.

PASS:
- runtime completion is not changed to a worse semantic status because evidence metadata is missing;
- changed artifact facts still work;
- unresolved/pending execution remains correctly represented.

---

## T003 — Remove model/host settlement schema from natural generation

Ensure model terminal output remains natural text.

Runtime creates operational receipt without requiring model fields such as:
- artifacts;
- evidence;
- unknowns;
- next_action.

Delete dead `RunSummary` pieces or the entire class if possible.

PASS:
- “写/改/分析” returns the actual result directly;
- no model instruction asks it to craft receipt/evidence fields.

---

## T004 — `case_id` → opaque bindings

Change:
- `CoreDeps`;
- terminal receipt;
- pause receipt;
- gateway start;
- continuation/resume;
- affected tests.

Use a plain immutable mapping.

Do not add registry/classes beyond what typing requires.

PASS:
- binding is frozen in paused record;
- resume uses identical binding;
- kernel logic does not inspect `"case"`.

---

## T005 — Move Case context into `zuaef-case`

Create the smallest Case-owned capability using released PydanticAI mechanisms.

Move current bounded projection behavior from generic `context_projection.py`.

Gateway must stop importing Case projection.

PASS:
- bound Case context reaches the model;
- Case mutation tools may remain deferred;
- no Case context branch in generic gateway bridge/runtime;
- `context_projection.py` deleted from core tree.

---

## T006 — Move cross-case approval validation into Case tool

Delete `_assert_pending_case_isolation()` from runtime.

Use PydanticAI-supported pre-approval argument validation.

PASS:
- same-case external send reaches approval pause;
- cross-case external send is rejected before an approval card is created;
- runtime has no Case-specific check.

---

## T007 — Simplify KnowledgeStore

Remove global semantic truth taxonomy and `SourceRef` enforcement.

Retain safe file operations and simple retrieval.

Decide based on real consumers whether generated run attribution stays.

PASS:
- plain document can be stored;
- source-linked document can contain actual URLs in Markdown;
- no kernel code claims a document is “verified” because frontmatter contains a source field.

---

## T008 — Close Generalist flag growth

Do not fully redesign generalist composition.

Add architecture guard/documentation:
- current compatibility list is closed;
- future Harness capabilities use plugin/local composition first.

PASS:
- no new capability-registry framework;
- existing profiles still resolve.

---

## T009 — Introduce document-first learning case vertical slice

Create a small `learning/cases/` or benchmark-local equivalent.

Use 3–5 real historical writing examples.

Each case preserves:
- request/context if available;
- before/output;
- source URLs;
- original human feedback/comment;
- revised/preferred text.

Minimal manifest only for addressing.

PASS:
- no mandatory `action`, `trigger_signals`, or numeric quality `weight`.

---

## T010 — LLM reviewer

Add a script/prompt that reads one case packet and produces `llm-review.md`.

Requirements:
- prose review;
- source-support questions;
- preservation recommendations;
- proposed changes;
- explicit option “no reusable lesson”.

Do not output a mandatory fixed label schema.

PASS:
- reviewer works on at least one real case.

---

## T011 — Human review and promotion

Human writes/edits `human-review.md`.

Build a simple promotion step that produces one of:
- Skill change;
- example pack item;
- plugin fix recommendation.

Promotion requires explicit human action.

No auto-promotion.

PASS:
- one accepted real lesson is applied;
- one later task can consume it.

---

## T012 — Comparative quality run

For at least 5 representative tasks where feasible:

- baseline version;
- learned version;
- same task/context/model budget as much as practical;
- LLM review;
- human pairwise judgment.

Report:
- preferred version;
- reason;
- edits still required;
- source support issues.

Machine sensors may be reported separately as diagnostics only.

PASS:
- report contains actual human judgments, not a score-only table.

---

## T013 — Architecture tests

Add tests/linters ensuring:

- kernel does not import business plugins;
- runtime contains no `case_id`;
- new receipt contains no `verified_*` fields;
- no semantic evidence parser exists;
- plugin ABI still only exposes existing primitive bundle;
- no new `GENERALIST_FLAGS` entries slipped in accidentally.

Use simple static tests; do not build an architecture framework.

---

## T014 — Real regression proof

Run:
- full pytest;
- CLI core run;
- profile composition check;
- pause/approve/resume path;
- Stillevo FDE flow if credentials/environment permit;
- writing result with real source links;
- WordPress external effect path without changing approval semantics.

Record actual commands and outcomes.

---

## T014A — Capability-owned Result Contract proof

Implement/normalize result-shaping responsibility in at least three existing capabilities/domains.

Requirements:
- writing result shape comes from writing Capability/plugin;
- budget result shape comes from budget Capability/plugin;
- client-service or research result shape comes from its Capability/plugin;
- generic terminal remains natural `str | DeferredToolRequests`;
- no universal BusinessResult/ResultSchema model;
- no result-type registry;
- no new domain fields in receipt/runtime.

Use Capability `get_instructions()` and domain-owned toolsets/save/finalize tools as the primary seams. Use domain-local Pydantic validation only where a deterministic business/API invariant requires it.

PASS:
- three materially different deliverables are produced through the same generic runtime;
- modifying one deliverable structure changes only its owning capability/plugin and tests;
- Kernel diff is zero for a follow-up structure-only change.

---

## T014B — Remove Pydantic workflow gates

Audit all new/changed Pydantic models and any existing models touched by this refactor.

Remove any generic field-driven process logic such as:
- phase/status progression;
- semantic completeness booleans;
- evidence/quality pass fields;
- next-stage enums;
- “required fields before continue” gates.

Keep Pydantic only where it models real data/config/API/persistence contracts.

PASS:
- Agent work progression remains model-driven through Capability instructions/tools;
- native approval exists only for real side-effect boundaries;
- no new generic workflow state machine is introduced.

---

## T015 — Delete legacy dead code and freeze

Only after all earlier gates pass:

- remove unused verification classes;
- remove obsolete tests;
- remove Case projection core module;
- remove dead receipt adapters not required for real historical data;
- update README/AGENTS.md;
- document kernel freeze.

Final diff must show subtraction, not a net-new framework explosion.
