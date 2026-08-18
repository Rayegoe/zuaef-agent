# ZUAEF Business Case Agent — SPEC v0.4

> **SUPERSEDED (2026-08-16):** 本稿的实质内容已被吸收进
> `ZUAEF FDE Agent Platform — SPEC v0.3.md` —— Business Case Agent 的正名是
> **FDE Agent**；本稿的四个对象（BusinessCase/Situation/Policy/Trajectory）
> 成为 FDE 六层架构的第二层 Business Context。保留本文件仅作设计演进证据。

**Status:** Draft for review
**Target:** ZUAEF Platform v0.4
**Repository:** `Rayegoe/zuaef-agent`
**Baseline:** v0.3 Interactive Business Gateway (PASS) + Client Service Decision Slice v0.1 (存量盘点见 §1)
**Primary Proof:** 真实 CASE-BEAUTY-003 case trajectory：目标输入 → 现场 Demo 文章 → 客户反馈 → 局势更新 → 诊断追问 → Barry 纠偏 → 推进 Pilot，全程 receipt + trajectory 可核验
**Primary Surface:** Telegram（supervisor chat + customer chat 双通道）
**Architecture rule:** one Agent, one runtime, one approval mechanism, one receipt/evidence system — plus one **case state** that turns runs into a trajectory.

---

# 0. Executive Decision

v0.3 证明了"自然语言 → 工具 → 安全执行 → 收据"的**控制平面**。但它的 Agent 形态是：

```text
Natural Language Tool Router
客户消息 → 翻译成工具调用 → 执行
```

v0.4 的 Agent 形态必须是：

```text
Business Case Agent
进入真实业务环境，持续感知上下文，
理解当前目标与参与者状态，自主决定下一步，
调用能力产生业务成果，再根据客户反馈调整。
Barry 拥有监督权、纠偏权、最终控制权。
```

主循环：

```text
PERCEIVE → SITUATION → DECIDE → ACT → OBSERVE → 再 DECIDE
```

关键判断：

> **Gateway 是 eyes / ears / hands / gate，不是 brain。**

> **Brain 不是"更多 Tool"。Brain = BusinessCase + Situation + Policy + Trajectory
> 四个对象，file-native，跨 run 延续。**

> **Barry 是 Supervisor，不是 Prompt Operator。** 纠偏是一等公民状态变更，
> 不是下一条普通消息。

> **对客户的外发是 external effect。** 默认 draft-and-hold，逐条审批。

v0.3 全部机器与语义继续复用：`execute_run` / `resume_paused_run` / native approval /
RunReceipt / StepPersistence / CompositionSnapshot。本 SPEC 不新增第二套 runtime、
第二套 approval、第二套 receipt、第二套 durable store。

---

# 1. 存量盘点（开工前必须核对，不得凭本 SPEC 猜测）

## 1.1 保留（作为 case 的子步骤，不再是驱动模型）

| 存量 | 保留理由 |
| --- | --- |
| `CustomerState` / `CustomerAssessment` | Situation 的雏形；改为 Situation 的一个片段 |
| `policy.py` 确定性决策引擎（feature → strategy → R0-R3 → D0-D5） | 判定与表达分离，是 Policy 对象的内核 |
| `InteractionReceipt` + `ClientServiceStore` | Trajectory 的每步记录前身 |
| 四个技能目录（sales-disclosure-boundary / semantic-preference / beauty-content-domain / client-service） | Policy 的 deferred 载体 |
| 私有语料 `slice_root`（evidence ledger / knowledge / semantics） | 客户机密材料不进仓库，case 只引用 id |
| v0.3 Gateway / Telegram adapter / store / renderer / bridge / continuation | 感官与通道，全部复用 |
| WordPress / ACE Writing 插件 | 组合能力，进入 composite profile |

## 1.2 替换

| 旧 | 新 |
| --- | --- |
| `examples/client_service_case.py` 的驱动模型："runs ONE customer message → Response Strategy → Draft" | event-seeded **case run**：目标是推进 case，回复只是可能动作之一 |
| 每条消息产出"建议回复" | 每次事件产出 **CaseStep**：决策 + 动作 + 局势增量，宿主校验 |
| profile 能力孤岛（一次一个插件） | composite role profile（见 §8） |
| 无 BusinessCase/Goal 对象 | `workspace/cases/<case_id>/` 全对象 |
| Barry 的话是普通消息 | `role=supervisor` 一等事件，纠偏写 decision trace |
| 跨 terminal run 无上下文（SPEC v0.3 §98 defer） | **本 SPEC 解除该 defer**：case context 是设计好的记忆，不是通用聊天记忆 |

---

# 2. 四个核心对象

## 2.1 `BusinessCase`

长期业务对象。`workspace/cases/<case_id>/case.md`：

```yaml
case_id: beauty-003
goal: >
  证明我们能够改善客户公众号 AI 内容同质化问题，
  并推动至付费 Pilot。
status: active
stakeholders:
  supervisor: barry
  customer: 公众号矩阵运营团队
supervisor_chat_id: "<telegram chat id>"
customer_chat_id: "<telegram chat id>"
started_at: ...
```

- `case.md` 由 Barry 创建/编辑（受保护文件，模型只读）。
- 一个 case 一条 goal。goal 是 case run 的持久北极星。

## 2.2 `Situation`

Agent **当前认为世界是什么样的**，机器可写、Barry 可读。`situation.json`：

```json
{
  "schema_version": 1,
  "case_id": "beauty-003",
  "updated_at": "...",
  "updated_by": "run:<run_id> | barry",
  "customer": {"confidence": "medium", "authority": "unknown", "budget": "unknown"},
  "problem": {"template_similarity": "confirmed", "low_originality": "confirmed"},
  "commercial": {"stage": "solution_validation"},
  "demo": {"article_v1": {"customer_feedback": "still_ai_like"}},
  "open_questions": ["客户认为什么是自然稿"],
  "evidence_ids": ["EVD-G-*"]
}
```

规则：

- 每个非 unknown 字段变更必须携带 `evidence_ids` 或 `barry_override` 引用；否则宿主拒绝写入。
- 写入走 `update_situation` 工具（`local_write`，自动执行），**工具体内宿主校验 schema + 证据引用**。模型提议，宿主落盘——与 RunSummary 的验证关系同构。

## 2.3 `Policy`

怎么判断。三层：

```text
Knowledge        （领域事实，KNO-*）
Semantic Preference（表达方式，SEM-*）
Decision Policy  （决策规则，canonical + Barry 修订）
```

- canonical 沿用现有语料与 `policy.py`。
- Barry 修订放 `cases/<case_id>/policy-overrides.md`（受保护，模型只读）：
  例如 `VALIDATE_VALUE_BEFORE_COMMERCIAL_QUALIFICATION`（先验证价值再资格审定）。
- 修订不是覆盖，是**带 reason 的 override**，进入 decision trace。

## 2.4 `Trajectory`

发生过什么。`cases/<case_id>/trajectory.jsonl`，append-only，每行：

```json
{
  "seq": 12,
  "ts": "...",
  "kind": "event | decision | action | feedback | override | approval",
  "role": "customer | agent | barry | system",
  "run_id": "...",
  "summary": "...",
  "refs": {"receipt": "...", "artifact": "cases/beauty-003/artifacts/...", "evidence_ids": [...]}
}
```

- 宿主拥有真相：每个 entry 要么由事件管道机械写入（event/feedback/approval），
  要么由 `record_case_step` 工具写入且携带本 run 的 `run_id`（decision/action）。
- RunReceipt 仍是执行真相的唯一权威；trajectory 是 case 级索引，不是第二份 receipt。
- 种子上下文 = trajectory 尾部 N 条 + situation + case.md + policy digest（见 §5）。
- **不是通用聊天记忆。** 不复制 message history 进 case 目录。

---

# 3. Case 文件布局

```text
workspace/cases/beauty-003/
├── case.md                 # BusinessCase（Barry 编辑）
├── situation.json          # Situation（update_situation 宿主校验写入）
├── trajectory.jsonl        # Trajectory（append-only）
├── policy-overrides.md     # Barry 的决策修订（可空）
├── drafts/                 # draft-and-hold 外发草稿（模型写，Barry 审批）
└── artifacts/              # demo 文章、诊断报告等宿主可核验产物
```

约束：

- case 目录在 `workspace/` 内 → 已有 FileSystem 保护与 artifact 核验天然覆盖。
- 私有客户语料**不迁入** workspace；case 文件只引用 `EVD-G-*` / `KNO-*` / `SEM-*` id。
- 凭据、bot token、WP 密码**永不进入 case 目录**。

---

# 4. 通道与角色（Stage A：Telegram 双 chat）

- **supervisor chat**：Barry ↔ Agent。此 chat 的一切消息 `role=supervisor`。
- **customer chat**：客户 ↔ Agent。一切消息 `role=customer`。
- 角色由 **channel_id 绑定机械推导**（case.md 声明两个 chat id），
  绝不由 LLM 猜测发信人身份。
- 两 chat 的用户都必须在 Telegram allowlist 中。

`InboundEnvelope` 不变。Gateway Service 之上新增 **Case Service 层**：
channel → case 绑定 → 角色标注 → 播种 run。Feishu 到来时只换 adapter，Case 语义不变。

---

# 5. 运行模型：event-seeded case run

## 5.1 一次事件 = 一次 run，目标始终是 case goal

```text
inbound event (role-tagged)
        ↓
CaseService
        ↓
种子上下文投影：
  case.md (goal)
  + situation.json
  + policy digest (canonical 命中 + overrides)
  + trajectory 尾部 N 条
  + 事件本身
        ↓
build_profile_agent(profile=beauty-fde)
        ↓
execute_run()
        ↓
run 内部：模型自主 感知 → 决策 → 行动 → 观察（多步工具循环，已有能力）
        ↓
TerminalRun / PausedRun
        ↓
宿主 settle：trajectory 落盘 + situation 增量已由 update_situation 校验
        ↓
外发？→ draft-and-hold 审批卡 → Barry Approve → 发送 → 下一事件
```

- 事件之间 Agent **休眠**。不建后台进程、定时器、心跳（v0.3 非目标延续）。
- 主动跟进 = Barry 在 supervisor chat 发一句"检查进展"，等于一次事件。诚实且可控。
- 单 case 串行：同一 case 一次只有一个 run。run 期间到达的事件：
  机械命令（/status /new /approve /deny）照常；普通消息回复
  "A case run is in progress; your message will be handled next."
  （Stage A 不支持 mid-run interrupt，与 v0.3 一致。）

## 5.2 跨 run 延续的机制（解除 §98 defer 的方式）

- **连续上下文**：`conversation_id = case_id` 固定不变；pause/resume 走
  StepPersistence 历史（v0.3 已证明）。
- **跨 terminal run 的记忆**：不搬 message history，搬**结构化的 case context**
  （§2 四对象）。这是设计好的记忆，不是通用聊天记忆。
- 每次 run 的 prompt 投影是确定性的（CaseService 机械组装），模型不参与组装。

## 5.3 CaseStep 产出契约

每次 case run 的 terminal 输出仍走 `RunSummary` 契约（不修改 core 输出类型），
但模型被要求用 case 工具表达决策：

- `record_case_step`：写入 trajectory（decision/action 类 entry，带 run_id）；
- `update_situation`：局势增量（宿主校验）；
- `save_draft`：外发草稿落到 `drafts/`；
- `send_to_customer`：**external effect → native approval**，审批卡显示草稿全文；
- 业务工具照常：ACE Writing / WordPress / client-service 评估与决策引擎。

---

# 6. 外发闸门：draft-and-hold

1. 模型写 `drafts/msg-<seq>.md`（save_draft，local write）。
2. 模型调用 `send_to_customer(draft_ref)` → `requires_approval=True` → run 暂停。
3. 审批卡 = v0.3 render_pause 扩展：显示**草稿全文** + [Approve] [Deny]。
4. Approve → resume → 草稿经 Gateway 发送到 customer chat → trajectory 记 approval。
5. Deny → 不发送；Barry 可自己写消息（supervisor 指令）或纠正后重触发。
6. "编辑后发送" v0.4 不实现：审批是 approve/deny，不是 edit。
   Barry 若要改稿：Deny + 自己发，或修正后重新触发一次 run。
7. 客户 chat 里模型打出的任何字都不能绕过本闸门（send 只能通过该工具）。

---

# 7. Supervisor 语义（Barry 纠偏一等公民）

- supervisor chat 的事件 kind=override 候选：run 读取后须区分
  (a) 新目标输入、(b) 对上一次决策的纠偏。
- 纠偏的机械效果：
  - `update_situation` 携带 `barry_override` 引用更新局势；
  - `record_case_step(kind=override)` 写 decision trace（含原文与 reason）；
  - 若纠偏指向 Policy：Barry 可写 `policy-overrides.md`（受保护文件），
    模型下一 run 的 policy digest 立即包含。
- **纠偏不等于授权**：审批仍只来自 Approve/Deny 按钮与 /approve /deny。
  模型绝不允许把 Barry 的话解释成授权（v0.3 §69/§70 原样延续）。
- 纠偏的解析是 LLM 的工作（语言理解），纠偏的**落盘是宿主校验的**（schema + 引用）。

---

# 8. Composite Role Profile

```toml
# profiles/beauty-fde.toml
schema = 1
name = "beauty-fde"

[[plugins]]
id = "zuaef-case"          # 新：case 四对象工具集 + 技能

[[plugins]]
id = "client-service"      # 存量：评估 + 决策引擎（降为子步骤）

[[plugins]]
id = "ace-writing"         # demo 文章生产

[[plugins]]
id = "wordpress"           # 测试页发布（可选能力）

[plugins.config]
site_url = "https://dynoedge.com"
```

- profile 代表**业务角色/工作环境**，不是单一工具类别。
- composition 层已支持多插件组合与 tool-conflict 检查；v0.4 直接使用，不改 composition。
- `zuaef-case` 是 **Toolset + Skills** 插件（遵循 Change Rule：新域先 Skill/Toolset）。
  它不做 Capability、不进 core；当且仅当第二个 profile 形态（非销售类 case）
  需要同一套对象+生命周期语义时，才按 Elevation Rule 讨论升级。
- 工具冲突检查照常：case 工具与 client-service 工具命名不重叠。

---

# 9. Case 工具面（zuaef-case v0.1）

```text
load_case_context(case_id)          → goal/situation/policy digest/trajectory 尾部（bounded）
update_situation(case_id, delta, evidence_ids?, barry_override?)   # local_write，宿主校验
record_case_step(case_id, kind, summary, refs)                     # local_write，append-only
save_draft(case_id, text)           → drafts/msg-<seq>.md          # local_write
send_to_customer(case_id, draft_ref)                               # external_write → approval
```

禁止：case 工具不得读 bot token / WP 凭据 / 私有语料原文（只经 client-service store 的 id 引用）。

---

# 10. Gateway 改动清单（在 v0.3 之上，最小增量）

1. **Case binding**：`case_bindings` 表（case_id ↔ supervisor_chat_id ↔ customer_chat_id ↔ 状态指针）。gateway.sqlite3 只存路由态，case 对象留在 workspace/cases/。
2. **Case Service 层**：channel → case → role → 播种 → `start_case_run`（bridge 新增，与 `start_profile_run` 平行，内部仍走 `build_profile_agent` + `execute_run`）。
3. **审批卡带草稿全文**：renderer 扩展 `render_draft_approval`。
4. **命令**：`/status` 显示 case 态（goal 摘要 + situation 关键字段 + trajectory 尾部）；`/new` 清 case 运行指针不动 case 对象。
5. 其余（allowlist / cursor / token 安全 / 恢复 / 幂等）全部沿用 v0.3，不改语义。

---

# 11. Stages

## Stage 0 — Freeze baseline
v0.3 全量测试 + ruff + manifest + 存量 client-service 测试盘点。

## Stage 1 — Case 对象与文件层（zuaef-case 插件骨架）
`cases/<id>/` 布局、case.md/situation.json/trajectory.jsonl 读写、schema 校验、append-only。
Gate：store 单测全绿（含证据引用校验、override 校验、越权写拒绝）。

## Stage 2 — Case 工具集
load_case_context / update_situation / record_case_step / save_draft / send_to_customer。
Gate：工具级单测 + send_to_customer 必然 pause 的 native approval 测试。

## Stage 3 — Composite profile
`profiles/beauty-fde.toml`（zuaef-case + client-service + ace-writing + wordpress）。
Gate：profile check PASS、tool conflict PASS、真实多插件组合 run（FunctionModel）。

## Stage 4 — Gateway case mode
case binding、双 chat 角色推导、start_case_run、draft 审批卡、/status case 态。
Gate：mock 双 chat 全流程 PASS（事件 → run → 草稿 → 审批 → 发送 → trajectory）。

## Stage 5 — 本地端到端 proof
mock Telegram + mock WordPress + 真实 runtime/composition/approval：
完整 beauty-003 子轨迹（目标 → 写 demo 稿 → 客户反馈 → 局势更新 → 诊断草稿 → Barry 审批）。
Gate：断言 continued case 上下文、trajectory 序列、situation 增量、RunReceipt 证据。

## Stage 6 — 真实 proof（CASE-BEAUTY-003）
真实 Telegram 双 chat + 真实语料 + 真实模型：
"写一篇真实的文章给客户看看" → Demo → 客户反馈 → 诊断追问 → Barry 纠偏 → 推进 Pilot。
Gate：CA-1..CA-12 全部 PASS，`spec/case-agent-gate.md` 记录。

---

# 12. Acceptance Gate — CA-1..CA-12

```text
CA-1  Case 对象存在：case.md/situation.json/trajectory.jsonl 可读可核
CA-2  目标驱动：run 的目标投影自 case goal，而非逐条消息回复
CA-3  自主多步：单次 run 内模型自主完成 ≥3 类动作（研究/写作/诊断/追问）
CA-4  跨能力：一次 case 用到 ≥2 个不同插件能力
CA-5  局势延续：客户反馈后 situation 出现被引用的增量
CA-6  纠偏一等：Barry 纠偏 → situation + trajectory 同时更新，下一 run 生效
CA-7  外发闸门：草稿全文审批，未 Approve 绝不发送
CA-8  授权不混同：聊天打 yes/可以 不等于批准（测试证明）
CA-9  宿主真相：trajectory 每条 decision/action 携带 run_id 且 receipt 可查
CA-10 旧系统全绿：v0.3 gateway + 存量 client-service 测试零退化
CA-11 无第二 runtime：无后台 agent/定时器/新 DB/新 memory 服务
CA-12 真实 trajectory：真实 CASE-BEAUTY-003 的 理解→Demo→反馈→修正→推进 链路可核验
```

---

# 13. 禁止清单

```text
class CaseAgent / class CaseRuntime / class SituationEngine / class CaseStateMachine
后台自主 agent / 定时器 / cron
第二份 message-history DB / 通用聊天记忆服务
LLM 猜测发信人角色 / LLM 解读授权
外发绕过审批的任何路径
把 case 四对象做成 Capability/Core（Elevation Rule 未触发）
Feishu / Slack / 群组多角色解析（Stage B+ 再议）
```

---

# 14. Stop Rule

CA-1..CA-12 全 PASS 即完成 v0.4，停止。不自动继续：Feishu、多 case 并发、
定时主动跟进、通用记忆。先回答一个问题：

> **Barry 是否已经把 ZUAEF 放进一个真实客户 case，Agent 自主推进了
> 理解 → Demo → 反馈 → 修正 → Pilot 的完整轨迹，且每一步都有 receipt 与
> trajectory 可核验？**

YES → v0.4 完成。NO → 继续修这条 case trajectory，而不是增加功能。
