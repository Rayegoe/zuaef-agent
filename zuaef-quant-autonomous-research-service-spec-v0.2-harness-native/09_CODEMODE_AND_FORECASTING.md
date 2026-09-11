# CodeMode & Forecasting

## 1. 保留当前 CodeMode

当前 read-only `/quant-cache` 是正确边界。

不得为了方便把：

```text
ledger
candidate state
strategy files
```

挂进可写 Sandbox。

---

## 2. CodeMode 适用

```text
event study
similar-history
forward distribution
relative strength
volatility regime
multi-symbol comparison
custom-window statistics
```

---

## 3. Fixed host tools 适用

```text
quote
membership
positions
candidate
watchlist
market rules
S3 distances
current triggers
```

---

## 4. Forecast contract

不做：

```text
明天一定涨
目标价必到 X
```

正式输出：

```text
Bull
Base
Bear
```

每个包含：

```text
conditions
evidence basis
invalidation
main uncertainty
```

---

## 5. Historical stats

如果 CodeMode 使用历史相似状态：

必须给：

```text
sample size
window
forward horizon
```

低样本不得包装成稳定概率。

---

## 6. Sandbox failure

如果 sandbox failure 但 fixed evidence 可用：

```text
research = PARTIAL
```

不是整个 Runtime FAILED。

只有 unresolved execution frontier 才是 Runtime failure。
