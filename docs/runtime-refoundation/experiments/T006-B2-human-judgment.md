# T006-B2 — Blind Human / Evidence Judgment

Status: HUMAN VERDICT RECORDED — A PREFERRED; EVIDENCE GATE FAILED

Review only these anonymous drafts:

- [A.md](../../../workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b2-blind/A.md)
- [B.md](../../../workspace/artifacts/writing-v0.2/eval/WCASE-2/t006-b2-blind/B.md)

Do not inspect profile names, selected technique IDs, request counts,
latencies or the experiment record until after recording the judgment.

## Judgment

Overall: **A**

Why (short free text):

```text
A is steadier and keeps the core person, formal v3 specification,
Siguniang Mountain test and commercial information substantially faithful to
the supplied materials. It uses the formal 380 g / 30 hours / 800 lumens /
RMB 699 figures rather than the obsolete 420 g / 24 hours / 600 lumens /
RMB 599 draft figures.

B has livelier prose, but invents concrete scene facts not present in the
interview: the flashlight shining on a teammate's face and the teammate
mumbling and turning over, needing to bring the watch close to the eyes after
dimming it, and sub-zero wind outside the tent. The interview supplied only
4 a.m., a dark tent, searching for a flashlight and the "hot / bright"
motivation.

A also lightly expands beyond the evidence with details such as the tent
being cold and white light being unable to warm it. The no-outside-facts gate
therefore fails for the pair rather than failing only because of B.
```

## Narrow evidence gate

| check | pass / fail / unclear | note |
|---|---|---|
| M002 obsolete figures were not treated as current facts | pass | A uses the formal v3 figures, not the obsolete draft figures. |
| M008 formal spec was correctly prioritized | pass | The 380 g / 30 hours / 800 lumens / RMB 699 specification was used. |
| M005/M006/M009 were not wrongly mixed into product facts | pass | No incorrect product-fact mixing was identified. |
| no facts outside the supplied materials appeared | fail | B adds several unsupported scene facts; A also contains lighter unsupported scene expansion. |

Reviewer/date: user-provided blind editorial review / 2026-08-21

## Anonymous mapping revealed after judgment

- A: model-owned Candidate
- B: Host-selected Control

The model-owned Candidate wins the comparative prose judgment and is less
severe in its unsupported expansion, but it does not pass the evidence gate.
It also reached `limit_reached` after repeated `save_article` calls. This is a
`REFINE` result, not admission or promotion.

The result is not a promotion decision by itself. The experiment record must
combine this gate with the observed Candidate terminal state and runtime
facts, while keeping Phase 2 open until the evidence is sufficient.
