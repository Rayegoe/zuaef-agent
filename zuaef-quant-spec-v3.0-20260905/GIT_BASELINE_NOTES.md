# Git Baseline Notes

The GitHub repository `Rayegoe/zuaef-agent` was used only as a **structural baseline**, because the operator explicitly states that Git can lag the currently running system by several hours.

Baseline inspection included repository metadata and current-tree searches/fetches around Quant tooling, including `tools/quant_trading_monitor.py` and `tools/quant_build_candidates.py` where available through the connected repository.

This pack deliberately avoids asserting that GitHub `main` exactly equals the deployed runtime. Codex must inspect the local running tree before edits and reconcile differences in `BASELINE_RUNTIME.md`.

The latest runtime facts in `00_SOURCE_OF_TRUTH_AND_CURRENT_STATE.md` override any older repository snapshot for behavioral status.
