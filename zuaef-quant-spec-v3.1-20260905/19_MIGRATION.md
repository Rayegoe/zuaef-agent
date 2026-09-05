# 19 — Migration Strategy

Adapter-first, additive, no rewrite.

1. Capture runtime truth.
2. Add namespace metadata around existing canonical artifacts without unnecessary moves.
3. Introduce replay clock/data-access seam at the narrowest viable point.
4. Run replay in isolated state/config.
5. Reuse current settlement contracts where semantically valid.
6. Add Regime as parallel shadow projection.
7. Add Experiment Registry around evaluator/replay/shadow.

Rollback requirement:
new replay/regime/experiment code must be removable without disabling M1 monitor,
Workbench, six tools, renderer, Bridge or Telegram delivery.
