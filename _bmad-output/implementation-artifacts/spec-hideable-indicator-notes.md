---
title: '将量化看板指标备注右侧栏改为隐藏式弹出面板'
type: 'feature'
created: '2026-09-04'
status: 'in-review'
review_loop_iteration: 0
baseline_commit: '58142afaa51b56365cb01d31251a2d14c52296c3'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 量化业务看板的“指标备注”当前作为机会板右侧常驻栏，占用首屏横向空间。用户希望默认隐藏，需要时从右侧弹出查看。

**Approach:** 保留现有 glossary 内容和指标详情 modal，将常驻 aside 改为右侧 drawer；机会板提供打开按钮，drawer 支持关闭按钮、遮罩点击和 Escape 键关闭。

## Boundaries & Constraints

**Always:** 初始状态隐藏；打开按钮使用 `aria-expanded`/`aria-controls`；面板可键盘操作并把焦点还给打开按钮；继续使用唯一的 `GLOSSARY` 与 `data-m` 详情路径；使用现有内嵌 CSS/JS，不引入外部依赖；窄屏不产生横向溢出。

**Ask First:** 无；沿用当前深色看板样式和右侧滑入交互。

**Never:** 不修改指标定义、真实数据、趋势图、候选排序、扫描接口、交易状态或 API；不复制第二份 glossary 数据；不恢复常驻右栏。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| DEFAULT_VIEW | 页面初次加载 | 备注 drawer 隐藏，机会板占满可用宽度，打开按钮可见 | 不依赖 drawer 先显示 |
| OPEN_PANEL | 点击打开按钮 | drawer 与遮罩显示，`aria-expanded=true`，焦点进入关闭按钮 | glossary 仍正常渲染 |
| CLOSE_PANEL | 点击关闭、遮罩或按 Escape | drawer 隐藏，状态恢复，焦点回到打开按钮 | 重复关闭不报错 |
| OPEN_METRIC | 点击 drawer 内指标 | 现有指标详情 modal 显示同一份定义数据 | 未知 key 不打开空 modal |

</frozen-after-approval>

## Code Map

- `tools/quant_render_business_dashboard.py:1320-1333` -- 机会板和当前 `note-side` 常驻右栏模板。
- `tools/quant_render_business_dashboard.py:1490-1511` -- 当前布局、右栏和 modal 样式；补充 drawer、遮罩、响应式规则。
- `tools/quant_render_business_dashboard.py:1545-1567` -- `GLOSSARY`、`renderGlossary()`、指标详情事件；加入 drawer 开关并保持 `data-m` 行为。
- `tools/quant_render_business_dashboard.py:1244-1407,1522-2147` -- 自包含 HTML/CSS/JS 模板；`render_html()` 将其内嵌输出。
- `tests/test_quant_business.py` -- business renderer 回归测试；目标是验证默认隐藏、开关控件和 glossary modal 不回归。

## Tasks & Acceptance

**Execution:**
- [x] `tools/quant_render_business_dashboard.py` -- 用右侧隐藏 drawer 替换 `note-side`，加入 ARIA、遮罩、Escape 和焦点恢复 -- 满足隐藏式弹出需求并保持现有指标说明。
- [x] `tests/test_quant_business.py` -- 增加 HTML 结构和交互钩子断言 -- 防止备注栏重新常驻或详情入口失效。

**Acceptance Criteria:**
- Given HTML 已生成, when 首次打开, then 无常驻指标备注右栏且存在打开按钮。
- Given drawer 隐藏, when 点击打开, then drawer、遮罩和 glossary 显示，`aria-expanded` 为 `true`。
- Given drawer 打开, when 点击关闭、遮罩或按 Escape, then drawer 隐藏且焦点回到打开按钮。
- Given glossary 已显示, when 点击指标, then 原有指标详情 modal 仍显示定义、计算、用法、局限和来源。
- Given 窄屏视口, when 打开 drawer, then 面板不超过视口且机会板无横向溢出。

## Spec Change Log

## Design Notes

drawer 与指标详情 modal 分层；glossary 只渲染到 drawer 一次。通过 `hidden`、`is-open` 和遮罩状态控制显示，不增加组件库。

## Verification

**Commands:**
- `timeout 180 .venv/bin/pytest -q tests/test_quant_business.py` -- expected: 全部通过。
- `.venv/bin/python -m ruff check tools/quant_render_business_dashboard.py tests/test_quant_business.py` -- expected: 无 lint 错误。
- `.venv/bin/python tools/quant_render_business_dashboard.py --out docs/quant/business.html` -- expected: 成功生成含隐藏 drawer 的 HTML。
