# PRD — ZUAEF Agent Runtime Re-foundation

Status: proposed implementation authority  
Scope: cross-domain Agent runtime behavior  
Initial canary: Writing WCASE-1..4  
Strategy: brownfield re-foundation, not greenfield rewrite

## 1. Problem

ZUAEF has reduced static architecture complexity while retaining excessive runtime trajectory complexity.

Observed Writing evaluations show the failure clearly:

- trivial or small-material tasks can require many model requests;
- model-visible planning/status actions consume turns without directly improving the business artifact;
- material selection can become item-by-item model-mediated transport;
- missing evidence can create repeated search/check loops;
- revision can reconstruct old history instead of operating on current artifact state plus a human delta;
- a small number of requests can still consume extreme input and reasoning tokens because history and tool returns accumulate.

The product risk is cross-domain. The same pattern would appear in negotiation, customer service, research, procurement, budgets and WordPress if their capabilities expose similarly fine-grained operational paths.

## 2. Product objective

Make ZUAEF an outcome-owning FDE Agent whose runtime complexity scales with the task's actual uncertainty and action requirements.

The target behavior is:

```text
simple task
→ small observation
→ semantic decision
→ result

complex task
→ bounded observation
→ semantic decision
→ necessary action
→ new information
→ another semantic decision
→ result
```

A new model turn is justified by **new semantic information or a new semantic decision**, not by bookkeeping.

## 3. Users

Primary engineering user:
- Coding Agent maintaining `zuaef-agent`.

Secondary:
- human maintainer reviewing architecture changes;
- benchmark/evaluation operator;
- future domain-plugin authors.

Business users are indirect beneficiaries: lower latency, lower token cost, more predictable completion and less framework-shaped behavior.

## 4. Product principles

### P1. Model-boundary complexity is architecture complexity

Python class count is not enough. Measure:
- model requests;
- visible tools;
- tool calls;
- prompt/context growth;
- input/output/reasoning tokens;
- latency;
- repeated observations;
- repeated semantic decisions.

### P2. Capability admission is evidence based

A Harness capability enters a production profile only when a reproduced task failure shows the need.

### P3. Mechanics stay deterministic

Hashing, persistence, bookkeeping, indexing, batching, receipt settlement, path validation and similar mechanical operations do not require LLM decisions.

### P4. Semantic autonomy is preserved

The host may transport and bound information. It must not silently decide:
- relevance;
- business meaning;
- editorial taste;
- negotiation strategy;
- factual conclusion;
- final business action.

### P5. Unknown is a valid state

Insufficient evidence must converge to `unknown`, `unsupported`, `needs external evidence`, or equivalent instead of generating an unbounded retry loop.

### P6. Revision is delta-oriented

Default revision input:
- current artifact/state;
- human delta;
- bounded source/evidence state;
- unresolved facts.

Full conversation replay is exceptional and must be justified.

### P7. Preserve proven assets

Do not discard validated:
- Gateway;
- approval/effect boundary;
- plugin ABI;
- ACE integration;
- benchmark fixtures;
- run/effect evidence;
- production-domain knowledge.

## 5. Success metrics

### Functional
- outcome quality non-regressing against accepted baseline;
- evidence integrity preserved;
- external effects remain approval-gated;
- artifact settlement remains verifiable.

### Runtime
Each benchmark records:
- request count;
- tool-call count by tool;
- model-visible tool count;
- input tokens;
- output tokens;
- reasoning tokens where available;
- cache hit/miss where available;
- total wall clock;
- per-request wall clock when instrumented;
- largest request context;
- repeated tool signatures;
- repeated observation categories.

### Architectural
- default production path starts from the smallest admitted capability set;
- optional capabilities are profile/task justified;
- current/legacy paths have explicit authority status;
- no business-domain fix creates a new core framework without cross-domain evidence.

## 6. Rollout

1. freeze and measure current Writing baseline;
2. establish Minimal Loop Canary with WCASE-1;
3. solve WCASE-2 as observation/action-surface design;
4. solve WCASE-3 as convergence/unknown behavior;
5. solve WCASE-4 as bounded revision;
6. generalize only mechanisms proven across at least one non-Writing case;
7. retire superseded runtime behavior.

## 7. Stop conditions

Stop an iteration when:
- outcome quality regresses;
- evidence integrity weakens;
- a new abstraction is proposed without reproduced failure;
- benchmark instrumentation is insufficient to explain the change;
- optimization is benchmark-specific rather than mechanism-specific;
- implementation starts rebuilding PydanticAI/Harness primitives locally.

