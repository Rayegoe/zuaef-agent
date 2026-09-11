# Spreadsheet artifact guidance

Use this capability when the outcome is structured numbers the user will
reuse and adjust: 报价、预算、预测、情景/敏感性分析、对比、跟踪表、经营模型,
or any explicit Excel request. When the user says "以后能自己改参数" /
"可以继续改的表", the workbook MUST keep that promise: input assumptions stay
editable cells and every derived value that expresses business logic stays a
formula — never bake results into static numbers.

Production discipline:
- Structure workbooks for reading: an assumptions/inputs area, calculation
  area with formulas referencing the inputs, and a summary (with a chart when
  a comparison or trend carries the message). One `create_spreadsheet` call
  with the full declarative spec.
- Number formats are part of the deliverable: currency as currency,
  percentages as percentages. Column widths so nothing renders as ####.
- Do not add formulas for decoration; do not add a spreadsheet at all when
  the user only wants a brief factual answer.
- For follow-up edits, `revise_spreadsheet` applies bounded operations to the
  existing workbook — preserve the formulas the user still needs.
- The QA cycle runs inside each tool call: reopen and structural checks are
  automatic; recalculation runs when LibreOffice is available — if cached
  results could not be recalculated, say so instead of claiming verified
  numbers.

Output discipline: report the workbook path (workspace-relative), which cells
hold the editable assumptions, and material assumptions only.
