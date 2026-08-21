# Iteration Protocol

One iteration should fit this shape:

```text
E0 baseline
E1 one bounded change
E2 same benchmark
E3 compare
E4 decision
```

Avoid "mega-refactors" where the causal reason for improvement cannot be isolated.

## Commit discipline

Prefer separate commits for:
1. instrumentation;
2. behavioral change;
3. deletion/cleanup.

Instrumentation should not silently change semantics.

## Required evidence

A completed iteration should leave:
- baseline record;
- candidate record;
- comparison;
- accepted outcome result;
- decision note.

