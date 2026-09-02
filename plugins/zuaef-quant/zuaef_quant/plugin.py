"""``zuaef-quant`` plugin factory (ZUAEF-ASHARE-001 P3).

Exposes the QuantDecision capability over the existing plugin composition
ABI: three model-visible deterministic tools (evaluate_strategy,
get_live_signals, record_trade_outcome) plus stable domain instructions.
Heavy quant work runs in the .venv-quant side environment via subprocess;
this package itself carries no data stack. The evaluator, market rules,
costs and benchmark are host-owned: the Agent may only supply a bounded
StrategySpec (numeric thresholds) and interpret the returned evidence.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic_ai.capabilities import Capability

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError, PluginBundle, PluginEnv

from .toolset import make_toolset

QUANT_INSTRUCTIONS = """\
You support a small-capital A-share trader with evidence-based decisions.

1. Evidence before intuition; simulation before capital.
2. Distinguish backtest, paper and real evidence. Real evidence outranks
   simulated evidence when they conflict, respecting sample size.
3. Research rounds follow one shape, then END: read the prior Strategy
   Result → propose one material mutation → evaluate_strategy exactly once
   → write the child's Strategy Result → stop. One evaluation per round is
   a hard host limit.
4. Never claim an opportunity without deterministic trigger evidence
   from get_live_signals. NO_TRADE is always a valid answer.
5. evaluate_strategy is host-owned: you cannot modify the evaluator,
   market rules, cost model, data split or benchmark; do not try.
6. Never generate or execute arbitrary strategy Python; supply numeric
   strategy parameters only.
7. Decision Briefs: use get_live_signals for triggers, decide
   NO_TRADE / WATCH / ENTER_CANDIDATE / HOLD / REDUCE / EXIT, and persist
   via record_decision_brief. ENTER_CANDIDATE is a candidate, never an
   order; the user decides whether to act.
8. File tools take workspace-relative paths — use the result_file path
   exactly as returned by tools; never prefix it.
9. State uncertainty and data limitations explicitly; the universe carries
   a current-membership survivorship limitation.
"""

#: Side-environment python used for evaluation/live scans (repo-relative).
QUANT_PYTHON_ENV = "ZUAEF_QUANT_PYTHON"
QUANT_PYTHON_DEFAULT = ".venv-quant/bin/python"


def resolve_quant_python(workspace_root: Path) -> Path:
    from .toolset import REPO_ROOT

    configured = os.getenv(QUANT_PYTHON_ENV)
    path = Path(configured) if configured else REPO_ROOT / QUANT_PYTHON_DEFAULT
    if not path.is_file():
        raise CompositionError(
            "quant plugin side environment missing: "
            f"{path} not found (set {QUANT_PYTHON_ENV} to the python that "
            "has akshare/qlib installed)"
        )
    return path


def create_plugin(env: PluginEnv, config: dict[str, Any]) -> PluginBundle:
    del config  # non-secret free configuration stays out until a need appears
    quant_python = resolve_quant_python(env.workspace_root)
    toolset = make_toolset(quant_python=quant_python, workspace_root=env.workspace_root)
    capability: Capability[CoreDeps] = Capability(
        id="quant-decision",
        description="Evidence-based A-share strategy research and decision support.",
        instructions=QUANT_INSTRUCTIONS,
        toolsets=[toolset],
    )
    return PluginBundle(capabilities=[capability])
