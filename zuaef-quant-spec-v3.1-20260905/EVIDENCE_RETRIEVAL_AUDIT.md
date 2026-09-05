# 定向证据检索审计

审计时间 2026-09-05；先审计已有证据，再决定新增读取面。

## T016 持仓 / 成本

`tools/quant_trading_monitor.py` 的 Store.open_position 已记录 id、symbol、entry_price、shares、entry_time/date、strategy、venue、state；close_position 加入 exit_price/shares/time 和 pnl。Workbench NOW/get_trading_context 已读取 canonical 持仓。故无需增加第二持仓/成本来源。

当前 `workspace/artifacts/quant/trading/positions.json` 的 open/closed 都为空；只有既有契约，没有当前实际成本样本。entry_price 是用户确认价，不含佣金/税的完整券商成本，不把它宣称为含费成本或券商对账结果。新接券商源不在范围。

## T014 广度

现有候选快照 base_count=800、candidate_count=50，来源含 CSI300/CSI500、809条报价计数及行业覆盖。候选筛选后的50股上涨比例不能冒充全市场上涨比例；行业缺失、样本覆盖、源时间都必须显示。当前 quote snapshot 不能回填任意历史 intraday 时点。

## T015 公告 / 公司行为

本地 `data/quant-cache/` 分类为 candidates、daily、fundamentals、industry、qlib_data、qlib_stage、universe、valuation3y，没有 announcement/corporate-action archive。

`workspace/artifacts/quant/semantic/pit_audit_20260903T045824Z.json` 报告公告日期覆盖 **0/154**。财务报告期不是发布时间；未知发布时间仅 NON_PIT，严格重放排除。现有 raw/qfq corporate-action crossing 检查可复用为风险检查，但价格比例推断不等于有发布时间的公司公告。

## T017 分钟数据必要性

本次唯一明确需求是恢复30–60秒生产 cadence 的历史输入；EOD 与当前 scan 不能代替。`data/quant-cache/` 未发现 minute/历史逐笔 quote archive；last_scan 只有一次盘后派生结果，不能恢复全天 quote volume 和事件序列。

因此可以实现带事件时间/available_at 的内部输入适配，但本次不引入泛用分钟行情服务、Level-2或第七工具。缺少真实档案时逐日阻塞。原研究 evaluator 的日线能力继续标 research。

## 统计边界

生产 forward.observations=[]、无HUMAN_SKIP原始样本；任何执行 vs 跳过的期待收益、尾部亏损、MFE/MAE、原因效用或Agent解释因果效果均不能从空数据估计。分析函数与fixture验证可完成，实际收益结论必须保留未知。
