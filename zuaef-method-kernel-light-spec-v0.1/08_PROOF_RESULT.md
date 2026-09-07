# Proof Result — Method Kernel v0.1 实施（2026-09-07）

按 `07_CODEX_MASTER_PROMPT.md` 的返回格式：

## Reused

- `CORE_INSTRUCTIONS` 既有种子（outcome ownership、tools-are-capabilities、事实/假设区分、命名未知、
  spill handles）——全部保留，未重写。
- `tools/llm_reviewer.py` 整个独立评审器（prose 合同、LESSON 行、无人称权威注入）。
- `tools/promote_lesson.py` 的人工门（ACCEPT 判定、T012 反冒充、refusal 路径）——逐行未动。
- `execute_run` 共享执行 seam + `RunReceipt`（消融的机器指标唯一来源）。
- `AgentSettings.with_overrides`（消融每侧隔离 workspace/state）。
- WCASE 比较包约定（`diagnostics.json` + "machine diagnostics only" 注记）。

## Changed

- `src/zuaef_agent/core.py`：`CORE_INSTRUCTIONS` 收敛出 Method Kernel 块（803 字符 ≈150 token，
  六原则 + "not a mandatory workflow / simple tasks just get done" 软性护栏；无 domain 名、无 checklist）。
- `tools/llm_reviewer.py`：泛化输入 contract——manifest 可用原 learning-case 键或中性的
  `task/context/result/validation/sources`，可选 `kind` 收窄角色句；问题集扩为 10 问
  （补：什么被证明 vs 仅声称、反例与更简单解释、应改什么）；prose-first 与"无 lesson 选项"保持。
- `tools/promote_lesson.py`：intervention-neutral——human-review 可选 `intervention:` /
  `disposition:` 行逐字入档（keep/simplify/replace/delete/retirement-candidate 皆为合法 outcome），
  无标记时 payload 保持 v1 形状；反冒充与人工权威路径零改动。
- 新增 `tools/ablate.py`：最小 baseline-vs-candidate runner（唯一轴=指令块追加；机器事实只取自
  receipt；无标量分、无自动裁决）。
- 新增 `tests/test_method_kernel.py`：9 个离线测试（kernel 短/软/无域泄漏、reviewer 兼容两种 packet、
  promotion 记录 marker/保持 v1/仍拒自动、ablate 机器事实形状/无 score 键/拒绝缺 task）。
- `BUILD_MANIFEST.json`：5 个文件外科手术式更新（3 改 + 2 增）。

## Real proof

**MK-ABLATION-1**（`learning/comparisons/MK-ABLATION-1/README.md`）：600550 结算故障现实重建 case，
真实模型两轮消融 + 独立盲评：

- Method Kernel 的"最小干预"判据被两侧共同命中——两侧独立收敛到与人类事后真实落地
  （`RetrySettledStepPersistence`）一致的 wrap 层结算修复，而不是新数据平台/新框架（acceptance B）。
- 独立评审器命中 acceptance C：对 baseline 提出了主实现未纳入主论证的**更简单解释**
  （id 复用/幂等跳过假说）并指出其"推断冒充事实"的表述问题。
- **消融结果（诚实）**：本 case、本模型上 kernel 常驻块无可测边际收益且有额外开销
  （trial2：4 vs 2 请求、8 vs 4 工具调用、1.8x 输入 token，质量无可辨差异）→
  **最终裁决（2026-09-08，Barry）：SIMPLIFY/RETIRE，已执行** —— 常驻块已从
  `CORE_INSTRUCTIONS` 删除，四项机制保留；正式记录
  `learning/promotions/MK-ABLATION-1.json`（acceptance E 完整闭环：系统支持
  "这个 scaffolding 没有显著边际收益，删除"这一结论并真实执行了它）。

## What remains unproven

1. Method Kernel 块对**其他任务类型**（研究、写作、架构）与**弱模型/未来回归**场景的价值——
   单 case 单模型不外推；若保留，此为开放问题。
2. 独立评审的"指出主实现遗漏"目前只有 1 case 命中， reviewer 触发条件（何时值得花一次评审）
   未形成证据。
3. 拆包/精简评审是在传输故障下的**有界绕行**；全尺寸评审合同在当前通道上不可靠，通道修复后
   应复跑一次全尺寸评审验证。
4. `ablate.py` 仅支持"指令块追加"这一消融轴；profile/Skill 目录/工具开关轴未实现（spec 允许：
   以当前项目风格从最小开始）。

## 附带产出（范围外但已复现，建议处理）

openrouter/deepseek 长补全通道间歇返回 **200 + application/json + 1100 字符纯空白体**
（固定偏移 JSONDecodeError），短补全稳定通过；证据与复现记录见
`learning/comparisons/MK-ABLATION-1/README.md` §基础设施发现。疑似与 live-ops 已知的
本地代理隧道病灶同源。
