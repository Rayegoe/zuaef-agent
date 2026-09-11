"""``zuaef-artifacts`` — native artifact production capabilities.

One plugin, four deferred capabilities (DOCX / PDF / Slides / Spreadsheet).
Each capability bundles a business-semantic description, production guidance,
a bounded deterministic toolset, and format-local QA. Final deliverables are
written only under ``workspace/artifacts/<format>/``; every artifact a run
produces is host-verified into the run receipt by the existing byte-snapshot
settlement — this plugin adds no second receipt or delivery mechanism.
"""

__all__ = ["build_plugin"]
