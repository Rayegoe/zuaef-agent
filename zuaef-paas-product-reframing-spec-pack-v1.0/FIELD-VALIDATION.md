# Deployment Authoring — Field Validation Protocol v1.0

Status: PENDING — step 0 may start immediately; trials require a real
natural-language business description from a real source.
Belongs to: `zuaef-paas-product-reframing-spec-pack-v1.0/SPEC.md` (D3, D7).
Date: 2026-08-21.

## 1. Hypothesis under test

H1: a customer's natural-language business description can be turned, by one
authoring pass against a fixed template, into a `deployment.md` that a human
approves with bounded edits, and from which a correct `profile.toml` is
derived through the existing composition path.

Falsifier: any of the failure modes F1–F5 in §6 recurring across trials, or
systematically heavy human rewriting.

This protocol produces evidence only. It authorizes no runtime change
(SPEC §10).

## 2. Pre-experiment state this protocol must not disturb

- T006-B1 human blind gate is pending. T006-B2 / T007 work does not run
  inside this protocol.
- Kernel freeze verification gate is BLOCKED; no kernel file is touched.
- `profiles/stillevo-fde.toml` remains production authority for the existing
  deployment regardless of anything authored here.

## 3. Step 0 — reference deployment document

Author `deployments/stillevo-fde/deployment.md` retroactively, from
authoritative sources only:

- `profiles/stillevo-fde.toml` (composition + `[generalist]` boundaries)
- `workspace/cases/` (case world for the bound engagement)
- README "Phase 2 — the product seam is one deployment" section
- "ZUAEF FDE Agent Platform — SPEC v0.3.md"

Rules: no invented business facts; facts the sources do not contain are
recorded as unknowns. Purpose: the convention has one real instance before
the first trial, and the template is validated against something already
true.

## 4. The deployment.md convention

Template (fixed section order):

```markdown
# Deployment: <name>

## Outcome
<the business outcome this deployment exists to produce>

## Deliverables
<what an accepted deliverable means, per domain>

## Boundaries
<what runs automatically vs. what requires human approval>

## Current constraints
<environment / system facts that bound the work>

## Proposed composition
<plugin ids + non-secret config — a proposal, not composition authority>

## Binding needs
<what must be bound at runtime — requirements, never values>
```

Rules:

- fixed section order; any future projection of this document is mechanical
  per SPEC D5 (read → bound → render);
- no secrets; no binding values (`case_id`, customer/conversation ids);
- no workflow definitions: content resembling `trigger/steps/conditions/
  routes/validation` structures is forbidden — the flow of work is a run
  result, not a configuration object;
- human-readable first: this is a business document the customer and
  operator can read and edit.

## 5. Trial procedure

Per trial:

1. **Field input** — one real natural-language business description; record
   source, date, and whether the source is a prospective or existing
   customer.
2. **Authoring pass** — LLM + authoring prompt + template → `deployment.md`
   draft. Record model and settings. The authoring model receives the
   installed-plugin inventory as its composition vocabulary.
3. **Human review** — reviewer edits the draft; record a per-section verdict:
   `unchanged / light-edit / rewritten / added / removed`, with the reason.
4. **Mechanical derivation** — human or script derives `profile.toml` from
   the approved deployment.md; diff against the profile the operator would
   have written by hand.
5. **Composition check** — derived profile passes `load_profile` /
   `resolve_profile` (dry run; no model request happens there by design).
6. **Record** — append the trial to `EXPERIMENT-LOG.md` (create at first
   trial), including the reviewed draft, the edits, the derived profile and
   the diff.

## 6. Observed failure taxonomy

- **F1 wrong plugin selection** — missing, extra, or misconfigured plugin in
  the proposed composition.
- **F2 boundary loss** — a boundary stated in the input is absent from the
  deployment.md or the derived profile (esp. approval-gated actions).
- **F3 deliverable definition loss** — the input's notion of "what we get"
  does not survive into Deliverables.
- **F4 binding need vague or missing** — the deployment does not state what
  must be bound at runtime.
- **F5 heavy human rewriting** — any section verdict `rewritten`, or a
  majority of sections beyond `unchanged/light-edit`.
- **F6 input insufficiency** — the customer description itself lacks a
  needed fact. Record as an unknown and a question back to the customer;
  this is a property of the input, not an authoring failure, and must not be
  counted against the seam.

## 7. Verdicts

- Per trial: `AUTHORING_SUFFICIENT` / `AUTHORING_INSUFFICIENT_F<n>` /
  `INPUT_INSUFFICIENT` (F6).
- Pack-level admission: requires at least 3 trials on distinct real
  descriptions with no unresolved F1–F5, edit distance bounded to
  `unchanged/light-edit` on all sections that matter, and a recorded human
  admission decision citing the trial log. Admission moves the authoring
  seam to PROFILE-ONLY candidacy (SPEC D3) and unblocks README narrative
  migration (SPEC §9). It unlocks nothing else.

## 8. Non-goals

No runtime code; no WorkflowEngine or DSL; no auto-binding; no deployment
registry service; no universal deliverable schema; no README rewrite.

## 9. What this protocol must never silently become

An LLM that outputs `profile.toml` directly, skipping the human-readable
deployment.md review, would void the experiment: the product claim under
test is that the **human-readable business document** is the reviewable
interface between customer language and machine composition. Derivation
must remain downstream of, and traceable to, an approved deployment.md.
