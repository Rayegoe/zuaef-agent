# 07 — Evidence Namespaces

Required namespaces:
- research
- replay
- shadow
- live_forward

Rules:
- replay cannot increment live-forward counters;
- research cannot be relabeled replay;
- shadow cannot be relabeled live-forward;
- live-forward cannot be rewritten after outcomes;
- every metric/report states namespace;
- every promotion decision identifies the namespace supporting each claim.

Common outcome fields:
D+1, D+3, D+5, D+8, MFE, MAE, exit outcome where applicable.
