# Minimal Code Change Map

优先扩展现有文件，不为概念创建服务。

## Existing

- `tools/quant_live_scan.py`：消费 semantic status、immutable scan ref；不重写策略。
- `tools/quant_build_candidates.py`：immutable candidate snapshot、factor-analysis export、PIT provenance。
- `tools/quant_eval_qlib.py`：lineage、net metrics、factor/ablation hooks、OOS lock。
- `tools/quant_core.py`：保持 execution truth，只为真实 market-rule bug 修改。
- `tools/quant_render_business_dashboard.py`：outcome badges、Lessons/Open Questions 摘要、report id；不重算策略。
- `tools/quant_daily.sh`：report id、取消 same-day dedup、archive exact inputs，保持一键 UX。
- `plugins/zuaef-quant/zuaef_quant/plugin.py`：明确 Decision/Research 两态；不要同 prompt 混合 live 决策与开放研究。

## Suggested New Deterministic Helpers

只在现有函数无法自然容纳时创建：

- `quant_validate_semantics.py`
- `quant_anti_leakage_check.py`
- `quant_factor_analysis.py`（也可并入 evaluator）
- `quant_archive_report.py`
- `quant_review.py`

这不是要求必须新建 5 个文件，**能复用就少建**。

## No New Service

不需要 Redis/Postgres/Celery/Kafka/vector DB/new microservice/workflow engine。
