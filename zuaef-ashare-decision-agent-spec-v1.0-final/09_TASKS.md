# Tasks

Checklist labels below are implementation planning only. Do not turn them into runtime states.

## U0 — Upstream
- [ ] **U001** Record `git status --short --branch` and local HEAD; preserve dirty worktree.
- [ ] **U002** Keep upstream-refresh changes separate from Quant business code.
- [ ] **U003** Resolve/test Pydantic AI 2.35.3 + Harness 0.27.x.
- [ ] **U004** Run upstream probe and full repo regression.
- [ ] **U005** Move fixed context thresholds to validated model-relative fractions where compatible.
- [ ] **U006** Pin validated Harness minor range; remove unbounded `>=0.1` behavior.
- [ ] **U007** Update upstream baseline record.

## P0 — Data
- [ ] **D001** Add AKShare in the smallest isolated dependency scope.
- [ ] **D002** Fetch one real A-share daily-history series.
- [ ] **D003** Fetch CSI500/index constituent-related data.
- [ ] **D004** Fetch current market snapshot and surface its timestamp.
- [ ] **D005** Measure latency/freshness and failure behavior.
- [ ] **D006** Add simple local historical cache with source/retrieval metadata.
- [ ] **D007** Normalize columns/types needed by evaluator/Qlib.
- [ ] **D008** Document actual PIT/universe/status limitations.

## P1 — Baseline strategy
- [ ] **S001** Define minimal StrategySpec v1.
- [ ] **S002** Implement one fixed price/volume baseline strategy.
- [ ] **S003** Prove no future-reference/lookahead in signal logic.
- [ ] **S004** Feed normalized real data into Qlib 0.9.7 through public supported mechanisms.
- [ ] **S005** Produce deterministic trade intents/signals.
- [ ] **S006** Calculate after-cost trade metrics.
- [ ] **S007** Emit `strategy.toml`, `evidence.json`, `trades.csv`, `equity.csv`.
- [ ] **S008** Produce a readable baseline result.

## P2 — Replay / A-share truth
- [ ] **R001** Freeze Qlib trade intents/signals as replay input.
- [ ] **R002** Validate/install maintained Backtrader-compatible replay runtime or prove a minimal replay is smaller/safer.
- [ ] **R003** Implement/test T+1.
- [ ] **R004** Implement/test suspension non-trade.
- [ ] **R005** Implement/test limit-up buy and limit-down sell blocking.
- [ ] **R006** Implement/test quantity/lot behavior for supported universe.
- [ ] **R007** Implement/test commission, minimum commission, stamp duty and slippage from frozen config.
- [ ] **R008** Use raw executable prices, not adjusted synthetic execution prices.
- [ ] **R009** Compare Qlib/replay performance and blocked trades.
- [ ] **R010** Fail/limit claims when required historical tradeability data is missing.

## P3 — ZUAEF integration
- [ ] **Z001** Create `plugins/zuaef-quant`.
- [ ] **Z002** Build QuantToolset around proven functions.
- [ ] **Z003** Build lightweight `Capability(id="quant-decision", ...)`.
- [ ] **Z004** Return it via existing PluginBundle.
- [ ] **Z005** Add narrow `quant-decision` profile.
- [ ] **Z006** Expose `evaluate_strategy`.
- [ ] **Z007** Expose `get_live_signals`.
- [ ] **Z008** Expose `record_trade_outcome`.
- [ ] **Z009** Confirm no business-domain Core change.
- [ ] **Z010** Run one real-model task and write Strategy Result.

## P4 — Learning
- [ ] **L001** Freeze benchmark dates/protocol and hashes.
- [ ] **L002** Separate iterative research, host-only promotion test and hidden champion holdout.
- [ ] **L003** Fresh strategy iteration 1.
- [ ] **L004** Fresh iteration 2 reading iteration 1 result.
- [ ] **L005** Fresh iteration 3 reading relevant prior result(s).
- [ ] **L006** Verify one material mutation per child or explicit direction change.
- [ ] **L007** Produce three-run learning analysis.
- [ ] **L008** After pass, implement 10-run A/B history-exposure test.
- [ ] **L009** Add Harness SpendLimits before materially larger autonomous runs.

## P5 — Live
- [ ] **V001** Define human/host-owned active strategy set.
- [ ] **V002** Deterministically scan current snapshot.
- [ ] **V003** Reduce broad universe to bounded candidates before LLM.
- [ ] **V004** Build compact DecisionContext.
- [ ] **V005** Generate Decision Brief from real/current evidence.
- [ ] **V006** Measure feed-to-brief staleness.
- [ ] **V007** Verify `NO_TRADE` without forced candidate.
- [ ] **V008** Add host watcher only if interactive use proves insufficient.

## P6/P7 — Feedback
- [ ] **F001** Record paper decision artifact.
- [ ] **F002** Settle paper outcome using frozen strategy/rules.
- [ ] **F003** Generate daily review.
- [ ] **F004** Record manually executed real trade.
- [ ] **F005** Compare intended vs actual execution.
- [ ] **F006** Compare historical vs paper vs real evidence.
- [ ] **F007** Feed result into next reflection without exposing hidden holdout.

## Regression
- [ ] Existing root tests pass.
- [ ] Ruff passes under repository policy.
- [ ] Quant tests protect real false-alpha failure modes.
- [ ] No generic Manager/Registry/Workflow/StateMachine framework was introduced.
