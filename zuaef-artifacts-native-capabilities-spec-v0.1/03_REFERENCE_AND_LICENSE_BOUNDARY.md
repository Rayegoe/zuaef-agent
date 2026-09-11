# 03 — OAI Reference and License Boundary

## Why this section exists

The repository root contains local OAI skill packages, but their bundled license text may impose restrictions on retaining, reproducing, distributing, sublicensing, transferring, or making derivative works from those materials.

This implementation must not assume that “files are locally visible” means “files are shippable product dependencies.”

## Preflight requirement

Before touching implementation:

1. Locate the four local OAI skill roots.
2. Read each adjacent `LICENSE.txt`.
3. Record only the practical licensing conclusion in `IMPLEMENTATION_REPORT.md`; do not paste the license text into the product.
4. Check whether `oai/` is untracked, ignored, or already tracked in Git.
5. Do not modify, delete, relocate, or commit the local reference directory as part of this task.

If the user's applicable agreement explicitly grants broader rights, that is an external authorization decision. Codex must not infer it.

## Default implementation rule

Implement independently using public libraries and this spec's functional requirements.

Do not:

- copy OAI Python or JavaScript files into `plugins/zuaef-artifacts/`;
- copy OAI `SKILL.md` prose into ZUAEF guidance files;
- copy slide template packs;
- copy helper modules;
- copy example assets;
- depend on `/home/oai/...` or another service-container path at runtime;
- require the local `oai/` directory for production execution.

## What may be preserved at the product-requirement level

These are generic functional outcomes, not implementation copying:

- create and revise office artifacts;
- render office artifacts for QA;
- inspect structure and obvious errors;
- keep intermediate QA files internal;
- re-run validation after a meaningful revision;
- preserve formulas in spreadsheet models where formulas are the expected business logic;
- maintain layout/readability as a shipping quality goal;
- support fixed-layout PDF as a common final-delivery format.

## Clean dependency requirement

A clean checkout without the local `oai/` directory must be able to install and run `zuaef-artifacts` after its declared open-source/system dependencies are installed.

This is an acceptance gate.
