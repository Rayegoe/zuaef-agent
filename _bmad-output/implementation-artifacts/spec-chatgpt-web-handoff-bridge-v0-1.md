---
title: 'ChatGPT Web 极薄交接桥 v0.1'
type: 'feature'
created: '2026-08-28'
status: 'done'
review_loop_iteration: 0
baseline_commit: '9947d8d1fc285900eda28a4bdfef51a4f5cbb5c2'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Codex 目前缺少一个低摩擦的本地入口，把提示词交给 ChatGPT Web，并接回用户明确复制的文本或下载的文件。

**Approach:** 增加独立的 `chatgpt-handoff` CLI：复制提示词并打开 ChatGPT，随后将剪贴板或下载文件导入本地 session 与 `artifacts/chatgpt/`。它只是确定性的本地传输工具，不进入 Agent Core。

## Boundaries & Constraints

**Always:** 提供 `ask`、`import-clipboard`、`import-file`、`wait-download` 四个命令；Linux 剪贴板按 `wl-copy/wl-paste`、`xclip`、`xsel` 的可用性选择；每次 `ask` 创建 `.chatgpt-handoff/<timestamp>/prompt.md`；导入文本写入最近 session 的 `response.md`；导入文件使用复制而非移动；ZIP 可直接解压到 session 和 `artifacts/chatgpt/<session>/spec/`；错误使用清晰文本和非零退出码。

**Ask First:** 只有需要新增第三方依赖、改变现有 `zuaef-agent` CLI 行为，或自动操作/读取 ChatGPT 页面时才暂停确认。

**Never:** 不增加门禁、fallback、schema、状态机、hash、manifest、policy、安全 gate、数据库、daemon、浏览器框架、DOM selector、网络拦截、自动登录或 API provider 抽象；不修改下载原件；不把该工具提升为 Capability 或 Core 机制。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 准备问题 | `ask TEXT` 或 `ask --prompt-file FILE` | 保存 prompt、复制到剪贴板、打开 `https://chatgpt.com/` 并打印后续命令 | prompt 为空或文件不存在时直接报错 |
| 导入回答 | 用户已复制回答 | 最近 session 生成 `response.md` | 无 session、无剪贴板后端或读取失败时直接报错 |
| 导入文件 | `import-file FILE` | 原文件不变；复制到 session 和 artifact 目录；ZIP 直接解压 | 文件不存在或 ZIP 无法解压时直接报错 |
| 等待下载 | `wait-download [--dir DIR]` | 忽略临时后缀，发现命令启动后且大小稳定的文件后执行导入 | 目录不存在时报错；无文件时持续等待直到 Ctrl+C |

</frozen-after-approval>

## Code Map

- `pyproject.toml:36` -- 在现有 `[project.scripts]` 中增量加入独立 `chatgpt-handoff` 入口；该文件已有用户修改，必须保留。
- `src/chatgpt_handoff/` -- 新的标准库优先包，与 `zuaef_agent` 运行时隔离；CLI、浏览器、剪贴板、session/下载操作保持少量直接函数。
- `tests/test_chatgpt_handoff.py` -- 使用临时目录和替身命令验证本地闭环，不访问 chatgpt.com。
- `src/zuaef_agent/cli.py` -- 现有主 CLI；只作为 argparse/退出码风格参考，保持只读，避免耦合 Agent Core。

## Tasks & Acceptance

**Execution:**
- [x] `src/chatgpt_handoff/__init__.py`、`cli.py` -- 实现四命令及清晰终端提示。
- [x] `src/chatgpt_handoff/clipboard.py`、`browser.py` -- 实现 Linux 剪贴板命令选择与标准库浏览器启动。
- [x] `src/chatgpt_handoff/handoff.py` -- 实现 timestamp session、最近 session、文件复制、直接 ZIP 解压及稳定下载轮询。
- [x] `pyproject.toml` -- 注册 `chatgpt-handoff = "chatgpt_handoff.cli:main"` 并纳入 wheel package。
- [x] `tests/test_chatgpt_handoff.py` -- 覆盖文本、文件、ZIP、临时下载忽略、文件稳定与原件保留。

**Acceptance Criteria:**
- Given 可用剪贴板后端，when 执行 `ask`，then prompt 被保存和复制且浏览器启动函数收到 ChatGPT URL。
- Given 用户复制回答或下载文件，when 执行对应 import 命令，then 最近 session 与 artifact 目录出现可供 Codex 读取的结果。
- Given 下载目录只有 `.crdownload`、`.part`、`.tmp` 或大小仍变化的文件，when 轮询，then 不提前导入。
- Given 完整测试套件，when 运行目标测试与 lint，then 新功能通过且不要求真实 ChatGPT 登录。

## Spec Change Log

## Verification

**Commands:**
- `uv run pytest -q tests/test_chatgpt_handoff.py` -- 新功能测试全部通过。
- `uv run ruff check src/chatgpt_handoff tests/test_chatgpt_handoff.py` -- 新增代码无 lint 问题。
- `uv run chatgpt-handoff --help` -- 四个子命令可见。

**Manual checks:**
- 实际文本与 ZIP 闭环需要操作者在 ChatGPT Web 中粘贴/发送并明确 Copy/Download；自动化测试不接触页面内容。

## Suggested Review Order

**命令入口**

- 四个命令保持独立分派，不耦合 Agent Core。
  [`cli.py:21`](../../src/chatgpt_handoff/cli.py#L21)

- 人工交接边界通过终端提示明确呈现。
  [`cli.py:57`](../../src/chatgpt_handoff/cli.py#L57)

**本地传输**

- Session 以文件目录表达结果，不引入状态模型。
  [`handoff.py:26`](../../src/chatgpt_handoff/handoff.py#L26)

- 下载文件复制到 artifact，ZIP 直接解压。
  [`handoff.py:62`](../../src/chatgpt_handoff/handoff.py#L62)

- 下载轮询只观察新文件与连续稳定大小。
  [`handoff.py:92`](../../src/chatgpt_handoff/handoff.py#L92)

- 剪贴板按 Linux 常见工具顺序直接选择。
  [`clipboard.py:13`](../../src/chatgpt_handoff/clipboard.py#L13)

- 浏览器只打开 URL，不接触 ChatGPT DOM。
  [`browser.py:11`](../../src/chatgpt_handoff/browser.py#L11)

**验证与安装**

- 21 项测试覆盖四命令及本地适配器。
  [`test_chatgpt_handoff.py:20`](../../tests/test_chatgpt_handoff.py#L20)

- 独立 console script 与 wheel package 增量注册。
  [`pyproject.toml:40`](../../pyproject.toml#L40)
