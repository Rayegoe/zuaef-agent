---
name: e-bike-product-intelligence
description: "Research e-bike product families, configurations, lifecycle and market evidence with disciplined source selection."
---

# E-bike Product Intelligence

Use this Skill for competitive/product intelligence on e-bikes, cargo bikes and closely related bicycle-industry products.

## Outcome

Build a decision-useful map of the competitor's actual product architecture. Do not stop at a specification table.

## Source hierarchy

For decision-critical product facts, normally prefer:

1. official market-specific product/configurator page;
2. official model-year announcement / press release;
3. official help/support page that resolves configuration/model-year detail;
4. official catalogue/PDF;
5. industry association/regulatory material;
6. credible dealer/review material for gaps or interpretation;
7. broad secondary summaries as discovery hints.

Secondary sources can reveal what to investigate. They should not replace an accessible decisive official page.

## Source-selection discipline

Opening many sources is not progress by itself. Before opening another result, ask:

> Can this source materially change product coverage, lifecycle, configuration, price, conflict resolution or commercial interpretation?

Prefer the page that can resolve the decision.

## Negative-claim rule — mandatory

Negative claims have a higher evidence burden than positive observations.

Before claiming any equivalent of 未见披露、未发布价格、德国市场没有、没有该配置、不再销售、已停产、没有某电池/传动/速度版本, first search the relevant official market-specific product/configurator surface, model-year/press surface, and official help/support surface.

If those checks were not performed or remain inconclusive, use:

> “在当前已检索材料中尚未确认。”

Do not turn absence-of-observation into observation-of-absence.

## Coverage

Before full report drafting, judge whether you understand major product families in scope, important variants/configurations, requested market, current vs announced-next vs older/legacy overlap, and major passenger/cargo/use-case segmentation.

This is a semantic judgment, not a host gate. Continue only with searches that can materially change that map.

## Lifecycle

Working labels when useful:

- CURRENT
- ANNOUNCED_NEXT
- PARALLEL_OLD
- LEGACY
- UNKNOWN

These are research labels, not Core states.

Do not use media publication date, search indexing date, page visibility, page existence, or article recency alone as lifecycle proof. Publication time is not model generation. Page visibility is not current sales status.

Prefer a combination of current market product index/configurator, model-year announcement, official availability language, current vs older family naming, and official press/help detail. If unresolved, use `UNKNOWN`.

## Configuration lens

Ask which differences create customer value, use-case separation or price separation: drive system/motor family, torque when relevant, battery, transmission, belt/chain, suspension, speed class, gross vehicle weight/payload, cargo geometry/capacity, accessories, cockpit/connectivity/security, and model-year changes.

Do not fill a field merely because a template contains it.

## Platform reasoning

Look for a repeatable commercial architecture:

```text
shared frame/platform
  + drive choice
  + battery
  + transmission
  + suspension
  + speed class
  + accessories
  → price/use-case ladder
```

The strategic result may be the ladder itself.

## Conflict handling

When credible sources disagree, preserve both, test market/model-year/configuration as explanations, record unresolved material conflicts in `conflicts.md`, and surface them when they can alter a decision. Never silently choose the cleaner number.

## Product matrix

Use `catalog.csv` as a flexible working map. Recommended columns are optional. The matrix supports reasoning; it does not dictate the report.

## Persistence checkpoint — mandatory

A run that never saves produces no business artifact. Persist early and keep the working map on disk:

- As soon as evidence for roughly five product families is on the table (or earlier, at the first moment a provisional map exists), save the provisional `catalog.csv` and `evidence.md` with `save_work_product`, even if rows are partial.
- Mark fields not yet confirmed with `UNKNOWN` (lifecycle labels too). UNKNOWN entries are explicit unknowns, not failures; they do not require approval and must not block a save.
- Continue acquisition from the saved map: every later save replaces the previous version and adds only what changed. Between saves, record evidence URLs so no read is ever stranded in a working buffer.
- Never defer the first save to "final synthesis": synthesis is the last phase, but the first persistence checkpoint is a phase boundary that happens long before it.

## Stop rule

Stop searching a fact when authoritative evidence is sufficient for the decision, or current evidence cannot resolve it and another search is unlikely to change that. UNKNOWN is better than repetitive inspection.

## Prior-agent failure check

Before final synthesis, ask:

> Did I actually open the decisive official page, or am I about to infer from secondary coverage?

If unclear, resolve that before making a strong product/price/lifecycle claim.
