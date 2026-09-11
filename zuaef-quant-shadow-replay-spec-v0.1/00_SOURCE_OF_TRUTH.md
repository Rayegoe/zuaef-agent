# 00 — Source of Truth

Status: implementation-ready (distilled 2026-09-09 from operator-side review
of an external shadow-trading proposal, a repo-side grounding assessment,
and empirical facts read from the running opi5 deployment).

Priority when sources disagree:
1. current local running tree / canonical artifacts / services;
2. reviewed Git main;
3. this pack;
4. `zuaef-quant-spec-v3.1-20260905` (still authoritative for the decision
   pipeline, PIT rules, and M1 scope — this pack does not amend it);
5. older docs.

## Reproduced failures this pack answers

All three are read from production facts, not imagined:

- F1 (semantic conflation): `alerts.jsonl` records three paper positions
  (600519 / 601799 / 000807) as `POSITION_OPENED` with
  `what="user BUY acknowledged"` while their own `note` fields say
  历史持仓登记/补登. Trading fact, trading authorization, and strategy
  simulation were conflated. 600519 additionally has two ledger entries
  (p-0001, p-0003) for the same symbol and price — the mutable ledger has
  already drifted.
- F2 (data trust corrupts arithmetic): 000807 EXIT_ALERT on 2026-09-07
  reports price 26.82 against entry 12.1 and labels it
  `take_profit 6% (entry 12.1, now 26.82)` — +121% mislabeled as 6%.
  Price/corporate-action evidence is not trustworthy at the arithmetic
  layer today.
- F3 (no safe validation venue): v3.1 records profitability UNPROVEN,
  true trade records 5, live forward observations 0. There is no venue
  where the frozen strategy can be evaluated without either touching the
  canonical user ledger or implying user authorization.

## Four boundaries (final architecture)

```text
1. Decision Events      frozen-strategy READY / EXIT (deterministic,
                        persisted) — the only trade-intent source Shadow
                        may consume. LLM text is never an input.
2. Shadow Replay        pure deterministic event projection:
                        replay(decision_events, market_evidence,
                        execution_policy, initial_capital) -> ShadowResult
                        near-pure function; no mutable balance, no
                        "load yesterday state".
3. Shadow Artifacts     trades.jsonl / positions.json / nav.jsonl /
                        performance.json under
                        workspace/artifacts/quant/shadow/
                        derived, deletable, never source of truth.
4. Evidence Gate        PIT trust decides what conclusions may be drawn,
                        NOT whether Shadow may run.
```

PIT contamination blocks **strategy performance conclusions**, never
Shadow engineering. While `data_trust != CLEAN` the surface must state:

```text
SHADOW ENGINE: OPERATIONAL
PERFORMANCE EVIDENCE: INVALID / NOT ADMISSIBLE
Reason: PIT trust gate failed
```

## Source-of-truth hierarchy

```text
Canonical user ledger      user-acknowledged transactions only; never
(positions.json)           accepts autonomous shadow writes; writes only
                           through tools/quant_trading_monitor.py under
                           the existing .ledger.lock contract.

Decision event store       frozen-strategy READY / EXIT events with
                           timestamps and symbols; Shadow's only
                           trade-intent source.

PIT market evidence        market execution data + corporate-action data,
                           each with available_at; controls execution
                           validity (suspension, limits, adjustments).
                           Corporate actions belong to market evidence,
                           not to a PnL patch.

Shadow artifacts           100% derived; rm + replay must reconstruct
                           them completely; never referenced as truth.
```

## The three concepts that were conflated (F1) — mandatory separation

Every ledger record and every trade event must carry explicit fields:

| field           | meaning                        | allowed values (v0.1)                     |
|-----------------|--------------------------------|-------------------------------------------|
| intent_origin   | who produced the trade intent  | `user` / `quant`                          |
| authorization   | who authorized the transaction | `user_ack` / `autonomous_shadow` / `none` |
| venue           | which execution world          | `paper` / `shadow` / `real`               |

Legitimate combinations include:

```text
manual paper position        intent_origin=user  authorization=user_ack          venue=paper
agent suggested, user acked  intent_origin=quant authorization=user_ack          venue=paper
quant autonomous experiment  intent_origin=quant authorization=autonomous_shadow venue=shadow
real account (future)        intent_origin=*     authorization=user_ack          venue=real
```

The string "user BUY acknowledged" must never be produced by the host
unless the record actually carries `authorization=user_ack`. The Agent
surface may explain decisions but must never assert authorization facts
it does not hold.
