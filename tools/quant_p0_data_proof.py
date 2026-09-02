"""P0 real-data proof for ZUAEF-ASHARE-001 (spec pack 04_DATA_AND_MARKET.md §2).

Proves, against live AKShare endpoints:
- one stock's real daily OHLCV history loads (qfq research series + raw series);
- CSI 500 constituent data loads;
- a current A-share market snapshot loads;
- timestamps, row/symbol counts, per-request latency and freshness are surfaced;
- historical data is cached locally with source/retrieval metadata;
- fetch failures are reported explicitly and never silently replaced by cache.

Environment note (recorded 2026-08-28): EastMoney endpoints
(`stock_zh_a_hist` / `stock_zh_a_spot_em`) refuse connections from this
deployment network at the transport layer. The proof therefore uses the
Tencent daily-history path (`stock_zh_a_hist_tx`), the CSIndex constituent
path and the Sina snapshot path of the same pinned akshare release. The
source of every cached dataset is recorded in its sidecar metadata.

Run with the isolated quant dependency group:

    uv run --group quant python tools/quant_p0_data_proof.py [--refresh]

Exit code 0 only if every required proof succeeded.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, datetime
from pathlib import Path

import akshare as ak
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from quant_core import TZ_SHANGHAI, fetch_csi500_constituents, fetch_history

HISTORY_SYMBOL = "600519"  # fixed proof symbol (贵州茅台, long continuous history)


def _measure_ms(fn, *args, **kwargs):
    start = time.perf_counter()
    df = fn(*args, **kwargs)
    return df, int((time.perf_counter() - start) * 1000)


def _freshness_days(latest: date) -> int:
    return (datetime.now(TZ_SHANGHAI).date() - latest).days


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="refetch even if cache exists")
    parser.add_argument("--cache-dir", type=Path, default=Path("data/quant-cache"))
    args = parser.parse_args()
    cache_dir = args.cache_dir

    ok = True
    print("== P0 real-data proof ==")

    # D002: fixed-symbol daily history, qfq (research) and raw (replay) series.
    series: dict[str, pd.DataFrame] = {}
    for adjust in ("qfq", ""):
        try:
            start = time.perf_counter()
            hist, meta, origin = fetch_history(
                HISTORY_SYMBOL, adjust, refresh=args.refresh, cache_dir=cache_dir
            )
            meta["request_ms"] = int((time.perf_counter() - start) * 1000)
            series[adjust or "raw"] = hist
            print(
                f"historical_rows={len(hist)} latest_history_date={meta['date_range'][1]} "
                f"symbol={HISTORY_SYMBOL} adjust={adjust or 'raw'} origin={origin} "
                f"request_ms={meta['request_ms']}"
            )
        except Exception as exc:  # noqa: BLE001 — proof reports every failure explicitly
            ok = False
            print(f"FAILURE daily-history {HISTORY_SYMBOL} adjust={adjust or 'raw'}: {exc}")

    # Adjust-parameter integrity: qfq must differ from raw somewhere if the
    # endpoint actually applies back-adjustment (600519 pays annual dividends).
    if "qfq" in series and "raw" in series:
        joined = series["qfq"].merge(series["raw"], on="date", suffixes=("_qfq", "_raw"))
        differs = bool((joined["close_qfq"] - joined["close_raw"]).abs().gt(1e-6).any())
        print(f"qfq_adjust_differs_from_raw={differs} compared_rows={len(joined)}")
        if not differs:
            print("LIMITATION: qfq series equals raw; adjust parameter appears ineffective")

    # D003: CSI500 constituents + one deterministic member's history.
    try:
        cons, cons_meta, cons_origin = fetch_csi500_constituents(refresh=args.refresh, cache_dir=cache_dir)
        print(
            f"csi500_constituents={len(cons)} effective_date={cons_meta['effective_date']} "
            f"origin={cons_origin}"
        )
        member = min(cons["constituent_code"])
        member_name = cons.loc[cons["constituent_code"] == member, "constituent_name"].iloc[0]
        m_hist, m_meta, m_origin = fetch_history(
            member, "qfq", refresh=args.refresh, cache_dir=cache_dir
        )
        print(
            f"historical_rows={len(m_hist)} latest_history_date={m_meta['date_range'][1]} "
            f"symbol={member}({member_name}) csi500_member adjust=qfq origin={m_origin}"
        )
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"FAILURE csi500-universe-or-member: {exc}")

    # D004/D005: full-market snapshot. Sina carries a per-quote 时间戳 column;
    # surface both it and the retrieval wall clock.
    try:
        snap, snap_ms = _measure_ms(ak.stock_zh_a_spot)
        if snap is None or snap.empty:
            raise RuntimeError("empty market snapshot")
        snap = snap.rename(columns={"代码": "symbol", "名称": "name", "最新价": "last_price"})
        quote_time = ""
        if "时间戳" in snap.columns:
            quote_time = str(snap["时间戳"].mode().iloc[0])
        print(
            f"snapshot_symbols={len(snap)} snapshot_quote_time={quote_time or 'NOT EXPOSED'} "
            f"snapshot_retrieved_at={datetime.now(TZ_SHANGHAI).isoformat()} "
            f"request_s={snap_ms / 1000:.1f}"
        )
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"FAILURE market-snapshot: {exc}")

    # Freshness: last calendar trade date on or before today (Sina publishes
    # the full-year calendar, so future entries must be excluded).
    try:
        cal, cal_ms = _measure_ms(ak.tool_trade_date_hist_sina)
        cal_dates = pd.to_datetime(cal["trade_date"]).dt.date
        today = datetime.now(TZ_SHANGHAI).date()
        latest_trade_date = max(d for d in cal_dates if d <= today)
        print(
            f"latest_trade_date={latest_trade_date} freshness_days="
            f"{_freshness_days(latest_trade_date)} (calendar) request_ms={cal_ms}"
        )
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"FAILURE trade-calendar: {exc}")

    print(f"== RESULT: {'PASS' if ok else 'FAIL'} ==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
