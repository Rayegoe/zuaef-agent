# Slides artifact guidance

Use this capability when the outcome is a presentation someone will show:
老板汇报、周会/月会材料、客户 pitch、项目复盘、strategy briefing. An explicit
PPT/幻灯片 request is authoritative. Respect an explicit page/slide budget
(e.g. "控制在 6 页以内") exactly — a deck over budget is a failed outcome.

Production discipline:
- Design the narrative arc first (situation → key points → evidence →
  recommendation), then build the whole deck in ONE `create_slides` call.
- Slide vocabulary: title, key message, bullets, two-column, image+text,
  table, chart, quote, closing. One idea per slide; short phrases, not
  paragraphs. Numbers the audience must trust go in tables/charts.
- Keep a conservative business theme; do not ask the user about colors or
  fonts.
- For follow-up edits, `revise_slides` targets slides by index — revise the
  current deck instead of regenerating an unrelated one.
- The QA cycle runs inside each tool call (reopen/inspect, render where the
  deployment provides a renderer). A failed QA state must be fixed or
  reported honestly.

Output discipline: report the deck path (workspace-relative), the slide
count, and material assumptions only — never internal tool or render details.
