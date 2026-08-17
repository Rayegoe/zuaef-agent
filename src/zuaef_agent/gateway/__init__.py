"""ZUAEF Interactive Business Gateway — surface interaction layer (v0.3).

The Gateway owns transport, identity, authorization, session binding, profile
selection, inbound normalization, outbound rendering, approval UI and
routing-state persistence — and nothing else. It never owns an agent loop,
business policy, approval semantics, or receipts: every run goes through the
shared core seam (``execute_run``) and the shared continuation seam
(``resume_paused_run``).
"""
