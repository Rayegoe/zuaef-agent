# BENCHMARKS — Runtime Fitness Function

## 1. Why this exists

Unit tests can all pass while the Agent runtime becomes worse.

A runtime optimization must evaluate both:

```text
BUSINESS OUTCOME
and
MODEL-BOUNDARY COMPLEXITY
```

Neither may substitute for the other.

## 2. Required metrics

Collect when available:

| Metric | Meaning |
|---|---|
| `requests` | model requests in the run |
| `tool_calls` | total visible tool calls |
| `tool_counts` | calls grouped by name |
| `model_visible_tools` | tool names offered to the model |
| `input_tokens` | provider input tokens |
| `output_tokens` | provider output tokens |
| `reasoning_tokens` | provider reasoning tokens |
| `cache_read_tokens` | cache reuse where available |
| `cache_miss_tokens` | cache miss/reprocessed tokens where available |
| `wall_clock_ms` | full run time |
| `request_latencies_ms` | per request |
| `tool_latencies_ms` | per tool |
| `largest_input_tokens` | largest single request |
| `repeated_signatures` | semantically equivalent repeated actions |

## 3. Outcome gate precedes efficiency gate

Never accept:

```text
requests 15 → 2
```

if the article, negotiation decision, budget analysis or evidence quality becomes materially worse.

Evaluation order:

1. correctness/safety;
2. outcome quality;
3. evidence integrity;
4. runtime complexity.

A run whose outcome evaluation is `null` cannot support an optimization
decision. Record a human verdict or apply the domain rubric to baseline and
candidate first. `execution_state=completed` is an execution fact, not an
outcome verdict, and the coding agent must not self-adjudicate article
quality to unblock itself.

## 4. Diagnosis expiry

A historical diagnosis is evidence about the code that produced it. Before
driving change from a recorded failure, re-run the case fresh on current
code.

Example: the pre-re-foundation WCASE-1 diagnosis (plan/status cycles,
repeated claim checks, ~16 requests / ~27 tools) no longer reproduces — the
current writing profile runs 2 requests / 1 tool call with generic
capabilities disabled. Honoring an expired diagnosis manufactures the
over-engineering this pack exists to prevent.

## 5. Initial benchmark ladder

### B0 — Bare loop smoke test

Purpose:
- prove PydanticAI + smallest domain surface can produce a terminal result.

No Planning, Memory, ConversationSearch, SubAgents, RepoContext by default.

### B1 — WCASE-1 Minimal Loop Canary

Question:

> Can a one-material writing task complete without framework choreography?

Failure signals:
- plan/status cycles;
- irrelevant skill loading;
- repeated material reads;
- repeated claim checking without changed evidence;
- generic workspace exploration.

Stop rule:
- do not proceed to WCASE-2 until a simple path exists and is measured.

### B2 — WCASE-2 Observation Test

Step 0 — audit the current host preselection (`build_writer_context()`:
lexical relevance ranking, excerpt bounding, technique tags, experience
selection). Enumerate what the host decides and what it drops, and measure
whether dropped content was materially relevant to the accepted article.

Then compare at least:

A. item-by-item regular tool calls;  
B. bounded batch observation;  
C. CodeMode only if the experiment specifically tests whether it improves this problem.

Measure:
- quality;
- model requests;
- total input;
- latency;
- selection correctness.

Do not allow host-side semantic preselection to fake efficiency.

### B3 — WCASE-3 Unknown Convergence Test

Expected semantic behavior:

```text
required claim
→ evidence unavailable
→ UNKNOWN / UNSUPPORTED
→ no fabrication
→ no equivalent repeated evidence loop
→ complete feasible outcome
```

Reject:
- repeated checks over unchanged source state;
- policy/status updates masquerading as progress.

### B4 — WCASE-4 Revision Test

Revision input should be bounded.

Current code already revises through a fresh run with bounded inputs
(current article + human feedback + bounded writer context, no
message-history replay). Prove or disprove boundedness on a fresh revision
trace before designing new machinery.

Measure separately:
- draft;
- revision.

Important signals:
- whether full old history is reintroduced;
- ConversationSearch usage;
- read_tool_result usage;
- old-plan reconstruction;
- context growth from draft to revision.

### B5 — Cross-domain proof

Before promoting a Writing-discovered mechanism to Core, reproduce its value in at least one non-Writing task shape, for example:

- client negotiation with an unknown budget fact;
- budget document revision;
- WordPress draft revision;
- supplier research with conflicting facts.

## 6. Complexity score

Do **not** optimize a single magic scalar in production.

For local comparison only, the provided script can calculate an indicative score:

```text
score =
  requests * request_weight
  + tool_calls * tool_weight
  + input_tokens / token_divisor
  + reasoning_tokens / reasoning_divisor
  + wall_clock_seconds * time_weight
```

Use the components to understand the change. A lower synthetic score never overrides outcome gates.

## 7. Repeated semantic observation

Potential duplicate signature examples:

```text
check_claim(same normalized claim, same evidence version)
read_material(same material id, no intervening state change)
retrieve_knowledge(same query family, same corpus revision)
search_history(same intent, unchanged history)
read_plan(no plan mutation since previous read)
```

These are diagnostic flags, not universal forbidden operations.

## 8. Experiment record

Each optimization iteration creates one experiment record from:

```text
templates/runtime-refoundation/experiment.md
```

No "we think this is faster" commits.

