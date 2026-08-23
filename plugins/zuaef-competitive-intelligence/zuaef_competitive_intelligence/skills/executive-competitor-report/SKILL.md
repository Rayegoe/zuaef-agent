---
name: executive-competitor-report
description: "Turn competitive product research into a decision-ready report while preserving source quality, lifecycle labels and unknowns."
---

# Executive Competitor Report

Use this Skill when competitive research must become a decision-ready external report.

## Reader

Assume a bicycle-industry product/business decision maker. The reader wants competitor map, lifecycle/configuration/price logic, strategic implications, and inspectable sources—not the Agent's internal process.

## Before drafting

Make a semantic coverage judgment first: product families, lifecycle, pricing/configuration, decisive official evidence, major source conflicts, and market context. If evidence only supports a partial report, say so. Do not draft a polished full report merely because some sources exist.

## Decisive-source rule

For decision-critical claims about current availability, price, configuration, model year, or official product capability, use an official product/configurator/press/help source when one is accessible. Secondary sources may supplement interpretation but should not replace accessible decisive official evidence.

## Negative claims

Distinguish “not found in the material inspected” from “not publicly disclosed / does not exist.” Use the stronger form only when official-source checks support it.

## Recommended report architecture

1. Executive Summary
2. Scope / research date / market
3. Brand and market context
4. Product-family + lifecycle map
5. Product matrix
6. Key family deep dives
7. Price/configuration ladder
8. Platform/component architecture
9. Cargo/use-case architecture when relevant
10. Commercial interpretation
11. Risks / unknowns / unresolved conflicts
12. Implications / next validation steps
13. Sources

## Executive Summary

Lead with 3–6 conclusions that could change a decision. Avoid generic brand history unless it explains strategy.

## Specs → meaning

Explain what patterns mean for segmentation, upsell, platform reuse, ASP, use case, and product planning. Only make stronger commercial claims when evidence supports them.

## Lifecycle

Make CURRENT / ANNOUNCED_NEXT / older overlap visually obvious. Do not mix next-model-year specs into current tables without explicit labels. Publication/index date alone is not lifecycle evidence.

## Pricing

Keep market/currency explicit. Do not substitute another market's price as German without labeling. Do not convert “not found” into “not disclosed” without official checks.

## Images

Use images to improve platform/form-factor/cargo/family understanding. Prefer official exact-model/model-year images. Do not imply an unverified configuration.

## Sources

Decision-relevant factual claims must be inspectable. Keep source URLs in footnotes/source sections. Before Golden Case signoff, the evaluator revalidates decision-relevant URLs. That is benchmark QA, not a runtime quality gate.

## Keep internal machinery out

Do not expose requests/tool counts, ToolSearch, receipts, `analysis.md`, WO/task IDs, prompt-engineering notes, or raw query history.

## Final content pass

Before render: remove repeated conclusions, keep lifecycle labels visible, ensure decisive pricing/config claims have decisive sources, preserve material unknowns/conflicts, and trace commercial conclusions back to the product map.

## Final delivery pass

After render: rasterize preview/contact sheet, perform actual operator visual review for the Golden Case, and record concrete layout issues in `qa.md`. Do not equate render success with visual-quality success.
