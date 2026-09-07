Decision: ACCEPT — 采纳并对 Method Kernel 常驻块执行 RETIRE（简化保留机制）。

溯源：以下为 Barry 2026-09-08 在 ZCode 会话中的裁决原话，由执行 agent 逐字转录
（本文件由 agent 代笔，但决策与理由文字均为 Barry 本人明确给出，非 LLM 生成）。

> 我建议裁决为：
>
> **SIMPLIFY / RETIRE**
>
> 也就是不要保留那块额外 803 字符的常驻方法论 Prompt，只保留原 `CORE_INSTRUCTIONS`
> 中已经存在的 outcome / evidence / unknown / no-process-for-process 原则。
>
> 真正保留：
>
> ```text
> generalized reviewer
> ablate.py
> intervention-neutral promotion
> retirement capability
> ```

裁决依据（Barry 对第一次真实消融的归纳）：

```text
六原则常驻块：
没有证明质量提升
但 requests/tool calls/token 明显增加
```

执行内容：从 `src/zuaef_agent/core.py` 的 `CORE_INSTRUCTIONS` 中删除 Method Kernel
六原则常驻块（该块由本专项 T001 加入、经并行提交 1617378 入库）；`kernel-block.txt`
与消融证据包全部保留为历史证据；六原则文本继续存活于 spec 包
`zuaef-method-kernel-light-spec-v0.1/00_START_HERE.md` 与本包记录中。
不得在未取得新消融证据前恢复该常驻块。

intervention: retirement（删除 core 常驻 Method Kernel 块；机制全部保留）
disposition: delete-after-confirming-ablation-executed
