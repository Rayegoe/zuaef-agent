---
type: concept
title: '量化数据面：akshare、缓存布局、universe 清单与已知限制'
tags:
- quant
- data
- akshare
- universe
sources:
- id: sources/zuaef-quant
  resource: docs/quant/README.md
  title: ZUAEF A股决策 Agent 实现总结与实操指南
  evidence: "§2 P0; §3.1 数据面; §3.4 环境变量; §4 已知限制; §7.2 故障排查"
- id: sources/zuaef-quant
  resource: zuaef-ashare-decision-agent-spec-v1.0-final/04_DATA_AND_MARKET.md
  title: Data and A-Share Market Truth
  evidence: "§1 data principle; §2 P0 smoke; §3 local cache; §10 data honesty"
- id: sources/zuaef-quant
  resource: data/quant-cache/universe/csi500_subset.meta.json
  title: Live universe manifest (37 symbols)
  evidence: "symbols array; selection; pit_limitation; excluded lists"
generated:
  by: zuaef-agent
  date: 2026-09-02
---

# 量化数据面

## 数据原则（spec 04 §1-2）

akshare 是**外部公共数据接口，不是交易所级行情 SLA**——要测量新鲜度和失败率，
不要假设"实时"。P0 证明实测：600519 日线 2018 起 2101 行（qfq+raw 双份，复权真实生效）、
CSI500 成分 500 只（CSIndex，生效日 2026-08-28）、全市场快照 5550 只、日历新鲜度 0 天。

## 数据面路径（本部署实际生效，README §2 P0/§7.2）

| 用途 | 路径 | 备注 |
|---|---|---|
| 历史日线 | `akshare.stock_zh_a_hist_tx`（腾讯，qfq+raw） | 2018-01-01 起；有界重试 0s/2s/8s |
| 指数成分 | `akshare.index_stock_cons_csindex`（CSI500 = 000905） | 带生效日 |
| 实时行情 | `qt.gtimg.cn` 批量报价（同腾讯数据面） | 37 只一次请求 ~2.9s（16× 提速） |
| 市场快照 | 新浪路径（备用） | — |

**EastMoney 端点在本部署网络被传输层拒绝（SSL EOF）**——这是真实失败①，已按数据面替换
为腾讯/新浪/CSIndex，来源写进每份缓存 sidecar。雪球报价需 token，不可用。

## 缓存布局（gitignored，可随时重建）

```text
data/quant-cache/
  daily/    <symbol>_qfq.csv + .meta.json、<symbol>_raw.csv + .meta.json
  universe/ csi500_cons.csv（成分股）+ csi500_subset.meta.json（子集清单）
  qlib_data/（Qlib bin 库，由评估流水线重建）
```

- 缓存 key：`<symbol>_<qfq|raw>`；sidecar meta.json 记录 source / symbol / adjust /
  retrieved_at / rows / date_range（spec 04 §3 的最小元数据）。
- 重建后必须重跑 P0 证明 + 一次基线评估核对一致性（README §5.6）。

## Universe 清单（想定制股票代码就看这里）

**唯一权威来源：`data/quant-cache/universe/csi500_subset.meta.json` → `symbols` 数组**
（当前 37 只，来自 CSI500 今日成分排序后 stride=10 采样，`selection` 字段记录）。

- `tools/quant_live_scan.py`（88–91 行）和 `tools/quant_eval_qlib.py`（232–235 行）直接读它；
  评估时 qlib 工具列表 `csi500_subset.txt` 由 eval 脚本自动重写（82 行）。
- 生成器 `tools/quant_fetch_universe.py`：`uv run --group quant python tools/quant_fetch_universe.py [--size N] [--stride S]`
  从 CSI500 成分采样；排除 ST 名称与 `--min-first-bar`（默认 2018-06-30）之前无足够回溯的股票。
- **换自选股**：直接编辑 `symbols` 数组 + 为新代码跑 `fetch_history(code,'qfq')/('')`
  （扫描需要 ≥25 天日线算回撤/量比，否则跳过）。

## 环境变量契约（README §3.4）

- `ZUAEF_QUANT_PYTHON`：侧环境解释器（默认 `.venv-quant/bin/python`）
- `ZUAEF_QUANT_REPO_ROOT`：仓库根（Agent 须从仓库根运行）
- 缺失即响亮组合错误（"quant plugin side environment missing" / "cannot locate repository quant tooling"），
  绝不静默降级。

## 已知限制（诚实记录，README §4）

- **PIT 未建**：今日 CSI500 成分回看所有历史日期（幸存者/成分偏差），已写进每份 Strategy Result；
  必须成为任何盈利声明的前置门。
- 汇率之外：SCAN 依赖解析 `qt.gtimg.cn` GBK 字段（手→股换算）。
- 数据面失败重跑即可（腾讯限流时）；长期失败率上升才构成换付费数据源的研究信号。