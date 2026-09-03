# P1/P2 — Factor Validation & Causal Research

## 先证明当前 Candidate Score 是否真的有用

Value / Quality / Tradability / Timing 是经济先验，不默认等于 alpha。

至少对 forward 5d / 8d 计算：

- IC；
- Rank IC；
- ICIR / Rank ICIR（样本够才算）；
- quantile return；
- Top-Bottom spread；
- turnover / stability。

覆盖 Value / Quality / Tradability / Composite。

如果没有 predictive relation，系统必须允许结论：

> candidate scoring adds no demonstrated short-horizon alpha

而不是再加因子护盘。

## Mandatory Scientific Controls

首轮必须做：

- A0 broad eligible universe + S3 timing；
- A1 deterministic seeded random pool；
- A2 liquidity-only pool；
- A3 candidate score only + fixed horizon；
- A4 remove volume confirmation；
- A5 remove close-strength；
- A6 remove MA5 exit；
- A7 original S3 + exit attribution。

A0–A7 是首轮科学控制，不是永久 workflow。之后研究问题由 Agent 从 evidence 自主选择。

## Exit Attribution

每笔 settled trade：first exit reason、all simultaneous conditions、MFE、MAE、holding sessions、net P&L。

回答：S3 实际由 MA5 / stop / TP / Day8 谁控制？

## Information-driven decline

当前 mean-reversion 最大机制风险：把情绪/流动性错杀与坏消息导致的合理重估混为一谈。

不要先硬编码 LLM 新闻利空分类。先放入 `OPEN_QUESTIONS`：

> 排除重大负面事件窗口是否提高净 expectancy / 降低 MAE？

只有当前基础 validity 通过后再研究。

## 新 Strategy Family

S3 如果被拒绝，Agent 可以提出新的经济机制；不限制永远改 S3。

准入必须有 mechanism / falsification / baseline / cost / bounded experiment。

禁止“试试 RSI/MACD/LSTM 看收益”。
