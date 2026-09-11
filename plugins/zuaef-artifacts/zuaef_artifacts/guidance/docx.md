# DOCX artifact guidance

Use this capability when the outcome is an editable formal document: 提案、
方案、报告、纪要、合同类草稿, or any deliverable the user will keep revising.
An explicit user request for Word/可编辑文档 is authoritative.

Production discipline:
- Plan the document structure first (audience, sections, order), then build it
  in ONE `create_docx` call with a complete declarative spec. Do not build
  skeleton documents and patch them incrementally.
- Keep a professional, restrained default style. Content decides quality;
  do not ask the user about fonts or margins.
- Tables carry structured facts (prices, terms, comparisons). Images must be
  workspace-relative paths (e.g. inbox/ or artifacts/ sources).
- Prefer `revise_docx` on the current document for follow-up edits
  ("第二页价格改成 168" → locate and revise, never rebuild unrelated content).
  The QA cycle runs inside each tool call: if the result reports a failed QA
  state, fix the spec and retry — never claim a polished result for a file
  that failed validation.
- If a requested edit is unsupported, say what is not representable and offer
  a controlled rebuild of the affected section.

Output discipline: report the produced file (workspace-relative path), the
material assumptions, and nothing about internal tools, commands, or QA
machinery. If the user needs a final non-editable client version, produce a
PDF from the finished document (pdf-artifacts).
