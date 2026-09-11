# 05 — Natural-Language Routing and Progressive Disclosure

## Principle

Routing is semantic reasoning by the existing outcome-owning agent, not a separate intent-classifier subsystem.

## Explicit format override

If the user explicitly asks for a particular format, that instruction is authoritative unless impossible or unsafe.

Examples:

- “给我 Excel” -> Spreadsheet.
- “输出 PDF” -> PDF.
- “做成 5 页 PPT” -> Slides.
- “需要 Word 可编辑版” -> DOCX.

## Implicit routing

When no format is named, capability descriptions should allow the model to discover the right domain from business intent.

Examples:

| User phrase | Expected capability selection |
|---|---|
| “老板明天要看的汇报” | Slides |
| “可以直接发客户的正式版” | PDF, possibly preceded by DOCX |
| “以后还要继续改的方案” | DOCX |
| “算三种销量下的利润” | Spreadsheet |
| “方案和详细测算都给我” | DOCX/PDF + Spreadsheet |

These examples are tests and guidance, not string-match rules.

## Deferred loading

Artifact capabilities should be on-demand if the pinned PydanticAI version supports capability-level deferred loading cleanly with the current tool-search configuration.

Desired initial catalog footprint:

```text
docx-artifacts      editable formal documents and proposals
pdf-artifacts       fixed-layout final/shareable deliverables
slides-artifacts    management/client presentation decks
spreadsheet-artifacts structured calculations and tabular models
```

Full instructions and tools should remain collapsed until the model chooses a capability.

If capability-level deferred loading is not supported in the pinned stack, use the smallest supported fallback without changing the kernel:

- keep capability instructions concise;
- defer individual tools only when the existing ZUAEF tool-search seam supports it;
- do not add a custom discovery service.

Record which mode is used in the implementation report.

## Capability guidance rules

Shared guidance across the four capabilities should include:

1. Honor an explicit user format.
2. Otherwise choose format based on intended result and audience.
3. Prefer revising the current relevant artifact over creating redundant variants.
4. Multiple artifacts are allowed when the user asks for distinct uses.
5. Do not create an office artifact when a direct chat answer is sufficient.
6. Do not generate a spreadsheet merely because input data is tabular if the user only wants a brief factual answer.
7. Do not create a deck when the user only asks for a short written summary.
8. For external final delivery, PDF is often appropriate, but do not force it when the user needs editable source.

## Routing tests must use paraphrases

Do not test only exact phrases from this spec. Use Chinese and English paraphrases that express the same outcome with different wording.

At minimum test:

- explicit format;
- implicit single-capability intent;
- implicit multi-capability intent;
- no-artifact intent;
- ambiguous intent where the agent should choose a reasonable default without asking a format question;
- follow-up revision referring to “刚才那个/上一版/客户版”.

## No format menu

The agent must not respond with “请选择 Word / PDF / PPT / Excel” when enough context exists to choose a useful default.
