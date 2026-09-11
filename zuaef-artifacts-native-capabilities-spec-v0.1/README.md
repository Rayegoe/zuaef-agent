# ZUAEF Artifacts Native Capabilities v0.1 — Spec Pack

## Purpose

This pack defines an implementable plan for turning four office-artifact domains — DOCX, PDF, Slides, and Spreadsheet — into native ZUAEF capabilities that can be selected from ordinary natural language without format commands.

The intended product behavior is simple:

- The user talks naturally in Feishu, CLI, or another ZUAEF surface.
- The single outcome-owning agent decides whether the requested result needs a formal artifact.
- The appropriate artifact capability is discovered and loaded only when useful.
- The capability creates or revises the artifact inside `workspace/artifacts/`.
- Mechanical rendering and validation happen inside the capability implementation, not as a sequence of user-visible commands.
- Feishu can return the completed file automatically after a successful run.

This is not an Office clone and not a new agent framework. It is a bounded business plugin over the primitives ZUAEF already uses.

## Source premise

The repository root already contains a local `oai/` directory with the four reference skill packages. Codex must verify the exact local layout before implementation. Common layouts may be either:

- `oai/docx`, `oai/pdfs`, `oai/slides`, `oai/spreadsheets`
- `oai/skills/docx`, `oai/skills/pdfs`, `oai/skills/slides`, `oai/skills/spreadsheets`

Do not assume one. Locate the four `SKILL.md` files and their adjacent `LICENSE.txt` files first.

## Binding decisions

1. One plugin: `zuaef-artifacts`.
2. Four native capability units: DOCX, PDF, Slides, Spreadsheet.
3. Natural-language routing only. No `/docx`, `/pdf`, `/ppt`, `/excel`, or equivalent format commands.
4. Explicit user format requests always win.
5. When format is not explicit, route from the intended business result.
6. Do not add a hard-coded keyword router for artifact formats.
7. Do not grant arbitrary shell access to any artifact capability.
8. Fixed external executables may be invoked internally by bounded wrappers with fixed argument construction and workspace path checks.
9. `core.py`, `runtime.py`, and `composition.py` must receive no functional changes for v0.1.
10. Gateway changes are permitted only for generic artifact delivery to surfaces; they must not contain document-domain business policy.
11. The existing Knowledge Worker remains the reading/search/research side. `zuaef-artifacts` is the production/revision side.
12. Do not claim full behavior parity with the local OAI reference packages in v0.1.
13. Do not copy OAI source, prompt text, templates, or assets into the shippable plugin unless the user's applicable agreement explicitly permits that use. Default implementation is independent and based on public libraries plus this spec's functional requirements.
14. The local `oai/` tree is never modified by this work.

## Product model

```text
User / Feishu
    |
    v
Single ZUAEF FDE Agent
    |
    +-- Knowledge Worker
    |      read / inspect / search / research
    |
    +-- Artifact capability catalog
           |
           +-- DOCX
           +-- PDF
           +-- Slides
           +-- Spreadsheet
                  |
                  v
           workspace/artifacts/
                  |
                  v
          Gateway file delivery
```

## Read order for Codex

1. `00_SOURCE_OF_TRUTH.md`
2. `01_PRODUCT_AND_UX.md`
3. `02_ARCHITECTURE.md`
4. `03_REFERENCE_AND_LICENSE_BOUNDARY.md`
5. `04_CAPABILITY_CONTRACTS.md`
6. `05_ROUTING_AND_DISCLOSURE.md`
7. `06_ARTIFACT_RUNTIME.md`
8. `07_FORMAT_ENGINES.md`
9. `08_FEISHU_INTEGRATION.md`
10. `09_IMPLEMENTATION_TASKS.md`
11. `10_ACCEPTANCE.md`
12. `11_DEPLOYMENT.md`
13. `12_CODEX_MASTER_PROMPT.md`

## Definition of success

The implementation is successful when a user can send a natural-language request such as:

> 根据这个报价表，做一份可以直接发给客户的正式方案，并附一个详细计算表。

and the agent can autonomously combine document reading with more than one artifact capability, produce validated deliverables, and return them through Feishu without asking the user to choose a format command.
