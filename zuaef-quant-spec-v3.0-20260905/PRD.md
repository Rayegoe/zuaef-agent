# PRD — ZUAEF Quant v3.0

## Problem

The current Quant runtime can operate, generate a 50-name candidate pool, evaluate triggers, produce an offline business report, and deliver it through Telegram. The current blocker is not basic runtime availability: it is evidence quality. PIT is contaminated, live forward observations are still zero, and profitability remains unproven.

At the same time, expanding toward full broker-app feature parity would dilute the product. The next product step is to turn the working runtime into a **decision + evidence + Agent research loop**.

## User outcome

The system should help a small retail operator answer, with evidence:

1. Should I participate now?
2. Which small set of names deserves attention?
3. Is there a valid trigger now?
4. Are current positions approaching exit/risk conditions?
5. Is the strategy degrading?
6. What experiment should be run next, and did it survive replay/shadow/forward validation?

## v3 requirements

- preserve current live/report/Telegram behavior;
- create 10-day PIT-safe recent replay;
- expose structured Agent observe/control actions;
- add a shadow-first market participation regime;
- add targeted evidence retrieval instead of broker-app cloning;
- create S0/S1/S2 code/sandbox experimentation;
- maintain strict separation among historical backtest, replay, shadow, and live-forward evidence;
- keep real broker execution outside the default v3 scope.

## Success metrics

Engineering:
- no regression of current runtime;
- future-data adversarial tests pass;
- replay cannot alter live-forward counts;
- Agent can inspect and safely operate the runtime through structured actions.

Research:
- recent 10-day replay produces auditable day/time decisions or explicit evidence blocks;
- experiments are reproducible and isolated;
- first formal M1 audit occurs at 20 trading days or 30 settled forward triggers, whichever occurs first, with no unresolved evidence-pipeline integrity failure.

See the numbered specifications for normative detail.
