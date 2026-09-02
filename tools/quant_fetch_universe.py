"""P1 universe preparation: bounded deterministic CSI500 subset (ZUAEF-ASHARE-001).

Selects a stride sample of the current CSI500 constituent list (documented
PIT limitation: today's membership is used for all historical dates), then
fetches qfq + raw daily history per member into the local cache.

Scope-reduction filters (spec 04 §6), each reported explicitly:
- ST/risk-warning names excluded (name contains "ST");
- names whose fetched history starts too late to provide lookback are
  excluded (first bar after --min-first-bar).

    uv run --group quant python tools/quant_fetch_universe.py [--size 50] [--refresh]
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from quant_core import fetch_csi500_constituents, fetch_history

CACHE_DIR = Path("data/quant-cache")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=50, help="target subset size")
    parser.add_argument("--stride", type=int, default=10, help="stride over sorted constituent codes")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--min-first-bar", type=date.fromisoformat, default=date(2018, 6, 30))
    args = parser.parse_args()

    cons, _, _ = fetch_csi500_constituents(refresh=args.refresh, cache_dir=CACHE_DIR)
    all_codes = sorted(cons["constituent_code"].unique())
    names = dict(zip(cons["constituent_code"], cons["constituent_name"]))

    stride_sample = all_codes[:: args.stride][: args.size * 2]
    excluded_st = [c for c in stride_sample if "ST" in names.get(c, "")]
    candidates = [c for c in stride_sample if "ST" not in names.get(c, "")][: args.size]

    selected, excluded_lookback = [], []
    start = time.perf_counter()
    for i, code in enumerate(candidates):
        try:
            df, _, _ = fetch_history(code, "qfq", refresh=args.refresh, cache_dir=CACHE_DIR)
            first_bar = pd_first_date(df)
            if first_bar > args.min_first_bar:
                excluded_lookback.append((code, str(first_bar)))
                continue
            fetch_history(code, "", refresh=args.refresh, cache_dir=CACHE_DIR)
            selected.append(code)
            print(
                f"[{i + 1}/{len(candidates)}] {code} {names.get(code, '')} rows={len(df)} "
                f"first={first_bar} last={df['date'].max()}",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001 — report, continue, summarize at end
            print(f"FAILURE fetch {code}: {exc}", flush=True)
    elapsed = time.perf_counter() - start

    out = CACHE_DIR / "universe"
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "universe": "csi500_subset",
        "basis": "index_stock_cons_csindex effective " + str(max(cons["effective_date"])),
        "pit_limitation": "current membership applied to all historical dates",
        "selection": f"sorted codes stride {args.stride} from {all_codes[0]}",
        "size": len(selected),
        "symbols": selected,
        "excluded_st": excluded_st,
        "excluded_insufficient_lookback": excluded_lookback,
        "fetch_seconds": round(elapsed, 1),
    }
    (out / "csi500_subset.meta.json").write_text(
        __import__("json").dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"== universe: selected={len(selected)} excluded_st={len(excluded_st)} "
        f"excluded_lookback={len(excluded_lookback)} fetch_seconds={elapsed:.0f} =="
    )
    return 0 if selected else 1


def pd_first_date(df) -> date:
    return df["date"].min()


if __name__ == "__main__":
    sys.exit(main())
