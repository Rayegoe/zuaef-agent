# ZUAEF-ASHARE-001 — program status (frozen 2026-09-02)

**P5.5 ENGINEERING FREEZE(2026-09-02):U0–P5 全部 PASS,代码冻结,转入观察模式。**
每日真实运行 + 一行日志(`OBSERVATION_LOG.md`);重启开发的准入规则与禁改清单见
`docs/quant/README.md` §5–§6。

| Proof | State | Evidence |
|---|---|---|
| Research Engine Proof | **PASS** | P0 real data + P1 Qlib/replay evaluation + P2 consistency (gen1: `workspace/artifacts/quant/gen1/`) |
| Self-learning Loop Proof | **PASS** | P4: S1 → S2 (rejected) → S3 real agent runs, one material mutation each, evidence-driven direction changes (`workspace/workspace/artifacts/quant/children/S*-result.md`) |
| Profitability Proof | **NOT YET** | best child ≈ +0.37% annualized on 29 trades with survivorship-limited universe — intentionally not chased further in-sample |
| Live Decision Product | **FIRST PROOF PASS (2026-09-02)** | P5 interactive chain verified with a real agent run: active-universe scan (37/37 quotes in ~2.9s via qt.gtimg.cn batch) → deterministic triggers → NO_TRADE verdict without forcing a candidate → persisted Decision Brief with measured 86s signal→brief latency (`workspace/artifacts/quant/briefs/brief-live-*.json`). Interactive-only; a polling watcher remains unbuilt by design until interactive use proves insufficient (spec V008). |

## Decisions frozen at P4.5

1. **S3 is frozen as `DEMO_ACTIVE_STRATEGY`** (`active.toml`). Historical
   parameter search stops — further S4/S5… mutations would be in-sample
   p-hacking on 29 trades. Next strategy evidence must be forward
   (paper/shadow, P6).
2. **One `evaluate_strategy` per research round** — hard host guard in the
   plugin; the round shape (read → mutate → evaluate once → write result →
   END) is in the capability instructions. No workflow engine.
3. **Live scanning uses the active universe only** (37-symbol frozen CSI500
   subset), never the full A-share market, with bounded candidates (≤10)
   before any LLM involvement.

## Known limitations carried forward

- Universe: current CSI500 membership applied to all historical dates
  (survivorship/membership bias). PIT reconstruction remains unbuilt and
  must gate any profitability claim.
- EastMoney endpoints unreachable from this deployment network; data plane
  is Tencent (history) / Sina (quotes) / CSIndex (constituents) via akshare
  1.18.94, with bounded retry.
- The best child's absolute edge is far inside noise; it is a demo
  instrument for the product chain, not a trading recommendation.
