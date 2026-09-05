# Agent Surface Gap Audit

结论：保留六工具，无新增 model-visible Quant 工具，使用本地主机 CLI/内部适配器。

|业务结果|现有入口|v3.1 处理|
|---|---|---|
|策略假设评估|evaluate_strategy|复用 research evaluator 和 reconciliation；严格 replay 独立主机适配|
|当前触发| get_live_signals |保留直接扫描；不让 Agent 轮询|
|解释/研究结果|record_decision_brief|保留解释权；实验记录由主机文件编排|
|人的成交/跳过事实|record_trade_outcome / canonical CLI|保持 ack-buy/ack-sell/skip；不创建 broker 工具|
|市场/持仓证据| get_trading_context |既有 position/cost basis；新证据经有 namespace 的产物提供|
|业务交付|render_quant_business_artifact|现有业务渲染不替换；重放报告为隔离文件|

六工具不能直接执行严格历史时钟，这是主机数据访问与状态隔离问题，无模型可见性必要。新增实现写入独立 v31 artifact 目录，不写 production ledger；实验不更改 active.toml；Bridge 仍是唯一主动发送者。幂等性由现有 runtime 保留，实验结果采用不可覆盖记录。无第七工具提案。
