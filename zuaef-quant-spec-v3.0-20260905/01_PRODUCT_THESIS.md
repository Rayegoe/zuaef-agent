# 01 — Product Thesis

## Core positioning

ZUAEF Quant is a **small-account survival, decision, and research system**, not an attempt to reproduce the breadth of Eastmoney/Tonghuashun/broker apps.

Broker/securities apps already own broad functionality: quotes, order books, K-lines, news, announcements, research, account services, execution, margin, IPO subscription, communities, and more. Competing feature-for-feature is strategically wrong.

Our value is the layer above raw market access:

> **Should I participate? What deserves attention? Is the trigger real? What could invalidate it? How did it actually perform? What should be tested next?**

## First-principles assumptions

The system should remain useful even under a pessimistic market hypothesis: retail participants may face structural information, execution, governance, and policy disadvantages. Therefore the system optimizes for:

- selective participation rather than constant exposure;
- avoiding adverse/uncertain situations before maximizing upside;
- small-capacity, reproducible edges rather than grand market prediction;
- short/medium exposure windows where modelable evidence exists;
- explicit regime/rule-change risk;
- evidence that was available **at the time**, not hindsight.

## Success definition

Success is not “beat the A-share market forever.” Success is:

- deterministic execution of the research/decision process;
- bounded risk and explainable abstention;
- a positive expectancy signal that survives costs and multiple regimes;
- stable forward evidence over time;
- rapid detection when the edge disappears.

## Non-goals

Do **not** prioritize:

- cloning a broker UI;
- Level-2 microstructure without evidence that execution is the bottleneck;
- social/community feeds;
- generic wealth-management/IPO/margin features;
- large collections of technical indicators simply because they exist;
- LLM-written narratives that do not alter a deterministic decision gate;
- automatic strategy mutation in production.

## Product surface

The main business surface should stay compact and answer:

1. Participation: `DO_NOT_PARTICIPATE / SELECTIVE / NORMAL`.
2. Attention: few actionable names, not a market encyclopedia.
3. Trigger: `READY / NEAR / NO` plus the exact evidence/gates.
4. Position: exit/risk attention.
5. Evidence health: data trust, PIT, forward sample quality, degradation.
6. Research: hypotheses tested, rejected, shadowed, promoted.
