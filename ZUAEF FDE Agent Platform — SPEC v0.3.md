# ZUAEF FDE Agent Platform — SPEC v0.3

**Status:** Implementation Ready（经 Barry 校准后的唯一现行 SPEC）
**Target:** ZUAEF Platform v0.3
**Repository:** `Rayegoe/zuaef-agent`
**Baseline:** current `main` + Interactive Gateway v0.3 PASS + Client Service Slice v0.1 + `zuaef-case` Stage 1（文件层已落地）
**Supersedes:** `ZUAEF Interactive Business Gateway — SPEC v0.3.md`（降级为历史档案，其内容被吸收为 Layer 1 与 Field Proof #1）、`ZUAEF Business Case Agent — SPEC v0.4.md`（设计草稿，被吸收为 Layer 2/3）
**Architecture rule:** one FDE Agent, one runtime, one approval mechanism, one receipt/evidence system.

---

# 0. Executive Decision

前两版 SPEC 的主语放错了。我们做的不是 Gateway 平台，也不是"多个业务插件的 Agent 平台"。

**真正的产品只有一个：ZUAEF FDE Agent。**

```text
Gateway   = FDE 的 眼睛 / 嘴 / 手 / 闸门
Writing   = FDE 的业务能力之一
Negotiation / Client Service = FDE 的商业判断能力
Budget    = FDE 的确定性计算能力
WordPress = FDE 操作真实系统的能力之一
Knowledge = FDE 的现场记忆
WorkOrder = FDE 的长期任务控制平面
Receipt   = FDE 的执行证据
```

Telegram 不是产品，是 FDE 进入业务现场的一个 **Field Surface**。
WordPress 不是产品，是 FDE 的一个 **Execution Capability**。
写作不是一个 Agent，是 FDE 在解决业务问题时调用的一种能力。

**FDE（Forward Deployed Engineer）定义：**

> 能够进入真实企业业务现场，理解目标、诊断问题、调用专业能力、
> 操作真实系统、请求必要授权、验证执行结果并持续沉淀业务知识的
> outcome-owning Agent。

与 Chatbot / Tool Agent 的本质区别：

```text
Chatbot:        用户问 → AI 答
Tool Agent:     用户要求 → AI → 调工具 → 返回结果
FDE Agent:      业务目标 → 理解现场 → 发现约束/Unknown → 诊断
                → 决定下一步 → 选择 Capability → 调查/写作/分析/谈判/操作系统
                → 高风险动作 → Human Gate → 执行 → 验证真实结果
                → Receipt/Evidence → 更新业务上下文 → 决定下一步
```

---

# 1. 产品关系图

```text
                    ZUAEF FDE AGENT
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
 Business Context      Reasoning Loop      Execution
 业务上下文             业务判断             业务执行
        │                  │                  │
        │                  │          ┌───────┼────────┐
        │                  │          │       │        │
        │                  │       写作     谈判     预算
        │                  │          │       │        │
        │                  │       WordPress  CRM/ERP  Research
        │                  │
        └──────────────────┼──────────────────┘
                           │
                    Evidence / Receipt
                           │
                    Human Approval
                           │
                           ▼
              Telegram / Feishu / Slack
              Web / CLI / WeCom / ...
```

---

# 2. 六层架构与归属

```text
┌──────────────────────────────────────────────────────┐
│ 1. FIELD INTERFACE                                   │
│    Telegram / Feishu / Slack / CLI / Web / API       │
│    人在哪里工作，FDE 就在哪里出现                     │
├──────────────────────────────────────────────────────┤
│ 2. BUSINESS CONTEXT                                  │
│    Customer / Project / Goal / Constraints /         │
│    Current State / History / Unknowns                │
│    FDE 知道"我现在进入的是什么现场"                   │
├──────────────────────────────────────────────────────┤
│ 3. FDE DECISION LOOP                                 │
│    Observe → Diagnose → Decide → Act → Verify        │
│    → Continue / Stop                                 │
│    ONE outcome-owning Agent                          │
├──────────────────────────────────────────────────────┤
│ 4. CAPABILITY PLANE                                  │
│    Writing / Negotiation / Budget / Research /       │
│    WordPress / Hardware Scout / future               │
├──────────────────────────────────────────────────────┤
│ 5. ACTION & HUMAN CONTROL                            │
│    observe / local_write / external_write→approval   │
│    destructive→approval / draft-and-hold outbound    │
├──────────────────────────────────────────────────────┤
│ 6. EVIDENCE & LEARNING                               │
│    Artifacts / Tool Effects / Sources / Knowledge    │
│    Receipts / Business Outcomes / Case Trace         │
└──────────────────────────────────────────────────────┘
```

**Layer 3（FDE Decision Loop）是中央核心。** 其余五层全部围绕它存在。

各层归属：

| 层 | owns | MUST NOT own |
| --- | --- | --- |
| 1 Field Interface | transport、identity、authorization、session binding、inbound/outbound 渲染、routing state | agent loop、业务政策、审批语义、receipts |
| 2 Business Context | 四对象（BusinessCase/Situation/Policy/Trajectory）的 schema 与宿主校验 | 执行真相（RunReceipt 才是权威） |
| 3 Decision Loop | 事件播种、上下文投影、run 编排、continue/stop 判定 | 第二套 runtime、状态机、后台进程 |
| 4 Capability Plane | 能力组合、冲突检查、Deployment Profile | 业务决策（那是 Loop 的事） |
| 5 Action & Control | effect 分类、审批 UI、外发闸门 | 授权语义（PydanticAI native approval） |
| 6 Evidence | 核验、沉降、知识沉淀 | 模型自述（模型声明只是提议） |

---

# 3. 五大护城河（产品壁垒 = 验收门）

1. **Business Context** — 知道客户是谁、项目是什么、当前状态，而不是只收到一句 prompt。
2. **Decision Policy** — 知道何时继续问、何时分析、何时报价、何时执行、何时拒绝或升级人工。
3. **Capability Composition** — 写作、谈判、预算、WordPress、Research 自由组合，而非一个 Agent 一个 vertical。
4. **Field Execution** — 真能进入 Telegram、飞书、网站、CRM 等真实现场。
5. **Evidence + Outcome Verification** — 不以"模型说完成"为完成，以真实 artifact / side effect / receipt 为完成。

这五条合起来才叫 FDE Agent；它们直接映射到 §17 的 FDE-1..FDE-12。

---

# 4. Baseline 盘点（开工前核对，不得凭本 SPEC 猜测）

| 器官 | 状态 | 位置 |
| --- | --- | --- |
| 共享续跑缝 `resume_paused_run` | PASS | `src/zuaef_agent/continuation.py` |
| Field Interface（原 Gateway） | PASS（真实 Telegram+WordPress 证明） | `src/zuaef_agent/gateway/` |
| Client Service 决策引擎 | 可用（降级为 Loop 子步骤） | `plugins/zuaef-client-service/` |
| ACE Writing / WordPress 插件 | 可用 | `plugins/zuaef-ace-writing/`、`plugins/zuaef-wordpress/` |
| Business Context 文件层 | Stage 1 已落地（18 测试） | `plugins/zuaef-case/` |
| 私有语料 | 不进仓库，仅 id 引用 | `~/.local/share/zuaef/client-service` |

**Field Proof #1（Telegram → WordPress 链）已在 v0.3 Gateway 周期内 PASS**：
真实手机 → 真实模型 → PausedRun `9cedcc01…` → Approve → 真实 WordPress draft 52 → publish → RunReceipt `6dbbb41d…`。它现在是 FDE 的**第一个 Field Proof**，不是产品本身。全部证据在 `spec/interactive-gateway-gate.md`。

**命名约定**：代码包名 `zuaef_agent.gateway` 暂不改名。它是 Field Interface 层的实现包；
仅当名称产生可测的误导时，才做重命名重构（属于纯机械改动，不在此 SPEC 的 Gate 内）。

---

# 5. Layer 1 — Field Interface

- 职责 = 原 v0.3 Gateway 全部语义：transport、身份 allowlist、session binding、
  入站规范化、出站渲染、审批 UI、routing-state 持久化、cursor、token 安全、重启恢复。
- 新增 v0.3 语义：**case mode**（§9）。
- Surface 路线：Telegram 先行（已 PASS）；Feishu 是第二个 surface，加入时不得修改
  Decision Loop、Business Context、审批语义——否则 Surface 抽象 FAIL（原 v0.3 §90 延续）。

---

# 6. Layer 2 — Business Context（FDE 的现场记忆）

四个对象，全部 file-native，位于 `workspace/cases/<case_id>/`：

```text
cases/beauty-003/
├── case.md               # BusinessCase：goal/status/stakeholders/双 chat 绑定（Barry 编辑，模型只读）
├── situation.json        # Situation：FDE 当前认为的世界（宿主校验写入）
├── trajectory.jsonl      # Trajectory：append-only 现场轨迹
├── policy-overrides.md   # Barry 的决策修订（可空，模型只读）
├── drafts/               # draft-and-hold 外发草稿
└── artifacts/            # demo 文章、诊断报告等可核验产物
```

- `case.md` / `policy-overrides.md` 是 core 受保护路径（已落地：
  `FILESYSTEM_PROTECTED_PATTERNS` 含 `cases/*/case.md`、`cases/*/policy-overrides.md`）。
- **Situation 宿主校验**：每个实质性（非 unknown）事实必须携带
  `evidence_ids` 或 `barry_override`，否则拒绝写入。模型提议，宿主落盘。
- **Trajectory append-only**：decision/action 类条目必须携带 `run_id`；
  无 update/delete API。它是 case 级索引，RunReceipt 仍是执行真相权威。
- 私有客户语料不迁入 workspace；case 只引用 `EVD-G-*` / `KNO-*` / `SEM-*` id。
- 凭据/token/密码永不进入 case 目录。

（Stage 1 已实现：`zuaef_case.models` + `zuaef_case.store`，18 个测试全绿，
覆盖 frontmatter 往返、id 防穿越、provenance 强制、append-only、drafts。）

---

# 7. Layer 3 — FDE Decision Loop（中央核心）

## 7.1 Event-seeded case run

```text
inbound event (role-tagged)
        ↓
CaseService：channel → case 绑定 → 角色推导（机械，绝不 LLM 猜身份）
        ↓
种子上下文投影（机械组装）：
  case.md(goal) + situation.json + policy digest + trajectory 尾部 N 条 + 事件
        ↓
build_profile_agent(deployment=stillevo-fde)   # Layer 4
        ↓
execute_run()                                   # Layer 3，复用现有 seam
        ↓
run 内部：Observe → Diagnose → Decide → Act → Verify → Continue/Stop
（多步工具循环，现有 execute_run 已支持）
        ↓
TerminalRun / PausedRun → 宿主 settle → trajectory/situation 落盘（Layer 6）
```

- **单 case 串行**：一次一个 run；run 期间新事件回复
  "A case run is in progress; your message will be handled next."
  （v0.3 不支持 mid-run interrupt，延续）。
- **跨 run 延续**：`conversation_id = case_id` 不变；pause/resume 走 StepPersistence
  历史；跨 terminal run 的记忆 = 结构化 case context（Layer 2），不是聊天记忆库。
- **休眠是特性**：事件之间 Agent 静默。主动跟进 = Barry 在 supervisor chat
  发一句（如"检查进展"）= 一次事件。不建后台进程/定时器。

## 7.2 Immediate Loop vs WorkOrder Loop（WO 的准确位置）

```text
Field message
    ↓
FDE Agent
    ├── 简单任务 ──→ Immediate Loop：一次事件一次 run，直接完成
    └── 复杂持续任务 ──→ WorkOrder：Goal/KR/Status/EvidenceRef → FDE 持续执行
```

WO 不是多 Agent 协调器，是 FDE 的**长期任务控制平面**。
本 SPEC 只定义其位置；WO 实现属于 v0.4+（见 §16 禁止清单）。

## 7.3 CaseStep 产出契约

run 输出仍走 `RunSummary` 契约（不修改 core 输出类型）。决策结构由 Layer 2/4
的工具表达：`record_case_step`（轨迹）、`update_situation`（局势）、
`save_draft`（草稿）、`send_to_customer`（审批外发）、业务工具照常。
**决策结构成为 run 正式输出类型 = core 级变更，本 SPEC 不引入；**
若真实运行证明文本型 RunSummary 无法承载决策轨迹，再单独论证。

---

# 8. Layer 4 — Capability Plane 与 Deployment Profile

**Profile 不是人格切换器。** 用户不说"现在你是预算 Agent"，而是：

> 帮我看看这个客户项目为什么超预算，顺便判断我们还要不要继续接。

FDE 自己组合 Client Service + Budget + Knowledge。因此：

```text
FDE Deployment Profile = 某个业务现场允许使用的 Capability Set + Workspace + Policy
```

```toml
# profiles/stillevo-fde.toml
schema = 1
name = "stillevo-fde"

[[plugins]]
id = "zuaef-case"

[[plugins]]
id = "client-service"

[[plugins]]
id = "ace-writing"

[[plugins]]
id = "budget"

[[plugins]]
id = "wordpress"

[plugins.config]
site_url = "https://stillevo.example"
```

用户面对的是 **Stillevo FDE**，不是五个 Agent。Plugin Composition Layer
（v0.2，已 PASS）正好承载这一点：多插件组合 + 工具冲突检查 + 冻结快照，
最终仍然 ONE AGENT。与仓库一贯的 "single outcome-owning agent" 完全一致。

`/profile` 语义变更：切换 = 更换 FDE 的部署现场（能力集），不更换人格；
切换规则与原 v0.3 一致（paused run 存在时禁止）。

---

# 9. Field Interface 的 case mode（在 v0.3 Gateway 之上最小增量）

1. **Case binding**：gateway.sqlite3 新增 case 绑定（case_id ↔ supervisor/customer chat id ↔ 运行指针）。路由态只存指针，case 对象留在 workspace/cases/。
2. **双 chat 角色推导**：supervisor chat / customer chat 由 channel_id 绑定机械推导；两 chat 用户都必须过 allowlist。
3. **start_case_run**（bridge 新增，与 start_profile_run 平行）：种子投影 + 组合 + execute_run。
4. **审批卡带草稿全文**：`render_draft_approval`。
5. **命令**：`/status` 显示 case 态（goal 摘要 + situation 关键字段 + trajectory 尾部）；`/new` 清运行指针不动 case 对象；`/approve /deny` 语义不变。
6. 其余（allowlist / cursor / token 安全 / 幂等 / 恢复）沿用 v0.3 全部语义。

---

# 10. Layer 5 — Action & Human Control

- effect 分类沿用：`observe / local_write 自动`；`external_write / destructive 必须审批`。
- **外发闸门 draft-and-hold**（v0.4 草稿已定，并入本 SPEC）：
  模型写 `drafts/msg-<seq>.md` → `send_to_customer` = external_write → 审批卡显示草稿全文 →
  Barry Approve 才发送；Deny = 不发送，Barry 自己写或纠正后重触发。不做"编辑后发送"。
- **Supervisor 纠偏是一等公民**：supervisor chat 事件 → 语言理解是 LLM 的工作，
  落盘是宿主校验的：`update_situation(barry_override=…)` + `record_case_step(kind=override)`；
  纠偏指向 Policy 时 Barry 写 `policy-overrides.md`，下一 run 的 policy digest 立即生效。
- **纠偏 ≠ 授权**：审批只来自 Approve/Deny 按钮与 /approve /deny。
  聊天里打 "yes/可以/执行" 永远不算批准（v0.3 §69/§70 原样延续，测试钉死）。

---

# 11. Layer 6 — Evidence & Learning

- 执行真相：StepPersistence + tool-effect ledger + RunReceipt（不动）。
- Case 级真相：trajectory.jsonl（append-only，带 run_id 引用 receipt）。
- 现场记忆：situation 增量（带证据引用）+ knowledge（现有 Knowledge 能力）。
- 学习闭环：客户反馈 → situation 更新 → 下一 run 的种子上下文改变 → 行为改变。
- 核验口径不变：模型声明只是提议，宿主核验后才入 receipt/trajectory。

---

# 12. zuaef-case 工具面

```text
load_case_context(case_id)        → goal/situation/policy digest/trajectory 尾部（bounded）
update_situation(case_id, delta, evidence_ids?, barry_override?)   # local_write，宿主校验
record_case_step(case_id, kind, summary, refs)                     # local_write，append-only
save_draft(case_id, text)         → drafts/msg-<seq>.md            # local_write
send_to_customer(case_id, draft_ref)                               # external_write → approval
```

禁止：case 工具读 bot token / WP 凭据 / 私有语料原文（只经 client-service store 的 id 引用）。

---

# 13. Field Proofs

- **P1（已完成）**：Telegram → ZUAEF → WordPress external write → Native Approval →
  手机 Approve → Resume → 真实 publish → RunReceipt。作为回归基线保留。
- **P2（v0.3 目标）**：真实 CASE-BEAUTY-003 trajectory——
  目标输入 → 现场 Demo 文章 → 客户反馈 → 局势更新 → 诊断追问 → Barry 纠偏 →
  推进 Pilot。全程 receipt + trajectory 可核验。

---

# 14. Stages

| Stage | 内容 | Gate |
| --- | --- | --- |
| 0 | Freeze baseline（全量测试/ruff/manifest + 存量盘点） | 306 tests PASS（记录） |
| 1 | Business Context 文件层（zuaef-case store/models） | **已完成**：18 测试全绿 |
| 2 | zuaef-case 工具集（§12 五工具 + send_to_customer 必然 pause） | 工具单测 + native approval 测试 PASS |
| 3 | Deployment Profile（stillevo-fde 复合能力集） | profile check + tool conflict PASS + 多插件组合 run |
| 4 | Field Interface case mode（双 chat/start_case_run/草稿审批卡） | mock 双 chat 全流程 PASS |
| 5 | 本地端到端 proof（mock Telegram/WordPress，真实 runtime） | P2 子轨迹断言 PASS |
| 6 | 真实 Field Proof（CASE-BEAUTY-003 + P1 回归） | FDE-1..FDE-12 全 PASS |

---

# 15. Acceptance Gates — FDE-1..FDE-12

```text
FDE-1  现场接入：真实 Field message 到达 FDE（Telegram 通道回归）
FDE-2  Business Context：case/situation/trajectory 可读可核，goal 驱动 run
FDE-3  局势延续：客户反馈后 situation 出现带证据引用的增量
FDE-4  Decision Policy：决策受 canonical + Barry override 约束，轨迹可查
FDE-5  Capability Composition：一次 case 跨 ≥2 个插件能力自主组合
FDE-6  Field Execution：真实外部系统写入（WordPress）经审批执行并核验
FDE-7  外发闸门：草稿全文审批，未 Approve 绝不发送
FDE-8  Outcome Verification：completed 效果在 verified_tool_effects 中
FDE-9  Case Trace：trajectory 每条 decision/action 带 run_id 且 receipt 可查
FDE-10 纠偏一等：Barry 纠偏 → situation + trajectory 更新，下一 run 生效；
       聊天 yes ≠ 批准
FDE-11 无第二 runtime：无后台 agent/定时器/新 DB/新 memory 服务
FDE-12 旧系统全绿：全部存量测试零退化
```

---

# 16. 禁止清单

```text
class FDEAgent / class CaseRuntime / class SituationEngine / class CaseStateMachine
后台自主 agent / 定时器 / cron / 心跳
第二份 message-history DB / 通用聊天记忆服务
LLM 猜测发信人角色 / LLM 解读授权
外发绕过审批的任何路径
把 Business Context 四对象做成 Capability/Core（Elevation Rule 未触发）
WorkOrder 实现（本 SPEC 只定位，v0.4+ 再议）
Feishu / Slack / 群组多角色解析（Stage B+ 再议）
代码包重命名（无测得的误导不动）
```

---

# 17. Stop Rule

FDE-1..FDE-12 全 PASS 即完成 v0.3，停止。不自动继续：Feishu、WO、多 case 并发、
定时主动跟进、通用记忆。先回答一个问题：

> **Barry 是否已经把 ZUAEF FDE 放进一个真实客户 case，FDE 自主推进了
> 理解 → Demo → 反馈 → 修正 → Pilot 的完整轨迹，且每一步都有 receipt 与
> trajectory 可核验？**

YES → v0.3 完成。NO → 继续修这条 case trajectory，而不是增加功能。
