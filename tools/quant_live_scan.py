"""Deterministic live-scan for the quant plugin's get_live_signals tool (P5).

Scans ONLY the active universe (frozen csi500_subset manifest) with the
active strategy (benchmarks/quant/gen1/active.toml), computes the entry
clauses deterministically on current quotes plus cached history, and prints
bounded JSON: at most --max-triggers candidates with timestamps and scan
latency. The LLM never scans the whole market (spec 07 §2).

Quote path: qt.gtimg.cn batch quote (Tencent, one request per ~50 codes).
akshare's available spot paths are full-market (Sina ~48s, Tencent ~74s),
which is materially too slow for a ~60s live cadence on a 37-symbol
universe, so this small implementation is substituted per spec
04 §9; the source is recorded in the output.

    .venv-quant/bin/python tools/quant_live_scan.py [--max-triggers 10]

Exit code 0 with {"triggers": []} is a valid NO_TRADE input.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import requests
from quant_core import TZ_SHANGHAI, load_config, read_cache, to_tx_symbol

CACHE_DIR = Path("data/quant-cache")
QUOTE_URL = "https://qt.gtimg.cn/q="
BATCH_SIZE = 50


def fetch_batch_quotes(symbols: list[str]) -> dict[str, dict]:
    """One batched Tencent quote request per ~50 codes. Deterministic parsing.

    Returns symbol -> {name, price, prev_close, open, volume(shares), date, time}.
    Field layout (v_shXXXXXX="..."), 0-indexed after '~' split:
    1 name, 2 code, 3 last, 4 prev_close, 5 open, 6 volume(手), 30 date, 31 time.
    """
    out: dict[str, dict] = {}
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}
    for i in range(0, len(symbols), BATCH_SIZE):
        batch = [to_tx_symbol(s) for s in symbols[i : i + BATCH_SIZE]]
        resp = requests.get(QUOTE_URL + ",".join(batch), headers=headers, timeout=10)
        resp.raise_for_status()
        text = resp.content.decode("gbk", errors="replace")
        for raw in text.split(";"):
            raw = raw.strip()
            if not raw or "=" not in raw:
                continue
            _, _, payload = raw.partition("=")
            fields = payload.strip('"').split("~")
            if len(fields) < 32 or not fields[3]:
                continue
            code = fields[2]
            try:
                out[code] = {
                    "name": fields[1],
                    "price": float(fields[3]),
                    "prev_close": float(fields[4]),
                    "open": float(fields[5]),
                    "volume": float(fields[6]) * 100.0,  # 手 -> shares
                    "date": fields[30],
                    "time": fields[31],
                }
            except ValueError:
                continue
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strategy",
        type=Path,
        default=Path("benchmarks/quant/gen1/active.toml"),
        help="active strategy (host-owned freeze)",
    )
    parser.add_argument("--max-triggers", type=int, default=10)
    args = parser.parse_args()

    active_cfg = load_config(args.strategy)
    committed_universe = Path("benchmarks/quant/gen1/universe.toml")
    try:
        uni = load_config(committed_universe)
        symbols = [str(s).strip() for s in uni["symbols"]]
        universe_source = str(uni.get("name", "user_universe"))
    except (OSError, KeyError, ValueError, TypeError):
        universe_meta = json.loads(
            (CACHE_DIR / "universe" / "csi500_subset.meta.json").read_text(
                encoding="utf-8"
            )
        )
        symbols = universe_meta["symbols"]
        universe_source = "csi500_subset"
    cons, _ = read_cache("universe", "csi500_cons", CACHE_DIR)
    name_by_symbol = (
        dict(zip(cons["constituent_code"], cons["constituent_name"]))
        if cons is not None
        else {}
    )

    scan_start = time.perf_counter()
    quotes = fetch_batch_quotes(symbols)
    quote_ms = int((time.perf_counter() - scan_start) * 1000)

    triggers = []
    quotes_detail = []
    for symbol in symbols:
        quote = quotes.get(symbol)
        base = {
            "symbol": symbol,
            "name": (quote.get("name") if quote else None)
            or str(name_by_symbol.get(symbol, "")),
        }
        if quote is None or quote["price"] <= 0:
            quotes_detail.append({**base, "quote": False, "reason": "no_quote"})
            continue
        hist, _ = read_cache("daily", f"{symbol}_qfq", CACHE_DIR)
        if hist is None or len(hist) < 25:
            quotes_detail.append(
                {
                    **base,
                    "quote": True,
                    "price": round(quote["price"], 2),
                    "reason": "insufficient_history",
                }
            )
            continue
        hist["date"] = pd.to_datetime(hist["date"])
        hist = hist.sort_values("date")
        close_5d = float(hist["close"].iloc[-6])
        volume_ma20 = float(hist["volume"].tail(20).mean())
        if volume_ma20 <= 0:
            quotes_detail.append(
                {
                    **base,
                    "quote": True,
                    "price": round(quote["price"], 2),
                    "reason": "no_volume_ma",
                }
            )
            continue
        pullback = quote["price"] / close_5d - 1
        ratio = quote["volume"] / volume_ma20
        strength = quote["price"] - quote["prev_close"]
        entry_pullback_max = float(active_cfg["entry_pullback_max"])
        entry_volume_ratio_min = float(active_cfg["entry_volume_ratio_min"])
        is_trigger = (
            pullback <= entry_pullback_max
            and ratio >= entry_volume_ratio_min
            and strength >= 0
        )
        quotes_detail.append(
            {
                **base,
                "quote": True,
                "reason": "ok",
                "price": round(quote["price"], 2),
                "prev_close": round(quote["prev_close"], 2),
                "pullback_5d": round(pullback, 4),
                "volume_ratio_20d": round(ratio, 3),
                "trigger": is_trigger,
            }
        )
        if is_trigger:
            triggers.append(
                {
                    "symbol": symbol,
                    "name": quote["name"] or str(name_by_symbol.get(symbol, "")),
                    "price": round(quote["price"], 2),
                    "prev_close": round(quote["prev_close"], 2),
                    "pullback_5d": round(pullback, 4),
                    "volume_ratio_20d": round(ratio, 3),
                    "quote_time": f"{quote['date']} {quote['time']}",
                }
            )
    triggers = triggers[: args.max_triggers]

    quote_times = sorted(
        {q["date"] + " " + q["time"] for q in quotes.values() if q.get("time")}
    )
    out = {
        "active_strategy": {
            "name": active_cfg["name"],
            "label": active_cfg.get("label", ""),
            "entry_pullback_max": active_cfg["entry_pullback_max"],
            "entry_volume_ratio_min": active_cfg["entry_volume_ratio_min"],
            "max_holding_days": active_cfg["max_holding_days"],
            "stop_loss_pct": active_cfg["stop_loss_pct"],
            "take_profit_pct": active_cfg["take_profit_pct"],
        },
        "universe": universe_source,
        "universe_size": len(symbols),
        "quotes_fetched": len(quotes),
        "as_of": datetime.now(TZ_SHANGHAI).isoformat(),
        "latest_quote_time": quote_times[-1] if quote_times else None,
        "scan_ms": int((time.perf_counter() - scan_start) * 1000),
        "quote_request_ms": quote_ms,
        "quote_source": "qt.gtimg.cn batch quote (Tencent); history: local cache of akshare stock_zh_a_hist_tx",
        "quotes": quotes_detail,
        "triggers": triggers,
        "limitation": (
            "volume_ratio uses today's cumulative volume vs full-day 20d average — "
            "intraday it understates; triggers are deterministic evidence, not orders"
        ),
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
