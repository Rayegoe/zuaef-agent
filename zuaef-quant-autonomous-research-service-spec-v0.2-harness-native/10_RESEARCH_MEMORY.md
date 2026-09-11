# Research Memory

## 1. Durable Research Packet

位置：

```text
workspace/artifacts/quant/research/<scope>/<symbol>/
```

内容：

```text
symbol
as_of
research_status
coverage
thesis
supporting facts
counter evidence
risks
invalidation
scenarios
unknowns
source references
```

不包含：

```text
tool trace
token usage
prompt
model hidden reasoning
```

---

## 2. Research reuse

下一次研究：

```text
current evidence
+
latest Research Packet
+
ConversationSearch if needed
```

旧 Research Packet 是：

```text
prior hypothesis
```

不是 current market truth。

必须重新检查 current quote / current evidence。

---

## 3. Generic Memory 暂不参与

不要把 Research Packet 复制进 Harness Memory。

以后如要启用 Memory，只存：

```text
stable user preferences
report style
risk preference if explicitly managed
```

不存 current market state。

---

## 4. Case

Case bound 时，可以把高价值、长期成立的客户业务背景写入 Case。

仍然要求 provenance。

---

## 5. Research artifact 与 Knowledge

不要每次研究都写成 durable Knowledge。

只有反复验证、跨 case 有价值的稳定方法论才考虑 Knowledge promotion。
