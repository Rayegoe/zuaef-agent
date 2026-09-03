# SOTA Audit — Borrow Principles, Not Platforms

Reviewed against public sources current as of 2026-09-03.

## Microsoft Qlib
https://qlib.readthedocs.io/

Borrow: IC/RankIC/ICIR、quantile/long-short、cost-aware portfolio analysis、benchmark/excess return、mature research engine。

Do not build another generic workflow around Qlib.

## Microsoft RD-Agent(Q)
https://github.com/microsoft/RD-Agent
https://www.microsoft.com/en-us/research/publication/rd-agent-quant-a-multi-agent-framework-for-data-centric-factors-and-model-joint-optimization/

Borrow: `Research -> Development -> Feedback`、hypothesis-driven R&D、Agent 能提出机制/代码而非只调参数。

Do not copy now: factor-model co-optimization factory、MAB scheduler、multi-agent swarm、autonomous production promotion。

## Freqtrade Lookahead Analysis
https://docs.freqtrade.io/en/latest/lookahead-analysis/

Borrow: 用 baseline 与 sliced/re-run 的行为差异检测未来函数，而不只源码 grep。

## DSR / PBO
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253

Borrow: research 是 search；trial history 是证据；winner 有 selection bias。样本足够才计算。

## Pydantic AI Harness
https://pydantic.dev/docs/ai/harness/
https://pydantic.dev/docs/ai/harness/step-persistence/

直接复用 capabilities、StepPersistence、complete/interrupted、tool-effect ledger、lineage、OpenTelemetry。不要造 quant duplicate runtime。

## RL / Deep Prediction

当前不引入 RL / Transformer / AutoML。当前连 S3 和 candidate score 的基础增量价值都未证实，复杂模型只会扩大不可解释性与过拟合面。
