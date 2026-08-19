# PLAN — Phase 2 Product Completion

Starting point: current `main` after Phase 1.

# Phase A — Freeze Phase 1 and create RED product tests

1. Record HEAD/status/pytest/ruff.
2. Keep Phase-1 substrate unless a Phase-2 test requires a change.
3. Add focused RED tests for:
   - profile-level generalist authorization;
   - `stillevo-fde` initial business surface;
   - Gateway Case binding;
   - bound Case isolation;
   - literal Turn-2 prompt/no hidden constraint reinjection.

# Phase B — Deployment + Case identity

1. Add minimal profile generalist policy.
2. Compute `host ceiling ∩ profile request`.
3. Freeze effective policy in CompositionSnapshot.
4. Extend existing Gateway SQLite/session state with Case binding.
5. Thread `case_id` through the existing execution deps.
6. Enforce bound-case isolation in Case tools.

No new runtime or database.

# Phase C — Business progressive disclosure

1. Add a deployment-level deferred-tool flag.
2. Mechanically wrap existing plugin Toolsets using released upstream deferred loading.
3. Configure `stillevo-fde`:
   - Case eager;
   - Client Service/Writing/Budget/WordPress deferred.
4. Prove initial vs loaded model-visible tool surface.

# Phase D — Converge the real FDE path

1. Reuse the real `stillevo-beauty` Case fixture/data.
2. Store production business-resource references in Case state.
3. Rewrite the existing two-turn proof to run:
   `GatewayService + stillevo-fde + bound Case + real model`.
4. Turn prompts remain literal.
5. Exercise approval/deny through the existing shared continuation seam.

# Phase E — Regression, docs, stop

1. Full test/lint + domain proofs.
2. Update README/.env/profile/Gateway docs.
3. Record P2-1..P2-8.
4. STOP when all pass.
