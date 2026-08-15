# Outcome-First PydanticAI Agent Engineering Guide v2.0

> **成果导向的 PydanticAI Agent 工程技术指南**
>
> 适用范围：产品研究、企业情报、WordPress/WooCommerce 上品、供应链研究、内容生产、企业内部业务 Agent、Coding Agent、FDE 项目。
>
> 核心命题：
>
> **薄 Agent 内核 + 丰富执行环境 + 渐进式能力 + 强成果契约 + 独立评估。**
>
> Agent 工程的目标，不是构造一个越来越完整的“智能体系统”，而是让越来越多真实业务 Case 能以更低成本、更高质量、更少人工完成。

---

# 1. 我们真正要纠正的，不只是“过度工程化”

过去一段时间，我们在 PydanticAI 项目中反复碰到过同一种演化：

```text
真实业务问题
↓
定义几个 Schema
↓
发现异常
↓
增加状态
↓
增加 Contract
↓
增加 Validator
↓
增加 Capability
↓
增加 Router
↓
增加 Agent
↓
增加 Evaluator
↓
增加恢复机制
↓
最终：

系统越来越完整
业务结果却没有同比提高
```

这类项目最大的问题不是代码多。

而是 **模型的注意力开始大量用于操作 Agent 框架，而不是操作业务世界。**

例如模型开始处理：

```text
load_capability
record_claim
transition_state
serialize_evidence
update_run_context
repair_output_schema
route_to_reviewer
resume_workflow
```

而不是：

```text
这是什么产品？
这个价格可信吗？
哪个规格发生冲突？
是否值得拿样？
还缺什么内部数据？
下一步应该问工厂什么？
是否应该发布？
```

我们的内部技术基线已经明确提出：模型主要注意力应当放在理解目标、调查材料、执行动作、形成判断和制作成果上；Capability 状态、多层 DTO、复杂状态迁移、遥测、框架路由等应由 Harness 或宿主程序承担。

因此，v2.0 不只是：

> 少做一点架构。

而是：

> **重新分配整个系统的智能预算。**

---

# 2. 新的总架构：薄内核、厚环境、强验收

推荐把一个业务 Agent 看成六层：

```text
┌────────────────────────────────────────────┐
│ 1. Outcome / Business Contract             │
│ 用户、决策、成果、完成条件、停止条件            │
└───────────────────┬────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ 2. Outcome-Owning Agent                    │
│ 理解 → 判断 → 调查 → 行动 → 写成果             │
└───────────────────┬────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ 3. Progressive Execution Environment       │
│ Files / Web / APIs / Skills / Capabilities │
│ Todo / Search / Domain Services            │
└───────────────────┬────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ 4. Deterministic Host Control              │
│ 权限 / 预算 / 计算 / 幂等 / Approval / Limits  │
└───────────────────┬────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ 5. Artifact + Evidence                     │
│ report / decision / evidence / draft       │
└───────────────────┬────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│ 6. Validator + Independent Evaluator       │
│ 硬规则 + 语义质量 + 业务结果                   │
└────────────────────────────────────────────┘
```

这与 PydanticAI 当前自身的产品演化已经高度一致：Core 提供 Agent loop、模型、Capability/Hook 等基础机制；Pydantic AI Harness 则将文件系统、代码执行、规划、上下文管理、Memory、Guardrails、多 Agent 等作为**按需选择的能力积木**，而不是要求每个 Agent 全部具备。

这意味着我们的默认工程思想应该变成：

> **不要建设“Agent 系统”，而要建设“Agent 可以工作的环境”。**

---

# 3. 第一原则：先设计 Outcome，而不是 Agent

任何新项目，第一个文件不应该是：

```text
agents.py
schemas.py
state.py
router.py
```

而应该是：

```text
CONTRACT.md
```

一个最小 Outcome Contract 至少回答六件事。

## 3.1 谁使用？

例如：

```text
用户：跨境业务负责人
```

而不是：

```text
downstream consumer = report_renderer
```

## 3.2 他要做什么决定？

例如：

```text
TEST / WATCH / DROP
```

或者：

```text
是否联系工厂
是否申请样品
是否发布产品
是否进入报价
```

## 3.3 最终成果到底是什么？

例如：

```text
decision.md
evidence.md
unknowns.md
supplier_questions.md
product-page-draft.html
product-images/
```

而不是：

```python
AgentResultDTO(...)
```

我们的内部基线已经把这一点明确为：Agent 的产品应当是人可以直接消费的报告、页面、草稿、图片包、决策卡等，而不是抽象 Result DTO。

## 3.4 什么叫完成？

不是：

```text
state == COMPLETED
```

而是：

```text
用户能看懂
AND
可以采取行动
AND
核心判断有证据
AND
未知项被明确标记
AND
下一步具体
```

## 3.5 什么情况下必须停止？

例如：

```text
成果已经足以支持决定
外部数据是唯一剩余缺口
继续搜索不会改变判断
预算达到收尾线
连续两轮没有取得有效进展
```

停止条件非常重要。

成熟 Agent 的能力不仅是：

> 知道怎么继续。

还包括：

> **知道什么时候已经不值得继续。**

---

# 4. 第二原则：一个 Agent 对一个 Outcome 负责

过去最容易犯的错误之一，是直接把企业岗位映射成：

```text
Planner Agent
Research Agent
Evidence Agent
Analyst Agent
Writer Agent
Reviewer Agent
```

这种架构表面上符合组织逻辑，实际上经常产生：

```text
上下文 → 摘要
摘要 → 摘要
摘要 → 判断
判断 → 再解释
```

最终形成 information telephone game。

Qualio 的生产实践也经历了类似过程：最初采用 supervisor + 多个专业 Agent，随后发现 handoff 带来延迟、上下文损耗和大量 glue code，最终收缩回单 Agent。

我们的内部实践也得出了相同原则：

```text
SearchAgent      ×
ClaimAgent       ×
WriterAgent      ×
ReviewerAgent    ×

ProductOpportunityDecisionAgent   ✓
ProductListingDeliveryAgent       ✓
FactoryReadinessAgent             ✓
QuotePreparationAgent             ✓
```



关键区别是：

**前一种按技术步骤拆 Agent。**

**后一种按业务责任定义 Agent。**

---

# 5. Multi-Agent 不是禁止，而是需要“举证责任”

当前 PydanticAI 官方文档本身也把复杂度描述为大致五级：

```text
Single Agent
↓
Agent Delegation
↓
Programmatic Handoff
↓
Graph
↓
Deep Agent
```

而不是默认从多 Agent 开始。

所以我们的原则不是：

> 永远不能 Multi-Agent。

而是：

> **Multi-Agent 必须证明自己优于 Single-Agent baseline。**

一个 Subagent 至少满足：

### 任务隔离

它不需要主 Agent 的完整上下文。

### 输入边界清楚

能够明确表达：

```text
input → task → output
```

### 独立验收

它的结果可以独立判断好坏。

### 原始证据可访问

主 Agent 不能只收到一段无法核验的摘要。

### 权限可以缩小

例如供应链搜索 Agent 只读 Web，而不会拥有 ERP 写权限。

### 收益可测量

例如：

```text
总耗时降低 45%
主上下文减少 60%
成本增加仅 12%
结果质量不下降
```

否则：

**普通函数 > Tool > Single Agent > Subagent。**

我们的既有准入标准也是如此。

---

# 6. 第三原则：Tool 不应该等于 API

这是整个 Agent 架构最值得继续深入的一点。

错误思维：

```text
我们有 100 个 API
→ 建 100 个 Tools
→ Agent 就拥有 100 种能力
```

实际上往往变成：

```text
Tool Schema ↑
Prompt tokens ↑
Tool selection entropy ↑
错误调用 ↑
维护成本 ↑
```

Qualio 的演讲里，他们一个业务流程一度需要 20 多个 Python Tool，后来转向少量抽象操作 + API discovery。

所以应该区分：

## 6.1 Domain API

系统内部可以有很多：

```text
/products
/suppliers
/evidence
/control
/gaps
/documents
/orders
```

## 6.2 Model Tool Surface

模型实际看到的应该少很多。

例如研究 Agent 第一版完全可能只有：

```text
search_web()
fetch_url()
search_internal()
write_artifact()
```

再加：

```text
inspect_product()
calculate_unit_economics()
```

而不是把后台所有函数暴露出去。

---

# 7. 一个 Tool 必须满足“模型决策必要性”

判断一个函数是否应该成为 Tool，可以问：

> **模型是否真的需要决定什么时候调用它，以及用什么参数调用它？**

如果答案是否定的，就不要暴露给模型。

例如：

```python
normalize_price()
slugify_filename()
calculate_margin()
validate_url()
check_file_exists()
serialize_claim()
transition_status()
```

多数情况下应该由普通 Python 调用。

而这些更像真正 Tool：

```text
search_supplier_database()
fetch_product_page()
create_wordpress_draft()
request_supplier_documents()
read_erp_product()
```

我们的内部白皮书对此已经给出非常明确的边界：格式转换、排序、路径生成、校验计算等确定性逻辑应留在宿主 Python；只有模型真正需要判断调用时机和参数的动作才应该进入工具面。

于是形成一个非常重要的工程原则：

> **Tool 是 Agent 与世界的动作边界，不是 Python 函数注册表。**

---

# 8. 第四原则：Progressive Disclosure，而不是 Full Exposure

Agent 变强，并不意味着每轮 Prompt 变大。

真正正确的方向恰恰相反：

```text
能力越来越多
但当前上下文越来越聚焦
```

这就是 Progressive Disclosure。

当前 PydanticAI 已正式支持 on-demand Capability：设置 `defer_loading=True` 后，完整 Capability 内容和工具定义不会预先进入 Prompt，只保留一个简短 catalog entry；直到模型决定加载，该能力才展开。

因此：

```text
Agent 知道：
“我有供应链调查能力”

但还不知道：
供应链能力里的全部规则
所有工具 schema
完整 SOP
所有模板
```

只有需要的时候：

```text
load supplier-investigation
```

然后才加载。

---

# 9. Capability 应该成为“能力胶囊”，而不是新领域模型

PydanticAI 当前把 Capability 定义为可复用、可组合的 Agent 行为单元，可以同时提供：

- tools；
- hooks；
- instructions；
- model settings；
- model selection。



因此我们应该进一步强化 Capability 的用途。

好的 Capability：

```text
WebResearch
Approval
CostTracking
ContextCompaction
SupplierInvestigation
WordPressPublishing
ProductEvidenceReview
```

它们有共同特征：

> **加载以后，Agent 获得一种新的行为能力。**

而不是：

```text
ProductCapability
ClaimCapability
EvidenceCapability
DecisionCapability
StateCapability
UserCapability
```

这些通常只是把领域名词重新包装了一遍。

DDD 的 Bounded Context、数据库实体、Capability、Agent、Skill 是完全不同的抽象。

不要因为都能“模块化”，就强行一一映射。

---

# 10. Skill 应该成为“可执行专家经验”

比 Capability 更值得投入的是 Skill。

Skill 不应该只是：

```markdown
调用 search()
然后调用 fetch()
然后输出 JSON
```

真正有价值的是：

```markdown
# 判断一个电助力车配置是否可信

## 适用条件

当官网、经销商、媒体、平台规格不一致时使用。

## 首先判断

1. 型号和地区版本是否一致
2. 是否混淆 nominal / peak power
3. 电池型号是否对应宣传容量
4. 整车重量是否包含电池
5. certification 是否只是 marketing claim

## 证据优先级

manufacturer technical document
> certification database
> official product page
> dealer
> marketplace
> review

## 常见错误

不要把 Amazon bought-in-past-month 当销量。
不要把 reseller 参数直接升级为 manufacturer fact。

## 输出

FACT
CONFLICT
UNKNOWN
ACTION TO ACQUIRE
```

这才是真正能够积累竞争力的东西。

因为：

```text
Tool = 能做什么
Skill = 应该怎么做好
```

PydanticAI 当前甚至给出了直接从 Markdown 构建 deferred Capability/Skill 的模式：文件在未加载时只向模型暴露 `id + description`，真正正文等需要时再进入上下文。

因此长期来看，我们的知识资产重点不应该是：

> Tool Registry 有多大。

而应该是：

> **有多少经过真实 Case 验证的工作方法。**

---

# 11. 第五原则：计划不是 Workflow Graph，而是“当前承诺”

研究型、分析型、Coding 型 Agent 的真实过程通常是：

```text
观察
↓
形成暂时计划
↓
获得新证据
↓
修改计划
↓
继续
```

所以 Planning 更适合被理解为：

> **Agent 当前承诺完成的任务集合。**

而不是预先冻结未来。

一个简单的：

```text
[ ] 确认产品身份
[ ] 找到官方规格
[ ] 比较三个竞争产品
[ ] 验证关键冲突
[ ] 写决策建议
```

往往比：

```text
20-node DAG
+
branch state
+
resume checkpoint
+
transition table
```

更符合实际推理。

Qualio 最终采用了类似 TODO 的简单规划方式，并通过 Tool 返回下一项任务来减少 Agent 偏航。

PydanticAI Harness 当前也正式提供 `Planning` Capability：模型通过小型工具集自己维护结构化 task list，并支持 add/update/subtask/dependency，而不是要求开发者预写完整 Agent graph。

因此：

> **Plan 是工作记忆，不是业务状态机。**

---

# 12. 第六原则：Artifact 是 Agent 的真正工作记忆

很多复杂 Agent 最大的问题是：

> 一切都留在 conversation。

研究几十轮之后：

```text
事实
推断
旧结论
新结论
搜索结果
失败工具
计划
用户指令
```

全部混在 message history 中。

这必然产生 context rot。

更好的方式是：

```text
workspace/
├── CONTRACT.md
├── inputs/
├── working/
│   ├── notes.md
│   ├── evidence.md
│   └── plan.md
├── deliverables/
│   ├── decision.md
│   ├── report.md
│   └── unknowns.md
└── run-summary.json
```

Agent 不需要“记住整个世界”。

它只需要知道：

```text
我现在在哪
权威成果在哪里
还有哪些问题没解决
```

这也是为什么 Markdown/file-first 对业务 Agent 很重要。

---

# 13. Write While Working

必须进一步强化一个以前容易忽略的原则：

> **不要最后才生成报告。**

Agent 应该边调查边写：

```text
发现事实 → 写 evidence
发现冲突 → 写 conflicts
形成判断 → 更新 decision
遇到未知 → 写 unknowns
```

而不是：

```text
搜索 20 轮
↓
上下文快满
↓
“请生成最终报告”
```

内部基线已经明确要求边工作边形成成果，因为这样预算耗尽时仍有结果，局部修订也不需要重新发送全部上下文。

这会直接改变 Agent 的失败模式：

旧模式：

```text
运行失败
→ 什么也没有
```

新模式：

```text
运行失败
→ 已经有 70% 可用成果
→ 剩余 30% 明确列为缺口
```

---

# 14. 第七原则：把“认识论”做强，而不是把 Schema 做大

研究 Agent 的核心问题从来不是：

```text
有没有 claim_id
```

而是：

```text
这句话到底是什么性质？
```

建议统一使用五级认识结构：

```text
OBSERVED FACT
SOURCE STATEMENT
INFERENCE
UNKNOWN
ACTION TO ACQUIRE
```

例如：

```text
FACT
官网列出 48V 20Ah。

SOURCE STATEMENT
品牌称续航可达 80 miles。

INFERENCE
在当前重量和电池容量下，
该续航很可能依赖低助力条件。

UNKNOWN
无法确认测试条件。

ACTION TO ACQUIRE
要求供应商提供测试速度、
载重、助力档位和环境温度。
```

这比：

```json
{
  "claim": "...",
  "confidence": 0.82,
  "status": "validated"
}
```

有用得多。

因为后者看起来精确，却可能根本没有真实意义。

---

# 15. Validator 永远不能代替 Evaluator

这是我们过去最需要保持警惕的地方。

Validator 擅长：

```text
文件存在？
字段存在？
URL 合法？
价格 > 0？
图片分辨率够？
有没有未经批准的发布？
```

Evaluator 才负责：

```text
这个结论有证据吗？
有没有遗漏反例？
有没有把 Source Claim 写成 Fact？
这个建议真的支持客户决策吗？
下一步可执行吗？
```

我们的内部白皮书已经明确将两者分离。

当前 Pydantic Evals 也明确区分了确定性的代码检查与非确定性的质量评估，并以 Dataset + Case + Evaluator 为基础，可以进一步使用 LLM Judge、Custom Evaluator 和 span-based evaluation。

---

# 16. 正确的测试金字塔

建议以后所有业务 Agent 使用四层质量系统。

## L1 — Software Correctness

```text
pytest
type check
API contract
permission
idempotency
file path
tool arguments
```

回答：

> 系统有没有坏。

## L2 — Agent Behavior

例如：

```text
有没有错误使用工具？
有没有绕过 approval？
有没有不断重复搜索？
有没有真的生成成果？
```

回答：

> Agent 有没有按正确方式工作。

## L3 — Semantic Outcome

例如：

```text
核心事实准确吗？
证据支持判断吗？
有没有遗漏冲突？
未知是否诚实？
下一步是否合理？
```

回答：

> 成果好不好。

## L4 — Business Result

例如：

```text
客户采用了吗？
拿样了吗？
发布了吗？
询盘增加了吗？
返工减少了吗？
判断后来被证实了吗？
第二次任务成本下降了吗？
```

回答：

> **这套 Agent 有没有价值。**

我们的内部评估基线已经把最后一级明确提升为样品、询盘、发布、决策、节省工时等真实结果。

---

# 17. Evaluator 必须与生产 Agent 解耦

不要：

```text
Agent 写报告
↓
Agent 自己检查
↓
Agent：很好，通过
```

Reviewer Agent 如果：

- 使用同一上下文；
- 接收同一摘要；
- 没有固定 rubric；
- 没有原始材料；

它并没有形成真正意义上的独立验证。

更好的结构：

```text
RAW INPUT
       ↘
        Evaluator
       ↗
ARTIFACT
```

Evaluator 获取：

```text
原始任务
原始证据
最终成果
固定 rubric
```

而尽量不读取：

```text
Producer 的自我解释
Producer 为什么这么写
Producer 的完整 chain history
```

Evaluator 应成为一种 **fresh-context critic**。

---

# 18. 第八原则：Human-in-the-loop 应绑定“承诺”，不是绑定“思考”

Gate 过多会杀死 Agent。

不应该：

```text
搜索？批准
引用？批准
写 markdown？批准
继续研究？批准
```

真正值得审批的是：

```text
发邮件
发布产品
修改价格
下采购单
删除数据
写 ERP
支付
法律/合规承诺
```

推荐：

```text
Agent 自主研究
↓
Agent 自主形成草稿
↓
确定性检查
↓
提出副作用动作
↓
Human Approval
↓
执行
```

PydanticAI 当前 Deferred Tools 已正式支持 `requires_approval=True`、动态 `ApprovalRequired` 以及 DeferredToolRequests/Results 流程。官方同时特别强调：Human approval 并不是身份认证/授权边界，敏感 Tool 本身仍必须执行服务端 authorization。

这点尤其重要：

> **模型审批机制 ≠ 安全边界。**

真正安全边界必须存在于 Tool implementation / service layer。

---

# 19. 第九原则：预算不是防故障，而是 Agent 的认知边界

很多系统把：

```python
UsageLimits(...)
```

看成防止爆 Token 的保险丝。

更好的理解是：

> **预算定义 Agent 应该在多大的调查空间内作出当前最优判断。**

因此预算应影响行为。

例如：

### 0–60%

探索。

```text
找证据
验证关键假设
调查主要冲突
```

### 60–80%

收敛。

```text
只处理影响决定的问题
```

### 80%+

收尾。

```text
停止扩散搜索
整理证据
写最佳当前结论
列 Unknown
形成 Partial Result
```

我们的既有基线已经明确提出 80% 左右预算触发收尾，并要求预算耗尽时保留 Artifact、运行验收并生成部分交付，而不是只抛 `UsageLimitExceeded`。

成熟 Agent 的一个重要能力因此是：

> **Graceful degradation。**

---

# 20. 第十原则：失败首先改变方法，而不是改变架构

以后碰到失败，不应该第一反应：

```text
加 Agent
加 Graph
加 State
加 Schema
加 Memory
```

应该先归因。

| 失败 | 首选修复 |
|---|---|
| 搜不到资料 | Search strategy |
| 来源质量差 | Source policy |
| 工具选错 | 减少工具 / 改 description |
| 上下文太大 | Files / Compaction |
| 漏步骤 | Planning / checklist |
| 报告结构差 | Artifact template |
| 无证据结论 | Evaluator |
| JSON 经常坏 | 缩小 structured output |
| 写操作危险 | Deferred Tool |
| 等待数小时 | Persistence |
| 大量独立子任务 | 再考虑 Subagent |

这是我们内部白皮书已经明确形成的 failure-first 架构决策方法。

应该确立一个非常严格的原则：

> **只有重复的真实失败，才拥有申请新架构的资格。**

---

# 21. Architecture Change 必须有“证据申请”

例如有人提出：

> 我们应该增加 Graph。

必须回答：

```text
哪几个真实 Case 失败了？
失败是不是控制流导致的？
普通 Python 是否无法解决？
Graph 后错误率降低多少？
成本增加多少？
复杂度增加多少？
有没有 regression dataset？
```

提出：

> 我们应该增加 Memory。

必须回答：

```text
哪个任务因为遗忘失败？
需要记什么？
有效期多久？
谁能修改？
什么情况下失效？
错误记忆如何撤销？
```

提出：

> 我们应该增加 Subagent。

必须回答：

```text
哪个任务值得隔离？
它能否独立验收？
并发提高多少？
主上下文减少多少？
交接损失是多少？
```

从此：

**架构不是 design preference。**

而是：

**experimental hypothesis。**

---

# 22. 一个值得长期坚持的复杂度阶梯

## L0 — Golden Outcome

人或高级通用 Agent 做出黄金成果。

没有平台。

---

## L1 — Single Outcome Agent

```text
1 Agent
3–6 Tools
Artifact Workspace
Usage Limits
Validator
```

目标：

```text
3 个 unseen cases
```

---

## L2 — Enterprise Boundary

加入：

```text
internal data
Evidence provenance
Work Order
Approval
Deferred Tool
permissions
```

---

## L3 — Repeated Service Loop

真正出现：

```text
每天
每周
跨系统
跨等待周期
```

才增加：

```text
schedule
persistence
durable execution
```

---

## L4 — Selective Specialization

真实测量发现单 Agent 瓶颈以后：

```text
Subagent
Code Mode
Tool Search
Dynamic Workflow
Graph
```

选择性启用。

---

## L5 — Controlled Improvement

最后才考虑：

```text
自动发现失败模式
提出 Skill 修改
提出 Prompt 修改
提出 Capability 修改
```

而且：

```text
proposal
↓
offline eval
↓
regression dataset
↓
human review
↓
next version
```

绝不是运行中的 Agent 随意修改自己。

这一成熟度路径已经在我们的内部 PydanticAI 白皮书中形成：从人工黄金成果、单 Agent，到内部审批、周期服务、选择性 Subagent，最后才进入受控自我改进。

---

# 23. 推荐的工程目录

```text
agent-project/
│
├── README.md
├── pyproject.toml
│
├── docs/
│   ├── ARCHITECTURE.md
│   └── FAILURE_PATTERNS.md
│
├── skills/
│   ├── supplier-investigation.md
│   ├── product-verification.md
│   └── decision-writing.md
│
├── src/
│   └── agent_name/
│       ├── agent.py
│       ├── deps.py
│       ├── tools.py
│       ├── deterministic.py
│       ├── validation.py
│       └── runtime.py
│
├── evals/
│   ├── dataset.py
│   ├── evaluators.py
│   └── cases/
│
├── tests/
│   ├── test_tools.py
│   ├── test_validation.py
│   └── test_permissions.py
│
└── workspace/
    ├── CONTRACT.md
    ├── inputs/
    ├── working/
    └── deliverables/
```

注意这里故意没有：

```text
agents/
router/
orchestrator/
state_machine/
ontology_engine/
capability_registry/
workflow_engine/
```

不是说永远不存在。

而是：

> **没有真实 Case 证明之前，不值得拥有。**

---

# 24. 推荐的最小 Runtime

示意代码：

```python
async def run_case(workspace: Path) -> RunSummary:
    contract = load_contract(workspace)

    agent = build_agent(
        deps=build_deps(workspace),
        capabilities=baseline_capabilities(),
    )

    try:
        await agent.run(
            build_primary_prompt(contract),
            usage_limits=PRIMARY_LIMITS,
        )

    except UsageLimitExceeded:
        mark_stop_reason("usage_limit")

    validation = validate_deliverables(workspace)

    revisions = 0

    while not validation.passed and revisions < MAX_REVISIONS:
        revisions += 1

        await agent.run(
            build_revision_prompt(validation),
            usage_limits=REVISION_LIMITS,
        )

        validation = validate_deliverables(workspace)

    if validation.passed:
        status = "completed"

    elif substantive_artifacts_exist(workspace):
        status = "partial"

    else:
        status = "failed"

    return write_run_summary(
        status=status,
        validation=validation,
        usage=collect_real_usage(),
    )
```

这里真正重要的不是代码。

而是运行语义：

```text
RUN
↓
ARTIFACT
↓
VALIDATE
↓
REVISE
↓
DELIVER
```

而不是：

```text
RUN
↓
STATE
↓
STATE
↓
STATE
↓
JSON
↓
STATE
```

我们的内部参考实现已经采用这种“主运行 → 验收 → 有界修订 → completed/partial/failed”的模式。

---

# 25. Pydantic Model 的正确位置

Pydantic 非常重要。

但需要记住：

> **Pydantic 验证接口，不验证世界。**

适合：

```text
API input
tool parameters
configuration
run summary
permission request
validation result
stable machine-consumed output
```

谨慎使用：

```text
整个研究过程
人的全部认知
所有 evidence
所有 inference
完整报告
整个企业业务世界
```

我们的内部指南已经明确要求：复杂报告优先直接写成 Markdown、HTML、表格等 Artifact，Pydantic Model 留给真正需要结构化消费的应用边界。

这并不是放弃类型安全。

而是：

> **把类型安全放在真正存在类型边界的地方。**

---

# 26. 最终应该优化什么？

不要再用这些做主 KPI：

```text
Schema completeness
Capability count
Agent count
tool-call success rate
workflow states completed
claims generated
```

应该优化：

## Outcome Quality

```text
成果是否直接可用
```

## Evidence Quality

```text
关键判断有多少得到支持
```

## Decision Quality

```text
是否真正帮助做决定
```

## Recovery Quality

```text
失败以后还能留下多少成果
```

## Human Effort

```text
人工返工分钟数
```

## Marginal Cost

```text
第二次做相同任务是否更便宜
```

## Business Outcome

```text
是否带来：

决策
发布
询盘
样品
报价
订单
节省时间
避免错误
```

内部 Outcome-First 基线已经把最终目标归纳为：完成真实任务、留下可直接使用成果、失败时能够部分交付，并让下一次更快、更便宜、更稳定。

---

# 27. 我们接下来真正应该加强的，不是 Agent 数量，而是这六类资产

## 27.1 Golden Cases

真正高质量的历史案例。

它们是：

```text
需求样本
Prompt 样本
Skill 原料
Evaluator 数据
Regression dataset
销售 Demo
```

---

## 27.2 Outcome Contracts

每种业务真正定义：

```text
用户是谁
决定是什么
成果是什么
完成是什么
什么时候停止
```

---

## 27.3 Skills

把经验变成：

```text
什么时候使用
怎么判断
优先看什么
常见坑是什么
什么算完成
```

这是最重要的长期知识资本之一。

---

## 27.4 Thin Domain Tools

稳定而少量的：

```text
search
fetch
read internal
calculate
write artifact
execute business action
```

---

## 27.5 Evaluator Dataset

把每一次真实错误都变成：

```text
Case
+
Expected property
+
Evaluator
```

这样系统才真正产生复利。

---

## 27.6 Failure Corpus

不要只保存成功 Demo。

真正有价值的是：

```text
搜错产品
误判销量
漏掉规格冲突
引用不能支持判断
预算耗尽
工具返回空结果
未经授权写入
模型空转
```

一个成熟 Agent 系统最有价值的资产，往往不是代码库。

而是：

> **已经知道它会怎么失败。**

---

# 28. 一个更准确的 Agent 技术哲学

传统软件工程追求：

```text
预先枚举状态
预先编码路径
尽可能确定执行
```

Agent 工程面对的是：

```text
开放输入
不完整信息
不稳定外部环境
概率性模型
动态任务路径
```

因此不应该试图把所有不确定性消灭掉。

正确方向是：

```text
确定性的东西 → Python
不可逆的东西 → 权限 / Human Gate
可以探索的东西 → Agent
复杂工作方法 → Skill
大量能力 → Progressive Disclosure
长任务承诺 → Planning
工作记忆 → Files / Artifact
质量判断 → Evaluator
真实改进 → Case Regression
```

---

# 29. 最终参考架构

```text
                         HUMAN / BUSINESS
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Outcome Contract  │
                    └─────────┬───────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │  Outcome-Owning Agent   │
                 │                         │
                 │ Inspect                 │
                 │ Plan                    │
                 │ Act                     │
                 │ Write                   │
                 │ Reflect on progress     │
                 └───────────┬─────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
       Tools              Skills          Capabilities
          │                  │                  │
          │            progressive        progressive
          │              loading            loading
          └──────────────────┼──────────────────┘
                             │
                             ▼
                    BUSINESS WORLD
                  Web / Files / API /
                 DB / ERP / WordPress
                             │
                             ▼
                       ARTIFACTS
                             │
              ┌──────────────┴─────────────┐
              ▼                            ▼
       Deterministic                    Semantic
         Validator                      Evaluator
              │                            │
              └──────────────┬─────────────┘
                             ▼
                 PASS / REVISE / PARTIAL
                             │
                             ▼
                     Human Commitment
                             │
                             ▼
                      REAL OUTCOME
                             │
                             ▼
                     Failure / Success
                             │
                             ▼
                     Dataset + Skills
```

这才形成真正的闭环：

```text
真实任务
→ Agent 工作
→ 真实成果
→ 真实评估
→ 真实行动
→ 真实反馈
→ 改进 Skill / Tool / Prompt
→ 下一次更好
```

而不是：

```text
框架
→ Schema
→ 状态
→ Agent
→ JSON
→ 更多框架
```

---

# 30. 最终工程公理

以后所有 PydanticAI 项目，可以用下面十五条作为默认 Constitution：

1. **Outcome First。先定义成果，再定义 Agent。**
2. **一个 Outcome 默认只有一个负责人 Agent。**
3. **模型操作业务世界，不操作 Agent 框架。**
4. **Python 负责确定性，LLM 负责语义判断。**
5. **Tool 是世界动作边界，不是函数注册表。**
6. **能力增长必须伴随 Progressive Disclosure。**
7. **Capability 是行为扩展，不是领域实体。**
8. **Skill 承载工作方法，而不是 API 文档。**
9. **Planning 是动态工作承诺，不是预制状态机。**
10. **Artifact 是主要工作记忆，Conversation 只是运行介质。**
11. **Validator 判断硬规则，Evaluator 判断质量。**
12. **Human Gate 绑定不可逆承诺，而不是日常思考。**
13. **Partial Delivery 是正常终态，不是失败羞耻。**
14. **架构复杂度必须通过真实 Case 的 A/B 结果获得合法性。**
15. **失败案例、Evaluator 和 Skill 的复利，比 Agent 数量更重要。**

最终可以把整套方法压缩成一句话：

> **不要试图把业务的不确定性全部编码进框架；给模型一个安全、可观察、可评估的工作环境，让它处理真正需要智能的部分，然后用真实成果和真实结果约束它。**

这也是我们从此前的 Schema、状态机、Contract、Ontology、Multi-Agent 等工程实践走到现在以后，更应该坚持的方向：

> **不是做一个更小的 Agent Framework。**
>
> **而是做一个更有效的 Agent 工作系统。**

只有当某项新的复杂性能够明确改善：

```text
Outcome Quality
↑

Evidence Quality
↑

Reliability
↑

Human Effort
↓

Cost
↓

Time-to-Outcome
↓
```

它才值得进入系统。

否则：

**删除它。**