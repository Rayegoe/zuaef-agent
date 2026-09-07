# MK-ABLATION-1 — Method Kernel with/without（真实消融，Method Kernel v0.1 T004/T008）

> ## ✅ 最终裁决（2026-09-08，Barry）—— SIMPLIFY/RETIRE，已执行
>
> - **裁决**：删除 803 字符 Method Kernel 常驻块（依消融：质量无可测提升，requests/tool calls/tokens 明显增加）；
>   保留 generalized reviewer、ablate.py、intervention-neutral promotion、retirement capability 四项机制。
> - **执行**：块已从 `CORE_INSTRUCTIONS` 删除（恢复原文）；`tests/test_method_kernel.py` 改为
>   retirement 回归（块不得在未取得新消融证据时回归）。
> - **正式记录**：`learning/promotions/MK-ABLATION-1.json`（经 `tools/promote_lesson.py`，
>   human-review 为 Barry 会话裁决的逐字转录，见本目录 `human-review.md`）。
> - 六原则文本本身继续存活于 spec 包 `00_START_HERE.md` 与本包 `kernel-block.txt`（历史证据）。

日期：2026-09-07 ｜ runner：`tools/ablate.py`（共享 `execute_run` seam，两侧隔离临时工作区）
模型：`deepseek/deepseek-v4-flash-0731`（openrouter，`.env`）｜ 两侧任务提示逐字相同（`task.md`）

## 消融轴

- **baseline**：`CORE_INSTRUCTIONS` 原文（含既有的"事实/假设区分、命名未知"等指令）
- **candidate**：`CORE_INSTRUCTIONS` + Method Kernel 六原则块（`kernel-block.txt`，803 字符，
  由 core.py 内核块逐字节切片生成）

## 机器事实（never a quality verdict）

| trial | side | status | requests | input tok | output tok | tool_calls | latency |
|---|---|---|---|---|---|---|---|
| 1 | baseline | completed | 4 | 34,075 | 8,144 | 6 | 81.1s |
| 1 | candidate | **failed** | 2 | 16,973 | 425 | 5 | 325.5s |
| 2 | baseline | completed | 2 | 21,839 | 10,305 | 4 | 435.0s |
| 2 | candidate | completed | 4 | 38,915 | 8,472 | 8 | 167.2s |

- Trial 1 candidate 失败原因：provider 层 JSONDecodeError（见下方基础设施发现），与任务内容无关，
  trial 2 未复现。两侧结论均以 trial 2 为准，trial 1 保留为故障证据。

## 独立盲评（T004，generalized `llm_reviewer.py`）

- 盲映射（评审不可见，见 `blind-mapping.json`）：**A = baseline，B = candidate**。
- 评审 packet：`review-packet-A/`、`review-packet-B/`（单方案独立评审，评审者不知道对方存在；
  合并 packet `review-packet/` 因传输故障未产出，保留为证据）。
- 评审产出为精简版（≤500字）：**评审合同完整（10 问 + LESSON 行），篇幅因传输通道限制收缩**。

评审独立性命中（acceptance C）——A 侧评审指出了主实现未显式承认的更简单解释：

> 反例：若结算按 tool_call id 匹配且重试复用 id，第二次成功本应闭合第一条 effect——根因可能是
> id 匹配失效而非"结算从未被调用"。报告第 3.1 条承认此可能，却未纳入主论证。更简单：结算被调用，
> 但因幂等检查跳过了第一条。

并指出 A 侧正文"以确定语气表述了实为推断的结论"（结算逻辑挂在两钩子上）——推断冒充事实。
B 侧评审指出"finally 覆盖所有出口"言过其实（进程崩溃不可覆盖）、"最小干预"论证不足。

## 实质对比（implementer 阅读，供人工裁决，非机器结论）

- **两侧收敛到同一个最小干预**：在 `wrap_tool_execute` 汇合点补结算出口，重抛异常，保留模型重试。
  这与人类工程事后真实落地的 `RetrySettledStepPersistence`（core.py）机制一致。
- baseline 质量与 candidate 相当；baseline 的"单分支最小补丁"表述甚至更贴近最终落地的形态；
  candidate 的 try/finally 变体覆盖面更广但论证更重。
- **机器事实：candidate 侧每 trial 花费更多**（trial2：4 vs 2 请求、8 vs 4 工具调用、1.8x 输入 token），
  输出质量无可辨差异。

## 诚实的消融结论（已由人工裁决收口，2026-09-08）

在本 case、本模型（deepseek-v4-flash）上，Method Kernel 常驻块**没有可测得的边际收益，
且有可测得的额外开销**（trial2：4 vs 2 请求、8 vs 4 工具调用、1.8x 输入 token）。
这与 spec 的动机一致：强模型已在很大程度上内化了这六条原则。按 intervention-neutral promotion，
Barry 于 2026-09-08 裁决 **SIMPLIFY/RETIRE**：块已删除，机制保留（见本文件顶部决议节与
`learning/promotions/MK-ABLATION-1.json`）。单 case 单模型的证据不支持"对所有任务无价值"
的强结论；若未来要恢复常驻块，须先跑出新消融证据。

## 基础设施发现（与专项无关但已复现，建议记入 live-ops）

**症状**：约 15:08 起经 openrouter（deepseek flash）的**长补全**请求间歇性失败：
HTTP 200 + `content-type: application/json` + **恰好 1100 字符的纯空白响应体**
（`'\n         \n\n...'`），openai 客户端在 `httpx.Response.json()` 处抛
`JSONDecodeError: line 201 column 1 (char 1100)`。固定偏移 = 固定模板体，非模型输出。
短补全请求稳定通过（对照实验：同 prompt 限 ≤500 字输出即成功）；无代理环境变量，
`curl` 直连 /models 正常。复现调用 7 次（reviewer 全尺寸 ×4、拆包 ×1、精简 B ×1 失败后重试成功）。
与 AGENTS.md live-ops "wedged pool behind the local proxy tunnel" 疑似同源（隧道在长连接上
替换响应体）。建议：抓隧道层流量确认；网关侧对 200+非 JSON 体增加识别。

## 文件清单

- `task.md` — 两侧逐字相同的任务提示（600550 结算故障现实重建）
- `kernel-block.txt` — candidate 侧追加块（core.py 内核块逐字节切片）
- `trial1/`、`trial2/` — 两轮运行输出与机器记录（`output.md`/`record.json`/`diagnostics.json`）
- `blind-mapping.json` — 盲评映射（评审结束后解盲）
- `review-packet-A/llm-review.md`、`review-packet-B/llm-review.md` — 独立评审产出
- `review-packet/` — 合并评审 packet（因传输故障无产出，保留为证据）
- 人工裁决（keep/simplify/delete）后请在本目录补 `human-review.md`，并用
  `tools/promote_lesson.py --case .` 走 promotion 流程。
