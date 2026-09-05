# Codex Implementation Brief

Mission:
Preserve the current event-driven Human-Agent Quant system and add strict PIT replay plus a governed research loop.

Start by reading:
`18_CODEX_MASTER_PROMPT.md`, then `15_TASKS.md`.

Do first:
- write BASELINE_RUNTIME.md;
- verify local-ahead work;
- do not edit before runtime baseline;
- complete Agent surface gap audit before proposing any new model-visible quant tool.

Primary deliverable:
A recent 10-trading-day production-equivalent PIT-safe replay that:
- cannot see future data;
- cannot mutate live-forward;
- uses the existing D+1/3/5/8 outcome contract;
- explains blocked/degraded days honestly.

Then:
Market Regime shadow -> Evidence Retrieval -> Experiment Registry -> S2 Shadow -> HUMAN_SKIP analysis.

Do not:
rebuild Workbench, rebuild Bridge, rebuild evaluator, expose loopback writes remotely,
relax production to create signals, or implement automatic broker orders.
