# 07 — Implementation Plan

## T001 — Preserve and relabel engineering dashboard

- Keep `docs/quant/dashboard.html`.
- Change visible title/subtitle to make clear it is **Engineering / Audit**.
- Add link to `/` or `/business`.
- Do not change replay/evidence semantics.

**Acceptance:** current engineering artifacts still render with no data loss.

## T002 — Split legacy watchlist from live opportunity universe

- Create `benchmarks/quant/gen1/legacy_watchlist.toml` with the existing four symbols.
- Stop treating current `benchmarks/quant/gen1/universe.toml` as the implicit default live opportunity set.
- Preserve compatibility only as an explicit watchlist input or migrate its content.

**Acceptance:** a four-symbol watchlist cannot silently become the candidate universe.

## T003 — Add candidate builder

New file:

```text
tools/quant_build_candidates.py
```

Responsibilities only:
1. get discovery-base membership;
2. fetch/cache required fundamentals and valuation;
3. normalize metrics;
4. apply eligibility;
5. compute transparent scores;
6. sector-cap the ranked list;
7. write `candidate_snapshot.json` + `active_symbols.json`.

No Agent calls.

## T004 — Add source fallback and freshness evidence

- Keep every fetched dataset with source/retrieval metadata.
- EastMoney-only failures must not destroy the candidate pipeline if an accepted fallback/cache exists.
- Missing essential coverage fails closed.

## T005 — Make live scanner universe explicit

Add:

```bash
python tools/quant_live_scan.py --universe-file <path>
```

Default priority:
1. `data/quant-cache/candidates/active_symbols.json` if valid/non-empty;
2. frozen historical CSI500 subset as compatibility fallback;
3. otherwise loud failure.

Never silently accept `symbols=[]`.

Watchlist scan must be explicit.

## T006 — Add business renderer

New file:

```text
tools/quant_render_business_dashboard.py
```

Read-only inputs:
- candidate snapshot;
- live-scan snapshot if available;
- latest Decision Brief;
- observation log/outcomes;
- active strategy;
- baseline/S1/S2/S3 evidence;
- legacy watchlist.

Output:

```text
docs/quant/business.html
```

Single self-contained HTML; no frontend dependency.

## T007 — Extend local server minimally

`quant_serve.py`:
- `/` and `/business` business page;
- `/engineering` old page;
- `/api/scan` candidate universe;
- `/api/watchlist` legacy watchlist.

Remain loopback-only and read-only.

## T008 — Update daily runner

`quant_daily.sh` must:
- require non-empty active candidate universe;
- run live scan;
- run Agent only on the resulting bounded signal set as today;
- render both pages at the end if renderer inputs are valid.

Do NOT rebuild full candidate fundamentals on every `quant_daily.sh`; candidate refresh is separately invoked.

## T009 — Tests

Add fixture-driven tests for:
- empty universe fails closed;
- 4 legacy names stay separate;
- negative PE does not rank as cheap;
- missing data reduces coverage;
- industry-relative ranking deterministic;
- sector cap deterministic;
- candidate builder output sorted/stable;
- business renderer handles zero triggers;
- business renderer handles one/multiple triggers;
- degraded data banner;
- server routes map to correct pages/endpoints.

No live network in unit tests.

## T010 — Documentation and freeze

Update `docs/quant/README.md`:
- business vs engineering dashboard;
- candidate refresh command;
- three-universe model;
- explicit statement that candidate rank is not a buy recommendation;
- profitability still unproven.

Stop after acceptance. No scheduler/systemd/broker work.
