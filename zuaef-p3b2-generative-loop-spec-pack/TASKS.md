# TASKS — P3B-2 Generative Agent Loop Separation

Use these task IDs in commits, test names, and completion reporting where practical.

---

## T000 — Baseline and guardrails

- [ ] Record current HEAD and dirty state.
- [ ] Run baseline Ruff + full pytest.
- [ ] Record current test count.
- [ ] Confirm `uv.lock` pins PydanticAI 2.30.0 / Harness 0.20.0.
- [ ] Do not upgrade dependencies during this work.
- [ ] Add/confirm a small probe showing the pinned PydanticAI Agent supports natural string terminal output plus `DeferredToolRequests`.

**Acceptance**
- baseline is reproducible;
- no dependency upgrade;
- no custom loop proposed.

---

## T001 — Remove RunSummary from model terminal contract

### Code

- [ ] Change `build_agent()` output type from `RunSummary | DeferredToolRequests` to natural string + `DeferredToolRequests`.
- [ ] Remove all generic model instructions about creating a `RunSummary`.
- [ ] Update typing in composition/continuation seams as required.

### Tests

- [ ] Structural test: normal Agent model output surface has no `final_result` RunSummary schema.
- [ ] Approval path still exposes deferred-tool semantics.

**Acceptance**
- normal completion no longer requires structured settlement output;
- PydanticAI native loop remains unchanged.

---

**目前总体是顺的，而且 T000 做得对。**真正值得警惕的不是测试失败，而是 Commit A 会不会把架构修复做成一次“字段搬家”。

前半段是健康的：基线 `559 passed`、Ruff 绿，而且已经实测 **PydanticAI 2.30.0 原生支持 `str + DeferredToolRequests`**。这实际上证明了一个非常重要的事实：

> **不需要再造 result schema、final_result tool、adapter 或业务输出协议。**

这和你整个项目现在强调的方向一致：已有 upstream primitive 能解决的问题，不再引入 ZUAEF 自己的 generic abstraction。你上传的 Phase 2 SPEC 也明确要求 `generic ZUAEF framework +0`，只允许很小的产品 seam。 而且明确禁止继续增加新的 generic capability/framework 一类东西。

### 现在 Commit A 的正确部分

这几个动作我支持：

```text
Agent
output_type = str | DeferredToolRequests
```

模型正常完成任务：

```text
LLM → "这是改写后的文章……"
```

需要外部效果：

```text
LLM → DeferredToolRequests
```

Host 再判断：

```text
str
→ 正常完成
→ 呈现给当前 Supervisor

DeferredToolRequests
→ PausedRun
→ 审批
```

这才是真正的 agent loop。

尤其是：

> `RunSummary` 改成纯结算契约

这是对的。

**RunSummary 不应该再参与模型“写什么”。**

模型写文章、分析预算、给谈判建议，本来就是生成任务；`RunSummary` 只应该是 runtime 在模型完成以后生成的控制面信息。

---

## 但我现在会盯死一个地方：`TerminalRun.presentation`

这东西**暂时不能判错**，但它是目前最大的黄色警报。

因为存在两种完全不同的实现。

正确的是：

```text
LLM
 ↓
str
 ↓
TerminalRun.presentation   # 只是把原始 terminal text 带给 Gateway
 ↓
renderer
 ↓
用户
```

这里 `presentation` 只是一个**通用 transport slot**。

那没问题。

错误的是：

```text
LLM
 ↓
RunSummary.deliverable
 ↓
改成
 ↓
TerminalRun.presentation
 ↓
renderer
```

如果只是这样，实际上什么都没有修。

只是：

```text
deliverable → presentation
```

换了字段名字。

这就是你说的**字段补丁**。

---

# 我建议现在给 coding agent 加一条非常硬的验收原则

Commit A 完成以后，架构必须能够画成：

```text
                       ┌── str ───────────────→ Supervisor
Model generation ──────┤
                       └── DeferredToolRequests → approval/resume

                              ↓
                       Host settlement
                              ↓
                         RunSummary
```

而**绝对不能**是：

```text
Model
 ↓
business fields
 ↓
result schema
 ↓
RunSummary
 ↓
presentation
 ↓
Gateway
```

核心区别就一句话：

> **用户结果是模型输出；RunSummary 是模型输出之后的宿主结算。**

这两个必须彻底正交。

---

## 我甚至建议再严格一点

Commit A 最终代码最好只有三个概念：

```python
Agent output:
    str | DeferredToolRequests

TerminalRun:
    presentation: str | None
    summary: RunSummary
    # existing control-plane state only

RunSummary:
    status
    run/control metadata
    # NO deliverable
    # NO article
    # NO answer
    # NO business output
```

而且要加一个禁止清单：

```text
RunSummary.answer
RunSummary.content
RunSummary.message
RunSummary.article
RunSummary.result
RunSummary.deliverable
RunSummary.business_result
```

**一个都不要再出现。**

否则以后 Writing 来一个字段、Budget 来一个字段、Negotiation 来一个字段，很快又会回到：

```text
LLM 被宿主的数据模型牵着走
```

---

## `presentation` 本身也不要继续长

这一点尤其重要。

不要下一步变成：

```python
TerminalRun(
    presentation=...,
    artifact=...,
    deliverable=...,
    response=...,
    result=...,
    draft=...,
)
```

那照样完蛋。

最好把它理解成：

> **opaque terminal model output**

runtime 不理解里面到底是一篇文章、一份分析、一段客户沟通建议还是研究结论。

这正是你之前强调的：

> **不要让业务字段影响 LLM 生成。**

---

# 现在这个进度，我给的判断

**T000：非常好。**

它实际上消除了做很多补丁的理由。

**Commit A 核心方向：对。**

`final_result schema → natural terminal str` 是一次真正的 architecture correction。

**`RunSummary` 去 deliverable：对。**

这是关键修复。

**`TerminalRun.presentation`：允许，但必须证明它只是单一通用 transport seam。**

不能成为新的 deliverable container。

---

还有一个很重要的信号：你上传的 Phase 2 规范本身其实已经把这类工程约束说得很清楚——Phase 1 substrate 已经固定，不允许重新制造 generic infrastructure；Phase 2 应该只收敛真实产品路径。 Phase 2 的实施计划同样明确写了 **“No new runtime or database”**。

所以我会要求 coding agent **不要因为接下来测试炸了，就开始一个字段一个字段补兼容层**。

测试炸了以后应该问：

```text
这个测试验证的是旧 architecture，
还是新的必要 invariant？
```

如果测试还在要求：

```text
final_result(...)
RunSummary.deliverable
structured business output
```

**改测试。**

不要为了让旧测试绿，把旧设计偷偷接回来。

---

### 我现在最想看到的 Commit A 验收，不是“pytest 全绿”

而是这 6 条：

1. 普通 authoring/research/analysis 可以直接 `str` terminal。
2. 模型完全不知道 `RunSummary` schema。
3. 不再要求 `final_result` tool。
4. `RunSummary` 中不存在任何业务结果字段。
5. approval 仍然由 `DeferredToolRequests → PausedRun → resume` 工作。
6. Gateway 只是呈现 terminal text，不重新解释或重构它。

**这六条成立，我会认为这次是真的把根修了。**

如果只是 `deliverable → presentation`，哪怕 `559 → 600 passed`，我也会判它**没有完成 P3B-2 的核心目标**。

所以目前可以继续，但我建议 **Commit A 完成后先停一次，不要直接 Commit B**：专门审一遍数据流，看是否真正变成 **“生成输出 / 控制结算”两条平行线**。这比继续补测试重要得多。


## T002 — Split Presentation from Settlement

### Code

- [ ] Add `TerminalRun.presentation: str`.
- [ ] Make runtime accept `result.output: str`.
- [ ] Host constructs `RunSummary`.
- [ ] Keep old receipt deserialization compatible.
- [ ] Deprecate `RunSummary.deliverable`; stop producing it.
- [ ] Renderer sends `TerminalRun.presentation` as primary response.

### Host settlement rules

- [ ] status comes from runtime/verification state;
- [ ] artifacts come from host verification;
- [ ] effects come from effect ledger;
- [ ] knowledge comes from host verification;
- [ ] errors/unknowns come from runtime/verification;
- [ ] outcome is a bounded host summary.

### Tests

- [ ] natural terminal → valid receipt;
- [ ] artifact auto-discovery still works;
- [ ] effect auto-settlement still works;
- [ ] error path still produces blocked/partial receipt;
- [ ] old receipts containing `deliverable` still load.

**Acceptance**
- presentation never depends on receipt schema;
- receipt completeness does not depend on model-crafted evidence fields.

---

## T003 — Rewrite Core instructions

- [ ] Replace receipt/workflow-oriented rules with the minimal FDE contract from SPEC.
- [ ] Remove `RunSummary`, `artifact:<...>`, `tool-effect:<...>`, and receipt-crafting guidance.
- [ ] Keep hard safety/evidence principles only.

**Acceptance**
- grep/model-surface test finds no settlement-schema guidance in normal core prompt.

---

## T004 — Introduce thin Case context projection

- [ ] Add `context_projection.py` (or equivalent thin host module).
- [ ] Project a bounded natural-language Case brief from the bound Case.
- [ ] Inject projection through Gateway/bridge before the model request.
- [ ] Projection explicitly states that background is context, not a workflow.
- [ ] Do not dump full `situation.json`.
- [ ] No new Context framework/database.

**Tests**
- [ ] bound Case injects relevant brief;
- [ ] unbound run works normally;
- [ ] projection is bounded;
- [ ] cross-Case isolation unchanged.

---

## T005 — Remove workflow policy from Case toolset

- [ ] Delete `load_case_context first`.
- [ ] Delete authoring completion workflow.
- [ ] Delete ACE routing workflow.
- [ ] Delete mandatory `save_artifact`.
- [ ] Delete RunSummary/evidence-crafting guidance.
- [ ] Delete assumption “current user is always Barry”.
- [ ] Keep tool semantics and Case isolation/provenance rules.

**Acceptance**
- Case toolset describes capabilities/state only;
- no writing/customer-delivery workflow is prescribed.

---

## T006 — Defer Case tools in stillevo-fde

- [ ] Set Case plugin `defer_tools = true`.
- [ ] Verify ToolSearch authorization still satisfies deferred loading.
- [ ] Confirm Case tools absent from initial model action surface.
- [ ] Confirm Case tools discover/load when a genuine durable state mutation is requested.

**Acceptance**
- normal authoring does not initially see `save_draft`/`send_to_customer`/`update_situation`.

---

## T007 — Remove deterministic Client Service judgment from production

### Production surface

- [ ] Remove `assess_customer` tool registration.
- [ ] Remove `select_response_strategy` tool registration.
- [ ] Keep/rework `retrieve_client_context`.
- [ ] Add thin evidence search only if needed.
- [ ] Keep existing policy engine code for offline eval/audit, but ensure production Agent path cannot invoke it.

### Guidance

- [ ] Convert useful approved business policies into retrievable precedent/guidance where practical.
- [ ] Preserve hard prohibitions as hard guards.

**Tests**
- [ ] production Client Service toolset does not contain strategy/assessment tools;
- [ ] offline policy tests still pass;
- [ ] FDE can answer a client-service judgment prompt through context + model.

---

## T008 — Make Client Service recording a local write

- [ ] Remove generic `requires_approval=True` from local interaction recording.
- [ ] Keep provenance and durable receipt/state update.
- [ ] If existing tests expect pause, rewrite them around local-write semantics.

**Acceptance**
- internal history write causes zero human approval;
- external customer send remains independently approval-gated.

---

## T009 — Clean Writing instructions

- [ ] Remove `final_result deliverable`.
- [ ] Remove mandatory `save_artifact`.
- [ ] Keep ACE evidence/source/exemplar semantics.
- [ ] Keep budgets/action-space withdrawal.
- [ ] Permit direct rewrite of pasted text when there is no legitimate ACE article/material identity.

**Tests**
- [ ] pasted text + rewrite succeeds without ACE ingest;
- [ ] existing grounded ACE flow still works when ACE material exists.

---

## T010 — Clean Budget instructions

- [ ] Remove mandatory `save_budget_report`.
- [ ] Remove RunSummary artifact declaration language.
- [ ] Keep deterministic arithmetic and health logic.

**Tests**
- [ ] budget question can return natural analysis with zero saved artifact;
- [ ] explicit “save report” still uses artifact tool and verifies it.

---

## T011 — Make approval payload self-describing

- [ ] Change `send_to_customer` (or its minimal equivalent) so pending args include exact outbound text.
- [ ] Keep Case identity server-owned where possible.
- [ ] After approval, execute exactly the approved text.
- [ ] Keep optional draft reference only as metadata if useful.

**Acceptance**
- what is shown at approval == what is executed.

---

## T012 — Remove Case storage knowledge from Gateway

- [ ] Delete `_outbound_draft_content` business-specific lookup.
- [ ] Delete Case draft regex/path coupling from Gateway.
- [ ] Approval renderer uses generic pending action args/content.
- [ ] No Gateway import of business plugins.

**Tests**
- [ ] Gateway approval card renders exact send text;
- [ ] Gateway source contains no `cases/.../drafts` logic.

---

## T013 — Golden regressions G1–G7

Implement all seven cases from SPEC:

- [ ] G1 unbound authoring;
- [ ] G2 bound authoring;
- [ ] G3 natural revision continuity;
- [ ] G4 client-service judgment;
- [ ] G5 budget reasoning;
- [ ] G6 explicit outbound pause;
- [ ] G7 approve once / deny zero.

---

## T014 — Model-visible surface contract

Create `tests/test_model_surface_contract.py`.

Capture first model request for a normal bound-Case authoring task.

Assert absence of:

- [ ] RunSummary;
- [ ] deliverable;
- [ ] settlement `final_result` schema;
- [ ] artifact/effect crafting instructions;
- [ ] approval level / disclosure ceiling;
- [ ] CustomerAssessment;
- [ ] deterministic response strategy;
- [ ] initially deferred Case mutation/delivery tools.

**Acceptance**
- this test fails if future work reintroduces control-plane leakage.

---

## T015 — Continuation / approval regression

- [ ] Terminal conversation history remains resumable.
- [ ] Pause receipt survives restart.
- [ ] Resume uses frozen CompositionSnapshot.
- [ ] Bound Case identity survives pause/resume.
- [ ] Approve/deny semantics unchanged.
- [ ] No duplicate external effect.

---

## T016 — Documentation

Update `README.md` and add `docs/agent-loop-contract.md`.

Must document:

1. model owns judgment/generation;
2. host owns settlement;
3. tools are capabilities, not workflows;
4. Case is context;
5. hard policy vs soft judgment;
6. approval only at external/destructive boundary;
7. model-visible-field test.

Do not document implementation as a new framework.

---

## T017 — Real-model proof

Disposable proof:

### Turn 1
- pasted “夏天的指尖” sample;
- “改写这篇文章”.

### Turn 2
- “开头还是太像 AI，第二段别动，其他地方保持。”

### Turn 3
- “这版可以，发给客户。”

Capture:

- [ ] direct natural result;
- [ ] zero approval on T1/T2;
- [ ] real history continuation;
- [ ] approval only on T3;
- [ ] exact payload visible;
- [ ] no cross-Case behavior;
- [ ] receipts still valid.

Do not commit disposable script unless it becomes a generally useful stable proof.

---

## T018 — Final quality gate

- [ ] Ruff green.
- [ ] Full pytest green.
- [ ] No unexpected test skips.
- [ ] Manifest regenerated and consistent.
- [ ] README/spec truth matches code.
- [ ] Review diff for accidental new framework/policy/router.
- [ ] Report changed files, commits, test counts, real-model proof.

Only then:

`P3B-2 = 100% — STOP`
