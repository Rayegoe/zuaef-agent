# Proposed AGENTS.md Amendment

Do not replace the current `AGENTS.md` blindly. Merge the following rules into its architecture section after review.

## Runtime complexity

Agent complexity is measured at the model boundary, not only by Python structure.

Model requests, model-visible tools, tool-result growth, repeated observations, context size and semantic decision count are architectural costs.

## Capability rule

Reuse an upstream PydanticAI/Harness primitive when it is needed; **reuse does not imply default composition**.

Do not enable a capability because it exists, is reusable, appears in another harness, or might help later.

A production capability must correspond to a demonstrated task failure or deployment requirement.

## Model-turn rule

A new model turn should correspond to new information that can change a semantic decision, a changed external state, a required semantic revision, or a human/external delta.

Persistence, hashing, bookkeeping, batching, indexing, serialization and receipt settlement are not model decisions.

## Autonomy boundary

Agent autonomy means ownership of semantic choices.

It does not mean every mechanical operation must be initiated as a separate LLM tool call.

The host may perform bounded deterministic transport without selecting business meaning.

## History and revision

History is a transcript, not the default task-state representation.

Revision should normally consume the current artifact, human delta and bounded authoritative state. Full-history reconstruction requires evidence that bounded state is insufficient.

## Unknown convergence

Insufficient evidence is a valid terminal epistemic state.

Do not repeatedly inspect unchanged evidence when it cannot satisfy the missing fact. Preserve the unknown and continue feasible work or return a partial result.

## Capability status

Classify capabilities as:

- REQUIRED_INVARIANT
- ADMITTED_PROFILE
- EXPERIMENTAL
- QUARANTINED
- DELETE_CANDIDATE

"Enabled" is a configuration fact, not an architectural justification.

## Optimization rule

For runtime refactors:
1. measure;
2. reproduce the failure;
3. make the smallest change;
4. rerun the same benchmark;
5. compare business outcome and runtime complexity;
6. delete obsolete authority.

Do not redesign multiple layers in one iteration.

