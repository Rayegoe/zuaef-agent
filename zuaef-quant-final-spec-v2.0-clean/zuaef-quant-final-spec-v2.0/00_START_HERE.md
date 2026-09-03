# ZUAEF Quant Final Spec v2.0

**Status:** FINAL / EXECUTABLE / FREEZE AFTER IMPLEMENTATION  
**Repo:** `Rayegoe/zuaef-agent`  
**Verified baseline:** `main (verified 2026-09-03 before implementation)`  
**Date:** 2026-09-03

## North Star

> 为小资金 A 股散户提供**更少的无依据交易、更高质量的可解释决策、更可靠的策略证据，并持续从真实结果中学习**。

这个版本替代 v1.1/v1.2。它不是平台重构，而是把现有真实数据、Qlib、独立重放、候选发现、实时扫描、业务看板和 `zuaef-quant` Agent 闭合成一个 Outcome-First Quant Research & Decision Harness。

## 成功不是这些

- 新增多少 schema / class / service；
- Agent 调了多少工具；
- 看板多了多少 KPI；
- 回测收益变漂亮；
- 测试数量变多。

## 成功是这四件事

1. 今天的 `NO_TRADE / WATCH / ENTER_CANDIDATE` 有可信证据。
2. 历史收益不是未来函数、PIT 污染、成本遗漏或反复试参制造的。
3. Agent 真正提出、检验、否定或修正研究假设，而不是硬编码参数按钮。
4. 任意旧报告都能还原当时数据、策略、Agent run、代码版本和后来结果。

## 已有能力保留

- AKShare + Tencent 数据面；
- Qlib 研究侧环境；
- `quant_core.py` 独立 A 股执行真相；
- CSI300∪CSI500 candidate discovery；
- sector-aware financial model；
- fail-closed live scan；
- Business / Engineering dashboard；
- `zuaef-quant` plugin；
- `UNPROVEN` / forward observation。

**不要重写。**
