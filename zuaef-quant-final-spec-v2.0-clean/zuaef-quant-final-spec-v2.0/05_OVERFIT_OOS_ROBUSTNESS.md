# P3 — Search Bias, OOS & Robustness

## Research Is Search

Agent 越勤奋，越容易从噪声里找到 winner。最终 winner 不能假装是事先指定策略。

每个 strategy family 必须保留所有 sibling trials，包括失败。

`RESEARCH_LOG` 是 search history 主账本。

## DSR / PBO

参考 Deflated Sharpe Ratio 与 Probability of Backtest Overfitting。

要求：

- 记录 trial count/search lineage；
- 提供 search-adjusted warning；
- 样本足够才算 DSR/PBO；
- 样本不足 => `INSUFFICIENT_SAMPLE`。

不要用高级统计制造假精确。

## Frozen Splits

Research / Validation / Untouched OOS / Forward 分离。

OOS 一旦打开，改变参数/机制 => 新 lineage；旧 OOS 不能重新叫 untouched。

## Walk-Forward

用于检查冻结机制跨年份稳定性，不用于滚动优化参数。

## Regime Breakdown

至少审视：bull/bear/sideways、high/low volatility、high/low liquidity。

目标是找失效条件，不是看完 regime 后反向调同一 OOS。

## Costs

Headline return 默认 NET。至少 commission / minimum commission（如建模）/ sell-side tax / slippage。

同时可显示 gross，但不得作为主结论。
