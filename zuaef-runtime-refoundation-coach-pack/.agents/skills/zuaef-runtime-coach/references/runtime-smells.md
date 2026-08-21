# Runtime Smell Catalog

## Process-for-process
Plan/status/review loops on a short task without outcome contribution.

## Model-mediated transport
The model spends turns fetching records that deterministic batching can safely transport.

## History archaeology
The agent searches prior transcript/tool outputs for current state that could be passed directly.

## Capability gravity
A capability is enabled because it is already available.

## Retry without information
The agent repeats an observation despite unchanged evidence state.

## Validation chatter
Validation is performed in many tiny semantic turns when a bounded final validation could work.

## Context snowball
Each turn carries growing old tool material that is not relevant to the next decision.

## Dual authority
Old and new runtime paths both remain production-valid with different semantics.

## Benchmark overfit
Implementation checks WCASE identifiers/content or makes a special path that would not generalize.

