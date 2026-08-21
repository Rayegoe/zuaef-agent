# Runtime Re-foundation Reviewer Prompt

Review the proposed change as an Agent-runtime architecture reviewer.

Do not focus only on code style or test coverage.

Evaluate:

- business outcome preservation;
- evidence/effect integrity;
- model request count and reason for each turn;
- action-space size;
- tool/capability admission;
- context growth;
- repeated observations;
- history-vs-state misuse;
- unknown convergence;
- whether deterministic batching stole semantic judgment;
- whether obsolete authority was actually removed.

Return:

1. `VERDICT`: PASS / REVISE / REJECT
2. `OUTCOME`
3. `RUNTIME_COMPLEXITY`
4. `SEMANTIC_OWNERSHIP`
5. `CAPABILITY_ADMISSION`
6. `DELETION/LEGACY`
7. `NEXT SMALLEST EXPERIMENT`

Reject architectural additions that solve only hypothetical failures.
