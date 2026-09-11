# Tool Disclosure & ToolSearch

## 1. 目标

避免研究能力扩展后，几十个 tool schema 每轮都进入 prompt。

---

## 2. 常驻核心 Quant evidence tools

可保持直接可用：

```text
get_symbol_context
get_trading_context
get_live_signals
get_analysis_watchlist
update_analysis_watchlist
```

是否全部常驻由实际 schema 成本测试决定。

---

## 3. Deferred / ToolSearch candidates

建议按需加载：

```text
market intelligence
customer evidence intake
research packet history
customer delivery
generic web research
other low-frequency capabilities
```

---

## 4. 复用现有 CJK ToolSearch

ZUAEF Core 已实现中文 tokenization 的 ToolSearch strategy。

不得另写 Quant tool router。

---

## 5. 不引入 scope state machine

禁止新增：

```text
DOMAIN → RETRIEVAL → REPO_AUDIT
request_tool_scope()
```

这些会制造多余 ceremony。

由：

```text
capability composition
+
ToolSearch
+
tool descriptions
+
Skills
```

完成 progressive disclosure。

---

## 6. Tool discovery测试

中文必须可发现：

```text
全面分析
公告
新闻
客户说
加入自选
持仓建议
```

同时避免：

```text
普通股票报价请求
```

无意义加载 customer delivery / repo tools。
