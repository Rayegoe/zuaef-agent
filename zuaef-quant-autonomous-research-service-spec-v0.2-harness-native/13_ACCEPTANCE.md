# Acceptance

## Harness-native acceptance

### A. Context

Normal multi-turn Quant chat:

```text
old tool results are not blindly replayed
```

Pause/resume still restores exact execution frontier.

### B. Conversation Search

A user asks:

```text
上次我们对600550的主要风险是什么
```

Agent can retrieve prior semantic/research facts without replaying entire old execution.

### C. Context Controls

Large tool outputs do not remain indefinitely in prompt.

### D. ToolSearch

Chinese query can discover deferred research capabilities.

---

## Data acceptance

### Cache miss

No cache for 600550.

User requests full analysis.

Expected:

```text
fetch_history
cache write
symbol context continues
```

Forbidden:

```text
“只能等25天”
```

---

## Research acceptance

Full analysis can include, when evidence available:

```text
current market
history
strategy context
structured finance evidence
web research
sandbox stats
scenario forecast
conditional recommendation
```

---

## Degradation

If WebSearch fails:

```text
technical/history analysis still completes
research PARTIAL
```

If Sandbox fails:

```text
fixed evidence still completes
no fake probabilities
```

---

## Evidence

Every market claim must come from:

```text
current-run host evidence
current-run web evidence
current-run sandbox derivation
```

Conversation memory alone is not market evidence.

---

## Customer intelligence

Customer-reported claim:

```text
saved as UNVERIFIED
can influence research
cannot create READY/NEAR
```

---

## Runtime

Original unresolved-tool incident root cause is demonstrated and regression-tested.

Normal customer chat never shows full token/tool dump.

---

## Regression

Must not change:

```text
frozen S3
candidate selection
PIT status
profitability status
trade ledger semantics
READY/NEAR source
auto-trading boundary
monitor determinism
```
