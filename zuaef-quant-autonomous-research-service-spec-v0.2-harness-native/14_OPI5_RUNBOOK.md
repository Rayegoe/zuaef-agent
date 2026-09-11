# OPi5 Runbook

## Preflight

```bash
cd ~/zuaef-agent
git status --short
git log -5 --oneline
```

Record local differences.

---

## Verify host capability ceiling

Confirm deployment allows:

```text
conversation_search
context_controls
tool_search
web_search
web_fetch
```

Do not silently assume profile request overrides host policy.

---

## Quant env

```bash
test -x .venv-quant/bin/python
.venv-quant/bin/python -c "import akshare; print(akshare.__version__)"
```

---

## Targeted tests

Run:

```text
history hydration
symbol context
watchlist
ToolSearch Chinese discovery
ConversationSearch
context controls
CodeMode
market intelligence
gateway semantic continuity
renderer
runtime unresolved tool
```

---

## Live proof

Use isolated/backup-safe no-cache condition for 600550.

Feishu:

```text
@ZUAEF-BOT 为 600550 做个全面分析和趋势预测
```

Observe:

```text
history hydration
structured evidence
web research if useful
CodeMode if useful
scenario synthesis
research packet
```

Second identical research:

```text
history should hit cache
old tool trajectory should not be replayed wholesale
```

---

## Watchlist

```text
@ZUAEF-BOT 把600550加入自选分析
```

Expected:

```text
watchlist persisted
history prewarm status returned
```

---

## Prior research retrieval

Ask:

```text
@ZUAEF-BOT 上次对600550的核心风险是什么？现在有变化吗？
```

Expected:

```text
retrieve previous research
refresh current evidence
compare
```

Not:

```text
blindly repeat old answer
```

---

## Failure injection

Simulate:

```text
web source fail
sandbox fail
history upstream fail
```

Ensure graceful partial result where possible.

---

## Final report

Codex returns:

```text
Reused
Changed
Harness capabilities enabled
Real proof
Not proven
Operator verification
```
