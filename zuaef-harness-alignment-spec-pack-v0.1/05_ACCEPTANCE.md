# Acceptance Gates

## A. Architecture gates — all mandatory

A candidate Harness minor cannot be promoted if it causes any of these without an independently approved architecture change:

- second agent runtime;
- second approval engine;
- second durable-execution truth store;
- new global agent registry;
- custom clone of an upstream generic capability;
- default multi-agent topology;
- new global capability enabled without admission evidence;
- new hash/checksum/manifest machinery for upgrade bookkeeping.

## B. Dependency gates

Pass when:

- candidate environment resolves;
- PydanticAI meets the candidate Harness floor;
- optional extras used by ZUAEF resolve together;
- no unrelated production dependency is gratuitously upgraded.

Fail/hold when a real unresolved dependency conflict remains.

## C. Public behavior gates

### C1. Agent composition

- one core Agent remains;
- existing plugins still compose as Toolsets/Skills/Capabilities;
- profile authorization remains effective;
- frozen composition still reconstructs continuation.

### C2. Tool surface

- no unexplained new model-visible tools;
- deferred tool behavior still works;
- representative tool schemas remain callable.

### C3. Filesystem

- root confinement remains correct;
- protected patterns remain effective;
- knowledge/artifact restrictions are not weakened.

### C4. Tool output limits

- oversized outputs are bounded/spilled according to current contract;
- raw large results are not injected into model context by regression.

### C5. Approval/continuation

- pause works;
- interrupted frontier is recoverable after process boundary;
- approve and deny work;
- conversation/composition/bindings are preserved;
- no duplicated effect in the deterministic effect fixture.

### C6. CodeMode

- profile opt-in only;
- intended selectors still select intended read/query tools;
- side-effect/artifact submission boundary is preserved.

### C7. CJK ToolSearch

- Chinese discovery works for intended domains;
- unrelated domains remain dormant;
- no fork of upstream ToolSearch.

## D. Test-quality gates

- private Harness implementation details are not treated as production contracts when public behavior is testable;
- tests are not deleted/weakened to hide candidate regressions;
- deterministic FunctionModel/local fixtures remain preferred for capability-surface tests;
- real-model canary is supplementary, not a replacement for deterministic gates.

## E. Runtime-complexity gates

A dependency promotion must not, by itself:

- add model turns;
- add default tools/capabilities;
- add host semantic preselection;
- add new persistence layers;
- add new schemas/gates that do not prevent a reproduced failure.

If upstream behavior changes these metrics, measure and review before promotion.

## F. Promotion rule

Promote only when all mandatory gates pass and no business/runtime regression remains unexplained.

Do not promote merely because:

- the newest version exists;
- release notes contain attractive capabilities;
- focused unit tests pass while continuation/surface behavior is untested.

Do not hold merely because:

- a test reached into a private upstream attribute that changed;
- an internal class name moved while public behavior is unchanged.
