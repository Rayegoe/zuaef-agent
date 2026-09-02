# ZUAEF-ASHARE-001 — program status (frozen 2026-09-02)

**P5.5 ENGINEERING FREEZE(2026-09-02):U0–P5 全部 PASS,代码冻结,转入观察模式。**
每日真实运行 + 一行日志(`OBSERVATION_LOG.md`);重启开发的准入规则与禁改清单见
`docs/quant/README.md` §5–§6。

**2026-09-02 checkpoint — P5 Observation UX: PASS。** 新增有界观察工具化(一键 daily runner
`tools/quant_daily.sh` + loopback 实时看板 `tools/quant_serve.py` + 看板每 60s 轮询确定性
scan), 属 P5 观察模式的工具化, 不是 P6。明确不做 watcher/systemd timer —— 无"手动运行已烦到
影响使用"的真实失败。**实时观察 ≠ 实时烧模型**: 看板只拉确定性 scan, LLM 仅在手动运行
`quant_daily.sh` 时启动。当前活跃宇宙 = 用户自选 4 只 (601233/002460/002415/000009;
本地 meta, gitignored; 原 37 只 CSI500 子集备份 `csi500_subset.meta.json.orig37`)。

| Proof | State | Evidence |
| --- | --- | --- |
| Research Engine Proof | **PASS** | P0 real data + P1 Qlib/replay evaluation + P2 consistency (gen1: `workspace/artifacts/quant/gen1/`) |
| Self-learning Loop Proof | **PASS** | P4: S1 → S2 (rejected) → S3 real agent runs, one material mutation each, evidence-driven direction changes (`workspace/workspace/artifacts/quant/children/S*-result.md`) |
| Profitability Proof | **NOT YET** | best child ≈ +0.37% annualized on 29 trades with survivorship-limited universe — intentionally not chased further in-sample |
| Live Decision Product | **FIRST PROOF PASS (2026-09-02)** | P5 interactive chain verified with a real agent run: active-universe scan (37/37 quotes in ~2.9s via qt.gtimg.cn batch) → deterministic triggers → NO_TRADE verdict without forcing a candidate → persisted Decision Brief with measured 86s signal→brief latency (`workspace/artifacts/quant/briefs/brief-live-*.json`). Interactive-only; a polling watcher remains unbuilt by design until interactive use proves insufficient (spec V008). |

## 2026-09-02 增补 — 业务看板与候选发现(不变更四行证明状态)

新增确定性候选发现管线与业务决策页(见 `docs/quant/README.md` §5.7):
`legacy_watchlist.toml`(用户自选 4 只,只诊断)/ `candidate_pool`(CSI300∪CSI500 筛选,
目标 20–50,证据排名)/ `active_symbols.json` handoff(实时扫描默认宇宙)。上表四行证明状态不变;
**盈利能力仍未证明**,候选排名不是买入建议。上文 checkpoint 中"当前活跃宇宙 = 用户自选 4 只"
自本增补起失效:自选 4 只降级为 legacy 诊断位,活跃宇宙改为候选池 handoff
(缺失时回退 37 只子集,空宇宙响亮失败)。

**批准记录(2026-09-03)**: 本增补经 operator 审核后批准入库 — 候选发现管线、业务决策页
与指标备注交互均属 §6 禁改清单的有界解冻(对应"手动运行烦 → watch scheduler"触发),
解冻范围仅限确定性候选构建 + 只读看板; 不含 watcher/scheduler/broker, 四行证明状态不变,
盈利仍未证明。候选池时代的首个完整每日决策已产生 (2026-09-03 00:09, 50 只, 0 触发, NO_TRADE,
延迟 10s, 见 OBSERVATION_LOG)。

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
