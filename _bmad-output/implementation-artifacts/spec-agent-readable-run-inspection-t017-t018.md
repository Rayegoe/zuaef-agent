---
title: 'Agent-readable Run Inspection — T017/T018'
type: 'feature'
created: '2026-08-22'
status: 'complete'
review_loop_iteration: 0
baseline_commit: '6617dd52a228a2864520a4a28404c2b1c779cd99'
context:
  - '{project-root}/zuaef-agent-console-spec-pack-v0.4-run-analysis/TASKS.md'
  - '{project-root}/zuaef-agent-console-spec-pack-v0.4-run-analysis/SPEC.md'
  - '{project-root}/zuaef-agent-console-spec-pack-v0.4-run-analysis/ADR.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `project_run()` 是完整 UI envelope，含有不适合直接喂给 Engineering Agent 的 payload；Agent 需要一个只保留运行事实、可读、有界的 inspection projection。

**Approach:** 在现有 `load_run_facts() → project_run()` 之后增加一个薄的 deterministic inspection 模块。Markdown 与 JSON 共享同一份事实计算；不做 LLM 判断、不增加 API、CLI、store 或 schema。

## Boundaries & Constraints

**Always:** 只从现有 `project_run()` 派生；机械计算 status、wall clock、counts、authoritative duration、per-request usage、排名、tool activity、artifacts、diagnostics 与 bounded chronology。Unknown 保持 Unknown；默认不读取或输出 prompt、response、message history、tool args/result bodies。

**Ask First:** 无；若事实缺失，保留 Unknown，不以推断填补。

**Never:** 解析 Harness raw files/private layout；创建第二套 Run DTO、trace store、数据库、runtime event、receipt schema、LLM/tool registration、Analyze UI、Stillwrite、analysis.md、诊断/建议/因果判断或 T019–T023 代码。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| COMPLETED | 完成 run 的现有 projection | Summary、排名、tool activity、artifacts、chronology 均确定 | N/A |
| UNKNOWN_USAGE | aggregate-only 或无 per-request usage | 总量保留来源；request 排名显示 unavailable，不分摊为 0 | N/A |
| INCOMPLETE_UNRESOLVED | incomplete request 或 unresolved tool | 原状态与引用保留；不写 running/failed | N/A |
| LARGE_RUN | 超过 chronology/top-N 上限的 projection | 只保留 bounded collections，明确 omitted 数量；Markdown ≤12,000 字符 | 不截断半个表格/JSON |
| LEGACY_RECEIPT | 现有 projection 带 receipt_unavailable diagnostic | 仍输出有意义的事件事实与 diagnostics，不 crash | N/A |

</frozen-after-approval>

## Code Map

- `src/zuaef_agent/web/readers.py:93-140` -- 唯一 run facts reader；inspection convenience surface 复用它，不触碰 store layout。
- `src/zuaef_agent/web/projector.py:264-463` -- `build_timeline()` 已确定 request/tool 状态、duration、usage 与排序。
- `src/zuaef_agent/web/projector.py:466-582` -- `usage_summary()`、artifact/diagnostic view 与 `project_run()` 唯一 envelope。
- `src/zuaef_agent/web/api.py:81-92` -- 现有 detail path，证明 facts → project_run 的边界；本轮不加 endpoint。
- `tests/test_web_console.py:141-358` -- completed、legacy、incomplete、unresolved、usage 与 mixed-clock 的真实 FileStepStore/receipt fixtures。

## Tasks & Acceptance

**Execution:**

- [x] `src/zuaef_agent/web/inspection.py` -- 增加共享 deterministic fact builder、稳定 top-N/ranking、tool grouping、unknown facts、bounded chronology，以及 `render_run_markdown()` / `render_run_json()` convenience entry points。
- [x] `tests/test_web_console.py` -- 复用现有 public StepStore/Receipt fixtures，覆盖排名、Unknown、状态、tool grouping、bounded output、JSON/Markdown 一致性、无 content 与 legacy receipt。

**Acceptance Criteria:**

- Given an existing projected run, when inspection renders, then summary contains status/timing/counts/tokens, rankings and artifacts without raw content or causal language.
- Given missing per-request usage, when rankings render, then unavailable remains explicit and aggregate usage is never distributed.
- Given an oversized timeline, when default bounds apply, then Markdown is ≤12,000 characters and JSON collections are bounded with omitted counts.
- Given the same projection, when Markdown and JSON render, then their key numbers, statuses and references match because both consume one inspection result.
- Given an incomplete request, unresolved tool, or legacy receipt diagnostic, when inspection runs, then the known fact remains visible and no crash or fabricated terminal state occurs.

## Spec Change Log

## Verification

**Commands:**

- `timeout 180 .venv/bin/pytest -q tests/test_web_console.py` -- expected: all existing and T017/T018 tests pass.
- `.venv/bin/ruff check src/zuaef_agent/web tests/test_web_console.py` -- expected: no findings.
- `.venv/bin/python - <<'PY' ... render_run_markdown(...) ... PY` -- expected: real run output is deterministic and ≤12,000 characters.
