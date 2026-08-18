# ZUAEF Interactive Business Gateway — SPEC v0.3

> **SUPERSEDED（历史档案）:** 本文件已被 `ZUAEF FDE Agent Platform — SPEC v0.3.md`
> 取代。Gateway 语义被吸收为 FDE 六层架构的 Layer 1 Field Interface；
> Telegram → WordPress 链降级为 Field Proof #1（已 PASS，证据在
> `spec/interactive-gateway-gate.md`）。保留本文件仅作实现细节参考，
> 不再作为产品方向的权威。

**Status:** Superseded (historical)  
**Target:** ZUAEF Platform v0.3  
**Repository:** `Rayegoe/zuaef-agent`  
**Baseline:** current `main`, ZUAEF Agent Core `0.1.1` + Plugin Composition Layer v0.2  
**Primary Proof:** Telegram → ZUAEF → WordPress external write → Native Approval → Telegram Approve/Deny → Resume → Host Verification → Receipt  
**Primary Surface:** Telegram  
**Second Surface:** Feishu/Lark, Stage B only  
**Primary Business Adapter:** WordPress  
**Architecture rule:** one Agent, one runtime seam, one approval mechanism, one receipt/evidence system

---

# 0. Executive Decision

ZUAEF 从本版本开始从：

```text
Thin Agent Harness
```

演化为：

```text
Composable Business Agent Platform
```

但平台化不得通过增加第二套 runtime、第二套 approval、第二套 state machine、第二套 receipt system 实现。

平台结构固定为：

```text
                         ZUAEF PLATFORM

┌───────────────────────────────────────────────────────┐
│ Surface / Gateway Layer                               │
│                                                       │
│ Telegram    Feishu    Slack    Web/API    future      │
│     \          |        |        |                    │
│      └──── Normalized Interaction ────┘               │
└──────────────────────┬────────────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────────────┐
│ Profile / Plugin Composition                          │
│                                                       │
│ writing                                               │
│ negotiation                                           │
│ budget                                                │
│ wordpress                                             │
│ content-operator                                      │
└──────────────────────┬────────────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────────────┐
│ ONE ZUAEF Runtime                                     │
│                                                       │
│ build_agent / build_profile_agent                     │
│                  ↓                                    │
│              execute_run()                            │
│                  ↓                                    │
│        TerminalRun | PausedRun                        │
└──────────────────────┬────────────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────────────┐
│ Evidence / State                                      │
│                                                       │
│ StepPersistence                                       │
│ Tool Effects                                          │
│ Artifacts                                             │
│ Knowledge                                             │
│ PauseReceipt / RunReceipt                             │
│ CompositionSnapshot                                   │
└───────────────────────────────────────────────────────┘
```

本 SPEC 的关键设计判断：

> **Gateway 是 Agent 外部的交互控制面，不是新的 Agent Runtime。**

以及：

> **Gate 是 PydanticAI native approval 的交互界面，不是 Approval Engine。**

---

# 1. Baseline — 当前已有能力

Coding Agent 开工前必须先确认当前仓库实际状态，不得基于本 SPEC 猜测不存在的接口。

当前 baseline 应至少包含：

```text
src/zuaef_agent/
├── cli.py
├── composition.py
├── config.py
├── core.py
├── effects.py
├── models.py
├── plugin_api.py
├── profiles.py
├── receipt_store.py
├── runtime.py
└── ...
```

以及：

```text
plugins/
└── zuaef-ace-writing/

profiles/
└── ace-writing.toml
```

当前必须视为冻结的公共接口：

```python
build_agent(...)
build_profile_agent(...)
execute_run(...)
```

以及：

```python
TerminalRun
PausedRun
RunReceipt
PauseReceipt
CompositionSnapshot
CoreDeps
```

当前 Approval 已存在：

```text
PydanticAI DeferredToolRequests
PydanticAI DeferredToolResults
PydanticAI requires_approval=
```

当前 CLI 已证明：

```text
zuaef-agent resume RUN_ID --approve
zuaef-agent resume RUN_ID --deny
```

可以恢复 paused run。

本 SPEC 不允许重新实现这些语义。

---

# 2. 开工前 Preflight

Coding Agent 第一阶段只检查，不修改。

必须执行：

```bash
git status
git rev-parse HEAD
uv sync
uv run pytest -q
uv run ruff check .
```

记录：

```text
baseline commit
baseline test count
baseline test result
baseline ruff result
```

如果 baseline tests 不通过：

```text
STOP implementation
```

先记录失败。

不得为了实现本 SPEC 删除、skip 或 weaken 已有测试。

不得：

```text
git reset --hard
git checkout .
```

去覆盖用户现有未提交工作。

---

# 3. Goals

## G1 — Telegram 可以启动真实 ZUAEF run

用户发送：

```text
帮我检查 WordPress 文章 123
```

必须实际经过：

```text
Telegram
→ Gateway
→ profile composition
→ execute_run()
```

不能做独立 Bot Agent。

---

## G2 — Gateway 能绑定 Surface Session 与 ZUAEF Conversation

至少保存：

```text
surface
user_id
channel_id
conversation_id
profile
active_run_id
paused_run_id
```

---

## G3 — Profile 是业务能力组合入口

Gateway 不直接 import：

```text
writing toolset
budget toolset
wordpress toolset
negotiation toolset
```

而是：

```python
build_profile_agent(
    settings,
    profile=session.profile,
)
```

---

## G4 — Native Approval 可在 Telegram 中交互

当：

```python
execute_run(...)
```

返回：

```python
PausedRun
```

Gateway 必须呈现：

```text
等待授权

Tool
wordpress_publish_post

Target
...

[批准执行]
[拒绝]
```

---

## G5 — Telegram Approval 恢复原 paused run

Approve/Deny 必须恢复：

```text
PauseReceipt
+
StepPersistence message history
+
DeferredToolResults
+
Frozen CompositionSnapshot
```

不得重新发起新的自然语言任务模拟“批准”。

---

## G6 — Resume 必须使用冻结 Composition

如果 paused 时：

```text
wordpress 0.1.0
```

而 resume 时已安装：

```text
wordpress 0.2.0
```

现有 composition drift 检查必须生效。

Gateway 不得绕过。

---

## G7 — WordPress external write 作为真实 proof

至少完成一个：

```text
wordpress_publish_post
```

真实 external write。

该调用必须：

```text
requires_approval=True
```

并在完成后出现在：

```text
RunReceipt.verified_tool_effects
```

---

## G8 — Gateway 可被第二个平台复用

Stage A 只实现 Telegram。

Stage B 实现 Feishu 时不得：

```text
修改 execute_run()
修改 Plugin API
重写 approval logic
重写 session semantics
```

如果加入 Feishu 必须重写上述层，则 Stage A architecture FAIL。

---

# 4. Non-Goals

v0.3 明确不做：

```text
Multi-agent
Agent registry
Graph runtime
Generic event bus
Hook framework
Custom durable runtime
Custom approval engine
Custom receipt system
Long-term memory service
Vector database
Background autonomous agents
Cron platform
Task scheduler
Cross-session message mirroring
Generic workflow engine
Web admin dashboard
Marketplace
Remote plugin registry
Hot reload
Surface dependency solver
OAuth platform
RBAC platform
Multi-tenant SaaS billing
```

也不做：

```text
20 个 messaging platforms
```

Stage A：

```text
Telegram only
```

Stage B：

```text
Feishu only
```

只有两个独立 Surface 证明同一 interface 后，才允许讨论：

```text
zuaef.surfaces entry-point system
```

不要提前实现 Surface Plugin Registry。

---

# 5. Architecture Boundaries

## 5.1 Core owns

```text
Agent
Usage limits
Tool output limits
Step persistence
Approval semantics
Artifacts
Knowledge
Tool effect verification
RunReceipt
PauseReceipt
Terminal status
```

---

## 5.2 Plugin owns

```text
domain actions
domain-local tool policy
optional Skill
optional explicitly permitted Capability
```

例如：

```text
ACE Writing
Budget
Negotiation
WordPress
```

---

## 5.3 Gateway owns

仅：

```text
transport
identity
authorization
session binding
profile selection
inbound normalization
outbound rendering
approval UI
routing-state persistence
```

---

## 5.4 Gateway MUST NOT own

```text
business decision policy
tool execution policy
approval policy
LLM loop
artifact truth
effect truth
receipt truth
business workflow state machine
```

---

# 6. State Ownership Matrix

必须严格区分。

## Execution Truth

唯一来源：

```text
.zuaef-state/steps/
.zuaef-state/tool-results/
.zuaef-state/receipts/
```

Gateway 不复制 execution truth。

---

## Business Artifacts

唯一来源：

```text
workspace/artifacts/
```

---

## Knowledge

唯一来源：

```text
workspace/knowledge/
```

---

## Gateway Routing State

允许新增：

```text
.zuaef-state/gateway.sqlite3
```

只能包含：

```text
session binding
surface cursor
approval interaction token
surface delivery metadata
```

不得保存：

```text
完整 Agent trajectory
第二份 RunReceipt
第二份 tool-effect ledger
模型内部 reasoning
业务 artifact 副本
```

---

# 7. Package Layout

Stage A 目标目录：

```text
src/zuaef_agent/
├── gateway/
│   ├── __init__.py
│   ├── models.py
│   ├── store.py
│   ├── surface.py
│   ├── telegram.py
│   ├── bridge.py
│   ├── renderer.py
│   └── service.py
│
├── cli.py
├── composition.py
├── runtime.py
└── ...

plugins/
├── zuaef-ace-writing/
└── zuaef-wordpress/
    ├── pyproject.toml
    └── zuaef_wordpress/
        ├── __init__.py
        ├── client.py
        └── toolset.py

profiles/
├── ace-writing.toml
└── wordpress-operator.toml

tests/
├── test_gateway_models.py
├── test_gateway_store.py
├── test_gateway_telegram.py
├── test_gateway_bridge.py
├── test_gateway_service.py
└── test_wordpress_plugin.py

spec/
└── interactive-gateway-gate.md
```

不要建立顶层：

```text
gateway/
```

因为当前 wheel 只打包：

```text
src/zuaef_agent
```

Gateway 必须进入现有 package。

---

# 8. Gateway Domain Models

文件：

```text
src/zuaef_agent/gateway/models.py
```

至少定义以下模型。

---

## 8.1 AttachmentRef

```python
class AttachmentRef(BaseModel):
    kind: Literal["document", "image", "audio", "other"]
    local_path: str
    original_name: str | None = None
    mime_type: str | None = None
    size: int | None = None
```

`local_path` 必须：

```text
workspace-relative
```

不得保存绝对路径到用户可见消息中。

---

## 8.2 InboundEnvelope

```python
class InboundEnvelope(BaseModel):
    surface: str
    tenant_id: str = "default"

    user_id: str
    channel_id: str
    thread_id: str | None = None

    message_id: str
    text: str = ""

    attachments: list[AttachmentRef] = Field(default_factory=list)

    callback_token: str | None = None
    callback_action: Literal["approve", "deny"] | None = None
```

Gateway 上层不得处理 Telegram-specific Update object。

---

## 8.3 SessionBinding

```python
class SessionBinding(BaseModel):
    surface: str
    tenant_id: str

    user_id: str
    channel_id: str
    thread_key: str

    conversation_id: str
    profile: str | None

    active_run_id: str | None = None
    paused_run_id: str | None = None
    last_terminal_run_id: str | None = None
```

重要：

> `conversation_id` 在 v0.3 是 correlation identity，不等于自动长期 memory。

普通 terminal run 之间不得假装具有模型聊天记忆。

真正 pause/resume continuity 必须来自 StepPersistence message history。

---

## 8.4 ApprovalBinding

```python
class ApprovalBinding(BaseModel):
    token_hash: str

    surface: str
    user_id: str
    channel_id: str

    paused_run_id: str

    state: Literal[
        "pending",
        "approved",
        "denied",
        "expired",
    ]

    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None = None
```

---

# 9. Gateway Store

文件：

```text
src/zuaef_agent/gateway/store.py
```

使用：

```python
sqlite3
```

不得引入 ORM。

不得引入 migration framework。

使用：

```sql
PRAGMA user_version = 1;
```

---

# 10. SQLite Schema

至少：

```sql
CREATE TABLE IF NOT EXISTS session_bindings (
    surface TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    thread_key TEXT NOT NULL,

    conversation_id TEXT NOT NULL,
    profile TEXT,

    active_run_id TEXT,
    paused_run_id TEXT,
    last_terminal_run_id TEXT,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    PRIMARY KEY (
        surface,
        tenant_id,
        channel_id,
        thread_key
    )
);
```

注意：

```text
thread_id = None
```

写入数据库前规范化为：

```text
thread_key = ""
```

避免 NULL composite key 问题。

---

新增：

```sql
CREATE TABLE IF NOT EXISTS approval_bindings (
    token_hash TEXT PRIMARY KEY,

    surface TEXT NOT NULL,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,

    paused_run_id TEXT NOT NULL,

    state TEXT NOT NULL,

    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT
);
```

---

新增：

```sql
CREATE TABLE IF NOT EXISTS surface_offsets (
    surface TEXT PRIMARY KEY,
    cursor TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

用于 Telegram：

```text
update_id offset
```

防止 process restart 后重复处理旧 update。

---

# 11. Store API

至少：

```python
class GatewayStore:

    def get_or_create_session(
        self,
        *,
        surface: str,
        tenant_id: str,
        user_id: str,
        channel_id: str,
        thread_id: str | None,
        default_profile: str | None,
    ) -> SessionBinding:
        ...

    def save_session(self, binding: SessionBinding) -> None:
        ...

    def reset_session(...) -> SessionBinding:
        ...

    def get_cursor(self, surface: str) -> str | None:
        ...

    def set_cursor(self, surface: str, cursor: str) -> None:
        ...

    def create_approval(
        self,
        *,
        session: SessionBinding,
        paused_run_id: str,
        ttl_seconds: int,
    ) -> str:
        """
        Return RAW opaque callback token.
        Database stores SHA-256 only.
        """
        ...

    def resolve_approval(
        self,
        raw_token: str,
    ) -> ApprovalBinding | None:
        ...

    def consume_approval(
        self,
        raw_token: str,
        *,
        decision: Literal["approved", "denied"],
    ) -> ApprovalBinding:
        ...
```

---

# 12. Approval Token Security

不得把：

```text
run_id
tool_call_id
```

直接作为唯一 callback authorization。

生成：

```python
secrets.token_urlsafe(16)
```

用户看到：

```text
opaque token
```

数据库保存：

```python
sha256(raw_token.encode()).hexdigest()
```

Callback Data：

```text
zg:<token>:a
zg:<token>:d
```

其中：

```text
a = approve
d = deny
```

Telegram callback data 必须保持短小。

---

## Validation 顺序

Callback 到来必须：

1. 验证 Telegram user 在 allowlist。
2. lookup token hash。
3. token 必须存在。
4. token.state == pending。
5. token 未过期。
6. token.user_id == callback user。
7. token.channel_id == callback channel。
8. 对应 session.paused_run_id == token.paused_run_id。
9. ReceiptStore 中该 run 必须仍然是 `PauseReceipt`。
10. 才允许 resume。

任一失败：

```text
DO NOT resume
```

---

# 13. Surface Interface

文件：

```text
src/zuaef_agent/gateway/surface.py
```

Stage A 不实现 entry-point registry。

定义最小 Protocol：

```python
class SurfaceAdapter(Protocol):

    surface_name: str

    def poll_once(
        self,
        *,
        timeout_seconds: int,
    ) -> list[InboundEnvelope]:
        ...

    def send_text(
        self,
        channel_id: str,
        text: str,
    ) -> None:
        ...

    def send_document(
        self,
        channel_id: str,
        path: Path,
        *,
        caption: str | None = None,
    ) -> None:
        ...

    def send_approval(
        self,
        channel_id: str,
        *,
        text: str,
        approve_token: str,
    ) -> None:
        ...

    def answer_callback(
        self,
        callback_id: str,
        text: str,
    ) -> None:
        ...
```

如 callback_id 不适合放入 `InboundEnvelope`，允许新增：

```python
transport_context: dict[str, str]
```

但不得把完整 Telegram Update 向 Gateway Service 泄漏。

---

# 14. 为什么 Stage A 使用同步 Gateway

当前：

```python
execute_run()
```

内部：

```python
asyncio.run(agent.run(...))
```

因此 Stage A 必须避免在已经运行的 asyncio event loop 里直接调用它。

首版规定：

```text
single process
single dispatcher
blocking Telegram long polling
serial Agent execution
```

逻辑：

```text
getUpdates
   ↓
handle one inbound event
   ↓
execute_run()
   ↓
return TerminalRun / PausedRun
   ↓
send response
   ↓
continue polling
```

Agent 执行期间 Telegram update 留在 Telegram 服务端。

v0.3 不支持：

```text
mid-run interrupt
parallel conversations
background runs
```

这是有意的约束。

---

# 15. Telegram Adapter

文件：

```text
src/zuaef_agent/gateway/telegram.py
```

不得引入大型 Bot SDK。

当前 repo 已依赖：

```text
httpx
```

Stage A 直接使用 Telegram Bot HTTP API。

实现：

```text
getUpdates
sendMessage
editMessageText if needed
answerCallbackQuery
getFile
sendDocument
```

---

# 16. Telegram Configuration

环境变量：

```text
ZUAEF_TELEGRAM_BOT_TOKEN
ZUAEF_TELEGRAM_ALLOWED_USERS
```

其中：

```text
ZUAEF_TELEGRAM_ALLOWED_USERS=12345,67890
```

Stage A：

```text
allowlist mandatory
```

如果 allowlist 为空：

```text
gateway start MUST fail closed
```

不要默认 allow all。

可选：

```text
ZUAEF_TELEGRAM_POLL_TIMEOUT=30
ZUAEF_GATEWAY_APPROVAL_TTL=86400
ZUAEF_GATEWAY_MAX_UPLOAD_BYTES=20971520
ZUAEF_GATEWAY_MAX_ARTIFACT_BYTES=10485760
```

---

# 17. Telegram Token Handling

Bot token：

```text
never enter:
profile
CompositionSnapshot
RunReceipt
PauseReceipt
logs
Telegram response
```

所有 error rendering 必须 redact URL 中：

```text
/bot<TOKEN>/
```

---

# 18. Telegram Stage A Chat Scope

只支持：

```text
private chat
```

Group / supergroup：

```text
ignore or return:
"Group chats are not enabled in this gateway build."
```

不要在 Stage A 实现：

```text
mentions
topics
group roles
thread routing
```

模型已经保留 `thread_id` 接口用于 Stage B/C。

---

# 19. Telegram Document Upload

Stage A 应支持文档，因为 Budget 能力需要真实文件输入。

收到：

```text
message.document
```

执行：

```text
getFile
→ download file
→ workspace/inbox/telegram/
```

目标文件命名：

```text
workspace/inbox/telegram/
    <uuid>-<sanitized-original-name>
```

必须：

```python
Path(original_name).name
```

不得信任用户文件路径。

拒绝：

```text
size > ZUAEF_GATEWAY_MAX_UPLOAD_BYTES
```

`AttachmentRef.local_path`：

```text
inbox/telegram/...
```

---

# 20. Prompt Projection

Gateway 不负责业务理解。

Inbound：

```text
帮我分析这个预算
```

附带：

```text
budget.csv
```

转成 Agent prompt：

```text
帮我分析这个预算

Attached files available in the workspace:
- inbox/telegram/<uuid>-budget.csv
```

不要：

```text
自动总结附件
自动判断 domain
自动选择 tool
```

---

# 21. Profile Selection

Gateway startup 必须有：

```text
--profile
```

或 env：

```text
ZUAEF_GATEWAY_DEFAULT_PROFILE
```

例如：

```bash
zuaef-agent gateway start \
  --surface telegram \
  --profile wordpress-operator
```

---

## Session-level Profile

每个 SessionBinding 保存：

```text
profile
```

支持：

```text
/profile
/profile wordpress-operator
```

规则：

### no paused run

允许切换。

### paused run exists

禁止切换：

```text
A run is waiting for approval.
Approve, deny, or /new before changing profile.
```

理由：

> paused run 必须按照自己的 frozen CompositionSnapshot 恢复。

---

# 22. Profile Must Be Explicitly Validated

Gateway startup：

```python
resolve_profile(...)
```

先校验 default profile。

如果失败：

```text
process startup fails
```

不要等用户第一条消息才发现 plugin 不存在。

`/profile NAME`：

切换前也必须：

```python
resolve_profile(NAME, settings)
```

校验通过后才保存。

---

# 23. Shared Runtime Bridge

这是本版本最关键的代码抽取。

文件：

```text
src/zuaef_agent/gateway/bridge.py
```

但其中真正与 surface 无关的 continuation function 推荐放：

```text
src/zuaef_agent/continuation.py
```

优先方案：

```text
continuation.py
```

因为 CLI 与 Gateway 都需要使用。

---

# 24. 禁止复制 CLI Resume Logic

当前 CLI 已经包含：

```text
ReceiptStore.read
FileStepStore
continue_run
DeferredToolRequests
DeferredToolResults
ToolDenied
ToolFailed
build_profile_agent(snapshot=...)
execute_run(...)
```

必须从 CLI 抽成共享函数。

目标：

```python
def resume_paused_run(
    settings: AgentSettings,
    paused_run_id: str,
    *,
    decision: Literal["approve", "deny"],
    reason: str | None = None,
) -> RuntimeOutcome:
    ...
```

CLI：

```python
_resume(...)
```

改为调用：

```python
resume_paused_run(...)
```

Gateway 也调用同一个 function。

---

# 25. resume_paused_run Contract

执行顺序必须严格为：

```text
1. ReceiptStore.read(paused_run_id)

2. require state == paused

3. FileStepStore(settings.step_store_dir)

4. continue_run(store, run_id=paused_run_id)

5. reconstruct DeferredToolRequests

6. DeferredToolResults()

7. every pending approval:
      approve -> True
      deny -> ToolDenied(reason)

8. every pending call:
      ToolFailed("no external executor configured")

9. new continuation run_id

10. if PauseReceipt.composition:
       build_profile_agent(
           snapshot=receipt.composition
       )
    else:
       build_agent(...)

11. CoreDeps(new run_id)

12. execute_run(
       message_history=history,
       deferred_tool_results=results,
       prior_pause_receipt=receipt,
       conversation_id=receipt.conversation_id,
       composition=receipt.composition,
    )
```

不得重新加载：

```text
current session profile
mutable TOML profile
latest plugin versions
```

替代 frozen snapshot。

---

# 26. Approval Granularity

v0.3 采用：

> **pause-level batch approval**

即如果：

```text
PauseReceipt.pending_approvals
```

包含多个 approval：

Telegram 显示：

```text
3 actions require approval

1. ...
2. ...
3. ...

[Approve all]
[Deny all]
```

Approve：

```text
all approval calls = True
```

Deny：

```text
all = ToolDenied(...)
```

v0.3 不实现 per-tool-call approval UI。

不要为了 per-call approval 修改 runtime。

---

# 27. Gateway Bridge — New Run

Gateway Bridge 提供：

```python
def start_profile_run(
    *,
    settings: AgentSettings,
    profile: str | None,
    prompt: str,
    conversation_id: str,
) -> RuntimeOutcome:
```

内部：

```python
run_id = uuid4().hex

agent, snapshot = build_profile_agent(
    settings,
    run_id=run_id,
    profile=profile,
)

deps = CoreDeps(
    workspace_root=settings.workspace_root.resolve(),
    run_id=run_id,
)

return execute_run(
    agent,
    deps,
    prompt=prompt,
    settings=settings,
    run_id=run_id,
    conversation_id=conversation_id,
    composition=snapshot,
)
```

如果：

```text
profile=None
```

允许使用无 profile core agent。

但 Gateway production proof 必须使用 profile。

---

# 28. Gateway Service

文件：

```text
src/zuaef_agent/gateway/service.py
```

核心：

```python
class GatewayService:

    def handle(
        self,
        envelope: InboundEnvelope,
    ) -> None:
        ...
```

调用顺序：

```text
authorize
↓
get/create SessionBinding
↓
callback?
    yes → approval flow
↓
slash command?
    yes → command flow
↓
paused?
    yes → reject normal task
↓
start run
↓
TerminalRun / PausedRun
↓
persist binding
↓
render/send
```

---

# 29. Session Run Invariant

同一个 session：

```text
active_run_id != None
```

时不得启动第二 run。

Stage A 单线程基本天然满足，但仍然在数据层维护。

---

# 30. Normal Message While Paused

如果：

```text
paused_run_id != None
```

普通文本不得启动新 Agent run。

返回：

```text
This session is waiting for approval.

Use the buttons above, /approve, /deny, or /new.
```

防止出现：

```text
paused run A
+
new run B
+
user approval 不知道批准谁
```

---

# 31. `/new`

行为：

1. 如果存在 paused run：
   - 不自动 approve。
   - 不继续。
2. 作废所有该 paused run 的 pending approval tokens。
3. 清除：
   ```text
   active_run_id
   paused_run_id
   last_terminal_run_id
   ```
4. 新建：
   ```text
   conversation_id
   ```
5. profile 保持不变。

返回：

```text
New ZUAEF conversation started.
Profile: ...
```

注意：

`/new` 不需要篡改 PauseReceipt。

旧 pause receipt 保留作为历史证据。

---

# 32. Required Commands

Stage A 只实现：

```text
/help
/new
/profile
/status
/approve
/deny
/artifacts
```

禁止 command explosion。

---

# 33. `/help`

显示：

```text
ZUAEF

Send a task normally.

Commands:
/new
/profile [name]
/status
/approve
/deny
/artifacts
/help
```

---

# 34. `/profile`

无参数：

```text
Current profile: wordpress-operator
```

可附：

```text
Available profiles:
...
```

列表使用现有：

```python
list_profiles(...)
```

有参数：

```text
/profile ace-writing
```

先 resolve，再保存。

---

# 35. `/status`

必须完全 host-grounded。

不得让 LLM 生成 status。

状态：

```text
READY
RUNNING
PAUSED
LAST COMPLETED
LAST PARTIAL
LAST BLOCKED
```

例如：

```text
ZUAEF

Profile: wordpress-operator
Conversation: 84f31c...

State: PAUSED
Run: a18e4...
Pending approvals: 1

Tool:
wordpress_publish_post
```

---

# 36. `/approve`

若当前 session 没 paused run：

```text
Nothing is awaiting approval.
```

如果存在：

调用：

```python
resume_paused_run(..., decision="approve")
```

和按钮语义完全一样。

---

# 37. `/deny`

同理：

```python
decision="deny"
```

默认 reason：

```text
denied by operator from gateway
```

---

# 38. `/artifacts`

读取：

```text
last_terminal_run_id
```

对应：

```text
RunReceipt.verified_artifacts
```

只能展示：

```text
host-verified artifacts
```

不得展示 model claimed but unverified artifact。

---

# 39. Artifact Delivery

如果 verified artifact：

```text
size <= ZUAEF_GATEWAY_MAX_ARTIFACT_BYTES
```

并且文件仍存在、路径仍在 workspace 内：

允许：

```text
sendDocument
```

否则：

```text
send path + size
```

不能读取任意绝对路径。

---

# 40. Renderer

文件：

```text
src/zuaef_agent/gateway/renderer.py
```

必须是 deterministic renderer。

禁止 LLM。

接口：

```python
render_terminal(...)
render_pause(...)
render_status(...)
render_error(...)
render_profile(...)
```

---

# 41. Terminal Result Rendering

TerminalRun：

```text
✅ Completed
```

或：

```text
⚠️ Partial
```

或：

```text
⛔ Blocked
```

随后：

```text
outcome
verified artifact count
verified effect count
run_id
```

不要把整份 receipt JSON 发到聊天。

---

# 42. Pause Rendering

必须显示：

```text
⚠️ Approval required
```

至少：

```text
run_id
pending approval count
tool_name
sanitized argument preview
```

例如：

```text
⚠️ Approval required

Action:
wordpress_publish_post

Arguments:
post_id: 123

Run:
7f31...

[Approve]
[Deny]
```

---

# 43. Approval Argument Redaction

Generic argument preview 必须 redact key 名匹配：

```text
token
secret
password
passwd
api_key
apikey
authorization
auth
cookie
credential
```

值替换：

```text
***REDACTED***
```

preview 最大：

```text
1200 characters
```

超出截断。

---

# 44. Telegram Message Length

Renderer 输出必须 chunk。

建议：

```text
max chunk = 3800 characters
```

不要碰 Telegram 硬边界。

---

# 45. WordPress Plugin

新增：

```text
plugins/zuaef-wordpress/
```

必须沿用现有 Plugin Composition Layer。

---

# 46. WordPress Plugin Packaging

`plugins/zuaef-wordpress/pyproject.toml`

结构：

```toml
[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[project]
name = "zuaef-wordpress"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
  "httpx>=0.28",
  "pydantic-ai>=2.27,<3",
]

[project.entry-points."zuaef.plugins"]
wordpress = "zuaef_wordpress:create_plugin"

[tool.hatch.build.targets.wheel]
packages = ["zuaef_wordpress"]
```

不得让主 core import：

```text
zuaef_wordpress
```

---

# 47. WordPress Plugin Config

Profile 只允许 non-secret config。

例如：

```toml
schema_version = "1"
name = "wordpress-operator"

[[plugins]]
id = "wordpress"

[plugins.config]
site_url = "https://example.com"
site_label = "production"
```

Credential 不允许进入：

```text
profile
snapshot
receipt
```

使用：

```text
ZUAEF_WORDPRESS_USERNAME
ZUAEF_WORDPRESS_APP_PASSWORD
```

---

# 48. WordPress Client

`client.py`：

```python
class WordPressClient:
    ...
```

使用：

```text
WordPress REST API
/wp-json/wp/v2
```

认证：

```python
httpx.BasicAuth(
    username,
    application_password,
)
```

Request timeout：

```text
20 seconds
```

返回值必须 bounded。

不要把完整 WordPress REST payload 原样返给模型。

---

# 49. WordPress Tool Surface v0.3

只做：

```text
wordpress_get_post
wordpress_create_draft
wordpress_update_post
wordpress_publish_post
```

不要做：

```text
delete
users
plugins
themes
settings
WooCommerce
media bulk sync
```

---

# 50. wordpress_get_post

Effect：

```text
observe
```

输入：

```python
post_id: int
```

输出：

```json
{
  "id": 123,
  "status": "draft",
  "slug": "...",
  "link": "...",
  "title": "...",
  "modified": "..."
}
```

不要默认返回全文 HTML。

---

# 51. wordpress_create_draft

输入：

```python
title: str
content: str
excerpt: str | None = None
```

固定：

```text
status = draft
```

Effect：

```text
external_write
```

因此：

```python
requires_approval=requires_approval(
    EffectClass.EXTERNAL_WRITE
)
```

即使是 draft，也是远程系统写入。

---

# 52. wordpress_update_post

Effect：

```text
external_write
```

所有远程修改必须 approval。

---

# 53. wordpress_publish_post

输入：

```python
post_id: int
```

执行：

```http
POST /wp-json/wp/v2/posts/{id}
{
  "status": "publish"
}
```

Effect：

```text
external_write
```

必须 native approval。

这是 Stage A 最终真实 Gate proof。

---

# 54. WordPress Error Handling

HTTP：

```text
401
403
404
409
429
5xx
timeout
network error
```

必须 fail loud。

不得返回：

```text
"success"
```

除非真实响应支持。

不得 fabricated link。

---

# 55. WordPress Response Bounding

写操作返回：

```json
{
  "id": 123,
  "status": "publish",
  "link": "...",
  "modified": "..."
}
```

不要返回：

```text
full rendered content
embedded objects
headers
cookies
credentials
```

---

# 56. Plugin Factory

`zuaef_wordpress/__init__.py`

实现：

```python
def create_plugin(
    env: PluginEnv,
    config: dict,
) -> PluginBundle:
    ...
```

返回：

```python
PluginBundle(
    toolsets=[wordpress_toolset],
)
```

v0.3 不需要 Capability。

v0.3 不需要 Skill，除非真实运行证明 Agent 无法正确使用四个简单 tool。

不要为了“完整”先添加 Skill。

---

# 57. WordPress Profile

新增：

```text
profiles/wordpress-operator.toml
```

只启用：

```text
wordpress
```

先证明纯 domain adapter。

不要一开始组合 ACE Writing。

---

# 58. Composite Content Profile — Deferred

当 WordPress proof PASS 后，才允许新增：

```text
profiles/content-operator.toml
```

类似：

```toml
[[plugins]]
id = "ace-writing"

[[plugins]]
id = "wordpress"
```

它用于：

```text
材料
→ 写作
→ artifact
→ WordPress draft/publish
```

但不作为 Gate PASS 的前置条件。

---

# 59. Gateway CLI

修改：

```text
src/zuaef_agent/cli.py
```

新增：

```text
gateway
```

子命令。

---

# 60. CLI Contract

```bash
zuaef-agent gateway start \
  --surface telegram \
  --profile wordpress-operator
```

可选：

```text
--workspace
--model
--config-root
```

---

Stage A 不实现：

```text
gateway daemon
gateway stop
gateway restart
PID manager
systemd installer
```

`gateway start`：

```text
foreground blocking process
```

即可。

---

# 61. Startup Validation

启动前按顺序：

```text
settings validation
gateway DB init
profile resolve
Telegram token present
allowed users present
Telegram getMe probe
```

任一失败：

```text
exit non-zero
```

且不得进入 polling。

---

# 62. Gateway Loop

伪代码：

```python
def run_gateway(...):

    while True:

        events = surface.poll_once(
            timeout_seconds=poll_timeout
        )

        for event in events:
            service.handle(event)

        persist latest surface cursor
```

处理：

```text
KeyboardInterrupt
```

正常关闭。

---

# 63. Telegram Offset Rule

对 update：

```text
update_id=N
```

处理完成后保存：

```text
cursor=N+1
```

如果 process 在“处理前”崩溃：

允许重收。

如果 process 在“处理后、保存 cursor 前”崩溃：

可能重收。

因此 Gateway Service 必须使：

```text
approval token consumption
```

幂等。

普通业务消息 Stage A 不承诺 exactly-once。

但是必须尽量避免 external side effect duplication，因为 external write 本身需要 approval。

---

# 64. Approval Idempotency

同一个 approval token：

第一次：

```text
pending → approved
```

第二次点击：

```text
already consumed
```

不得再次：

```text
resume
```

---

# 65. Process Restart Recovery

Gateway startup 扫描 SessionBinding。

如果：

```text
paused_run_id
```

存在：

读取 ReceiptStore。

### receipt == PauseReceipt

保留 paused。

重新生成 approval token 或恢复已有 pending token。

向用户下一次 `/status` 显示：

```text
PAUSED
```

### receipt terminal

清除：

```text
paused_run_id
```

### receipt missing

清除：

```text
active_run_id
paused_run_id
```

记录 deterministic warning：

```text
routing state referenced a run without a receipt
```

不得 fabricated terminal status。

---

# 66. Active Run Crash Recovery

Stage A Agent 执行是同步的。

如果整个 process 在运行时硬崩溃：

Gateway DB 可能留下：

```text
active_run_id
```

重启后：

1. 查 ReceiptStore。
2. terminal → settle binding。
3. paused → paused binding。
4. no receipt → clear active_run_id。

不要构建第二套 crash replay。

---

# 67. Authorization

Stage A：

```text
Telegram user ID allowlist
```

不是 username。

用户名可变，不可信。

如果 unauthorized：

```text
ignore
```

或返回：

```text
Unauthorized
```

但 log 不得输出 bot token。

---

# 68. Authentication vs Approval

必须保持：

```text
Telegram allowlist
```

解决：

```text
who may interact
```

PydanticAI approval 解决：

```text
whether this model-proposed side effect is authorized
```

两者不得合并。

---

# 69. No Model Authorization

以下全部禁止：

```text
model says user approved
model sees "yes"
model infers approval
model decides action is safe
```

只有：

```text
Gateway validated callback
→ DeferredToolResults approval
```

才算 authorization。

---

# 70. User Message “yes” Is Not Approval

如果 paused：

用户输入普通：

```text
yes
可以
好的
执行
```

不得解释成 approval。

必须：

```text
button
/approve
```

显式操作。

---

# 71. Logging

允许使用 stdlib：

```python
logging
```

Stage A 不引入 observability platform。

至少记录：

```text
gateway started
surface connected
authorized inbound
profile
conversation_id
run_id
terminal state
paused state
approval consumed
resume run id
```

不得记录：

```text
bot token
WordPress password
full authorization headers
cookies
full sensitive tool args
```

---

# 72. Test Strategy

所有外部网络测试默认 mock。

真实 Telegram / WordPress proof 单独运行。

Unit tests 不依赖：

```text
internet
real API keys
real Telegram
real WordPress
```

---

# 73. test_gateway_models.py

覆盖：

```text
InboundEnvelope validation
AttachmentRef validation
thread_id normalization assumptions
ApprovalBinding states
```

---

# 74. test_gateway_store.py

至少：

```text
create/get session
same chat gets same conversation_id
/new creates new conversation_id
profile persists
cursor persists
approval token raw value not stored
approval resolve works
expired token rejected
consumed token cannot consume twice
different user cannot use token
```

---

# 75. test_gateway_telegram.py

mock `httpx`.

覆盖：

```text
getUpdates normalization
text message
document metadata
callback query
sendMessage
sendDocument
send approval keyboard
cursor behavior
token redaction
unauthorized user
```

---

# 76. test_gateway_bridge.py

使用：

```text
FunctionModel / TestModel
```

覆盖：

### new run

```text
build_profile_agent
execute_run
conversation_id propagated
composition propagated
```

### paused resume

验证：

```text
PauseReceipt read
history loaded
approve → True
deny → ToolDenied
new continuation run_id
same conversation_id
prior_pause_receipt propagated
frozen composition used
```

---

# 77. CLI Regression Test

现有：

```text
resume --approve
resume --deny
```

行为必须保持。

加入测试证明 CLI 已改为调用共享：

```text
resume_paused_run
```

而不是另写一套。

---

# 78. test_gateway_service.py

至少：

```text
normal message starts run
terminal updates last_terminal_run_id
paused sets paused_run_id
paused creates approval token
normal message while paused rejected
approve resumes
deny resumes
duplicate approval rejected
/new invalidates current interactive gate
/profile forbidden while paused
/status never calls model
/artifacts uses verified artifacts only
```

---

# 79. test_wordpress_plugin.py

mock WordPress REST。

覆盖：

```text
factory returns PluginBundle
tool names exact
get_post observe
create_draft external_write approval
update external_write approval
publish external_write approval
credentials absent fails loud
HTTP error fails loud
response bounded
secrets not returned
```

---

# 80. Static Architecture Tests

新增防回归测试。

例如读取 source 验证：

Gateway 不得定义：

```text
class Agent
class ApprovalEngine
class Workflow
```

更可靠的是 behavioral test。

必须至少证明：

```text
Gateway uses execute_run
Gateway resume uses shared continuation
WordPress uses zuaef.plugins
```

---

# 81. Existing Tests Must Stay Green

最终：

```bash
uv run pytest -q
uv run ruff check .
```

必须全部 PASS。

不得：

```text
xfail
skip
delete test
relax assertion
```

来换 PASS。

---

# 82. Manifest

仓库存在：

```text
BUILD_MANIFEST.json
```

完成改动后运行：

```bash
uv run python tools/regen_manifest.py
```

然后：

```bash
uv run pytest -q
```

必须通过 manifest integrity test。

---

# 83. Stage Breakdown

实现严格按以下 Stage。

---

# Stage 0 — Freeze Baseline

Tasks：

```text
T0001 baseline tests
T0002 baseline ruff
T0003 record HEAD
T0004 inspect current resume path
T0005 inspect current plugin pattern
```

Acceptance：

```text
zero functional changes
baseline recorded
```

---

# Stage 1 — Shared Continuation Seam

Tasks：

```text
T0101 create continuation.py
T0102 extract CLI resume orchestration
T0103 CLI delegates to shared function
T0104 preserve CLI exit behavior
T0105 add continuation tests
```

Gate：

```text
existing CLI resume tests PASS
new continuation tests PASS
```

不通过不得继续 Gateway。

---

# Stage 2 — Gateway Models + Store

Tasks：

```text
T0201 gateway/models.py
T0202 gateway/store.py
T0203 SQLite schema
T0204 session CRUD
T0205 cursor
T0206 opaque approval tokens
T0207 TTL
T0208 idempotent consume
```

Gate：

```text
all store tests PASS
```

---

# Stage 3 — Surface Contract + Telegram Transport

Tasks：

```text
T0301 surface.py
T0302 telegram.py
T0303 getUpdates
T0304 sendMessage
T0305 callbacks
T0306 inline approval buttons
T0307 document upload
T0308 artifact sendDocument
T0309 allowlist
T0310 redaction
```

Gate：

```text
all Telegram transport tests PASS
zero model dependency
```

---

# Stage 4 — Gateway Runtime Bridge

Tasks：

```text
T0401 start_profile_run
T0402 resume bridge
T0403 prompt attachment projection
T0404 profile validation
```

Gate：

```text
FunctionModel run PASS
PausedRun → Approve → TerminalRun PASS
PausedRun → Deny → terminal/blocked semantics PASS
```

---

# Stage 5 — Gateway Service

Tasks：

```text
T0501 dispatcher
T0502 session lifecycle
T0503 /help
T0504 /new
T0505 /profile
T0506 /status
T0507 /approve
T0508 /deny
T0509 /artifacts
T0510 terminal renderer
T0511 pause renderer
```

Gate：

完整 mocked flow：

```text
message
→ paused
→ approval button
→ resume
→ terminal
```

PASS。

---

# Stage 6 — Gateway CLI

Tasks：

```text
T0601 gateway parser
T0602 gateway start
T0603 startup validation
T0604 foreground polling
T0605 KeyboardInterrupt shutdown
```

Gate：

```text
CLI parser tests PASS
invalid config fail closed
```

---

# Stage 7 — WordPress Plugin

Tasks：

```text
T0701 plugin package
T0702 WordPressClient
T0703 get_post
T0704 create_draft
T0705 update_post
T0706 publish_post
T0707 effect classification
T0708 profile
T0709 plugin tests
```

Gate：

```text
profile check PASS
tool conflict check PASS
native approval test PASS
```

---

# Stage 8 — Local End-to-End Proof

使用 mocked Telegram + mocked WordPress，但真实：

```text
ZUAEF runtime
profile composition
PydanticAI approval
PauseReceipt
resume
RunReceipt
```

完整路径：

```text
Telegram InboundEnvelope
↓
GatewayService
↓
wordpress profile
↓
Agent
↓
wordpress_publish_post
↓
PausedRun
↓
approval token
↓
Approve callback
↓
resume_paused_run
↓
WordPress tool completes
↓
RunReceipt
```

必须断言：

```text
continued_from_run_id == paused run
conversation_id unchanged
composition_id unchanged
verified_tool_effects contains publish call
terminal status valid
```

---

# Stage 9 — Real Telegram Proof

使用真实 Telegram Bot。

Proof：

```text
phone Telegram
↓
send task
↓
real ZUAEF
↓
PausedRun
↓
Approve button appears
```

这里 WordPress 可以先用 test endpoint。

必须保留：

```text
run_id
pause receipt
screenshots optional
logs redacted
```

---

# Stage 10 — Real WordPress Proof

这是 v0.3 最终 Gate。

准备一个：

```text
test WordPress site
```

以及一个：

```text
existing draft post
```

Telegram：

```text
Publish WordPress draft <ID>.
```

预期：

```text
Agent proposes wordpress_publish_post
↓
native approval pauses
↓
Telegram approval card
↓
human taps Approve
↓
resume from frozen composition
↓
WordPress REST write
↓
status=publish
↓
verified tool effect
↓
RunReceipt completed/partial with valid evidence
↓
Telegram final response
```

---

# 84. Final Acceptance Gate — GW-1..GW-12

全部必须 PASS。

## GW-1 — Surface

真实 Telegram message 到达 Gateway。

---

## GW-2 — Composition

任务通过：

```text
build_profile_agent
```

加载：

```text
wordpress
```

不得手工 import toolset。

---

## GW-3 — Runtime

任务真实经过：

```text
execute_run()
```

---

## GW-4 — Pause

`wordpress_publish_post` 产生真实：

```text
PausedRun
PauseReceipt
```

---

## GW-5 — UI

Telegram 显示：

```text
Approve
Deny
```

---

## GW-6 — Security

随机伪造 token：

```text
cannot approve
```

另一个 user：

```text
cannot approve
```

重复按钮：

```text
cannot resume twice
```

---

## GW-7 — Resume

Approve：

```text
resume_paused_run
```

恢复原 paused history。

---

## GW-8 — Frozen Composition

continuation：

```text
composition_id
```

与 PauseReceipt 一致。

不得重新读取 mutable profile 作为 authority。

---

## GW-9 — External Effect

真实 WordPress：

```text
status changes to publish
```

---

## GW-10 — Verification

最终 receipt：

```text
verified_tool_effects
```

包含完成的 WordPress effect。

---

## GW-11 — Existing Core

全部旧测试 PASS。

---

## GW-12 — No Second Runtime

代码审查确认没有：

```text
Gateway Agent
ApprovalEngine
GatewayReceipt
WorkflowRuntime
EventBus
```

---

# 85. Machine-readable Proof Record

新增：

```text
spec/interactive-gateway-gate.md
```

记录真实 proof：

```text
date:
commit:
model:
surface:
profile:
plugin:
plugin_version:

initial_run:
pause_receipt:
conversation_id:
composition_id:

approval:
continuation_run:

wordpress_post_id:
wordpress_before_status:
wordpress_after_status:

verified_effect:
terminal_status:

tests:
ruff:

GW-1: PASS
GW-2: PASS
...
GW-12: PASS
```

Unknown 必须显式写。

---

# 86. Definition of Done

只有同时满足：

```text
tests green
ruff green
manifest green
real Telegram gate proven
real WordPress write proven
receipt verified
composition frozen
approval secured
README updated
SPEC proof recorded
```

才能声明：

```text
ZUAEF Interactive Business Gateway v0.3 PASS
```

不能因为：

```text
Telegram bot replies
```

就宣布 PASS。

也不能因为：

```text
WordPress API works
```

就宣布 PASS。

核心 proof 是：

```text
Surface
→ Composition
→ Runtime
→ Native Approval
→ Human Gate
→ Resume
→ External Effect
→ Host Verification
```

整条链。

---

# 87. README Update

最终 README Architecture 更新为：

```text
User Surfaces
CLI / Telegram
       |
       v
Surface Gateway
       |
       v
Profile Composition
       |
       v
one PydanticAI Agent
       |
       v
Toolsets / Skills / Capabilities
       |
       v
Pause / Resume / Verification
       |
       v
Artifacts + Knowledge + Receipts
```

明确写：

> Gateway does not own an agent loop. It translates external interaction into the same ZUAEF runtime used by the CLI.

---

# 88. AGENTS.md Update

只在 proof PASS 后补充一条：

```text
Surface/Gateway is an external interaction layer.
It may own transport, authorization, session bindings and approval presentation,
but must not implement agent execution, business policy, approval semantics,
durable execution truth or receipts.
```

不要大规模改写 AGENTS.md。

---

# 89. Feishu Stage B

v0.3 Stage A PASS 后再开始。

目标：

```text
Feishu message
→ same InboundEnvelope
→ same GatewayService
→ same bridge
→ same approval semantics
```

允许 Feishu adapter 内部采用：

```text
WebSocket
```

但 Gateway Service API 不应改变。

Feishu 至少实现：

```text
text inbound
text outbound
interactive approval card
document inbound
artifact outbound
```

---

# 90. Feishu Architecture Gate

加入 Feishu 时：

如果必须修改：

```text
execute_run
resume_paused_run semantics
Plugin API
WordPress plugin
approval token semantics
GatewayService main dispatch semantics
```

则：

```text
Surface abstraction FAIL
```

先修抽象，再加平台。

---

# 91. `zuaef.surfaces` Entry Points — Deferred

只有：

```text
Telegram PASS
+
Feishu PASS
```

之后，才能讨论：

```toml
[project.entry-points."zuaef.surfaces"]
telegram = "..."
feishu = "..."
```

原因：

> 一个实现不足以证明稳定 extension contract。

遵守 ZUAEF elevation rule：

```text
reuse twice is signal
not automatic abstraction
```

---

# 92. Slack / WeCom / WeChat

全部 deferred。

优先级建议：

```text
A Telegram
B Feishu
C Slack
D WeCom
E personal WeChat
```

个人微信不得为了兼容 unofficial transport 污染 Gateway 通用协议。

---

# 93. Platform Product Model

技术层：

```text
Plugin
```

用户不应直接面对。

产品层暴露：

```text
Profile
```

未来示例：

```text
Writing
Client Service
Budget Analyst
WordPress Operator
Content Operator
Hardware Scout
```

Surface 只选择：

```text
profile
```

而不直接选择 Toolset。

---

# 94. Future Composite Profiles

平台 proof 完成后：

```text
content-operator
├── ace-writing
└── wordpress

client-service
├── negotiation
└── customer-state

finance
└── budget
```

仍然：

```text
one Agent
```

不是：

```text
writing agent
negotiation agent
budget agent
wordpress agent
```

---

# 95. Prohibited Implementations

Coding Agent 若准备加入以下内容，必须停止。

```text
class TelegramAgent
class WordPressAgent
class GatewayAgent
class ApprovalEngine
class GatewayWorkflow
class BusinessRouterAgent
class AgentRegistry
class EventBus
class TaskGraph
class GatewayReceipt
```

同样禁止：

```text
Telegram approval directly calls WordPress API
```

正确：

```text
Telegram approval
→ DeferredToolResults
→ ZUAEF resume
→ WordPress Tool
```

---

# 96. 禁止 Surface 绕过 Plugin Composition

禁止：

```python
from zuaef_wordpress import wordpress_toolset
```

出现在 Gateway。

正确：

```python
build_profile_agent(
    profile=session.profile,
)
```

---

# 97. 禁止复制 Execution State

Gateway SQLite 不得保存：

```text
message_history
tool calls
model outputs
full receipts
artifact contents
knowledge contents
```

如果 restart 需要恢复 run：

```text
ReceiptStore
+
StepPersistence
```

才是 authority。

---

# 98. General Multi-turn Chat — Explicitly Deferred

v0.3 不建立新的通用 conversation-history store。

原因：

当前需要证明的是：

```text
business execution gate
```

不是复制 Hermes 完整 chat runtime。

保证：

```text
pause → resume
```

拥有真实上下文连续性。

普通：

```text
terminal run A
→ user second message
→ terminal run B
```

不承诺自动携带完整 A message history。

如果 client-service 真实案例证明需要，再单独设计：

```text
Terminal Conversation Continuation
```

并优先研究能否复用 Harness persistence，而不是 Gateway 自建 message DB。

---

# 99. Stage A Success Interpretation

Stage A 成功意味着：

ZUAEF 已经证明：

```text
可从移动聊天入口接收真实业务命令
可组合真实业务能力
可暂停高风险操作
可让人在手机审批
可恢复原 Agent trajectory
可对真实外部系统执行
可对执行结果留下机器可核验 receipt
```

这就是：

```text
Interactive Business Agent Platform
```

的最小可信闭环。

---

# 100. Coding Agent Execution Rule

Coding Agent 应：

1. 阅读：
   ```text
   AGENTS.md
   README.md
   runtime.py
   cli.py
   composition.py
   models.py
   plugin_api.py
   tests/test_execute_run_seam.py
   tests/test_plugin_composition.py
   ```
2. 跑 baseline。
3. Stage-by-Stage 实现。
4. 每个 Stage 先测试再继续。
5. 不做“顺手重构”。
6. 不新增 SPEC 未要求的 subsystem。
7. 如果现有 API 可以复用，必须复用。
8. 如果必须修改 core invariant，停止并记录 blocker。
9. 真实外部 write 永远使用 native approval。
10. 最终必须实际跑 Telegram + WordPress proof。

---

# 101. Final Reference Flow

最终生产路径必须等价于：

```text
Telegram
    |
    | "Publish draft 123"
    v
TelegramAdapter
    |
    v
InboundEnvelope
    |
    v
GatewayService
    |
    +--> Authorization
    |
    +--> SessionBinding
    |
    +--> profile = wordpress-operator
    |
    v
build_profile_agent()
    |
    v
wordpress plugin
    |
    v
execute_run()
    |
    | model proposes wordpress_publish_post(123)
    |
    v
PydanticAI native approval
    |
    v
PausedRun
    |
    v
PauseReceipt
    |
    v
Gateway Renderer
    |
    v
Telegram

┌────────────────────────────┐
│ Approval required          │
│ wordpress_publish_post     │
│ post_id: 123               │
│                            │
│ [Approve]      [Deny]      │
└────────────────────────────┘

    |
    | Human taps Approve
    v
Opaque approval token
    |
    v
Gateway validation
    |
    v
resume_paused_run()
    |
    +--> PauseReceipt
    +--> StepPersistence history
    +--> Frozen CompositionSnapshot
    +--> DeferredToolResults=True
    |
    v
execute_run()
    |
    v
wordpress_publish_post()
    |
    v
WordPress REST API
    |
    v
Tool Effect completed
    |
    v
Host Verification
    |
    v
RunReceipt
    |
    v
Telegram

✅ Completed

WordPress post published.
Run: ...
Verified effects: 1
```

这条路径是 v0.3 的架构真北。

任何实现如果让路径变成：

```text
Telegram
→ custom bot agent
→ direct WordPress call
```

即使功能可用，也判：

```text
ARCHITECTURE FAIL
```

任何实现如果让路径变成：

```text
Telegram Approve
→ direct API call
```

同样：

```text
ARCHITECTURE FAIL
```

唯一接受：

```text
Surface
→ ZUAEF composition
→ ZUAEF runtime
→ native pause
→ human interaction
→ ZUAEF continuation
→ business tool
→ host verification
```

---

# 102. Stop Rule

本 SPEC 完成后停止。

不要继续自动增加：

```text
Feishu
Slack
WeCom
dashboard
cron
multi-agent
memory
workflow
```

先回答一个问题：

> **真实用户是否已经可以在 Telegram 上可靠地下达业务任务、看到 native approval、批准真实 WordPress external write，并从 receipt 证明执行确实发生？**

如果答案是：

```text
YES
```

v0.3 完成。

如果答案是：

```text
NO
```

继续修这一条 vertical slice，而不是增加功能。