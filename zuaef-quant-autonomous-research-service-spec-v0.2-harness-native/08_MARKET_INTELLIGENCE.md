# Market Intelligence

## 1. 两层结构

### Structured Finance Evidence — Quant owned

第一阶段可以提供一个 bounded tool：

```text
get_market_intelligence(symbol)
```

仅负责：

```text
recent official notices
structured company news
possibly fundamentals
```

使用已有 side-env/AKShare 能力。

### Open-ended Research — Harness owned

需要回答：

```text
为什么最近异动
行业发生了什么
政策有什么影响
海外有没有相关信息
```

时使用：

```text
WebSearch
WebFetch
```

由 Harness/PydanticAI capability 提供。

---

## 2. Quant tool 不做什么

不要让 `get_market_intelligence()` 逐渐变成：

```text
crawler
search engine
browser
research agent
```

只做 bounded structured evidence adapter。

---

## 3. Web evidence contract

WebSearch/WebFetch 得到的事实必须保留：

```text
source
published_at if known
observed_at
url/ref
```

LLM 不得只说：

```text
网上消息显示
```

---

## 4. Customer evidence

用户在 Feishu 提供：

```text
“供应商说订单很满”
```

记录为：

```text
CUSTOMER_REPORTED
UNVERIFIED
```

可以影响：

```text
attention
research hypothesis
web search terms
scenario discussion
```

不能直接影响：

```text
READY/NEAR
candidate pool
strategy
fills
```

---

## 5. Case integration

Case bound：

优先使用 Case durable situation/trajectory。

无 Case：

使用 Quant research artifact 按 analysis_scope 隔离。
