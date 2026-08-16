# ZUAEF × ACE：Harness-neutral Context Delivery Proof

> 目标不是“Agent 写完一篇文章后等人改稿”，而是证明：
> **自主运行中的 ZUAEF Agent 是否真的按需 pull ACE 的 raw material、writing corpus、knowledge/evidence 与 claim validation，并留下可追溯 receipt。**

## 四层验收

```text
CAP-1 Harness 能接 Context Engine
CAP-2 Agent 在运行过程中真实使用 Context（不是预塞，是运行中 pull）
CAP-3 trajectory 由 Harness/Agent 产生，不由 Context Engine 或测试代码规定
CAP-4 Context Engine 不依赖 ZUAEF；ZUAEF 侧只是 thin adapter
```

## 工具边界

ZUAEF 侧 `examples/writing_toolset.py` 只做 thin adapter，业务逻辑全部调用 ACE `tools/ctx.py`：

```text
list_materials       observe
read_material        observe
retrieve_exemplars   observe
retrieve_knowledge   observe
check_claim          observe
save_artifact        local_write（canonical 由 ACE 写；ZUAEF 只写 run snapshot）
```

禁止：

- 把 corpus selection / evidence policy / material validation 复制进 zuaef-agent；
- 在 `writing_case.py` 里硬编码 `read → exemplar → draft → verify → save` 控制流；
- 引入 quality_score / human_likeness / style / AI-probability 评分；
- 让人工编辑成为 Harness Integration Test 的 blocking condition。

## Context delivery receipt 要求

- 所有 receipt 必须携带 `run_id` / `article_id` / `timestamp`；Integration Test 只统计当前 `run_id` 的记录，历史 receipt 永不满足本次验收。
- budget（check_claim 8 / retrieve_exemplars 6 / retrieve_knowledge 4）以**当前 run 的 ACE receipt 为持久真值**（按 `run_id` 过滤）+ 本进程递送计数为 fast-path：resume 后新 toolset 重新读 receipt，额度不会因进程重建而重置；不同 `run_id` 的 receipt 永不参与计数。
- 额度耗尽后的 refusal 是**正常终态返回**（在 step ledger 中 settle 为 completed effect）；同时该工具在下一 model step 从 action space **消失**（`get_tools` 不再提供），模型不再被展示该工具。
- `read-material`：query=material_id，selected_refs，material_sha256。
- `pull-exemplars`：query、requested_functions、requested_tags、selected_refs、hashes、rights_checked。
- `retrieve-knowledge`：query、selected_refs、hashes。
- `check-claim`：ACE `_state/claim-checks.jsonl` 留痕，记录 `run_id` 与 `purpose`（`validation` / `integration_probe`）。
- exemplar 必须标记为 language/technique reference，不得成为当前文章事实来源。

## Trajectory 语义

Agent 拥有**有界自主轨迹**（bounded autonomous trajectory）：调用顺序与时机自主决定，没有固定 pipeline；但验收与证据规则是硬约束。其中 claim-check 的 `purpose=integration_probe` 是**显式 capability canary**（集成测试桩），不是伪装成自然写作步骤。

**probe 非权威声明**：`integration_probe` 对已保存 artifact 是 **non-authoritative**——probe 的输出不得触发再次 save；probe 只证明 capability delivery，不是工作流步骤。若有人把 probe 写成 `save → probe → 据 probe 意见改文 → save`，即违规。

## Harness Integration Test Complete

```text
= 真实 Agent execution 完成
+ receipt.status == completed
+ raw material 在运行中被 pull（本 run_id）
+ writing corpus 在运行中被 pull（本 run_id，至少一次）
+ knowledge/evidence 在运行中被 pull（本 run_id）
+ claim-check capability probe 在运行中发生（本 run_id，purpose=integration_probe）
+ canonical artifact 存在
+ settlement hash equality
+ ACE gate machine-ready 或 fully-reviewed（唯一剩余 blocker 是 human_final_reviewed，或 gate 全绿）
```

## Optional editorial observation

人工盲改与 ACE trace 是**长期 corpus 数据闭环**，不是本测试的完成条件。测试完成后可以继续做，但不阻塞 `TEST COMPLETE`。

## 已记录的第一版运行（旧题：写作 + 人工边界）

- article_id：`vs-hw951-20260815`
- run_id：`bd023f87347f4ef98b50485c00c22ebe`，receipt completed
- 该运行证明“Agent 能写完并通过 evidence gate”，但用的是预生成 context pack + 固定四工具，未证明运行中 pull-based context。
- 保留为对照证据；`draft.md/final.md` 保留，不要求人工修改。

## 完成记录：Harness-neutral pull-based proof（PASS）

- article_id：`vs-hw951-context-proof-20260815`（2 份真实 HW-951 bringup 素材，M001/M002）
- run_id：`c58bf8cc62534cb3b991d47b6b5f404c`，receipt **completed**，model `deepseek-v4-flash`，22 requests
- 全部 machine check PASS：本 run 内 4× read-material / 4× pull-exemplars / 4× retrieve-knowledge / 2× claim-check（purpose=integration_probe）；canonical final.md 与 run snapshot SHA256 一致；ACE gate 唯一剩余 `human_final_reviewed`。
- 收敛机制在真实 run 中生效：knowledge 与 exemplars 均精确停在 per-run cap（4），无超量；probe 发生在最终 save_artifact 之后且未触发再次 save（non-authoritative 合约成立）。
- 该 workspace 内历史 receipt（旧无 run_id 时代的 22 条 knowledge pulls）被 `context_usage(run_id)` 完全忽略。
- 结论：Context Engine 提供可追溯能力；Agent 自主选择 context；Harness 不规定写作流程，只限制合法动作并保证执行最终收敛。

## 完成记录：Plugin Composition Layer parity（SPEC v0.2 §35，PASS）

- 插件：`zuaef-ace-writing` 0.1.0（`zuaef.plugins` entry point `ace-writing` = `zuaef_ace_writing:create_plugin`），profile `ace-writing`（config: ace_root → article-context-engine）。
- article_id：`vs-hw951-parity2-20260816`（同一份 2 素材，M001/M002）；run_id：`35cfd8bb043248a2b29804476a3a66b6`。
- 命令：`python examples/writing_case.py --profile ace-writing --request-limit 30 ...`——agent 由 `build_profile_agent`（resolve → freeze → compose）构造，非手写 toolsets；`--profile` 缺省时原直连路径不变（§33 proof evidence 保持不动）。
- 结果：receipt **completed**（21 requests）；settlement ok（canonical final.md 与 run snapshot SHA256 一致，字节级相等 4392 B）；probe `purpose=integration_probe ok=True checked=['C4']` 发生在最终 save_artifact 之后。
- 插件化未降低原 proof：同一份 writing domain adapter（byte-identical 副本），全部 machine check 与历史 proof 同构（run-isolated deliveries / bounded retrieval / claim probe / canonical artifact / snapshot equality）。
- 首次运行（`vs-hw951-parity-20260816`）因默认 `request_limit=12` 触顶为 partial（`The next request would exceed the request_limit of 12`），未到 save_artifact；`--request-limit` 放宽后 completed——parity 差异是预算边界，不是能力边界。
- Composition 已随 receipt 持久化（CAP-P4）：profile=ace-writing、plugin ace-writing/0.1.0、composition_id `7e8a90ff…`。
