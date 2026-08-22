---
title: 'Console Fact Fidelity Fix — T016B'
type: 'bugfix'
created: '2026-08-22'
status: 'done'
baseline_commit: '0cccad2c20eccc552713665112ef92feeb45914f'
review_loop_iteration: 0
context:
  - '{project-root}/zuaef-agent-console-spec-pack-v0.4-run-analysis/TASKS.md'
  - '{project-root}/zuaef-agent-console-spec-pack-v0.4-run-analysis/SPEC.md'
  - '{project-root}/zuaef-agent-console-spec-pack-v0.4-run-analysis/ADR.md'
---

# Console Fact Fidelity Fix — T016B

## Frozen scope

修复 Live Overview 中六个事实忠实度问题：`started/incomplete` 状态语义、`NOW` 时间轴、缺失指标的 `Unknown`、SSE 触发的重复 fetch、异步响应竞态、live 失败后的显式重试。补充 4–6 个 browser smoke tests。

本轮禁止新增 schema、store、runtime event、raw-log 解析、日志数据库、Stillwrite RPC、observability warehouse、向量库、AI Analysis Dashboard 或 Run Analysis 页面。只改现有 Console 投影与其浏览器交互；不得改变后端事实来源。

## Desired behavior

- `started` 是仍在进行的请求：显示 live elapsed，并让时间轴覆盖到当前 `now`。
- `incomplete` 不是可证明仍在进行的请求：不得伪造 elapsed 或把它绘成 live；缺少结束事实时显示 `Unknown`。
- latency、input、output 缺少事实时显示 `Unknown`，不以 `0` 参与比例尺或 tooltip 数值判断。
- 有活动请求时 `NOW` 位于实际当前时间；无活动请求时使用完成时间轴，不强行显示 `NOW`。
- 一次 SSE `run_changed` 只触发一次必要的列表刷新和一次选中 run 投影刷新。
- 旧的 list/projection 响应不能覆盖较新的选择或请求；用户 Refresh 或重新选择 run 后，live stream 可以再次建立。

## Code map

| Area | Existing authority | Change |
| --- | --- | --- |
| Overview facts | `web-ui/src/state.ts` (`isActiveRequest`, `endMs`, `metricValue`, `buildOverview`) | 修正状态、now 边界和 nullable metric；保留现有投影模型。 |
| Overview display | `web-ui/src/components/overview-strip.ts` | 正确显示 Unknown、elapsed、时间轴右端和 ticker。 |
| Live coordination | `web-ui/src/views/console-view.ts` (`syncStream`, `scheduleInvalidate`, `reloadRuns`, `reloadProjection`) | 去重 fetch、丢弃 stale response、实现显式 retry。 |
| Browser proof | `web-ui/` smoke harness | 用现有 UI/API 契约验证 4–6 个事实场景，不引入运行时 schema。 |

## Tasks & Acceptance

1. [x] 在 `state.ts` 修正 `started` 与 `incomplete` 的 active/elapsed 语义；将未知指标保持为未知，比例尺只使用已知值；活动请求将 `now` 纳入时间轴。
2. [x] 在 `overview-strip.ts` 更新 tooltip、header 和 axis，使 Unknown 不被渲染成 0，且 NOW 与投影时间轴一致。
3. [x] 在 `console-view.ts` 给 list/projection 请求增加最小的请求代次或等价 guard；SSE invalidation 不重复拉取选中 run；只在 Refresh/重新选择等明确动作后恢复 live retry。
4. [x] 增加 4–6 个 browser smoke tests：完成 run 轴、started+NOW、incomplete、缺失指标、SSE 单次刷新、live 失败后的显式重试；另以 smoke 覆盖异步旧响应竞态。
5. [x] 运行 TypeScript 检查、构建、现有 Python Console 测试和 smoke tests；不修改不相关 dirty worktree 文件。

## Acceptance criteria

### Scenario: active request and NOW

- Given a run containing a `started` request
- When the Live Overview renders
- Then it shows live elapsed and the rendered time axis reaches the current `now`/`NOW` boundary.

### Scenario: incomplete request

- Given a request whose status is `incomplete` and has no authoritative finish/duration
- When the overview renders
- Then it is not treated as an active request and its unavailable latency is `Unknown`.

### Scenario: missing metric

- Given a row without the selected usage or duration fact
- When that metric is selected
- Then the UI shows `Unknown` and the row does not distort the numeric scale as zero.

### Scenario: one invalidation

- Given one SSE `run_changed` event for the selected run
- When invalidation settles
- Then exactly one list request and one selected-run projection request are made.

### Scenario: stale response and retry

- Given overlapping requests or a live EventSource error
- When a newer selection, Refresh, or explicit retry occurs
- Then stale data cannot replace the current selection and the stream can reconnect once the user requests it.

## Verification

```text
npm run check --prefix web-ui
npm run build --prefix web-ui
npm run smoke --prefix web-ui
timeout 180 .venv/bin/pytest -q tests/test_web_console.py
.venv/bin/ruff check src/zuaef_agent/web tests/test_web_console.py
```

## Verification evidence

- `npm run check --prefix web-ui`：通过。
- `npm run build --prefix web-ui`：通过。
- `npm run smoke --prefix web-ui`：通过；六个场景连续运行三次均通过。
- `timeout 180 .venv/bin/pytest -q tests/test_web_console.py`：18 passed，7 warnings。
- `.venv/bin/ruff check src/zuaef_agent/web tests/test_web_console.py`：通过。
- `git diff --check`：通过。

The existing projector, API contracts, receipts, and runtime event model remain the sole authorities. T017/T018 projection work and T019–T023 Run Analysis/Stillwrite closure are deferred until this fidelity fix is verified.

## Suggested Review Order

**Live stream and request coordination**

- 先看 stream 身份 guard 与 SSE 去重，理解竞态和重试边界。
  [`console-view.ts:136`](../../web-ui/src/views/console-view.ts#L136)

- 再看 list/projection 代次 guard，确认旧响应不会覆盖当前选择。
  [`console-view.ts:185`](../../web-ui/src/views/console-view.ts#L185)

**事实投影与呈现**

- 查看 started/incomplete、NOW 和 Unknown 的纯函数语义。
  [`state.ts:223`](../../web-ui/src/state.ts#L223)

- 查看 tooltip、可访问标签和时间轴视觉绑定。
  [`overview-strip.ts:200`](../../web-ui/src/components/overview-strip.ts#L200)

**浏览器证明与构建入口**

- 按六个场景检查真实浏览器交互与请求计数。
  [`browser-smoke.mjs:408`](../../web-ui/smoke/browser-smoke.mjs#L408)

- 查看 check/build/smoke 的最小命令入口。
  [`package.json:6`](../../web-ui/package.json#L6)
