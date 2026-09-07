# 方案A

（说明：本次诊断基于你给出的已知代码事实与运营观察；先做了记忆/知识/历史检索确认，当前环境没有与本系统相关的既有记录，因此以下内容完全以本次提供的事实为准，并在第三部分明确标注哪些是我的推断、哪些无法核实。）

---

# 一、诊断：故障真实过程与根因

## 1. 真实过程重建（时间线）

把运营观察（事实）与源码控制流（已知代码事实）拼起来，实际发生的是：

1. **模型发起工具调用**：模型为「600550 历史行情分析」生成了一次 `run_code`（CodeMode 内）工具调用，请求在沙箱中执行一段分析代码。
2. **运行时落账「开始」**：执行进入我们的持久化层，`wrap_tool_execute`（或其下的落账点）为这次调用写入了一条 `tool_call_started` effect 记录（工具名、调用标识、开始时间等）。
3. **第一次执行出错并抛出可重试错误**：沙箱内代码执行失败，错误内容由工具层以 `ModelRetry` 形式返回。
4. **触发钩子盲区**：按已知代码事实，`ModelRetry` / `ToolRetryError` / `ToolFailedError` 会直接从 `handle_call` 向外传播，`after_tool_execute` 和 `on_tool_execute_error` 两个钩子**都不会触发**。而我们的 effect 结算逻辑恰恰挂在这两个钩子上 → 第 2 步写下的 `tool_call_started` 从此没有结算点，永久停在 `started`。
5. **模型收到错误并重试成功**：Agent 循环在钩子之外捕获 `ModelRetry`，把沙箱错误文本回送给模型；模型据此重写代码再次调用 `run_code`，第二次执行成功，正常结算（第二次也有自己的一条 started→finished effect 对）。
6. **运行收官误判失败**：运行结束，账本 finalizer 遍历 effect，撞见第 2 步那条未闭环的 `tool_call_started`。它无法区分「工具出错后被模型吸收并重试成功」和「工具真的挂死/被中断」，于是按既有规则把整次运行结算为 **failed**，理由是 `"run ended with unresolved tool call(s)"`，用户收到错误提示。

## 2. 证据链

| 运营观察（已确认事实） | 对应证据/机制 | 指向 |
|---|---|---|
| 工具调用开始写入了 `tool_call_started` | 落账发生在执行入口（wrap 层），在异常抛出之前 | 结算的起点存在 |
| 错误内容送达了模型 | `ModelRetry` 由 Agent 循环在钩子之外捕获后回送 | 走的是「重试」通道，绕开了钩子 |
| 模型重试后成功完成任务 | 第二次执行走正常成功路径并结算 | 结算只覆盖成功/普通异常通道 |
| 账本结算为 `"unresolved tool call(s)"` | finalizer 看到一条永久 open 的 started effect | 结算通道对重试异常缺失 |
| 已知代码事实：三类重试/失败异常绕过两个钩子 | 结算逻辑挂在这两个钩子上 | **根因的证据闭环** |

## 3. 根因

> **本质是持久化运行时的「effect 结算保证缺口（lifecycle gap）」**：结算被绑定在 pydantic-ai 的两个钩子上，而这套控制流里存在一整类分支（可重试的工具错误）会**绕过这两个钩子**，导致 started effect 永远没有终结状态。运行收官器把「未结算的 started effect」一律视为故障信号，于是把一次真实成功、仅含一次被吸收的重试的运行，误判为失败。

要点：

- **不是 `run_code` 的 bug**，也不是行情数据工具的 bug。沙箱出错→返回错误→模型重试，这一串都正确地按设计发生了，唯一的断裂点在第 4 步的结算通道。
- 与备注 5 的 600550 那次 `history cache miss` 是同类模式：**都是编排/生命周期层缺口，而非工具功能本身缺陷**（上次是编排缓存缺口的取数编排问题，这次是重试通道的结算问题）。两次事件的教训可归并为一条：本系统里「工具功能正确」与「编排落账完整」是两件独立的事。
- 值得指出：收官器判「unresolved = failed」这一语义本身是对的，它保有了「工具调用确未闭环 = 异常」的审计价值。错的是结算通道让它误报——修复应补结算通道，而不应削弱收官器语义。

---

# 二、干预提案

## 1. 最小干预：补上 wrap 层的结算分支

`wrap_tool_execute` 是唯一一个「无论 handler 返回还是抛出任何异常，都必然经过」的落账点，而两个钩子不是。最小且正确的做法是：**把结算从「钩子层」下沉到「wrap 层」的异常通行路径上，让每条 effect 在所有出口（成功 / 普通异常 / 可重试异常）都拿到终结状态**。

拟议形态（伪代码，具体 API 签名须对源码核实）：

```python
def _wrap_tool_execute(self, name, ctx, args):
    eff = self._record_event('tool_call_started', ...)      # 已有：开始落账
    try:
        out = original_tool(name, ctx, args)
    except (ModelRetry, ToolRetryError, ToolFailedError) as e:
        self._finish_tool_effect(eff, terminal='error', retryable=True, detail=str(e))
        raise                                  # 原样重抛，交给 Agent 循环正常处理重试
    except Exception as e:                     # 若既有代码已覆盖普通异常，则删此分支
        self._finish_tool_effect(eff, terminal='error', detail=str(e))
        raise
    else:
        self._finish_tool_effect(eff, terminal='success', output=out)
        return out
```

字面上的最小补丁往往更窄：如果成功路径和普通异常路径已经在 wrap 层结算，唯一要加的**就是 `except (ModelRetry, ToolRetryError, ToolFailedError)` 这一个小分支**——一次执行、一个分支，正是「能证明结果的最小干预」。

修复后的账本应是**逐次尝试**可见的诚实记录：第 1 次尝试 `started → error(retryable)`，第 2 次尝试 `started → success`，运行收官时零条 open effect → 结算为成功。错误仍完整送达模型，模型重试机制原样保留。

**为什么这是「能证明结果」的最小干预——验证闭环：**

1. **判定变更可观察**：用本次真实事故打回归。修复前重建现场 → 运行结算 failed；修复后同一路径 → 结算 success。这是直接的 yes/no 判定。
2. **确定性回归测试**：构造一个「第一次抛 `ModelRetry`、第二次成功」的假工具，断言：(a) 整次运行结算为成功；(b) 账本里该工具恰好两条 effect，第一条终结为 error，第二条终结为 success；(c) 运行结束时 open effect 数 = 0；(d) 事件顺序与真实时序一致（start→error→start→success）。再对「成功」「普通异常」两条既有路径各加断言，确认无行为回归。
3. **改动面极小**：不动账本 schema、不动收官器、不动运行时状态机，完全复用现有 `tool_call_started` / `_finish_tool_effect` / `_record_event`。风险面只有一个 wrap 函数。

**建议的加固（可选，非必须）**：把「正常运行的正常终态 = 零条 open effect」作为收官器不变量写进断言。这样修复之后，任何一次「unresolved tool call(s)」报出，就**真的是异常信号**（进程被 kill、工具真挂死）而非误报——它重新成为有效的告警，而不是噪声。

## 2. 考虑过但不选择的替代方案

| 方案 | 排除理由 |
|---|---|
| **在 `run_code` 工具内部改**：不抛 `ModelRetry`，改为返回结构化错误结果，或改抛 `ToolFailedError` | ① `ToolFailedError` 同样绕过两个钩子，**不解决账本问题**；② 只修这一个工具，任何其他抛重试/失败异常的工具都会复发同一 bug；③ 丢掉了 pydantic 的 model-retry UX（正是它驱动「模型看到错误→重写代码→重跑」的闭环），属功能损失；④ 在最低层修症状，而不修生命周期根因。 |
| **改收官器/结算规则**：把「无后续失败的 open started effect」判为成功，或「最终消息有结果即成功」，或对 open effect 直接忽略 | 收官器的职责就是检测未闭环效应；如此会**洗白真实挂死/进程中断**，审计意义归零；账本数据仍然错（它没有记录第一次尝试的失败）；混淆了「结果」与「证据」——第 2 次成功不构成第 1 次 effect 已闭环的证据。这是修复在错误的一层，且是不正确性损失。 |
| **在 Agent 循环捕获 `ModelRetry` 的位置挂新钩子结算** | 该位置在 pydantic-ai 上游 loop 里、**不在我们的扩展点内**，需要入侵性更强的子类补丁；会在布局上出现「开始在此、结算在彼」的两处插桩，且与 wrap 层重复。`wrap_tool_execute` 本就是成功/异常/重试三态的天然汇合点，没必要另开通道。 |
| **超时清扫器**：定时把超时的 started effect 自动闭合 | 启发式而非确定性；单进程运行时里，「工具真挂死」与「结算漏调」无法靠时间可靠区分，会引入抖动同时掩盖真实挂死；无法作为确定性证明，还会让回归测试变脆弱。 |
| **改 schema / 增加新事件类型**（如 `tool_call_retry` 事件） | 仅当现有终结状态集合无法表达「尝试出错后已恢复」才需要；优先**复用**现有 error/终结态，保持改动最小。列为备用而非默认选择，故不采用。 |

一句话：这些方案要么修错了层（工具层/收官层），要么依赖不确定的启发式，要么扩张 schema——都不如「在 wrap 层补一个必然经过的结算出口」来得小、来得确定、来得可证。

## 3. 后续值得做（因为 600550 两起同类）

建议加一条收尾任务：**审计其余「假设某钩子必然触发」的编排缝**——本系统里很可能还有别的持久化逻辑同样依赖某个被重试/异常分支绕过的钩子。把「工具功能正确」与「编排落账完整」作为两条独立验收维度写入项目记录。

---

# 三、不能确认的部分（未知 / 未验证）

以下是我**无法仅凭给定信息证实**、需要在实施时核实的点，绝不把它们当作已确认事实：

1. **结算 key 的匹配机制**：账本 effect 是按「模型 tool_call id」匹配结算，还是按「第几次执行调用（invocation index）」匹配？若按 tool_call id，而 pydantic 在重试时**复用同一 id**，那么第二次成功的结算可能本就该能闭合第一条——若如此，失效机制会略有不同（是 id 未匹配/未重查，而非结算从未被调用）。给定证据强烈指向「结算从未被调用」，但 key 化细节无法从文字确认。
2. **我们的 wrap_tool_execute 实际覆盖范围**：是否在重试路径上确实被调用；是否已结算成功与普通异常（我上面假设只有重试分支缺失——若普通异常也未结算，则要一并补）。这需要读子类实际代码确认。
3. **绕过钩子的确切异常集合**：给定的是 `ModelRetry/ToolRetryError/ToolFailedError`；随 pydantic-ai 版本差异，集合是否冻结、是否还含其他类型，需按实际依赖版本核实。
4. **`_finish_tool_effect(...)` 的真实签名**：终结状态字段名、是否幂等（若成功路径的钩子结算仍在，需避免二次结算），以及 `_record_event(...)` 的参数形态，都需要对照源码。
5. **run_code 实际抛出的异常对象**：是工具层直接抛 `ModelRetry`，还是内部错误被运行时包装成的 `ModelRetry`？「以 ModelRetry 形式返回」是墙上事实，但异常来源/包装点未验证。
6. **本事故与 600550 那次 cache miss 是否同源**：我只指出两者同属「编排/生命周期层」这一模式，**不**确认二者是一处代码缺陷的两种表象。
7. **复现环境**：是否具备可独立复现沙箱 `run_code` 出错的测试环境，尚无据；推荐先搭建并重放本事故，再做代码改动。

---

建议的实施顺序（说出来供你组织）：**先做第 3.1 的回归复现（红）→ 读子类代码核实 wrap 层现状与 `_finish_tool_effect` 签名 → 补最小分支（绿）→ 加回归断言保三条路径 → 上验证后交付**。需要我把这份材料落成持久化工件、或先帮你看一眼实际子类源码再细化伪代码，随时说。


---

# 方案B

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
