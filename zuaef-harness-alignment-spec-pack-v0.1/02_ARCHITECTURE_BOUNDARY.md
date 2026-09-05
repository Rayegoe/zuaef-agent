# Stable Architecture Boundary

## 1. Ownership model

```text
StillWrite / CLI / Web / Telegram / other surfaces
                    |
                    v
             ZUAEF Gateway
   transport / session binding / interaction projection
   approval presentation / host authorization
                    |
                    v
             ZUAEF Runtime
  execution boundary / operational settlement / receipts
  composition identity / artifact-effect inspection / resume seam
                    |
                    v
            PydanticAI Agent
                    |
        +-----------+-----------+
        |                       |
        v                       v
PydanticAI / Harness        ZUAEF domains
----------------------      -------------------------
agent loop                  quant
native approvals            case
usage limits                writing
filesystem                  client service
planning                    competitive intelligence
skills                      WordPress
step persistence            Telegram domain actions
tool-output limits          other business plugins
memory
conversation search
repo context
shell
subagents
code mode
context controls
web/tool search
```

## 2. Stable rules

### A. PydanticAI owns the agent loop

Do not introduce a ZUAEF graph runtime, agent registry, alternate tool dispatcher or second approval engine.

### B. Harness owns generic reusable agent capabilities

If an upstream primitive already solves the generic mechanism, integrate it through its public capability/toolset API rather than reproducing it.

### C. ZUAEF owns business semantics

Keep these local:

- domain action surfaces;
- business policy;
- domain evidence interpretation;
- customer/case/quant/writing semantics;
- external integration adapters;
- business-specific bounded state.

### D. ZUAEF Runtime may own generic operational settlement, but not a second execution model

Allowed runtime responsibilities include:

- acceptance boundary and terminal state normalization;
- run receipts as operational index/output;
- composition snapshot authority for resume;
- bounded artifact/effect settlement;
- process-level error boundary;
- restoring the current approved continuation seam.

Not allowed without a reproduced failure:

- custom event-sourced durable runtime;
- generic graph/state machine;
- custom memory service;
- custom compaction engine;
- duplicate tool-effect execution engine.

### E. Gateway is an interaction layer

Gateway may own:

- transport;
- authorization/session identity;
- user-facing approval presentation;
- projection for StillWrite/Telegram/Web.

Gateway must not own:

- agent execution semantics;
- domain business policy;
- approval semantics;
- durable execution truth;
- a second receipt authority.

## 3. Capability admission classes

Use the repository's existing classes:

- `REQUIRED_INVARIANT`
- `ADMITTED_PROFILE`
- `EXPERIMENTAL`
- `QUARANTINED`
- `DELETE_CANDIDATE`

Availability in Harness is not admission.

## 4. Default posture for notable upstream capabilities

| Capability | Posture | Reason |
|---|---|---|
| FileSystem | profile/invariant as currently justified | already used; protected-path behavior must remain stable |
| Planning | evidence-gated | do not default-on merely because task looks complex |
| Skills | profile-gated | deferred expert guidance only where outcome improves |
| StepPersistence | admitted where resume/debug requires it | current continuation depends on it |
| ToolOutputLimits | conditional | justified by oversized results/context pressure |
| Memory | not globally admitted | requires reproduced cross-session forgetting |
| ConversationSearch | not globally admitted | bounded current state preferred |
| RepoContext | repo-task profile | appropriate for code/repo tasks |
| Shell | trusted execution profile only | privileged capability |
| SubAgents | profile/experiment | only when isolation/parallelism wins |
| CodeMode | experimental/profile | useful for repeated dependent read/query tool calls; never use to bypass side-effect gates |
| DynamicWorkflow | experimental only | no default topology expansion |
| Guardrails | unadmitted until specific input/tool/output failure | generic availability is insufficient |
| PromptInjectionDefender | experimental candidate for untrusted research surfaces | must earn production admission with evidence |
| Spend | unadmitted | no established cross-window USD budget requirement |
| CapabilityCreation | quarantined from production core | conflicts with frozen composition/authority model unless explicitly redesigned |
| Coder/Researcher combined harnesses | delegate/profile candidates, not new ZUAEF core | reuse only when a task class justifies the whole stack |
| Temporal/DBOS/etc durable execution | unadmitted | current continuation requirement does not establish need |

## 5. Model-boundary rule

A new model turn must correspond to new information, changed external state, a semantic revision, a human/external delta, or a semantic decision that cannot be made deterministically.

Do not spend model turns on bookkeeping, serialization, indexing, receipt writing, batching or other deterministic transport.
