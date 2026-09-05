# 02 — Product Requirements

The product is not a broker-app clone. It is a private small-account A-share decision and research desk.

It must answer:
1. Is runtime healthy?
2. Is evidence trustworthy enough?
3. Should we participate in this market regime?
4. Which names deserve attention?
5. Is anything truly READY?
6. What position/exit risk needs attention?
7. What did the human execute or skip?
8. How did it settle at D+1/3/5/8?
9. Is strategy performance degrading?
10. What should be tested next?

v3.1 must preserve current live capabilities and implement:
- explicit research/replay/shadow/live_forward namespaces;
- 10-day production-equivalent PIT-safe replay;
- Agent surface gap audit rather than tool proliferation;
- shadow-first Market Regime;
- targeted Evidence Retrieval;
- experiment registry/orchestration over existing evaluator;
- human override/SKIP value analysis.

Deferred:
- autonomous real-money broker execution;
- Level-2;
- full broker terminal parity;
- broad community/news/研报 ingestion without a concrete hypothesis;
- autonomous production strategy rewriting.
