# ZUAEF Plugin Composition Layer — SPEC v0.2

**Status:** Proposed  
**Baseline:** ZUAEF Agent Core v0.1.1 + Harness-neutral Context Delivery Proof PASS  
**Target:** v0.2.x  
**Scope:** 在现有 Thin Harness 上增加可安装、可组合、可追溯、可恢复的业务插件层。

---

## 0. 核心原则

> **Plugin 是交付与组合单位，不是第四种 Runtime Primitive。**

ZUAEF 现有运行时原语保持：

```text
Core
Capability
Toolset
Skill
```

Plugin 只负责把这些现有原语打包并显式组合：

```text
Plugin
├── Toolset(s)
├── Skill(s)
└── Capability(s)   # 例外，不是默认
```

最终必须降解为：

```python
build_agent(
    settings,
    run_id=run_id,
    extra_toolsets=[...],
    extra_capabilities=[...],
)
```

禁止引入：

```text
PluginRuntime
Plugin Agent Loop
Event Bus
Graph Runtime
Plugin State Machine
Plugin Durable Runtime
第二套 Approval Engine
第二套 Receipt/Event Store
```

`execute_run()` 继续作为唯一公共执行 seam。

---

# 1. 已冻结的架构约束

插件系统不得破坏以下既有原则。

### 1.1 单 Agent

业务插件不得引入：

```text
Agent Registry
one agent class per domain
plugin-owned Agent
```

仍然是一个 outcome-owning Agent。

### 1.2 Explicit Composition

```text
installed != enabled
discovered != activated
```

只有 profile 明确声明的插件才能进入某次运行。

### 1.3 Toolset First

新增业务域默认：

```text
Toolset
+
optional Skill
```

只有确实需要：

```text
tools
+ instructions
+ hooks
+ settings
+ lifecycle semantics
```

作为一个稳定可复用单元时，才考虑 Capability。

### 1.4 Core Domain-neutral

正常新增业务插件：

```text
core.py       0 business changes
runtime.py    0 business changes
```

### 1.5 Harness 继续拥有公共语义

插件不得重新实现：

```text
UsageLimits
ToolOutputLimits
StepPersistence
Approval
artifact verification
knowledge verification
RunReceipt
pause/resume
```

### 1.6 Runtime State Isolation

运行状态仍位于：

```text
.zuaef-state/
```

并继续位于 model-writable workspace 之外。

---

# 2. 当前缺口

ZUAEF 已经具备：

```python
extra_toolsets=[]
extra_capabilities=[]
```

因此**程序级插件 seam 已存在**。

当前缺少的是：

```text
包装
安装
识别
配置
启用
组合
版本记录
resume 重建
CLI 管理
```

换句话说，我们缺的不是新的 Agent 架构，而是：

> **Plugin Composition Layer**

---

# 3. 目标

## G1 — 独立 Python 包可成为业务插件

外部 Python distribution 能暴露 ZUAEF plugin factory。

## G2 — Profile 显式组合

例如：

```bash
zuaef-agent run --profile writing "..."
```

和：

```bash
zuaef-agent run --profile hardware "..."
```

使用同一个 Harness，加载不同业务组合。

## G3 — Plugin 不侵入 Core

第二、第三个业务域无需修改：

```text
core.py
runtime.py
```

## G4 — Composition 可审计

每次运行能够知道：

```text
加载了哪些 plugin
plugin version
entry point
profile
non-secret config
composition hash
```

## G5 — Resume-safe

暂停后的运行必须使用暂停时冻结的 plugin composition，而不是 resume 时重新读取已经变化的 profile。

## G6 — 用两个不相关业务域证明通用性

不能只用 ACE Writing 证明插件平台。

至少需要：

```text
ACE Writing
+
Hardware Scout / WordPress / WooCommerce
```

两个明显不同的 domain。

---

# 4. 非目标

v0.2 明确不做：

```text
Marketplace
Remote Registry
Cordis-style Plugin Tree
Event Bus
Generic Hook Bus
Middleware Framework
DI Container
Graph Runtime
Multi-agent Runtime
Hot Reload
Plugin Sandbox
Dependency Solver
Cross-language RPC Protocol
Generic Subprocess Plugin Protocol
Vector Database
Generic Source Router
```

这些只能由真实业务失败反向证明需要。

---

# 5. 分层模型

以后统一使用以下判断：

```text
CORE
│
│ cross-domain invariant
│
▼
CAPABILITY
│
│ reusable tools/instructions/hooks/settings bundle
│
▼
TOOLSET
│
│ domain actions + local policy
│
▼
SKILL
    deferred domain instructions / knowledge
```

Plugin 位于它们之外：

```text
             Plugin Package
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
     Toolset      Skill   Capability*
        │                     │
        └──────────┬──────────┘
                   ▼
              build_agent()
```

Plugin 本身不是 Agent 原语。

---

# 6. Python Plugin Contract

## 6.1 标准 Entry Point

插件使用 Python 标准 package metadata：

```toml
[project.entry-points."zuaef.plugins"]
ace-writing = "zuaef_ace_writing.plugin:create_plugin"
```

其中：

```text
ace-writing
```

为稳定 plugin id。

允许系统扫描 entry-point metadata 用于：

```text
plugin list
plugin inspect
profile check
```

但绝不因此自动启用。

---

# 7. Plugin Factory

标准 factory：

```python
def create_plugin(
    env: PluginEnv,
    config: Mapping[str, Any],
) -> PluginBundle:
    ...
```

Factory 不允许：

```text
创建自己的 Agent
执行 agent.run()
调用 execute_run()
修改全局 registry
patch ZUAEF core
import 时启动后台服务
composition 阶段产生 external side effect
```

---

# 8. PluginEnv

第一版保持极薄：

```python
@dataclass(frozen=True)
class PluginEnv:
    plugin_id: str
    plugin_version: str
    workspace_root: Path
    state_root: Path
```

禁止塞入：

```text
Agent instance
Model credentials
Secrets
Mutable runtime state
Generic Service Locator
Dependency Container
```

否则 PluginEnv 很容易演变成隐藏式 DI Runtime。

---

# 9. PluginBundle

v0.2 唯一允许的输出：

```python
@dataclass(frozen=True)
class PluginBundle:
    toolsets: Sequence[AbstractToolset[CoreDeps]] = ()
    skill_dirs: Sequence[Path] = ()
    capabilities: Sequence[AbstractCapability[CoreDeps]] = ()
```

明确禁止增加：

```python
hooks=[]
middleware=[]
events=[]
services=[]
background_tasks=[]
runtime_callbacks=[]
```

至少在 v0.2 不允许。

---

# 10. Capability Policy

插件默认权限：

```text
Toolset       ALLOW
Skill         ALLOW
Capability    DENY unless explicitly enabled
Core mutation DENY
```

Profile 中如确实允许：

```toml
[[plugins]]
id = "special-runtime-plugin"
allow_capabilities = true
```

否则 factory 一旦返回 Capability：

```text
composition FAIL
```

且必须在第一次模型请求前失败。

---

# 11. Profile

增加：

```text
ZUAEF_CONFIG_ROOT
```

默认：

```text
~/.config/zuaef/
```

Profile：

```text
~/.config/zuaef/profiles/
├── writing.toml
├── hardware.toml
└── commerce.toml
```

---

# 12. Profile Schema v1

Writing：

```toml
schema = 1
name = "writing"

[[plugins]]
id = "ace-writing"
allow_capabilities = false

[plugins.config]
ace_root = "/path/to/article-context-engine"
```

Hardware：

```toml
schema = 1
name = "hardware"

[[plugins]]
id = "hardware-scout"
allow_capabilities = false

[plugins.config]
market = "shenzhen"
```

---

# 13. Secret Policy

Profile 只能存：

```text
non-secret configuration
```

禁止：

```text
API key
password
access token
private key
credential
```

这些继续由：

```text
environment
provider credential mechanism
OS secret mechanism
```

负责。

Composition Snapshot / Receipt 绝不能落 secret value。

---

# 14. Plugin Resolution

给定：

```text
profile = writing
```

Loader 必须执行：

```text
1. Parse profile
2. Validate schema
3. Read explicit plugin ids
4. Resolve each id to exactly one zuaef.plugins entry point
5. Read distribution version
6. Import ONLY enabled plugin
7. Call factory
8. Validate PluginBundle
9. Reject unauthorized capabilities
10. Convert Skill dirs through existing Skills primitive
11. Collect Toolsets
12. Collect allowed Capabilities
13. Detect tool conflicts
14. Build Composition Snapshot
15. Call build_agent()
```

核心原则：

> **Installed-but-disabled plugin MUST NOT be imported into execution.**

---

# 15. Tool Conflict Policy

禁止：

```text
plugin A.tool = publish
plugin B.tool = publish
→ B silently overrides A
```

第一版必须：

```text
duplicate tool
→ composition process error
```

不要引入：

```text
priority
plugin ordering override
namespaced magic resolution
```

除非之后真实业务需要。

---

# 16. Composition Snapshot

增加：

```python
class PluginRef(BaseModel):
    id: str
    version: str
    entry_point: str
    config: dict[str, Any]
    capabilities_allowed: bool = False
```

以及：

```python
class CompositionSnapshot(BaseModel):
    schema_version: Literal["1"] = "1"

    profile: str | None
    plugins: list[PluginRef]

    composition_id: str
```

`composition_id`：

```text
SHA256(
  canonical serialized composition
)
```

以下变化必须改变 hash：

```text
plugin id
plugin version
entry point
non-secret config
plugin order
capability permission
```

---

# 17. Receipt Schema

建议：

```text
RunReceipt    1.1 → 1.2
PauseReceipt  1.1 → 1.2
```

增加：

```python
composition: CompositionSnapshot | None = None
```

无 Profile 的旧路径：

```python
composition = None
```

因此保持兼容。

这是允许修改跨域 receipt contract 的少数情况，因为：

> Plugin composition identity 是 resume 与 execution provenance 的一部分。

---

# 18. Resume Contract — P0

这是整套插件设计最重要的地方之一。

错误实现：

```text
run using profile A
↓
pause
↓
user changes profile A
↓
resume
↓
load NEW profile A
```

这是不允许的。

正确实现：

```text
RUN
│
├─ profile writing
│
├─ plugin ace-writing 0.2.1
│
└─ composition_id abc123
        │
        ▼
PauseReceipt
        │
        ▼
RESUME
        │
        ├─ read frozen CompositionSnapshot
        ├─ require ace-writing == 0.2.1
        ├─ require same entry point
        └─ use frozen config
```

Resume 必须：

```text
ignore mutable current profile
```

---

# 19. Resume Version Mismatch

如果 PauseReceipt 要求：

```text
ace-writing 0.2.1
```

但环境只有：

```text
ace-writing 0.2.2
```

则：

```text
PROCESS ERROR
before model request
```

禁止：

```text
自动升级
best effort
silent substitution
```

因为那已经不是同一 composition。

---

# 20. Composition API

新增：

```text
src/zuaef_agent/
├── plugin_api.py
├── profiles.py
└── composition.py
```

职责：

### `plugin_api.py`

```text
PluginEnv
PluginBundle
PluginRef
CompositionSnapshot
```

### `profiles.py`

```text
ProfileConfig
ProfilePluginConfig
TOML loading
schema validation
```

### `composition.py`

```text
entry point resolution
plugin factory loading
bundle validation
skill adaptation
tool conflict validation
composition snapshot
build_profile_agent()
```

---

# 21. Public Composition API

建议：

```python
def resolve_profile(
    name: str,
    settings: AgentSettings,
) -> CompositionSnapshot:
    ...
```

以及：

```python
def build_profile_agent(
    settings: AgentSettings,
    *,
    run_id: str,
    profile: str | None = None,
    snapshot: CompositionSnapshot | None = None,
):
    ...
```

规则：

### 新运行

```text
profile
→ resolve
→ freeze snapshot
→ compose
```

### Resume

```text
snapshot
→ exact resolve
→ compose
```

不得同时传：

```text
profile + snapshot
```

作为两套 authority。

---

# 22. 不复制 build_agent

`build_profile_agent()` 不允许复制：

```text
FileSystem
ToolOutputLimits
StepPersistence
Knowledge
Planning
Skills
```

这套 core composition。

只能：

```python
return build_agent(
    settings,
    run_id=run_id,
    extra_toolsets=toolsets,
    extra_capabilities=capabilities,
)
```

Plugin Composition Layer 不得形成第二个 core。

---

# 23. Skill Composition

Plugin Skill 必须继续通过现有 Harness `Skills` primitive。

不要：

```text
cat SKILL.md
append system prompt
plugin custom prompt injection
```

Plugin 只声明：

```python
skill_dirs=[...]
```

Composition Layer 负责将其映射到既有 Skills 机制。

如果当前 Skills primitive 不能接受多个 source dir：

> 应添加最小 adapter/composition helper。

不能因此再造 Skill Runtime。

---

# 24. CLI

现有：

```text
run
resume
```

扩展为：

```text
run
resume

plugin
profile
```

---

# 25. Run

新增：

```bash
zuaef-agent run \
  --profile writing \
  "完成这篇文章"
```

无：

```text
--profile
```

时必须保持当前行为。

这是 regression gate。

---

# 26. Resume

继续：

```bash
zuaef-agent resume <run_id> --approve
```

Resume 不接受：

```bash
--profile ...
```

来覆盖原 composition。

PauseReceipt 才是 authority。

---

# 27. Plugin Inspect CLI

v0.2 第一版：

```bash
zuaef-agent plugin list
zuaef-agent plugin inspect <id>
```

例如：

```text
$ zuaef-agent plugin list

ace-writing       0.2.0
hardware-scout    0.1.0
wordpress         0.1.3
```

这里表示：

```text
installed / discoverable
```

不是：

```text
enabled
```

---

# 28. Profile CLI

```bash
zuaef-agent profile list
zuaef-agent profile show writing
zuaef-agent profile check writing
```

其中：

```text
profile check
```

需要完整执行：

```text
resolve
factory loading
bundle validation
conflict detection
capability policy
snapshot generation
```

但：

```text
NO MODEL REQUEST
```

---

# 29. Enable / Disable

可增加：

```bash
zuaef-agent plugin enable ace-writing --profile writing
zuaef-agent plugin disable ace-writing --profile writing
```

它们只编辑 profile。

不要创建隐藏 global registry。

---

# 30. Plugin Add / Remove 延后

v0.2.0 **不要求**：

```bash
zuaef-agent plugin add
zuaef-agent plugin remove
```

先证明 composition contract。

证明后再考虑：

```bash
zuaef-agent plugin add ./foo
zuaef-agent plugin add git+...
```

但它只能是 Python packaging 的薄 wrapper。

禁止：

```text
ZUAEF Package Solver
ZUAEF Remote Registry Protocol
ZUAEF Marketplace Runtime
```

---

# 31. Failure Boundary

以下错误发生在 `execute_run()` 之前：

```text
invalid profile
plugin not installed
duplicate plugin id
factory import failure
invalid PluginBundle
unauthorized Capability
missing Skill
tool conflict
resume version mismatch
invalid config
```

全部：

```text
PROCESS ERROR
```

且：

```text
no RunReceipt
```

这与当前 pre-acceptance CLI/config error contract 保持一致。

进入：

```python
execute_run()
```

之后，才使用既有：

```text
completed
partial
blocked
paused
```

语义。

---

# 32. Trust Model

Python Plugin 本质上是：

> 被安装进同一 Python 环境的可执行代码。

所以：

```text
Plugin System != Security Sandbox
```

启用恶意 Python package 等价于信任本地代码。

插件系统保护的是：

```text
Agent action semantics
```

而不是：

```text
host process against malicious imports
```

Side-effect 工具仍然必须使用 native approval。

---

# 33. ACE Writing Plugin

现有：

```text
examples/writing_toolset.py
examples/writing_case.py
spec/writing-slice-gate.md
```

先保持不动。

它们已经是 proof evidence。

不要为了插件化立即移动或重构。

---

# 34. ACE Writing Plugin 化

Composition Layer 本身通过测试后，再创建：

```text
zuaef-ace-writing
```

它暴露：

```text
ace-writing
```

Plugin：

```text
ace-writing
│
├── BudgetedWritingToolset
│   ├── list_materials
│   ├── read_material
│   ├── retrieve_exemplars
│   ├── retrieve_knowledge
│   ├── check_claim
│   └── save_artifact
│
└── optional Skills
```

ACE 继续是外部 Context Engine。

不得复制：

```text
corpus selection
evidence validation
material validation
canonical artifact semantics
```

回 ZUAEF。

---

# 35. Writing Plugin Parity Gate

Plugin 版本必须重新跑原 proof。

需要证明：

```text
receipt completed
run-isolated deliveries
bounded retrieval
tool withdrawal
claim probe
canonical artifact
snapshot equality
machine-ready / complete
```

插件化不能降低现有 proof。

---

# 36. 第二 Vertical Slice

Plugin Layer 不允许因为：

```text
ace-writing works
```

就宣布完成。

第二个必须是不同业务域。

优先建议：

```text
Hardware Scout
```

或：

```text
WordPress / WooCommerce Operator
```

---

# 37. 第二 Slice 的硬性验收

第二个插件完成真实任务时：

```text
core.py          0 domain changes
runtime.py       0 domain changes
plugin_api.py    0 domain branches
composition.py   0 domain branches
profiles.py      0 domain branches
```

允许新增：

```text
plugin package
Toolsets
Skills
plugin config
tests
domain evidence adapter
```

---

# 38. Capability Promotion Rule

每次有人提出：

> “这个是不是应该升级 Capability？”

按以下顺序判断。

### Q1

是否只属于一个业务域 action surface？

```text
YES → Toolset
```

### Q2

两个以上不相关业务域是否真的需要同一机制？

```text
NO → Domain-local
YES → 尝试抽最小 reusable helper
```

### Q3

抽出来以后是否必须捆绑：

```text
tools
instructions
hooks/settings
lifecycle
```

？

```text
NO → Toolset wrapper/helper/library
YES → Capability
```

### Q4

是不是所有业务域都必须遵守？

```text
NO → Optional Capability
YES → 才考虑 Core
```

以下理由都不充分：

```text
代码多
用了两次
很重要
感觉像基础设施
以后可能用到
```

---

# 39. Testing — Static

必须测试：

```text
PluginBundle type validation
Capability fail-closed
profile schema
unknown fields
secret non-serialization
factory restrictions
architecture invariants
```

---

# 40. Testing — Resolver

必须覆盖：

```text
one id → one entry point
zero match → FAIL
duplicate id → FAIL
disabled installed plugin not imported
deterministic ordering
factory exception → pre-run FAIL
```

---

# 41. Testing — Composition

验证：

```text
Toolset → extra_toolsets
Capability → extra_capabilities
Skill → existing Skills
duplicate tools → FAIL
no-profile behavior unchanged
```

---

# 42. Testing — Receipt

必须证明：

```text
same composition → same composition_id

config change
→ different composition_id

plugin version change
→ different composition_id

entry point change
→ different composition_id
```

并验证：

```text
secret never appears in receipt JSON
```

---

# 43. Testing — Resume P0

测试：

```text
1. profile A 启动
2. run pause
3. 修改 profile A
4. resume
5. 必须使用 PauseReceipt snapshot
```

同时：

```text
missing required version
→ FAIL before model request
```

成功 resume 继续满足：

```text
new run_id
same conversation_id
continued_from_run_id populated
```

---

# 44. Real Integration Proof

至少完成：

### Proof A

```text
ACE Writing Plugin
```

真实模型运行。

### Proof B

```text
Unrelated Business Plugin
```

真实任务运行。

### Proof C

第二个或第三个插件必须包含：

```text
external_write
```

并真实走一次：

```text
native approval
→ pause
→ resume
→ receipt
```

---

# 45. 实施阶段

## Stage 0 — Freeze

冻结当前：

```text
writing proof
test baseline
ruff baseline
```

不顺手重构。

---

## Stage 1 — Plugin Contract

新增：

```text
plugin_api.py
profiles.py
composition.py
```

以及 fixture plugin tests。

**不做 installer。**

---

## Stage 2 — Composition Receipt

实现：

```text
CompositionSnapshot
composition_id
RunReceipt 1.2
PauseReceipt 1.2
```

---

## Stage 3 — Resume-safe Composition

修改 resume composition path：

```text
PauseReceipt snapshot
→ exact reconstruct
```

这是 P0。

---

## Stage 4 — CLI

增加：

```text
--profile
plugin list
plugin inspect
profile list
profile show
profile check
```

---

## Stage 5 — ACE Writing Plugin

把已验证 writing domain 通过 plugin contract 包装。

重新跑旧 proof。

---

## Stage 6 — 第二业务插件

建议：

```text
Hardware Scout
```

优先。

或者：

```text
WordPress/WooCommerce
```

---

## Stage 7 — Installer 决策

只有前面全部证明以后才判断是否需要：

```text
plugin add/remove
```

---

# 46. Plugin Composition Acceptance Gate

只有全部满足才可以宣布：

> `Plugin Composition Layer PROVEN`

---

## CAP-P1 — Installable Resolution

独立 Python distribution 可以暴露：

```text
zuaef.plugins
```

entry point，并被 profile 显式解析。

---

## CAP-P2 — No Implicit Activation

安装但没有写进 profile 的插件：

```text
NOT IMPORTED
NOT EXPOSED
```

---

## CAP-P3 — Primitive Reduction

Plugin 最终只降解到：

```text
Toolset
Skill
explicitly allowed Capability
```

没有 Plugin Runtime。

---

## CAP-P4 — Receipt-visible Composition

RunReceipt / PauseReceipt 能证明：

```text
plugin id
plugin version
entry point
config
composition_id
```

且不泄露 secret。

---

## CAP-P5 — Resume-safe

Paused run 使用冻结 composition 恢复。

Profile 后续变化不得影响它。

---

## CAP-P6 — Domain-neutral Core

ACE Writing + 第二业务域均运行成功，同时：

```text
core.py      无业务变更
runtime.py   无业务变更
```

---

## CAP-P7 — Shared Harness Semantics

插件运行继续复用：

```text
UsageLimits
ToolOutputLimits
StepPersistence
Native Approval
Verification
RunReceipt
```

没有 plugin-specific clone。

---

## CAP-P8 — Two Real Business Proofs

至少两个不相关真实业务插件完成真实任务。

其中至少一个完成：

```text
pause
approval
resume
receipt settlement
```

---

# 47. Stop Rule

CAP-P1 ~ CAP-P8 全部 PASS 后：

> **停止增加 Plugin Platform infrastructure。**

不要因为“别的平台都有”就增加：

```text
Marketplace
Event Bus
Graph Runtime
Plugin Tree
Hot Reload
Generic RPC
Automatic Activation
Cross-language Protocol
```

下一项基础设施必须由真实业务插件失败驱动。

---

# 48. 最终目标架构

```text
                         ZUAEF
                    Thin Agent Harness
                           │
                           ▼
                Plugin Composition Layer
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
     ACE Writing      Hardware Scout    WordPress
        Plugin            Plugin            Plugin
          │                │                │
    Toolset/Skill     Toolset/Skill     Toolset/Skill
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                     build_agent()
                           │
                           ▼
                  one PydanticAI Agent
                           │
                           ▼
                     execute_run()
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
       Persistence      Approval        Spill
            │              │              │
            └──────────────┼──────────────┘
                           ▼
                        Receipt
```

---

# 49. 最终架构不变量

项目是否真正成为“可插拔平台”，不看插件数量。

只看这一条：

> **Business capability can be installed and explicitly composed without becoming Harness architecture.**

换成人话：

> 新业务可以装进来，但不能因为每多一个业务，就让 ZUAEF Core 多长一层。