# Data Hydration

## 目标

任意合法 A 股第一次被研究时：

```text
cache miss
→ host 自动补历史
→ 继续分析
```

---

## 复用

必须复用：

```python
tools/quant_core.py::fetch_history
```

---

## 新增薄 seam

建议：

```python
ensure_history(
    symbol,
    adjust="qfq",
    required_bars=25,
    refresh_if_needed=True
)
```

只负责编排：

```text
read_cache
→ validate
→ fetch_history if needed
→ structured evidence
```

---

## symbol-context

修改：

```text
quote fetch
+
ensure_history
+
strategy diagnostics
```

历史获取失败不得抹掉 quote。

---

## Watchlist

Add：

```text
persist watchlist
→ read-back
→ best-effort ensure_history(new symbols)
```

Hydration failure：

```text
watchlist remains added
history = unavailable
```

Agent 必须分别报告。

---

## Freshness

分开：

```text
quote freshness
history freshness
cache structural validity
```

禁止混成一个字段。

---

## 并发

同一 symbol 首次 hydration 可使用 per-symbol bounded file lock。

不得锁整个 quant-cache。

---

## Sandbox

CodeMode 不负责联网补数。

流程必须：

```text
Host hydrate
→ validated cache
→ read-only mount
→ CodeMode
```
