# ZUAEF Quant Autonomous Research Service v0.2
## Harness-Native 修正版 Spec Pack

### 目标

把 ZUAEF Quant 从：

> “固定 Quant tools + 长会话历史 + cache 有什么就分析什么”

升级成：

> “Harness 负责上下文、能力发现、长程执行与临时研究；Quant 只负责市场事实、策略事实和业务状态；LLM 只负责解释、判断与综合。”

这个专项解决的直接事故是：

```text
用户：为 600550 做个全面分析和趋势预测
→ 实时 quote 有
→ 历史 cache 缺失
→ Agent 拒绝研究
```

但修复不能只加一个 `fetch_history()` 调用。必须同时保证：

1. 新股票可按需自动补历史；
2. 普通 follow-up 不再携带整段旧工具轨迹；
3. 工具按需暴露，而不是全部进入 prompt；
4. 开放式市场研究优先使用 Harness/Web capabilities，不把 Quant plugin 做成爬虫平台；
5. 临时计算继续交给 Harness CodeMode；
6. durable state、research memory、market evidence 与 conversation memory 明确分层；
7. 不引入新的 Agent framework。

---

# 一句话架构

```text
Harness Core
负责：
context / conversation search / tool search / compaction / CodeMode /
step persistence / tool output limits / web research / skills

Quant Domain
负责：
market data / history hydration / market rules / candidate / watchlist /
positions / strategy evidence / research artifacts

LLM
负责：
intent / research planning / evidence interpretation /
recommendation / scenario synthesis
```

---

# 设计原则

## 1. Context 是工作集，不是数据库

普通业务 follow-up：

```text
bounded recent semantic turns
+
ConversationSearch 按需找旧信息
```

不是：

```text
完整 fork_run execution history
```

Pause/resume 仍使用完整 execution continuation。

## 2. Tool surface 按需暴露

核心 Quant evidence tools 可以常驻或低成本可发现；
低频 research/delivery/generalist tools 通过 Harness ToolSearch/deferred tools 按需加载。

## 3. Quant 不实现 Web Research Framework

结构化金融源属于 Quant；
开放式网页研究属于 Harness WebSearch/WebFetch。

## 4. CodeMode 是一次性研究环境

复杂统计、事件研究、历史相似状态、forward distribution 用 CodeMode。
不得因为一次客户问题写永久 Python 脚本。

## 5. Durable market truth 不放 Generic Memory

Market truth 使用 canonical artifacts / Case / research packets。
Generic Memory 暂不用于当前行情、公告、策略状态。

## 6. 不为了“更智能”引入 Multi-Agent

默认继续 single outcome-owning FDE Agent。
SubAgents / DynamicWorkflow 暂不进入 Quant production。

---

# 阅读顺序

1. `01_ARCHITECTURE_DECISIONS.md`
2. `02_SOURCE_OF_TRUTH.md`
3. `03_GAP_DIAGNOSIS.md`
4. `04_HARNESS_RESOURCE_POLICY.md`
5. `05_DATA_HYDRATION.md`
6. `06_TOOL_DISCLOSURE.md`
7. `07_RESEARCH_CAPABILITY.md`
8. `08_MARKET_INTELLIGENCE.md`
9. `09_CODEMODE_AND_FORECASTING.md`
10. `10_RESEARCH_MEMORY.md`
11. `11_RUNTIME_AND_CHAT_UX.md`
12. `12_TASKS_AND_CHANGE_MAP.md`
13. `13_ACCEPTANCE.md`
14. `14_OPI5_RUNBOOK.md`
15. `15_CODEX_MASTER_PROMPT.md`
