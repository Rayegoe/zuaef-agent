# 10 — Market Regime / Participation Gate

Initial mode: shadow only.

Fields:
- regime
- participation_permission
- regime_reason_codes
- regime_as_of
- regime_rule_version

Do NOT overload `market_no_trade`.

States:
- DO_NOT_PARTICIPATE
- SELECTIVE
- NORMAL

Start low-dimensional:
- CSI300/CSI500 trend;
- realized volatility;
- market breadth;
- sector breadth/dispersion;
- turnover/liquidity change;
- recent trigger degradation;
- abnormal trading state.

Rollout:
implement deterministic rule -> shadow -> PIT replay 10/20/60 days ->
compare avoided losses vs suppressed opportunities -> explicit promotion review.

Shadow output must never change current production decisions.
