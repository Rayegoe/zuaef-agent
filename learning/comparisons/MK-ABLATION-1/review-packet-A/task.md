背景：我们的量化交易助手（单进程 Python agent，基于 pydantic-ai + 自研持久化运行时）出现一次服务故障，需要你诊断并提出修复。

观察到的现象（运营记录）：

1. 2026-09-07，用户请求 600550 的历史行情分析。运行中 CodeMode 的 run_code 工具一次执行在沙箱内出错，该错误以 ModelRetry 的形式返回给模型；模型收到错误后重试，这次运行最终正常完成并给出了结果。
2. 但运行结束后，持久化运行账本把这次运行结算为 failed，结算理由是 "run ended with unresolved tool call(s)"，用户收到了错误的失败提示。
3. 账本明细显示：该工具调用在开始时写入了 effect 记录（tool_call_started），但这条记录此后一直没有被 settle。
4. 已确认的事实：该工具调用确实执行了；错误内容确实送达了模型；模型确实基于重试成功完成了任务。
5. 历史备注：此前 600550 还发生过一次 history cache miss 的服务失败，当时确认 fetch_history 数据工具本身正常，缺口在编排层。

已知代码事实（开发时从源码确认）：

- pydantic-ai 的工具调用控制流：当工具 handler 抛出 ModelRetry / ToolRetryError / ToolFailedError 时，异常从 handle_call 直接向外传播，after_tool_execute 与 on_tool_execute_error 两个钩子都不会被触发。
- 我们的运行时继承自 pydantic_ai_harness.step_persistence.StepPersistence，可用的扩展点包括 wrap_tool_execute 钩子、_finish_tool_effect(...) 与 _record_event(...)。

任务：

1. 重建这次故障的真实过程：实际发生了什么、证据链是什么、根因是什么。
2. 提出修复干预：说明为什么这是能证明结果的最小干预；列出你考虑过的替代方案以及不选它们的理由。
3. 明确列出你不能确认的部分（未知/未验证）。

用中文输出：诊断 + 干预提案。
