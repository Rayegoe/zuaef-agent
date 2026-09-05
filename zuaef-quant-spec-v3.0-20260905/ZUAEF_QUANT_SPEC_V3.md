# ZUAEF Quant Spec v3.0 — Consolidated
> This file concatenates the normative Markdown sections from the spec pack. Runtime truth outranks lagging Git.

---

# 00 — Source of Truth & Current State

## Status labels

Every requirement in this pack must use one of these meanings:

- **CURRENTLY_OBSERVED** — directly supported by the latest operator/runtime report.
- **REPORTED_BASELINE** — behavior previously observed/discussed and believed present; Codex must verify against the running tree before relying on implementation details.
- **TARGET_V3** — new or strengthened behavior to implement.
- **EXPERIMENTAL** — may run only in sandbox/replay/shadow until promoted.
- **TO_VERIFY_RUNTIME** — unresolved implementation detail; never guess.

## CURRENTLY_OBSERVED — latest run

| Field | State |
|---|---|
| Report | `quant-business-20260904-1647.html` |
| Delivery | Telegram success, message ID `107` |
| Run | `a97d4047…` |
| Host/runtime | healthy |
| Decision | `NOT_RUN_TODAY` |
| Trigger count | `0` |
| Candidate count | `50` |
| Data trust | `FAIL` |
| PIT | contaminated / primary trust blocker |
| Coverage | `PASS` |
| Freshness | `WARN` |
| Semantic integrity | `PASS` |
| Source | `PASS` |
| Profitability | `UNPROVEN` |
| S3 | frozen |
| True trade records | `5` |
| Live forward observations | `0` |
| M1 evidence | `PARTIAL` |

### Interpretation

`NOT_RUN_TODAY + trigger_count=0` is **not** an outage. The host and delivery path are healthy. It means no currently eligible action was produced under the active rules/evidence state.

The system is therefore:

- operationally alive;
- capable of producing and delivering business reports;
- not yet allowed to claim trusted historical performance because PIT is contaminated;
- not yet allowed to claim live profitability because forward evidence is absent/insufficient.

## REPORTED_BASELINE — verify, do not re-invent

The current system has been described as approximately:

1. Universe near `CSI300 ∪ CSI500` (~800 names).
2. Hard exclusions such as risk-warning/ST, `PE <= 0`, insufficient liquidity, insufficient price history, and stale financial data.
3. Candidate scoring approximately `Value 40 + Quality 35 + Tradability 15 + Timing 10`.
4. Compression to roughly 50 candidates.
5. Live/latest observation and timing/trigger evaluation (`READY / NEAR / NO` or equivalent runtime vocabulary).
6. Deterministic trading gates and `NO_TRADE`/entry/exit decisions.
7. Position lifecycle and exit handling; the 5-day moving average has been used as an exit-oriented rule rather than as a universal selection rule.
8. Evidence/report rendering and Telegram delivery.
9. Previous engineering fixes discussed: trading-day alignment, volume-unit normalization/fail-closed behavior, cache schema/metadata migration checks, suspension valuation using last available close, initial-capital metric baseline, frontend/JSON escaping, lifecycle reset after acknowledged sell, and cleanup around exit evaluation.

Codex must inspect the actual runtime tree and retain any working implementation. Do not replace these merely because this spec uses more general names.

## TARGET_V3

The next milestone adds five capabilities **without pretending they already exist**:

1. **PIT-safe Replay Clock** and 10-day recent historical replay.
2. **Market Regime / Participation Gate** above stock-level signals.
3. **Agent Control Surface** for observe/control/decision-support actions.
4. **Evidence Retrieval Layer** for targeted external/context evidence.
5. **Sandbox + Code Experiment Loop** with immutable promotion rules.

## Conflict policy

If Git says one thing but the live report/runtime says another:

1. record the discrepancy;
2. preserve the live behavior;
3. patch the repository toward the runtime truth only after reproducing it;
4. never regress the running system merely to make it match stale Git.

---

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

---

# 02 — Architecture

## Target architecture

```text
                    ZUAEF-Agent
            reasoning / orchestration / research
                         │
          ┌──────────────┼─────────────────┐
          │              │                 │
          ▼              ▼                 ▼
   Quant Action API   Evidence API     Experiment API
          │              │                 │
          └──────┬───────┴────────┬────────┘
                 │                │
                 ▼                ▼
        Deterministic Core   Sandbox / Code Runner
        signals/risk/gates    S0 / S1 / S2
                 │                │
                 ▼                ▼
           Evidence Store   Experiment Store
                 │                │
                 └──────┬─────────┘
                        ▼
              Dashboard / Telegram
                        │
                        ▼
                      Human

Broker/data providers remain below the system as market/account infrastructure.
```

## Component responsibilities

### Quant Runtime — production authority

- ingest/normalize permitted data;
- generate candidate pool;
- evaluate timing/triggers;
- evaluate deterministic risk gates;
- manage position lifecycle;
- freeze observations and decisions;
- settle outcomes;
- emit machine-readable state.

The runtime must not delegate hard risk permissions to an LLM.

### ZUAEF-Agent

- interpret system state;
- decide which read/control tools to call;
- investigate anomalies;
- retrieve contextual evidence on demand;
- formulate hypotheses;
- schedule/run sandbox experiments;
- explain decisions and failures;
- create work packets for code changes;
- never silently modify production strategy or evidence.

### Evidence Store

Append-oriented source of truth for:

- observations;
- data-trust verdicts;
- trigger/gate states;
- decisions;
- position lifecycle events;
- settlements;
- replay outputs;
- experiment outputs;
- deployment/config identifiers.

### Sandbox / Code Runner

- S0 Scratch: exploratory Python/SQL/shell.
- S1 Replay: historical clock and PIT-safe data boundary.
- S2 Shadow: live data, simulated actions, no broker effects.

### Evidence Retrieval Layer

On-demand contextual evidence, not a bulk LLM feed. Primary first wave:

- market/sector breadth;
- announcements;
- corporate actions;
- current positions/cost basis;
- minute price/volume.

### Presentation/Attention

Dashboard and Telegram are **projections**, not the source of truth. Agent should consume structured state/events rather than scrape HTML.

## Architectural invariants

1. Production strategy is versioned and frozen until explicit promotion.
2. Replay and live-forward evidence use separate namespaces.
3. An experiment can never rewrite historical production evidence.
4. A real order is an external effect and requires the configured external-effect gate.
5. Missing/uncertain critical evidence fails closed for live trade permission.
6. The LLM can propose; deterministic code permits/denies.

---

# 03 — Decision Pipeline

## Baseline flow

```text
Universe (~800, verify runtime)
  ↓
Hard eligibility filters
  ↓
Candidate scoring/ranking
  ↓
Top-N attention pool (~50 current)
  ↓
Market participation gate          [TARGET_V3]
  ↓
Live timing/trigger evaluation
  ↓
Evidence/risk gates
  ↓
Decision: BUY / NO_BUY / HOLD / EXIT / NO_TRADE
  ↓
Freeze observation + decision
  ↓
Future settlement (+1d/+3d/+5d/exit, MFE/MAE, costs)
  ↓
Evidence update + degradation analysis
```

## Separation of concerns

### Candidate generation

Purpose: reduce the search space. A candidate is **not** a trade signal.

The current score weighting is a `REPORTED_BASELINE`, not a constitutional rule. Keep the active production weights frozen under a versioned config. Weight changes belong in experiments.

### Participation gate

Purpose: determine whether the market environment permits normal participation, selective participation, or no participation.

This gate is evaluated **before** individual-stock permission. See `05_MARKET_REGIME.md`.

### Trigger

Purpose: answer whether the timing evidence is currently sufficient. Trigger vocabulary should map cleanly to:

- `READY`: timing requirement met;
- `NEAR`: close but not permitted;
- `NO`: no actionable timing evidence.

Do not convert `NEAR` into an order merely because an LLM likes the setup.

### Deterministic decision gates

Recommended minimum live-entry gate set:

```text
market_regime != DO_NOT_PARTICIPATE
critical_data_trust == PASS
critical_freshness == PASS
trigger == READY
position_limit == PASS
risk_budget == PASS
symbol_trade_status == PASS
```

If any required gate fails, decision is `NO_BUY` or `NO_TRADE` with machine-readable reasons.

### Exit

Exit logic is independently testable. Do not assume entry optimization and exit optimization should change together. Candidate experiments include fixed stop, trailing stop, time stop, MA exit, volatility stop, and regime-deterioration exit.

## Abstention is a first-class result

`NOT_RUN_TODAY`, `NO_TRADE`, or zero triggers are valid business outcomes when the evidence says not to participate. The system must distinguish:

- no opportunity;
- market closed;
- critical evidence unavailable;
- data stale;
- runtime failure;
- trading disabled;
- strategy gate rejected.

---

# 04 — Data & Point-In-Time Integrity

## Definition

**PIT (Point-In-Time)** means: at decision time `T`, the strategy may only consume facts actually available at or before `T`.

The fundamental rule is:

```text
available_at <= decision_time
```

Not:

```text
report_period <= decision_time
```

Example: a 2025-12-31 annual report published on 2026-04-30 is unavailable to a 2026-03-01 decision.

## Why current trust fails

The latest runtime report marks overall data trust `FAIL`, with PIT contamination as the primary blocker. The system should treat this as a **validation problem, not a host/runtime outage**.

## Required time fields

Every evidence item used in historical/replay decisions should carry, where applicable:

- `event_time` — time the economic/market event happened;
- `source_time` — provider/announcement timestamp if supplied;
- `available_at` — earliest time the strategy is allowed to use it;
- `ingested_at` — when our system obtained it;
- `decision_time` — replay/live decision clock;
- `source_id` and lineage metadata.

For bars, `available_at` must reflect when that bar is complete/observable under the production cadence. Never let a 15:00 daily bar leak into a 10:30 replay.

## Unknown availability policy

For **strict replay/live trading evidence**:

- if `available_at` is required and unknown → `INSUFFICIENT_EVIDENCE` / fail closed;
- do not silently substitute report period/date;
- an optional research-only mode may use approximations but must be labeled `CONTAMINATED` or `NON_PIT` and excluded from promotion evidence.

## Historical membership and survivorship

If universe composition is part of historical/replay validation, use membership valid at `decision_time`. Current index constituents cannot be blindly projected backward.

## Corporate actions

Price/volume adjustments and corporate actions must be explicit and versioned. Replay should be able to state:

- raw price source;
- adjustment method;
- corporate-action records used;
- whether a later revision was required.

## Data trust dimensions

Machine-readable trust should include at least:

- `coverage`
- `freshness`
- `semantic_integrity`
- `source_integrity`
- `pit_integrity`
- `timing_integrity`

A composite status must not hide a failed critical dimension.

## Critical live rule

A production trade permission may use a stricter subset than research. For example, an old fundamental factor could remain informational while fresh price/trading status/risk data must be `PASS`. The schema must make criticality explicit rather than treating every warning identically.

---

# 05 — Market Regime / Participation Gate

**Status:** TARGET_V3, initially shadow-only.

## Purpose

Before asking “which stock should be bought?”, answer “should a weakly informed small retail participant be in this market state at all?”

This is deliberately above stock-level triggers.

## Initial state model

Use three production-relevant states first:

- `DO_NOT_PARTICIPATE`
- `SELECTIVE`
- `NORMAL`

`AGGRESSIVE` may exist later but should not be necessary for v3 acceptance.

## Inputs — start simple

Do not invent a large factor zoo. Start with auditable, low-dimensional inputs such as:

- index trend/return/realized volatility;
- market breadth: advancing/declining ratio, fraction above relevant moving averages;
- sector breadth/dispersion;
- turnover/liquidity change;
- trigger success/failure/degradation metrics from recent forward observations;
- abnormal market/trading status.

All inputs need `as_of`/`available_at` semantics.

## Output contract

Output:

- `regime`
- `confidence` (optional numeric, never a substitute for gates)
- `reason_codes[]`
- `as_of`
- `input_snapshot_id`
- `model_or_rule_version`
- `mode`: `shadow | production`

## Rollout

1. Implement deterministic baseline.
2. Run shadow-only against current production decisions.
3. Replay recent 10/20/60 trading days PIT-safely.
4. Measure whether it reduces bad exposure without merely suppressing all trades.
5. Promote only after explicit evidence review.

## Interaction with signals

Recommended semantics:

```text
DO_NOT_PARTICIPATE → no new entries regardless of symbol READY state
SELECTIVE          → higher entry/risk threshold; lower exposure
NORMAL             → standard production thresholds
```

Do not let Agent prose override `DO_NOT_PARTICIPATE`.

---

# 06 — Agent Control API

## Goal

Let ZUAEF-Agent operate the system through structured actions instead of scraping Dashboard HTML or shelling ad hoc into production state.

## Permission tiers

### L0 — Observe (enable first)

- status
- attention
- candidates
- triggers/decisions
- positions
- observations
- evidence health
- latest report/run metadata
- experiment/replay status

### L1 — Control

- run one scan/tick
- refresh permitted data
- generate report
- settle due observations
- start replay
- start sandbox experiment

### L2 — Decision support

Agent may request evaluation such as entry/exit/participation, but the returned decision is produced by deterministic gates.

### L3 — External execution

Real broker order/cancel is **not part of v3 default enablement**. It requires an explicit external-effect gate and separate acceptance work.

## Suggested CLI surface

```text
quant status --json
quant once --json
quant attention --json
quant candidates --json
quant decision [--symbol SYMBOL] --json
quant positions --json
quant observations --json
quant settle --json
quant replay ... --json
quant experiment ... --json
```

Existing command names should be reused when already present; aliases are acceptable. Do not break working scripts solely to match this spelling.

## Tool/API behavior

All action results should include:

- `schema_version`
- `run_id`
- `as_of`
- `mode` (`production|shadow|replay|scratch`)
- `strategy_version`
- `data_snapshot_id` where applicable
- explicit `status`
- machine-readable `reason_codes`

## Idempotency

Control actions that may be retried must have an idempotency key or deterministic run key. Re-sending a Telegram report must not accidentally create a new trading decision.

## Error taxonomy

At minimum distinguish:

- `MARKET_CLOSED`
- `INSUFFICIENT_EVIDENCE`
- `DATA_STALE`
- `PIT_BLOCKED`
- `NO_TRIGGER`
- `RISK_BLOCKED`
- `RUNTIME_ERROR`
- `EXTERNAL_EFFECT_REQUIRED`

## Agent policy

The Agent is allowed to reason broadly but must not:

- mutate production strategy config silently;
- edit frozen observations/settlements;
- convert experimental results directly into production;
- bypass a deterministic gate;
- issue a real order without the external-effect policy.

---

# 07 — Evidence Retrieval Layer

## Why

If Agent only sees the same 50 candidate scores that Quant already computed, it becomes a narrator rather than an investigator. But importing every feature of a securities app is unnecessary.

Use **targeted retrieval** after Quant narrows the problem.

## Priority 1 evidence

1. Market and sector breadth.
2. Exchange/company announcements.
3. Corporate actions and trading-status changes.
4. Current positions and cost basis.
5. Minute-level price/volume needed by active timing rules.

## Priority 2

- regulatory events;
- targeted current news;
- financing/margin or ETF/flow context when an experiment justifies it;
- sector/industry classifications and state.

## Defer by default

- Level-2/order-book depth;
- bulk sell-side research ingestion;
- community/social feeds;
- generic “money flow” metrics whose construction is opaque.

These should be added only when a specific hypothesis shows they can improve a measured bottleneck.

## Suggested tool surface

```text
get_price_history(symbol, start, end, as_of?)
get_intraday(symbol, date, interval, as_of?)
get_announcements(symbol, start, end, as_of?)
get_financials(symbol, period?, as_of?)
get_market_breadth(as_of)
get_sector_state(sector, as_of)
get_corporate_actions(symbol, start, end, as_of?)
get_regulatory_events(symbol, start, end, as_of?)
get_news(symbol_or_topic, start, end, as_of?)
get_position(symbol?)
```

## Retrieval invariants

- Historical/replay retrieval must accept and enforce `as_of`.
- Evidence returned to Agent includes source and availability timestamps.
- If provider data cannot honor historical availability, mark it non-PIT and exclude it from strict replay promotion evidence.
- Announcements begin as **risk/event filters**, not automatic alpha signals.

---

# 08 — Sandbox & Code Experiment Environment

## Principle

> **Experiment freely; preserve production truth; never rewrite evidence.**

Code access should be broader than real-money execution access.

## S0 — Scratch

Purpose: fast diagnosis and exploratory analysis.

Allowed:

- Python
- shell
- SQL (SQLite/DuckDB)
- temporary files
- data profiling
- plots/statistics
- disposable code

No production mutation.

## S1 — Replay

Purpose: reproduce past trading days with a frozen historical clock.

Requirements:

- full/compatible Quant runtime copy or isolated data/config surface;
- `decision_time = T` controls every historical read;
- network/provider reads after `T` are forbidden or sanitized;
- output namespace distinct from live forward;
- production cadence can be replayed intraday.

## S2 — Shadow

Purpose: current real-time market data, simulated actions.

Requirements:

- same observation/decision contracts as production where possible;
- no real broker external effects;
- immutable shadow decisions;
- later settlement against real outcomes.

## Agent + Code permissions

Allowed in sandbox:

- branch/diff code;
- run tests;
- vary parameters;
- replay/backtest/walk-forward;
- run sensitivity/ablation/counterfactual studies;
- generate reports;
- create a patch/work packet.

Forbidden:

- direct production strategy overwrite;
- delete/alter frozen evidence;
- rewrite historical observations after outcomes are known;
- deploy a parameter because “backtest got better” without promotion gates.

## Debugging loop

```text
Observe failure/anomaly
  ↓
Collect runtime state/logs
  ↓
Form hypotheses
  ↓
Reproduce in S0/S1
  ↓
Patch sandbox branch
  ↓
unit + integration + replay verification
  ↓
produce diff + evidence
  ↓
explicit promotion/release process
```

## Zero-trigger diagnostic experiment

If production has candidates but zero triggers for 10–15 trading days, Agent must test competing hypotheses rather than loosen production reflexively:

- true absence of opportunity;
- trigger threshold too strict;
- stale/freshness fail-close;
- PIT blocker;
- data/unit bug;
- regime mismatch.

Production remains frozen while variants are tested.

---

# 09 — 10-Day PIT-Safe Replay

**Priority:** P0.  
**Purpose:** create fast diagnostic/evidence value while live forward data accumulates.

## Important semantic boundary

Replay evidence is **not live forward evidence**.

Keep separate counters:

```text
Historical Backtest
Recent PIT-Safe Replay
Live Forward
```

Never increment `live_forward_observations` from replay.

## Scope

Start with the most recent **10 trading days** for which required data is available. Expand to 20 then 60 only after the 10-day pipeline is verified.

## Time-machine rules

For replay point `T`:

1. Runtime clock reports `T`.
2. Every market/fundamental/event read must enforce `available_at <= T`.
3. A bar not yet complete at `T` cannot be used as if complete.
4. Current/future index composition may not leak backward.
5. Later corrections/revisions must either be reconstructed correctly or clearly label the run degraded.
6. The production strategy/config version under test must be explicit.

## Intraday cadence

If production observes at multiple times during the day, replay those times. Do not run only at 15:00 and claim to know what 10:30 would have seen.

Example:

```text
09:35 → observation/decision
10:00 → observation/decision
10:30 → observation/decision
...
14:30 → observation/decision
```

Use actual production cadence if different.

## Settlement

After a replay decision is frozen, the evaluator may reveal later data and calculate:

- +1d / +3d / +5d return where applicable;
- realized exit return;
- MFE (maximum favorable excursion);
- MAE (maximum adverse excursion);
- estimated costs/slippage;
- rule compliance.

## 10-day output

The report must show:

- trading days replayed;
- observation count;
- candidates and triggers per day;
- decisions by reason;
- settled trigger count;
- PIT blocked/degraded events;
- runtime/evidence-pipeline failures;
- expectancy/dispersion only where sample size permits;
- explicit warning that this is replay, not live forward.

## Acceptance

- no read after replay clock in an adversarial leakage test;
- repeated run with same inputs/config is deterministic;
- replay evidence cannot appear in live-forward counters;
- at least one synthetic test proves an EOD bar cannot leak intraday;
- report can explain every zero-trigger day as either valid no-trigger or blocked/degraded.

---

# 10 — Experiment System

## Experiment lifecycle

```text
PROPOSED
  ↓
RUNNING_S0 / RUNNING_S1
  ↓
REJECTED  or  REPLAY_PASS
                  ↓
              SHADOW
                  ↓
          FORWARD_EVALUATION
                  ↓
          PROMOTED / REJECTED
```

## Required experiment record

- `experiment_id`
- human/Agent hypothesis stated before evaluation
- baseline strategy/config version
- exactly what changed
- data/evidence scope
- expected causal mechanism
- primary metric(s)
- risk/guardrail metrics
- pre-declared rejection condition where practical
- run IDs
- result summary
- promotion state

## First experiment families

### Candidate count

`Top 30 vs 50 vs 80` — measure trigger quality and concentration, not just signal count.

### Score weights

Current reported baseline is value/quality heavy. Explore whether a short-cycle small-account strategy benefits from more tradability/relative-strength/timing weight, while treating fundamentals more as quality/risk filters.

### Trigger sensitivity

Vary one threshold at a time (e.g. volume ratio) and observe trade count, expectancy, drawdown, stability, and regime dependence.

### Market regime

Compare no regime gate vs shadow regime gate; evaluate whether it avoids negative-expectancy periods without eliminating the opportunity set.

### Exit policy

Hold entry fixed and test exit families independently.

## Anti-overfit rules

Forbidden loop:

```text
bad result → tweak parameter → rerun same data → good result → production
```

Required loop:

```text
problem → hypothesis → isolated change → replay/walk-forward → shadow → new forward evidence → promotion decision
```

Do not optimize dozens of parameters simultaneously. Prefer ablations and small causal experiments.

## Production freeze

Production config receives a stable version. Experiments reference it but cannot mutate it in place. Promotion creates a new production version with an audit trail.

---

# 11 — Live Forward Evidence

## Why

Live forward observations are the strongest evidence because they are generated before the outcome is known and naturally preserve the real runtime/data conditions of the day.

## Evidence milestones

Do not use calendar days alone. Count valid, settled, sufficiently independent triggers.

Suggested gates:

- **Operational cold start:** 5–10 trading days to prove the loop remains alive.
- **Preliminary evidence:** ~20–30 valid settled triggers.
- **Early meaningful assessment:** ~50–100 triggers, ideally across different regimes.
- **More credible assessment:** 100+ triggers spanning clear market-state changes.

Time ranges such as 2–4 months or 3–6+ months are only rough expectations; sample count and regime diversity matter more.

## M1 formal audit gate

Trigger the first formal M1 audit when either:

- 20 trading days have elapsed, **or**
- 30 valid forward triggers have settled,

**whichever occurs first**, provided the evidence pipeline has had **zero unresolved integrity failures**.

## Observation record

Minimum useful fields:

- timestamp / available-at clock;
- symbol;
- contemporaneous price;
- market regime (once deployed, or shadow state);
- candidate score/version;
- trigger state and reason;
- every deterministic gate state;
- decision;
- position/risk context;
- +1d/+3d/+5d or actual exit outcome;
- MFE/MAE;
- transaction cost/slippage assumption or actual cost if later available;
- final settlement state.

## Evaluation metrics

Prioritize:

- expectancy after costs;
- distribution and tail loss;
- max drawdown at strategy/account level;
- hit rate only with payoff ratio;
- MFE/MAE;
- performance by market regime;
- `READY` vs `NEAR` separation;
- concentration of profit in a few outliers;
- signal/strategy degradation over rolling windows.

## Zero-trigger policy

If 10–15 trading days pass with a healthy candidate pool but zero triggers:

- diagnose in sandbox;
- do not loosen production merely to manufacture signals;
- test whether the cause is market state, thresholds, stale data, PIT blocking, or a bug.

---

# 12 — Risk & Execution

## Principle

LLM reasoning must never be the final permission layer for capital-changing actions.

## Deterministic risk gates

At minimum represent explicitly:

- market participation permission;
- symbol eligibility/trading status;
- data freshness/trust;
- trigger readiness;
- max position size;
- portfolio concentration;
- sector concentration when relevant;
- risk budget / loss budget;
- duplicate/order lifecycle state;
- exit urgency.

## External effects

Real brokerage actions are external effects. v3 may prepare the interface but should keep real order execution disabled by default until:

- live forward evidence reaches the agreed gate;
- order idempotency/reconciliation exists;
- broker/account state is verified;
- emergency stop/kill switch is tested;
- operator explicitly enables the external-effect path.

## Human role

During current M1:

- Agent may recommend/prepare;
- deterministic core may permit/deny;
- human retains final real-money action unless a later release explicitly changes that policy.

## Fail-closed conditions

Examples:

- critical fresh price unavailable;
- trading status unknown;
- data unit/semantic mismatch;
- conflicting open-order/position state;
- production strategy version unknown;
- evidence store unavailable;
- external-effect authorization absent.

---

# 13 — Observability, Dashboard & Telegram

## Current achievement

Latest report generation and Telegram delivery are operational. Preserve this path.

Dashboard/HTML is a **human projection** of underlying state. Agent should consume structured contracts directly.

## Attention model

Notifications should prioritize exceptions and actionability:

1. real `READY` trigger or exit attention;
2. `DO_NOT_PARTICIPATE`/regime change;
3. critical data/evidence degradation;
4. runtime/bridge failure;
5. experiment promotion/rejection summary;
6. routine no-action report.

## Daily brief

A compact machine/human brief should contain:

- market participation state;
- production decision;
- READY/NEAR counts;
- top attention candidates (bounded number);
- current positions/exit attention;
- data trust/PIT/freshness;
- live forward counts and settlements;
- replay/shadow experiment summary;
- runtime health.

## Zero-trigger report

Do not write “nothing happened.” Report whether:

- no true timing opportunity existed;
- market gate blocked participation;
- evidence gate blocked action;
- data was stale/insufficient;
- runtime failed.

## Delivery idempotency

A report delivery event is distinct from a trading decision. Retrying Telegram delivery must not create a new decision/evidence record.

---

# 14 — Test Plan

## Unit tests

- PIT availability predicate boundaries;
- daily/minute bar completion rules;
- trust aggregation and criticality;
- regime state transitions;
- gate reason-code stability;
- experiment state machine;
- evidence namespace separation;
- idempotency keys.

## Integration tests

- `once` when market closed returns a non-action state and creates no fake trigger;
- candidate → trigger → decision → observation → settlement;
- report renders from structured state;
- Telegram retry does not duplicate decision;
- Agent read/control calls do not bypass gates;
- sandbox never writes production evidence/config.

## Replay adversarial tests

1. Future announcement timestamp injected → replay must block it.
2. EOD daily bar queried at 10:30 → unavailable.
3. Future/current index membership projected backward → detected or blocked.
4. Provider row revised after T → run marked degraded unless historical version is available.
5. Randomized future values changed → decisions before T remain byte/semantically identical.

## Data integrity tests

- price/volume units;
- duplicate bars;
- missing trading days;
- date/timezone alignment;
- cache metadata vs rows/date range;
- stale data fail-closed;
- corporate action adjustment consistency;
- suspension valuation behavior.

## Experiment tests

- variant cannot mutate baseline config;
- experiment records predate outcome evaluation;
- promotion requires declared gates;
- rejected experiment remains queryable;
- identical run seed/input/config is reproducible where deterministic.

## Runtime smoke

- status
- once
- candidates
- observations
- settle
- report generation
- Telegram bridge
- replay dry-run
- shadow experiment dry-run

---

# 15 — Roadmap

## P0 — Preserve truth + unlock fast evidence

### P0.1 Runtime truth snapshot

Expose machine-readable current status and version identifiers without changing strategy behavior.

### P0.2 PIT-safe replay foundation

Implement replay clock, availability gate, namespace separation, and adversarial tests.

### P0.3 Recent 10-day replay

Run the current production strategy/config through recent PIT-safe intraday replay; produce a report separate from live forward.

### P0.4 Agent L0/L1 action surface

Structured observe/control tools: status, once, attention, candidates, decisions, positions, observations, settle, replay.

**P0 outcome:** Agent can safely inspect/control the loop and we can diagnose trigger behavior without waiting weeks.

## P1 — Decision quality + research loop

### P1.1 Market Regime shadow gate

Three-state deterministic participation gate, shadow-only first.

### P1.2 Evidence Retrieval v1

Breadth, announcements, corporate actions, positions/cost, intraday data.

### P1.3 Experiment Manager

Hypothesis/variant/run/result/promotion records with S0/S1/S2 separation.

### P1.4 Shadow experiments

At minimum candidate-count, trigger-sensitivity, regime, and exit experiments.

**P1 outcome:** Agent becomes an investigator/researcher, not merely a reporter.

## P2 — Evidence-based promotion and optional execution integration

- live-forward degradation metrics;
- strategy promotion/rejection workflow;
- broker execution contract/reconciliation only if evidence gate is met;
- emergency/kill-switch and external-effect authorization.

## Explicitly defer

- broad broker-app feature parity;
- Level-2;
- social/community;
- large sell-side research corpus;
- autonomous production strategy self-modification.

---

# 16 — Acceptance Criteria

## Release v3 foundation — required

### A. No regression of current production

- latest working live/host/report/Telegram path continues to operate;
- market-closed path does not produce fake events;
- existing deterministic gates retain behavior unless a separately approved production change says otherwise.

### B. Machine-readable control surface

- Agent can query status/candidates/decisions/positions/observations;
- Agent can invoke safe control actions with explicit mode and idempotency;
- all results identify strategy/runtime mode and reason codes.

### C. PIT-safe replay

- 10 recent trading days replayed where data permits;
- intraday time boundary enforced;
- adversarial future-data test passes;
- replay and live-forward evidence are impossible to confuse programmatically.

### D. Experiment isolation

- production config/evidence cannot be mutated by S0/S1/S2;
- variant changes are explicit and reviewable;
- experiment outcome has an immutable lifecycle.

### E. Market regime shadow

- deterministic 3-state output exists;
- output has reason codes/as-of/version;
- no effect on production orders/decisions until separately promoted.

### F. Evidence/report transparency

Dashboard/report explicitly distinguish:

- host/runtime health;
- data trust/PIT;
- production trigger/decision;
- replay results;
- live forward results;
- experiments/shadow results.

## M1 evidence gate

First formal audit at 20 trading days or 30 settled forward triggers, whichever first, with no unresolved evidence-pipeline integrity failure.

## Non-acceptance examples

The project is **not** accepted merely because:

- HTML got more pages;
- more indicators were added;
- replay generated many trades by relaxing rules;
- an LLM produced a convincing explanation;
- backtest CAGR improved on the same tuned sample.

---

# 17 — Migration From Current Runtime

## Strategy

Use an **additive strangler-style migration**, not a rewrite.

## Step 1 — Discover and map

Codex must first identify the currently running entrypoints, state directories, services/timers, report renderer, bridge, and candidate/live-monitor modules. Record exact runtime paths and versions in `BASELINE_RUNTIME.md` before changes.

## Step 2 — Add adapters

Wrap existing status/once/candidates/position/evidence behavior behind structured JSON/CLI/API adapters. Do not move core logic just to create architectural neatness.

## Step 3 — Add evidence namespaces

Create explicit mode/namespace separation:

- production/live-forward;
- replay;
- shadow;
- scratch/ephemeral.

Existing production records remain intact.

## Step 4 — Replay clock

Introduce a clock/data-access abstraction at the narrowest viable seam. Production continues to use wall/market time; S1 uses replay time.

## Step 5 — Market regime shadow

Add as a parallel projection. Do not wire it into production entry permission in the first release.

## Step 6 — Agent surface

Expose safe reads and idempotent controls. Keep shell internals private behind the adapter where practical.

## Step 7 — Experiments

Run on copied/isolated config/state. Promotion creates a new version; it never overwrites the active config in place.

## Rollback

Every P0/P1 capability needs a feature flag or independently removable adapter. If new Agent/replay functionality fails, the existing live loop/report/Telegram path must remain usable.

---

# 18 — Security, Integrity & Non-Negotiable Invariants

1. **Evidence immutability:** frozen observations/decisions/settlements are append-only or otherwise tamper-evident through storage/version controls.
2. **Mode isolation:** replay/shadow/scratch cannot write production evidence or brokerage effects.
3. **No silent future data:** strict replay reads enforce `available_at <= decision_time`.
4. **No silent strategy mutation:** experiments cannot alter active production config.
5. **Deterministic risk authority:** LLM cannot bypass hard gates.
6. **External-effect boundary:** real orders/cancels require explicit external-effect authorization.
7. **Idempotency:** retries of control/delivery cannot duplicate state-changing actions.
8. **Traceability:** every decision is attributable to strategy version, data snapshot/clock, and gate reasons.
9. **Fail closed:** unknown critical data/risk state prevents new capital exposure.
10. **Dashboard is not truth:** presentation failure cannot overwrite/redefine runtime/evidence state.
11. **No evidence laundering:** contaminated historical/backtest/replay results cannot be relabeled as live forward.
12. **No feature accretion without hypothesis:** Level-2/news/research/community integrations require a defined decision/research use case.

---

# 19 — Runtime Questions Codex Must Verify

These are intentionally **not** answered by assumption.

1. What exact local branch/tree is currently running relative to GitHub `main`?
2. What service/timer units own the Quant loop and Telegram bridge today?
3. What is the canonical state/evidence store format and directory?
4. What command currently implements `status`, `once`, candidate build, live monitor, settlement, and report rendering?
5. What exact trigger vocabulary is present in code today (`READY/NEAR/...`)?
6. What is the actual intraday polling cadence?
7. Which current data providers supply daily bars, intraday data, financials, index membership, and corporate actions?
8. Which fields have trustworthy `available_at`/announcement timestamps today?
9. What exactly is included in the current 5 “true trade records” and how are they distinguished from replay/backtest records?
10. What code produces the reported PIT verdict and trust aggregation?
11. Is current position/cost basis sourced from system state, manual acknowledgement, or a broker/account source?
12. What is the exact production scoring config currently active?
13. Which prior fixes are already in the running tree but not yet pushed to Git?
14. Are there any uncommitted changes that would be overwritten by a checkout/reset?

Codex must create `BASELINE_RUNTIME.md` with answers before modifying files. A missing answer should be marked unknown, not guessed.

---

# Codex Implementation Brief

## Mission

Extend the **currently running** ZUAEF Quant system into a live decision + PIT-safe replay + Agent experiment platform **without regressing the working runtime/Telegram pipeline and without treating stale Git as the sole truth**.

## Mandatory first action — baseline, no edits

1. Inspect current working tree, branch, `git status`, last local commit and `origin/main`.
2. Inspect running user/system services, timers and recent Quant/bridge logs.
3. Identify exact current commands/modules for status, once/live monitor, candidate generation, positions/exit, evidence/settlement, report rendering and Telegram delivery.
4. Capture current successful behavior and the latest runtime report if present.
5. Write `BASELINE_RUNTIME.md` using the labels from this pack.
6. **Do not reset, clean, checkout, stash, merge or overwrite uncommitted runtime work.**

## Work order

### WP0 — Preserve runtime truth

- add/verify machine-readable status snapshot;
- include mode, strategy version, trust dimensions, trigger/candidate counts, forward/replay counts, host health;
- no strategy behavior change.

### WP1 — PIT-safe replay foundation

- introduce replay clock / as-of data access seam;
- enforce `available_at <= decision_time`;
- create separate replay evidence namespace;
- add leakage adversarial tests;
- replay recent 10 trading days at production-equivalent intraday cadence.

### WP2 — Agent action surface

- structured read actions first;
- idempotent safe controls next;
- explicit reason/error taxonomy;
- no broker effects.

### WP3 — Market Regime shadow

- deterministic three-state participation gate;
- reason codes and versioned inputs;
- shadow-only, not production-blocking yet.

### WP4 — Evidence Retrieval v1

- breadth;
- announcements;
- corporate actions;
- current positions/cost basis;
- required minute-level price/volume.

Historical mode must honor as-of availability or label evidence non-PIT.

### WP5 — Experiment Manager + S0/S1/S2

- immutable hypothesis/variant/run/result records;
- sandbox config isolation;
- replay and live-shadow execution;
- promotion/rejection state machine.

## Engineering constraints

- Reuse existing paths/modules/contracts wherever they already solve the job.
- Prefer adapters over rewrites.
- New features are feature-flagged or shadow-only until validated.
- Tests must prove namespace isolation and future-data blocking.
- Do not widen scope into a broker terminal.
- Do not add a database/framework solely for architectural aesthetics; use the smallest durable mechanism compatible with current runtime.
- Do not silently normalize trust failures into warnings.

## Completion evidence

At the end provide:

1. changed file list and why;
2. exact commands run;
3. test results;
4. 10-day replay summary;
5. proof replay count does not alter live-forward count;
6. proof a future-data adversarial test is blocked;
7. proof current live report/Telegram path still works or, if market closed, its smoke-equivalent path;
8. known limitations;
9. next promotion decision, not just “done”.
