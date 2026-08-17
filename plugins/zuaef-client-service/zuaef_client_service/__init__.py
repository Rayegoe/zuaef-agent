"""ZUAEF Client Service Decision Slice plugin (SPEC v0.1).

Exposes the ``client-service`` ``zuaef.plugins`` entry point. The plugin
combines a deterministic policy engine over a private business corpus with
four domain tools; it never modifies the ZUAEF core (§5.1).
"""

from __future__ import annotations

from .canonical import CANONICAL_POLICIES, policy_by_id
from .models import (
    CustomerAssessment,
    CustomerState,
    InteractionReceipt,
    Policy,
    PolicyMatch,
)
from .plugin import build_plugin
from .policy import decide, match_policies, merge_matches
from .store import ClientServiceStore, CorpusError
from .toolset import ClientServiceToolset

__all__ = [
    "CANONICAL_POLICIES",
    "ClientServiceStore",
    "ClientServiceToolset",
    "CorpusError",
    "CustomerAssessment",
    "CustomerState",
    "InteractionReceipt",
    "Policy",
    "PolicyMatch",
    "build_plugin",
    "decide",
    "match_policies",
    "merge_matches",
    "policy_by_id",
]
