# 01 — Product and UX Contract

## Product statement

Artifact capabilities turn ZUAEF from “an agent that answers” into “an agent that produces finished work.”

The user-facing abstraction is not DOCX/PDF/PPTX/XLSX. The user-facing abstraction is the requested result:

- 客户方案
- 正式报告
- 报价表
- 财务模型
- 老板汇报
- 周报/月报
- 研究报告
- 采购比较
- 项目复盘

File format is normally an execution decision.

## Natural-language only

The following UX is prohibited as a required path:

```text
/docx ...
/pdf ...
/ppt ...
/excel ...
```

Users may still explicitly name a format in natural language:

- “给我一个 Excel”
- “做成 PDF”
- “输出 5 页 PPT”
- “我要可编辑的 Word”

Such explicit constraints override automatic format selection.

## Default result mapping

When no file format is explicit, use semantic intent:

| Outcome intent | Preferred artifact |
|---|---|
| editable formal report, proposal, contract-like draft, long-form brief | DOCX |
| fixed-layout final deliverable, archival/shareable version | PDF |
| management presentation, client pitch, review, briefing | Slides |
| calculations, scenarios, budgets, pricing, trackers, structured tabular model | Spreadsheet |

Multi-artifact requests are normal. Examples:

- “正式方案 + 客户最终版” -> DOCX then PDF.
- “老板汇报 + 明细计算” -> Slides + Spreadsheet.
- “报价模型 + 客户版报价” -> Spreadsheet + PDF.

## Feishu interaction target

### Example A — customer proposal

User uploads a quotation file and says:

> 把这个报价整理成能直接发给客户的方案，采购成本别出现。

Expected behavior:

1. Read the uploaded quotation from inbox.
2. Infer external-client deliverable intent.
3. Build a formal proposal.
4. Produce a client-safe final PDF and, when useful, an editable DOCX.
5. Reply with a concise result summary.
6. Attach final deliverable files automatically.

No format menu and no slash command.

### Example B — management review

User:

> 把本周销售、报价、未成交原因整理成周会材料，控制在 6 页以内。

Expected behavior:

- infer Slides;
- use available business evidence;
- produce a six-slide-or-fewer deck;
- validate renderability;
- return the deck in Feishu.

### Example C — pricing model

User:

> 这三个供应商按 399、499、599 三档售价分别算毛利，再给我一个可以自己改参数的表。

Expected behavior:

- infer Spreadsheet;
- formulas remain editable rather than replacing every derived value with static numbers;
- result workbook is delivered.

### Example D — follow-up revision

User after a generated proposal:

> 第二页价格改成 168，付款方式改成 30/70，再给我客户版。

Expected behavior:

- locate current relevant artifact from bounded conversation/run context;
- revise instead of rebuilding unrelated content;
- revalidate;
- deliver the revised file.

## User-visible response discipline

For a successful artifact run, the final text should contain only what helps the user act:

- what was produced;
- material assumptions or unresolved gaps;
- the final files.

Do not expose internal capability names, renderer commands, temporary images, or implementation details unless asked.

## Result-first rule

The artifact is the primary work product. Chat text is the concise cover note.
