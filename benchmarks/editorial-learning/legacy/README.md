# legacy/ — demoted editorial-control runtime (v1.2 T014B)

This directory is the explicit `derived/legacy/` location required by
QUALITY_LOOP §11 (migration of editorial learning). Everything here is
**benchmark/legacy authority**, never production authority.

## What moved here (v1.2 T014B)

- `editorial_capability.py` — `EditorialControlCapability`, the five
  trajectory sensors, the save veto, `EditorialEvidence(weight, approved_by)`,
  and the seed evidence store. Previously
  `plugins/zuaef-ace-writing/zuaef_ace_writing/editorial.py`; the production
  plugin factory no longer constructs it and rejects `editorial_*` config
  keys with a `CompositionError` pointing here.

## Authority rules

1. `trigger_signals`, `action`, `weight`, `approved_by` in
   `evidence/human_patches.jsonl` and `compiled/evidence.jsonl` are legacy
   derived features, not human truth.
2. The authoritative learning record is the document-first case packet
   (`learning/cases/<case-id>/`: raw before/after text, raw editor comments,
   source pointers). Human review prose there outranks anything here.
3. No production capability may import this directory; only benchmark
   scripts/experiments and their tests do.
4. New learning records are document-first; do not extend the evidence-row
   schema here.

## Why the demotion happened

The Phase 9 blind A/B (2026-08) showed no stable advantage of editorial
control ON over OFF, and v1.2 removed Pydantic/workflow-style process gates
from the production surface: a veto-before-save driven by regex drift scores
is a machine gate on taste — exactly what v1.2 SPEC forbids as semantic
authority. The sensors remain useful as cheap diagnostics inside benchmark
experiments only (QUALITY_LOOP §9 "tertiary diagnostics").
