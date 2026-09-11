# 03 — Acceptance

## A1 — M0 semantic separation

- every new ledger/event record carries `intent_origin` / `authorization`
  / `venue`; a record without them fails schema validation;
- no code path can persist `authorization=user_ack` except the ack-CLI
  path (enforced by construction + test);
- the three legacy positions are relabeled per evidence, 600519 is
  deduplicated, all three carry
  `legacy_validation_record=true, admissible_to_shadow=false`;
- exit-reason labels show observed % alongside configured % when data
  trust is degraded;
- grep-proof: `user BUY acknowledged` no longer appears anywhere except
  records that genuinely hold `authorization=user_ack`.

## A2 — Replay determinism (gate C)

Run twice into separate locations from identical inputs:

```bash
shadow-replay --as-of <T> --out /tmp/shadow-a
shadow-replay --as-of <T> --out /tmp/shadow-b
diff -ru /tmp/shadow-a /tmp/shadow-b   # must be: 0 differences
```

Also:

```bash
rm -rf workspace/artifacts/quant/shadow
shadow-replay --as-of <T>              # full reconstruction (gate B)
```

## A3 — Isolation (gate A)

- canonical `positions.json` byte-identical before/after any replay run;
- no file written outside `workspace/artifacts/quant/shadow/`;
- replay adds zero model requests and zero Agent tool calls (receipt /
  usage receipt check).

## A4 — Evidence gate (gate D)

- with data trust FAIL (current production state), Shadow runs and
  produces artifacts; every artifact and any surface that renders
  performance carries:

  ```text
  PERFORMANCE EVIDENCE: INVALID / NOT ADMISSIBLE
  Reason: PIT trust gate failed
  ```

- when v3.1 PIT remediation reaches CLEAN, the same artifacts become
  admissible without code change (the gate reads trust status, it does
  not recompute it).

## A5 — Regression

- quant-decision profile, monitor, bridge, workbench: unchanged behavior;
- canonical-ledger write path (ack-CLI) unchanged for legitimate user
  flows;
- new fields are additive; existing consumers of positions.json /
  alerts.jsonl keep working (additive schema only).

## Non-goals (restated, with their own future admission gates)

- Qlib Account runtime, vn.py PaperAccount, RQAlpha: deferred; each
  requires its own reproduced-failure admission (intraday paper execution
  for vn.py; measured replay-engine insufficiency for Qlib);
- intraday fidelity (partial fills, queues, impact): deferred;
- PIT remediation: owned by v3.1 (06/09), prerequisite for admissible
  performance evidence, not for this build.
