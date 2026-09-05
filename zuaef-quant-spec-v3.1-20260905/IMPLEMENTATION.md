---
title: ZUAEF Quant v3.1 全包执行
type: feature
created: 2026-09-05
status: in-progress
baseline_commit: 6714ca722b2dd2c1f7c92e457af5e817ff9762e4
context:
  - /home/barry/zuaef-agent/AGENTS.md
---

<frozen-after-approval reason="用户已明确授权全部 v3.1 实现和验证，无阶段确认">

## Intent

完整执行本目录 `18_CODEX_MASTER_PROMPT.md`、`15_TASKS.md` 和全部 normative 00–21 文档/ schemas。主目标是保留正在使用的 Quant 系统，添加严格 PIT replay 和隔离研究闭环。外部历史数据不可得时逐日阻塞，继续所有实现与验证。T000 基线和 T004 gap audit 已由主 agent 完成；主 agent 负责最终报告、运行验证和任务清单，实施 agent 负责下述实现、测试及 CLI 执行。

## Boundaries & Constraints

Always：六工具、monitor lifecycle、ack/skip、D+1/3/5/8 和五日 MFE/MAE，loopback writes、Bridge 权威与幂等。当前生产 ledger 不可改动。无新增 Core/capability/framework/database/hash。新功能是可拆卸主机适配器。隔离 namespace research/replay/shadow/live_forward，不能伪称证据。所有代码修改使用 apply_patch。你不是唯一工作者，不回退别人的改动。

Never：自动实盘 broker、放松生产阈值、向 Telegram 发送测试消息、生产策略修改、用 research 伪装 replay、重复 evaluator、当前成分回投历史、未知发布时间按报告期冒充。仅文件研究权限，不需要新模型工具。

## I/O & Edge-Case Matrix

|场景|输入|行为|
|---|---|---|
|严格历史运行|时间戳明确的完整可用记录|调用生产 timing/lifecycle，隔离结果可重复|
|未来数据/日内 EOD/修订/成分|available_at>T 或发布时间未知|fail closed，明确原因，不观察被拒数据|
|缺历史 quote/universe|真实本地 cache|10 日期逐日 blocked，不声称 NO_TRIGGER|
|shadow regime|独立证据|新字段/确定 reason，不影响生产|
|实验 promotion|仅 research/replay 改进|拒绝 promotion，要求新 live-forward 与完整性证明|
|HUMAN_SKIP|人类 skip + forward|研究分组，不生成 fill，不变 lifecycle|

</frozen-after-approval>

## Code Map

- `tools/quant_trading_monitor.py`: Store、run_cycle(store, active_cfg, spec, state_dir, now, semantic_status)；run_cycle 内 hardwire resolve_universe/fetch_batch_quotes/read_cache，可选内部 adapter 窄 seam；forward_math 为共用结算；position exit 也必须裁剪历史。禁止默认路径语义变化。
- `tools/quant_live_scan.py`: timing_from_quote_hist 已剔除 T/future bars；现有 gate 必须保留。
- `tools/quant_core.py`: read_cache、load_config、StrategySpec；`tools/quant_eval_qlib.py` 和 `tools/quant_p05_reconcile.py` 为既有 evaluator/reconcile。
- `plugins/zuaef-quant/zuaef_quant/toolset.py`: 六工具保持不变。
- `tests/test_quant_trading_monitor.py`, test_quant_business.py, test_quant_plugin.py, test_quant_replay.py, test_quant_telegram_bridge.py：基线回归集合，主 agent 已启动。
- cache `data/quant-cache/daily/601128_qfq.meta.json` 09-04 晚抓取；latest universe 08-28/09-02，candidate handoff 09-03 晚，财务 availability 0/154；不存在十日 intraday quote archives。不能用当下抓取重建过去 quote。交易日期从真实 cache/calendar 获取 Aug24–Sep4，不使用假定工作日历冒充。
- `workspace/artifacts/quant/trading/forward.json`=[]；positions=[]；只读研究该事实，不 fabricate 样本。

## Tasks & Acceptance

Execution（实现者 ownership）：
- [ ] `tools/quant_v31*.py`（按需最少文件）、可选 monitor 窄 seam：T005–T011 namespace、PIT gate、clock、隔离10日 runner，真实缓存逐日阻塞原因、结算调用、可重复性和 adversarial tests。
- [ ] 同样的本地 adapter：T013–T017 shadow regime（字段规范同时兼容 schema）；breadth/sector 与 announcement/corporate action availability；先 verify positions/cost，分钟数据仅 historical cadence 必需；无源则明确 NON_PIT/blocked，不发明 provider。
- [ ] 同样的本地 adapter：T018–T024 文件实验 registry（hypothesis、one variable、原 evaluator/reconciliation links）、S0/S1/S2 orchestration、不可覆盖结果、正式 promote/reject、regime/degradation metrics 和 SKIP 研究。实际执行能跑的 research/S1/shadow；可复用已有 evaluator结果但要明确原始窗口、不可重命名为 replay。
- [ ] `tests/test_quant_v31*.py`：覆盖上表及隔离（生产文件 bytes 前后相等，不新加 hash）、两次结果一致、六工具不变；有真实成功输入 fixture 证明生产路径，不只有全 blocked stub。
- [ ] 产物统一 `workspace/artifacts/quant/v31/`；给主 agent 汇报命令、证据、逐 T 状态建议，勿修改 master completion report 或 15_TASKS.md。

Acceptance：Given 可用或缺失历史数据，when CLI 跑最近十日，then 每日有 namespace、candidate重建、观察/transition/decision、trust、blocked/degraded、D+1/3/5/8 pending及MFE/MAE，未获得历史数据也完成可执行 runner 和测试。Given shadow/replay，when 执行，then 不变 production ledger/live_forward/active config。Given 无样本，when 分析，then 计数为0且报告证据不足，不生成收益。

## Verification

`.venv/bin/python -m pytest tests/test_quant_v31*.py tests/test_quant_trading_monitor.py -q`；按脚本 CLI 实际运行10日 replay/实验/shadow，报告结果路径。

## Spec Change Log

用户已显式要求单次全包不中断，覆盖 skill 的分阶段确认；保留其实现与 review 流程。
