---
type: concept
title: 'Outcome Lock: 先设计 Outcome，而不是 Agent'
tags:
- agent-design
- contract
- outcome-first
- tool-surface
sources:
- id: sources/outcome-first-guide-v2
  resource: ./Outcome-First PydanticAI Agent Engineering Guide v2.0.md
  title: Outcome-First PydanticAI Agent Engineering Guide v2.0
  evidence: §3 '第一原则：先设计 Outcome，而不是 Agent'; §7 '一个 Tool 必须满足 模型决策必要性'
generated:
  by: zuaef-agent
  run_id: c75f0e6a690f4a7c83f86c6fd7966566
---

# Outcome Lock

Outcome Lock is the first principle of the Outcome-First guide: engineering starts by fixing the Outcome and its acceptance contract, before any agent, schema, state, or router is written. The very first file of any new project should be `CONTRACT.md` — not `agents.py`/`schemas.py`/`state.py`/`router.py` — and a minimal Outcome Contract answers at least six things (§3).

The principle pairs with a distinct tool-surface rule (§7): a function becomes a Tool only if the model genuinely must decide when to invoke it and with what parameters. Deterministic logic (format conversion, sorting, path generation, validation, calculations, state transitions) stays in host Python; only model-decision-required actions belong on the tool surface. Tool is "the agent's action boundary with the world," not a Python function registry.

Together these prevent two failure modes: over-designing the agent before defining done, and flooding the model with functions it has no business deciding about.
