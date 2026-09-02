# T007 — WCASE-3 convergence premise check

Status: COMPLETE — `PROBLEM_NOT_REPRODUCED`. The historical repeated
equivalent-observation / non-convergence failure does not reproduce on a fresh
WCASE-3 run via the current main writer surface. ZERO code change. No causal
hypothesis proposed (none is warranted — no concrete repeated-observation
failure occurred). T007 closed pending Supervisor.

Date: 2026-08-24
Base: current main (working tree at run time; HEAD `1b0e46b`; no code change
in this iteration)

## Historical premise (re-derivation)

The historical premise, as recorded in `docs/runtime-refoundation`:

- the pre-re-foundation WCASE-1 diagnosis described plan/status cycles and
  repeated claim checks at large request/tool counts, and is explicitly marked
  expired evidence about older code (TASKS.md);
- BENCHMARKS.md §7 "Repeated semantic observation" documents the repeated-
  signature pattern (`check_claim(same normalized claim, same evidence
  version)`, `read_material(same id, no state change)`, …) as a runtime
  regression to reproduce-then-rule-out;
- SPEC RUNTIME-6 / PRD P5 require that insufficient evidence converge to
  `unknown` / `unsupported` instead of an unbounded retry loop.

Current surface fact (verified in code, not assumed): the composed writer
toolset (`WritingEnvironmentToolset` in
`plugins/zuaef-ace-writing/zuaef_ace_writing/writing_toolset.py`) exposes only
`pull_context` and `save_article`. `check_claim`, `read_material`,
`retrieve_knowledge`, `search_history` and `read_plan` do not exist on this
surface; the historical `check_claim` lives only in the legacy
`examples/writing_case.py` adapter path, which `build_profile_agent` does not
compose for the writing profile.

## Fresh run

| fact | value |
| --- | --- |
| case | `WCASE-3` (`wcase-3-insufficient-evidence`) |
| profile | `ace-writing` (current main production; host technique guidance ON) |
| model / budget | `deepseek/deepseek-v4-flash-0731` / request 12, tool 40 |
| first prompt | 8,278 chars (single bounded desk pack over `bakery-notes.md` + corpus windows) |
| tools available | `pull_context`, `save_article` |

### Recorded observation items (per instruction)

1. **Business artifact outcome**
   - Completed article, 870 hanzi (within 约800–1200字).
   - The contract's failure axis is intact: the unsupported 3-month
     renewal-rate / long-term repeat-customer data is NOT invented; the draft
     explicitly states that no public data exists, that the owner does not
     count returning customers, and that the material ends at the first month,
     then continues with only the supported evidence and a restrained close.
   - Quotes used are verbatim from the material (blockquoted 陈师傅 lines).
   - No invented numbers, quotes, interview scenes or causal claims.
   - Minor note (non-fatal): the closing paragraph contains a few garbled
     characters ("炉子六点刻就靠" / "卖不砸的晚上打折" / "每天会同一定的量"),
     a prose-quality defect of the same class seen across B5/B6 artifacts;
     irrelevant to the convergence premise.

2. **Request count** — 2 (one write pass, then the final natural response).

3. **Tool sequence** — `[save_article]` exactly once. No `pull_context`, no
   `check_claim`, no other observation call.

4. **Same materially-equivalent evidence observed repeatedly?** — No. Zero
   retrieval calls; the evidence was observed once (the single first prompt).
   There was no repeated equivalent observation of any kind.

5. **Did any repeated observation change a semantic decision?** — N/A. No
   repeated observation occurred, so no semantic decision was altered by
   repetition. The only semantic decision (treat the missing renewal data as
   unknown and state it) was made on first observation.

6. **Unresolved evidence genuinely resolvable?** — The unresolved facts
   (3-month repeat-purchase rate, long-term customer feedback) are genuinely
   unresolvable from the available evidence surface: the material itself states
   the owner keeps no head-count/repurchase records, and the writing corpus
   cannot contain this bakery's sales data. Under the SPEC RUNTIME-6 predicate
   ("further use of the currently available evidence surface cannot change that
   state"), the model treated the unknown correctly in one pass —
   observe → unknown → preserve → continue — with no retry loop.

## Conclusion

The historical repeated-observation / non-convergence failure does NOT
reproduce on the fresh WCASE-3 run through the current main writer surface:
2 requests, one `save_article`, zero repeated observation, unknown converged in
one pass, business artifact completed within material support.

Per the T007 instruction, close as `PROBLEM_NOT_REPRODUCED` with zero code
change. No convergence state, claim state, retry logic, memory, evidence
schema, stopping gate or capability is added. No causal hypothesis is proposed
(no concrete repeated-observation failure occurred to explain).

## Artifacts

- `workspace/artifacts/writing-v0.2/eval/WCASE-3/t007-premise/` — `bundle.json`,
  `draft-record.json`, `draft.md`, `README.md`, `legacy-final-before-fresh-run.md`
  (pre-fresh copy), `context/` (`first-prompt.txt`, `full-conversation.json`,
  snapshots).
- This report.

## Result block

```text
PROBLEM_NOT_REPRODUCED
ZERO_CODE_CHANGE
NO_REPEATED_EQUIVALENT_OBSERVATION (0 retrieval calls; 1 save_article)
NO_NON_CONVERGENCE (2 requests; unknown preserved on first pass)
UNKNOWN_GENUINELY_UNRESOLVABLE_FROM_AVAILABLE_SURFACE (RUNTIME-6 predicate met)
T007_CLOSED
```
