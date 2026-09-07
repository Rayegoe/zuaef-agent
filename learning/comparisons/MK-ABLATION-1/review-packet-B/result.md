

# 诊断 + 干预提案

> 说明：工作区无可读源码/知识库（`knowledge/` 为空），以下结论全部建立在任务给出的观测事实（F1–F7）与源码确认事实（F6、扩展点）之上。凡属推断之处已标注；凡依赖代码现场确认之处列入"未知/未验证"。修复方案的落地位置需要在真实源码上核对后再定稿。

## 一、故障过程重建（实际发生了什么）

**效应生命周期**：账本里每个工具调用以 `tool_call_started` 效应记录在调用开始时写入，随后应在一个结算点被 settle（成功→finished；失败→failed）。根据已知的可疑扩展点（`after_tool_execute` / `on_tool_execute_error` 与 `wrap_tool_execute`），结算逻辑此时依赖 pydantic-ai 的回调钩子完成。

**本次时序**（F1–F6 拼接）：

1. 模型调用 CodeMode 的 `run_code`，账本写入 `tool_call_started`。 ✅ 已确认（F4）
2. handler 在沙箱内执行并出错。 ✅ 已确认（工具确实执行，F5）
3. handler 抛出 `ModelRetry`。异常按 pydantic-ai 的控制流直接从 `handle_call` 向外传播，**`after_tool_execute` 与 `on_tool_execute_error` 两个钩子都不触发**（F6）。
4. 因此，本该在钩子里执行的结算没有被执行 → 这条 `tool_call_started` 从此停留在 `unresolved` 状态。 ✅ 与账本明细一致（F4）
5. 异常以重试反馈形式送达模型，模型重试，第二次工具调用成功走完 normal 结算路径，最终给出分析结果。 ✅ 已确认（F2、F5）
6. 运行收尾器扫描时发现：仍存在一条从未被 settle 的效应记录，据此判定 `run ended with unresolved tool call(s)`，将运行结算为 **failed**，并对用户给出失败提示。 ✅ 已确认（F3）

**结论性判断**：这是一次**假阴性账本结算**。真实业务结果成功（F2、F5），账本却判 failed。数据工具（`run_code` 本身、连同历史上被排查过的 `fetch_history`）均正常；故障完全发生在**编排/持久化层**的效应结算路径上，与 F7 的历史结论同属一类——"缺口在编排层"。

## 二、根因

单一因果机制：**效应结算与工具调用真正的结束点脱钩**。

- 结算被寄放在 `handle_call` 的 happy-path / error 钩子上；
- 而对 `ModelRetry` / `ToolRetryError` / `ToolFailedError` 这类控制流异常，pydantic-ai 不触发这两个钩子，异常直接外传；
- 于是凡走这些非 happy-path 出口的工具调用，其效应记录必然遗留为 `unresolved`；
- 收尾器把"存在 unresolved 效应"当成失败信号，即使在模型已通过重试成功完成任务时仍判 failed。

换句话说：`unresolved` 的语义本该是"我们丢失了对该调用的追踪"，而现在它实际表示"该调用走了一条钩子观察不到的出口"。两者被混为一谈。这是编排层对异常出口路径的防御缺口，不是工具或模型任务的缺陷。

## 三、修复干预（介入提案）

### 最小干预：把结算收敛到 `wrap_tool_execute`，用 `try/except/finally` 覆盖所有出口

将效应结算移入 `wrap_tool_execute`（已有的扩展点），用 `try/finally`（必要时加 `except`）包裹真实的 handler 调用，使**无论 handler 以何种方式退出**（正常返回、`ModelRetry`、`ToolRetryError`、`ToolFailedError`、其他异常），都在同一处调用 `_finish_tool_effect(...)` 完成结算：

- 正常返回 → settle 为成功终态；
- `ModelRetry` / `ToolRetryError` → settle 为"已重试/可恢复"终态（这是合法的、将促成后续成功的一轮，不是未完成），并 `_record_event(...)` 记录 `tool_call_retried` 等事件供观测；
- `ToolFailedError` 及其他异常 → settle 为 failed 终态（效应被终结，收尾器可给出真实的失败原因，而不是误导性的 "unresolved"）。

**配套约束**：
- 保证 `_finish_tool_effect` 对同一效应**幂等**，避免与旧结算点 double-settle；
- 若原结算逻辑分散在 `after_tool_execute` 与 `on_tool_execute_error`，建议**收敛为单一结算点**并退役这两处，消除"同一 lifecycle 两条路径"的脆弱性；
- 修复停留在现有扩展点内，**不改收尾器的"unresolved→失败"判定语义**（见替代方案 1）。

### 为什么这是能证明结果的最小干预

- 只触碰**已经暴露且绕过的那一层**（编排层的结算路径），不引入新机制、不依赖 pydantic-ai 内部、不改模型循环、不改工具语义、不改收尾器逻辑；
- 它把结算放回工具调用"真正结束"的位置，从机制上杜绝 `unresolved` 遗留，使此前错误信号（unresolved→failed）确定性地消失；
- 因而可以用一个确定的回归测试直接复现原故障并断言新信号（见第四节），满足"以结果验证修复"的门槛：**修复后，同样的 retry-成功轨迹必须结算为 completed / 成功，且账本中无 unresolved 效应**。

### 考虑过的替代方案及不选理由

1. **弱化收尾器**（"存在 unresolved 效应但最终有 assistant 输出时不再判失败"）
   → 不选。这是治症状不治原因：`unresolved` 的正当用途正是捕获"丢失追踪"的场景（中断、取消、崩溃）。一旦弱化，真实的数据完整性问题会被掩盖；且收尾器无法**不做推断**地区分"合法重试遗留"与"真实丢失"，会把修复压力推到语义不清的地方。修复必须发生在效应被绕过的那一层，而不是放宽失败判定。

2. **monkeypatch / 补给 pydantic-ai 的 `handle_call`，使钩子在 `ModelRetry` 时也触发**
   → 不选。侵入第三方库内部，对库版本脆弱，改动面大于修复面；且没有触及本问题第一性原则（结算应绑定于调用自身的结束，而非外部回调）。

3. **让模型自行结算**（提供结算工具/指令，由模型在每个分支后调用）
   → 不选。这是把**确定性机械簿记**移入**模型语义决策**域，违背"机械工作保持确定、语义工作模型所有"的原则；无法保证模型覆盖所有分支，反而增加模型轮次与不确定性。

4. **在 `wrap_tool_execute` + `finally` 中结算（本方案）** → 选中。

## 四、验证 / 回归测试

以确定性方式复现原故障并验证修复结果：

- 构造一个 handler：第一次调用抛 `ToolRetryError`，第二次成功（或注入假模型强制发生重试），经 harness 跑完整轮次；
- 断言 (a) 运行结束后无任何 `unresolved` 效应；
- 断言 (b) 运行结算为 **completed**、outcome 为成功（不再是 `failed` / `"unresolved tool call(s)"`）；
- 断言 (c) 重试确实发生（由 `_record_event` 留下可观测事件）；
- 断言 (d) `_finish_tool_effect` 对同一效应幂等。

该测试直接对应本次故障的证据链（F1→F2 的 retry-成功轨迹），是"此前提报错、修复后正确"的最小证明。

## 五、未知 / 未验证清单

以下项无法在当前环境确认，需在源码上核对后再定稿最终 patch：

1. **结算代码当前的确切位置与分支**——`after_tool_execute` / `on_tool_execute_error` 内分别做了什么、是否部分已落在 `wrap_tool_execute`。
2. **`wrap_tool_execute` 的包裹范围**——它是否确实包裹真实 handler 调用，使 `finally` 能捕获 `ModelRetry` 等异常。这是决定本修复能否成立的关键前置验证；若它只包裹簿记而不含 handler，则结算点必须放到实际持有 handler 调用的那一层。
3. **`_finish_tool_effect` 的终态模型**——是否原生支持"retry / 可恢复"作为终态，还是只支持 success/fail（若只有后两者，可能需要新增一个终态或依赖 `_record_event` 记录 retry 事件）。
4. **收尾器判定 `unresolved` 的确切条件**——是否只检查效应记录，还是还校验最终 assistant 消息等；这不改变根因结论，但影响回归断言的精确性。
5. **pydantic-ai 的版本行为窗口**——"`ModelRetry`/`ToolRetryError`/`ToolFailedError` 时不触发两钩子"为用户给出的源码确认事实；一旦升级 pydantic-ai 需重新核对。
6. **是否存在其他非 happy-path 泄漏**（例如 `KeyboardInterrupt` / async `CancelledError` / 进程中断）同样遗留 `unresolved` 效应——本修复的 `finally` 在原则上应覆盖，但需测试确认。
7. **账本判 failed 是否污染了下游其他消费方**（是否还有其他地方复用了这个结算结果向用户/下游提示）——未验证。
8. **历史 cache-miss 修复是否已上线、与本次是否有关联**——未验证；两个案例同属"编排层缺口"，但无证据表明它们共享同一行代码或相互触发。
