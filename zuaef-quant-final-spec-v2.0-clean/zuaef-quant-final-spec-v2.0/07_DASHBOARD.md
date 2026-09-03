# Business Dashboard Final Shape

## 首页只回答四个问题

### 1. 今天做什么？

- NO_TRADE / WATCH / candidate
- trigger count
- latest report id
- data reliability

### 2. 为什么？

动作候选显示：pullback、volume ratio、stabilization、candidate quality reason、red flags、invalidation。

### 3. 系统证据到哪？

紧凑 badges：

- Semantic PASS/WARN/FAIL
- PIT CLEAN/PARTIAL/CONTAMINATED
- Anti-Leak PASS/FAIL/UNKNOWN
- OOS state
- Forward settled count
- Strategy UNPROVEN/WEAK/PROMISING/REJECTED

### 4. 最近学到了什么？

最多 3 个 Lessons + 3 个 Open Questions + latest Review verdict。

不要把 Research Log 全塞首页。

## Research View

展示 baseline/ablation、IC/RankIC/quantile、exit attribution、walk-forward、regime、cost、trial/search warning。

## Engineering/Audit View

展示 source/provenance、artifact refs、commit、Agent trace refs、semantic/PIT/anti-leak/test gates。

## 禁止

业务页不得变 CI 大屏、schema explorer、tool-call timeline、token monitor 或 50 KPI dashboard。
