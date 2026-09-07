工作区里没有任何代码或知识文档（只有空的 `knowledge/`），也没有历史对话记录可查。因此这份诊断完全建立在你的问题陈述 + pydantic-ai 控制流的公开语义之上，所有从本会话拿不到源码的地方我都明确标为"未验证"。

---

# 诊断 + 干预提案

## 一、故障过程重建（实际发生了什么）

时间线还原：

1. **记账**：run 开始时，编排层为 `run_code` 的工具调用写入 effect 记录 `tool_call_started`（一条处于"开放/待结算"状态的账记）。
2. **出错**：沙箱内第一次执行失败 → 工具 handler 抛出 `ModelRetry`（或同族 `ToolRetryError`/`ToolFailedError`）。
3. **泄漏**：按 pydantic-ai 语义，`ModelRetry` 是**控制流异常**而不是"执行失败"——它不终止运行，而是"把错误文本回给模型，让模型重试"。该异常从 `handle_call` **直接向外传播**，`after_tool_execute` 与 `on_tool_execute_error` 两个负责结算的钩子**都不触发**。于是第 1 步写下的开放 effect **再也没有被结算**。
4. **重试**：模型循环按设计捕获 `ModelRetry`，把错误内容送回模型；模型选择重试并成功，本次运行正常产出结果。
5. **误判**：运行结束时，账本结算逻辑扫描到那条从未被 settle 的 `tool_call_started` → 判定存在 "unresolved tool call" → 整个 run 被结算为 **failed**，理由 "run ended with unresolved tool call(s)"，用户收到错误失败提示。

**定性**：这不是交易逻辑或数据工具失败，而是**编排层（持久化账本）的记账缺陷**导致的一个**假阴性误报**——运行本身真实成功，账本却把它结算成失败。

## 二、证据链

| 观察 | 含义 |
|---|---|
| ledger 明细：`tool_call_started` 已写入 | 开放 effect 确实建立 |
| ledger 明细：该记录此后从未被 settle | 存在泄漏的开放 effect |
| 源码事实：ModelRetry 从 `handle_call` 直接传播，两结算钩子都不触发 | 解释了为什么没人关闭它 |
| 事实④：工具确实执行、错误确实送达模型、重试确实成功 | 证明这不是真实业务失败 |

链条是闭合的：**ModelRetry 逃逸 → 效应漏结算 → 结束检查误判**。每一步都有观察依据。

## 三、根因

- **主线缺陷（账本）**：工具执行 effect 的生命周期保证缺了一条出口路径。正常结束（success）与真实错误（failed）两条出口有结算，唯独 `ModelRetry` 这条控制流出口没有结算 → 开放 effect 泄漏。
- **触发缺陷（检查逻辑）**：结束检查把"存在未结算 effect"等价于"运行失败"。检查本身按设计工作——它只是**暴露了泄漏**；但因为账本从不允许 effect 泄漏，它把账本不完整误当成了业务失败。

结论落点：与历史备注"`fetch_history` cache miss 缺口在编排层"属于**同一层**（编排/账本），但**根因不同**（一个是缓存命中问题，一个是记账出口泄漏），不能断言同根。

## 四、修复干预（最小干预）

**选定做法：把结算保证收到 `wrap_tool_execute` 这个唯一执行咽喉点里**，用 try/except 关闭所有出口，并**原样重抛**以保留控制流语义。

```
def wrap_tool_execute(self, tool, args):
    effect = self._start_tool_effect(tool)                       # 写入 tool_call_started
    try:
        result = tool.function(*args)
        self._finish_tool_effect(effect, outcome="success")
        return result
    except (ModelRetry, ToolRetryError, ToolFailedError) as exc:
        self._finish_tool_effect(effect, outcome="errored_or_retried")
        raise exc                # ★ 必须原样重抛，否则破坏重试语义
    except Exception as exc:                                    # 兜底任何出口
        self._finish_tool_effect(effect, outcome="errored")
        raise exc
```

**为什么这是能证明结果的最小干预：**
- `wrap_tool_execute` 是每个 handler 执行的**唯一入口/出口咽喉**，在它内部保证结算，能同时覆盖 `ModelRetry` 以及其它潜在泄漏出口，而不是只修这一条。
- 改动局限在一个扩展点内，不触碰第三方 pydantic-ai 控制流，也不改结束检查逻辑。
- 结算用显式 outcome（"重试过一次"）如实记账，与观察事实一致：工具出错 → 模型重试 → 成功，审计不失真。
- 关键约束：结算后**必须把 ModelRetry 原样继续抛出**，让模型循环仍执行重试。若在记账处吞掉异常，就成了"修好记账、破坏重试"的回归。

**实现注意事项（真正的风险点）：**
- 若正常 success 路径目前仍由 `after_tool_execute` 结算，改到 `wrap_tool_execute` 会造成**双重结算**。改动前必须先确认现有结算归属，并把结算所有权收拢到 `wrap_tool_execute` 一处，或让 `_finish_tool_effect` 对同一 effect 幂等（二次结算只更新不新增）。这在动手前是必须核实的一步。

## 五、考虑过的替代方案及不选理由

1. **给 ModelRetry 路径补调 `after_tool_execute`/`on_tool_execute_error`（改 pydantic-ai 控制流）**
   → 不选：源码已确认该路径根本不经过这两个钩子，等于要为第三方库打补丁/上游改动，升级即碎、改动面大；且 retry 本就不属于"执行后"生命周期，语义不对。

2. **推迟写 `tool_call_started`，执行成功后才记账**
   → 不选：丢掉"调用已开始但进程中断/挂起"的审计与崩溃恢复能力，账本出现假阴；也不修复已存在的在途记录。用弱化记账换掉当前误报，得不偿失。

3. **放宽结束检查，容忍未结算 effect**
   → 不选：治标不治本。未结算 effect 对崩溃恢复和审计本就重要（进程在调用中途被杀时它是唯一线索）；静默会掩盖真实失败。选择"保证结算"优于"弱化断言"。

4. **在模型循环层捕获 `ModelRetry` 时结算**
   → 不选：模型循环是第三方控制流且从多处可达，把持久化保证耦合进通用循环职责混乱。咽喉点 `wrap_tool_execute` 更局部、更健壮。

5. **定期扫除/对账器修补陈旧开放 effect**
   → 不选：最终一致性的兜底，仍保留"运行已完成却已误报失败"的客户可见窗口（正是本次现象）。可作为叠加的纵深防御，但非主修复——主修复应在执行管线里同步关闭。

## 六、不能确认的部分（未知/未验证）

可检查环境未提供实际源码，以下必须标注为未验证，动手前请核对：

1. `wrap_tool_execute` 当前真实实现、effect 实际在哪个函数里写入、正常路径现在由**谁**结算——这是第四节"双重结算"风险的直接输入。
2. `_finish_tool_effect(...)` 的真实签名 / outcome 枚举：是否接受 `"retried"/"errored"` 这类值，不接受该用什么值。`_record_event(...)` 的确切用途也未知。
3. 结束结算逻辑的准确条件：是"存在未结算 effect"就判 failed，还是"存在 errored/failed effect"也判？若后者也判，需同步确认 errored effect 不会再把 run 翻成 failed——否则"重试过一次"仍会误报。
4. 实际抛出的异常究竟是 `ModelRetry` 还是 `ToolRetryError`/`ToolFailedError` 中哪一个（你的源码事实把整族归为同类，方案同等对待所以不影响结论，但账本记录需写准确）。
5. 是否存在其它泄漏出口（如 `ToolNotAuthorized`、agent 顶层异常、进程被杀/超时）同样让 effect 不结算——本次只确认了 retry 一族；因方案放在咽喉点已顺带覆盖，但未逐一验证。
6. pydantic-ai 的具体版本（"ModelRetry 直接传播、两钩子不触发"我采信你的源码确认，但未亲自核对对应版本行为）。
7. 历史 "cache miss 缺口在编排层" 与本故障是否同根——只能确认同层、不同成因，无更多数据，不推断共享底层缺陷。

---

一句话结论：**账本在执行咽喉点缺少对 `ModelRetry` 这条控制流出口的结算，导致开放 effect 泄漏，结束检查把账本不完整误判为业务失败；最小修复是在 `wrap_tool_execute` 内 try/except 全部出口并原样重抛，让结算与重试语义并存。** 改动的真正风险在"双重结算"，动手前须先确认现有结算归属。
