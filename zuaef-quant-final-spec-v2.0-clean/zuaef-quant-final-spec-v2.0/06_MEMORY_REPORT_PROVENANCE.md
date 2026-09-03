# P4/P5 — Research Memory + Immutable Provenance

## Research Memory

不建 Memory Platform。

```text
workspace/artifacts/quant/research/
  RESEARCH_LOG.md
  LESSONS.md
  OPEN_QUESTIONS.md
  experiments/
  reviews/
```

### RESEARCH_LOG

回答“过去试过什么？”；成功失败都留。

### LESSONS

回答“目前什么值得相信但仍可推翻？”

Lifecycle：`CANDIDATE / SUPPORTED / CONTRADICTED / RETIRED`。

每个 Lesson 有 scope、evidence refs、interpretation、`Do not infer`、revisit condition。

### OPEN_QUESTIONS

记录最高价值 uncertainty，不是开发 TODO。

### Research Run Start

Agent 先读 active strategy、relevant Research Log、Lessons、Open Questions、parent experiment、latest forward evidence，然后回答：

> 现在最值得减少的一个 uncertainty 是什么？

### Research Run End

必须输出：Observation / Comparison / Interpretation / Lesson Impact / Next Question。

新证据与旧 Lesson 冲突时不得静默覆盖，要追加反证并允许 `SUPPORTED -> CONTRADICTED`。

---

# Immutable Report Provenance

Latest 可覆盖：

- `docs/quant/business.html`
- `docs/quant/dashboard.html`
- `.../last_scan.json`

History 不可覆盖：

`workspace/artifacts/quant/reports/<report_id>/`

每次有效运行生成 `QR-YYYYMMDD-HHMMSS-<shortid>`，保存实际存在的 business/engineering HTML、candidate snapshot、live scan、active strategy、Decision Brief、evidence refs。

`manifest.json` 只做 identity/provenance：report id、time、repo commit、input/config snapshot references、Agent run/trace refs、evidence refs。

不要把所有 metrics/candidate fields 再复制进 manifest。

取消“一天只追加一次”观察去重。10:00、11:30、14:50 是三个真实观察。

Forward outcome 后来只回链 report_id/decision_id，不改写旧报告当时的已知事实。
