---
title: '修复 Telegram 插件本地凭据未加载'
type: 'bugfix'
created: '2026-09-05'
status: 'draft'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** 仓库根目录的本地 `.env` 已有 Telegram 凭据，但直接由插件组合层调用 `create_plugin()` 时只读取当前进程环境，没有先加载本地环境文件，因此出现 credentials missing。标准 CLI 因 `AgentSettings.from_env()` 先加载 `.env` 不稳定地掩盖了这个入口差异。

**Approach:** 抽取一个共享的本地 `.env` 加载入口，保持显式进程环境优先；在 `AgentSettings.from_env()` 和 Telegram 插件工厂使用同一入口，使直接组合与 CLI 行为一致。保留缺少本地凭据时的 fail-closed 错误。

## Boundaries & Constraints

**Always:** 只读取仓库根目录 `.env` 作为本地环境来源；`override=False`，显式导出的环境变量优先；profile、CompositionSnapshot、receipt 和日志不接收或打印 token/chat id；缺少任一变量仍抛出原有配置错误；测试不得输出真实凭据。

**Ask First:** 无。

**Never:** 不把 Telegram 凭据写入任何 TOML profile、代码、测试 fixture、快照或 systemd unit；不放宽插件的缺凭据 fail-closed 语义；不增加第二套 profile 配置字段；不发送真实 Telegram 请求作为测试。

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| EXPLICIT_ENV | 两个变量已在进程环境中，`.env` 也存在 | 使用进程环境值，不被 `.env` 覆盖 | 不泄露值 |
| LOCAL_DOTENV | 进程变量缺失，仓库 `.env` 含两个变量 | 插件工厂和标准配置入口都能读取本地凭据 | 只在本地加载，不改 profile |
| MISSING_CREDENTIAL | 进程变量和本地 `.env` 都缺少任一变量 | 组合失败并保留 `credentials missing` | 不创建半配置客户端 |

</frozen-after-approval>

## Code Map

- `src/zuaef_agent/config.py:8-10,207-225` -- 已有 `python-dotenv` 依赖和 `AgentSettings.from_env()`，当前唯一的仓库 `.env` 加载点；抽取共享入口并保持现有配置行为。
- `plugins/zuaef-telegram/zuaef_telegram/plugin.py:22,41-55` -- profile 解析时调用的工厂；当前直接 `os.getenv()`，导致绕过配置入口时失败。
- `plugins/zuaef-telegram/zuaef_telegram/canary.py:20-31` -- Telegram 直接验证入口；只应复用同一 local-env 规则，不改变发送/错误语义。
- `plugins/zuaef-telegram/zuaef_telegram/notify.py:29-43` -- 机械通知入口；只应复用同一 local-env 规则，不改变消息内容或发送边界。
- `tests/test_cli_and_providers.py:112-143` -- 已验证 `AgentSettings.from_env()` 从项目根 `.env` 加载，提供配置入口回归模式。
- `tests/test_telegram_plugin.py:86-184,350-386` -- Telegram 工厂、缺凭据及 notify 入口测试；补充显式环境优先、本地 `.env` 加载和隔离缺凭据场景。

## Tasks & Acceptance

**Execution:**
- [ ] `src/zuaef_agent/config.py` -- 提供幂等的仓库本地 `.env` 加载函数，并由 `AgentSettings.from_env()` 复用 -- 避免多个入口各自实现加载规则。
- [ ] `plugins/zuaef-telegram/zuaef_telegram/plugin.py`, `canary.py`, `notify.py` -- 在读取 Telegram 凭据前复用共享本地环境入口 -- 直接入口与 CLI 一致且不读取 profile secrets。
- [ ] `tests/test_telegram_plugin.py` -- 覆盖显式环境优先、本地 `.env` 可用和无本地凭据仍失败 -- 防止回归及真实凭据泄露。

**Acceptance Criteria:**
- Given 进程环境未导出变量但仓库 `.env` 含两个变量, when `zuaef-agent profile check quant-decision` 或插件工厂运行, then 组合成功且输出中不出现任一凭据值。
- Given 进程环境与 `.env` 同时存在不同值, when 读取凭据, then 使用进程环境值。
- Given进程环境和本地 `.env` 都缺少任一变量, when 组合 Telegram 插件, then 保持 fail-closed 并返回 `credentials missing`。
- Given profile 文件, when 读取或序列化 profile/snapshot, then 只含非 secret 配置，不新增 Telegram 凭据字段。

## Spec Change Log

## Design Notes

共享函数只负责将仓库根 `.env` 的本地变量注入当前进程；插件仍只通过 `os.getenv()` 使用值。显式环境优先保证 systemd、shell 和 CI 可以覆盖本地文件，而 profile 永远保持非 secret。

## Verification

**Commands:**
- `env -u TELEGRAM_BOT_TOKEN -u TELEGRAM_CHAT_ID .venv/bin/pytest -q tests/test_telegram_plugin.py tests/test_gateway_cli.py` -- expected: 全部通过。
- `env -u TELEGRAM_BOT_TOKEN -u TELEGRAM_CHAT_ID .venv/bin/zuaef-agent profile check quant-decision --config-root .` -- expected: 组合成功，输出不含 token/chat id 值。
- `.venv/bin/python -m ruff check src/zuaef_agent/config.py plugins/zuaef-telegram/zuaef_telegram tests/test_telegram_plugin.py` -- expected: 无 lint 错误。
- `git diff --check` -- expected: 无空白错误。
