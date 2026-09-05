# Quant Telegram Phase 2 v0.1 — Bridge + T8 投递（含 5 项钉死修正）

## 已确认设计（上一版 + 你的 5 项修正，全部并入）
E1/E2 走 Agent；E3/E4/E5 确定性文案；self-delivery 无审批+固定范围收件人；quant-decision 挂 telegram 插件；bridge = oneshot + systemd timer；gateway 本体零改动。

## 五项修正的落地

### ① 唯一投递权威 = bridge（interpretation-only run）
- §9 run prompt 增加硬约束行：`You have no delivery authority. Do not send, report, or deliver anything anywhere — the bridge delivers your explanation. Explain only.`
- **host 侧守卫**：run 返回后 bridge 检查 `receipt.tool_effect_facts`，若出现任何 telegram-send 效应 → 视为投递权威违规：bridge **不转发 presentation、不补发**（避免双发），事件标记 delivered+violation，记入 bridge.jsonl（`DELIVERY_AUTHORITY_VIOLATION`）。
- **失败测试**：注入假 telegram 效应的 FunctionModel run → 断言 bridge 不产生第二条发送。

### ② 游标 ≠ 投递身份
- byte-offset 游标只表示"读到哪"；**delivery identity 另立**：bridge state 保存 bounded `delivered_ids`（最近 500 条，identity = `type:symbol:ts`，无哈希——hash admission rule）。
- **source reset 规则**（deterministic）：`os.stat` 的 `st_ino` 变化 或 `size < stored_offset` → 判定 truncate/rotate，游标归 0 重扫，靠 delivered_ids 防重发。

### ③ ordered, line-by-line, checkpoint-after-delivery
读一行 → 处理 → 投递成功 → 原子 checkpoint 到该行行尾（tmp+rename，镜像 receipt_store 模式）→ 下一行。A✓B✓C✗ 场景：offset 停在 B 行尾，下 tick 只重投 C。

### ④ SYSTEM_RECOVERED 的确定性证据规则
`pending_recovery` 仅在 E3(LIVE_CONNECTION_LOST) 投递后置位；恢复判定（bridge 读 canonical state，**Agent 永不判定 recovery**）：
```
in_trading_session(now) AND state.json.system_unavailable == false
AND heartbeat_age ≤ 90s   ← 沿用 M1 既有 NOW_STALE_AFTER_S 契约
```
满足 → 发一次 SYSTEM_RECOVERED，清位。`in_trading_session` 直接 import 渲染器现有实现（不复制镜像）。

### ⑤ T10 continuity 单一真相
**不造新阈值**：日报 continuity 直接复用渲染器 `load_real_trend()` 的 m1 verdict（PASS/PARTIAL/NO_REAL_EVIDENCE）——Dashboard 与 Telegram 日报同一实现，杜绝两套真相。

## 路径安全链（T8，最终形态）
`user/model path → workspace-relative 归一化 → resolve() → is_relative_to(quant_delivery_root) → 扩展名白名单 {html,json,csv,md,pdf,txt} → 常规文件（非 symlink，resolve 后仍在根内）→ ≤20MB → 发送`；补 symlink escape 测试。

## TELEGRAM_CHAT_ID
只写本机 `.env`（值 = supervisor chat，来自 gateway session binding），不进 repo/manifest/测试 fixture；测试一律假 chat id。

## 文件修改
1. `tools/quant_trading_monitor.py`：CLI ack 三处 append_alert 补 `ts`（行 596/639/664，事件契约必要修复）。
2. `plugins/zuaef-telegram/zuaef_telegram/client.py`：+`send_document(path, caption)`（multipart，镜像 gateway 实现，redact_token）。
3. `plugins/zuaef-telegram/zuaef_telegram/toolset.py`：+`send_artifact_to_supervisor(path)`（上述安全链；无 approval；固定收件人无 recipient 参数）；TOOLSET_INSTRUCTIONS 更新。
4. `profiles/quant-decision.toml`（repo + 安装副本）：+`[[plugins]] id="telegram"`。
5. **NEW `tools/quant_telegram_bridge.py`**：oneshot bridge
   - 消费 alerts.jsonl（offset 游标 + delivered_ids，②③语义）
   - 分发：E1/E2 → `start_profile_run(profile="quant-decision", surface="telegram", actor_role="supervisor", 全新 conversation_id)` + ①守卫；E3/E4/E5/SYSTEM_RECOVERED → 确定性文案（④规则）；§22.1 Agent 失败 → 降级文案即已投递
   - T10 日报（⑤单一 verdict）
   - `.zuaef-state/quant-bridge/{state.json, bridge.jsonl}`（runtime state，非第二账本；bridge.jsonl 含 event id/trading ts/run_id/delivery 结果/violation）
6. NEW `ops/systemd/zuaef-quant-bridge.{service,timer}`：Type=oneshot，TimeoutStartSec=900，proxy Environment 镜像 gateway unit，timer 45s（agent run 期间 systemd 自动不重叠）。
7. 测试：monitor ts 断言；telegram 插件 FakeTransport（send_document/越界/symlink escape/无 approval/双插件组合）；bridge（FakeAdapter + monkeypatch start_profile_run：分发矩阵/逐行 checkpoint/发送失败不推进/source reset 防重发/E3→RECOVERED 规则/日报一次/①违规不双发——FunctionModel 模式镜像 test_gateway_bridge）。
8. `docs/quant/README.md` addendum + `BUILD_MANIFEST.json`（新文件入册，covers-all 契约）+ ruff。

## 不做（§3 + 守卫）
第 7 个 quant tool、inline buttons、第二账本、Agent 轮询/常驻、NEAR 刷盘、自动下单、WAIT/MARKET_CLOSED/NO_TRADE 推送、盘前通知、Gateway 改动、客户审批路径改动、kernel/composition ABI 改动（tool masking 不做，用 ①的三层替代）。

## 如实限制
E1 无股票中文名；会话内 crash 无 durable alert（bridge 不可见）；Telegram 回复执行动作需 session 已切 quant-decision profile；**代码全绿 ≠ §25 完成——T12：下一真实 A 股时段，用户零发起、Runtime→Bridge→Agent→Telegram 手机收到，§25 才从 IMPLEMENTED 变 PROVEN**；完工定语 = "事件驱动的人机决策助理，非自动交易系统"。