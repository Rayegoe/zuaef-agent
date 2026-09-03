# Outcome Contract + Anti-Pattern Gates

## 产品当前本质

当前 S3 是**基本面/交易性过滤 + 短期均值回归择时**，大致持有 2–8 个交易日，不是长期价值投资。

经济假设：

> 在质量/交易性不太差的股票中，寻找短期快速下跌后出现成交放大与价格企稳的标的，博弈短期错误定价修复。

## 一级业务成果

- 每日有效决策；`NO_TRADE` 是完整成果。
- 用户能理解 why / invalidation / risk。
- 每个真实决策后续有 D+1/3/5/8、MFE/MAE、exit、net P&L。
- 每个 Research Run 减少一个真实 uncertainty。

## Outcome-First 门禁

任何新开发先回答：

1. 当前真实失败/未知是什么？
2. 它影响哪个业务成果？
3. 现有能力为什么不够？
4. 最小修改是什么？
5. 什么证据算成功？

答不出来，不开发。

## 禁止字段流转冒充业务

错误：

`Source DTO -> Candidate DTO -> Signal DTO -> Decision DTO -> Report DTO`

如果只是复制字段，没有产生新事实/判断，就是流程表演。

正确：

`Market facts -> deterministic evidence -> Agent interpretation -> human decision -> forward outcome`

## Schema Admission

新持久 field 必须立刻有 consumer：evaluator / validator / renderer / Agent recall / audit。

- 无 consumer：删除。
- quant-local schema 不升级成 Core mega-schema。
- 用 stable refs / IDs 代替跨层复制 metadata。
- Research Log / Lessons / Open Questions 优先 Markdown。
- 数值事实、trades、provenance 才用 JSON/CSV。

## Tool Admission

新增 model-visible tool 必须证明独立 action / permission / effect boundary。

不要因为 Agent 要读 `LESSONS.md` 就创建 `read_lessons/list_lessons/search_lessons/get_lesson/update_lesson`。现有 filesystem 能做就复用。

工具调用数量是诊断，不是目标。调用很多工具却没有新增证据 => `FAIL_TOOL_THEATER`。

## Architecture Admission

Database / queue / scheduler / vector DB / graph DB / workflow engine / new service 只能由真实失败触发。

“以后可能需要”不是理由。
