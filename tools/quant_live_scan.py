"""Deterministic live-scan for the quant plugin's get_live_signals tool (P5).

Scans ONLY the resolved active universe with the active strategy
(benchmarks/quant/gen1/active.toml), computes the entry clauses
deterministically on current quotes plus cached history, and prints bounded
JSON: at most --max-triggers candidates with timestamps and scan latency.
The LLM never scans the whole market (spec 07 §2).

Universe resolution (business-dashboard spec 03/T005) — priority:
  1. --universe-file <path> (explicit; e.g. legacy_watchlist.toml scan);
  2. data/quant-cache/candidates/active_symbols.json if valid and non-empty
     (deterministic candidate-pool handoff from tools/quant_build_candidates.py);
  3. frozen historical CSI500 subset manifest (compatibility fallback);
  4. otherwise loud failure. An empty/unreadable universe never silently
     becomes a NO_TRADE conclusion — the legacy four-symbol watchlist cannot
     implicitly define the opportunity universe.

Quote path: qt.gtimg.cn batch quote (Tencent, one request per ~50 codes).
akshare's available spot paths are full-market (Sina ~48s, Tencent ~74s),
which is materially too slow for a ~60s live cadence on a ~50-symbol
universe, so this small implementation is substituted per spec 04 §9; the
source is recorded in the output.

Volume semantics (spec v2.0 P0.1): the scan consumes the latest
quant_validate_semantics.py proof. A FAIL (no canonical cached volume unit)
suppresses all triggers fail closed — a broken volume clause must never
manufacture an entry signal — while the status stays visible in the output
so the decision brief can state why no trigger evidence exists.

    .venv-quant/bin/python tools/quant_live_scan.py [--max-triggers 10]
        [--universe-file benchmarks/quant/gen1/legacy_watchlist.toml]

Exit code 0 with {"triggers": []} is a valid NO_TRADE input.
Exit code 2 means the universe could not be resolved (loud failure).
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

GEN1_DIR = Path("benchmarks/quant/gen1")
LEGACY_WATCHLIST_PATH = GEN1_DIR / "legacy_watchlist.toml"
UNIVERSE_TOML_PATH = GEN1_DIR / "universe.toml"
ACTIVE_SYMBOLS_PATH = CACHE_DIR / "candidates" / "active_symbols.json"
SUBSET_META_PATH = CACHE_DIR / "universe" / "csi500_subset.meta.json"
SEMANTIC_DIR = Path("workspace/artifacts/quant/semantic")


class UniverseError(RuntimeError):
    """Raised when no valid, non-empty universe can be resolved (fail closed)."""


def fetch_batch_quotes(symbols: list[str], *, max_batches_fail: int = 2) -> dict[str, dict]:
    """One batched Tencent quote request per ~50 codes. Deterministic parsing.

    Each batch retries boundedly (0s/2s/8s — same pattern as quant_core
    history fetch) because this deployment has observed transient SSL EOF
    transport failures. Up to max_batches_fail batches may fail without
    killing the caller: their symbols simply come back without a quote
    (surfaced downstream as no_quote / excluded, never as fresh data).
    Raises only when every batch failed.

    Returns symbol -> {name, price, prev_close, open, volume(shares), date,
    time, pe_ttm, pb, dividend_yield_pct, turnover_cny, market_cap_cny}.
    Field layout (v_shXXXXXX="..."), 0-indexed after '~' split:
    1 name, 2 code, 3 last, 4 prev_close, 5 open, 6 volume(手),
    30 quote datetime (YYYYMMDDHHMMSS), 31 change, 32 change%,
    37 turnover(万元), 38 turnover rate(%), 39 PE(TTM), 43 amplitude,
    44 float mktcap(亿), 45 total mktcap(亿), 46 PB, 64 dividend yield(%).
    Fundamental fields are best-effort: empty -> None, never a guess.
    """
    out: dict[str, dict] = {}
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}

    def _num(fields: list[str], idx: int) -> float | None:
        if idx >= len(fields) or not fields[idx]:
            return None
        try:
            return float(fields[idx])
        except ValueError:
            return None

    def _fetch_one(batch: list[str]) -> None:
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
                    # field 30 is the full quote datetime; field 31 is the
                    # abs change, not a time (pre-2026-09 misparse)
                    "date": fields[30][:8],
                    "time": fields[30][8:],
                    "turnover_cny": (_num(fields, 37) or 0.0) * 10_000.0,
                    "turnover_rate_pct": _num(fields, 38),
                    "pe_ttm": _num(fields, 39),
                    "market_cap_cny": (_num(fields, 45) or 0.0) * 1e8 or None,
                    "pb": _num(fields, 46),
                    "dividend_yield_pct": _num(fields, 64),
                }
            except ValueError:
                continue

    batches = [
        [to_tx_symbol(s) for s in symbols[i : i + BATCH_SIZE]]
        for i in range(0, len(symbols), BATCH_SIZE)
    ]
    failed = 0
    last_exc: Exception | None = None
    for batch in batches:
        for attempt, delay in enumerate((0.0, 2.0, 8.0)):
            if delay:
                time.sleep(delay)
            try:
                _fetch_one(batch)
                last_exc = None
                break
            except Exception as exc:  # noqa: BLE001 — transient transport failures retried boundedly
                last_exc = exc
        else:
            failed += 1
            if failed > max_batches_fail:
                raise RuntimeError(f"quote batches failing ({failed} failed): {last_exc}")
    return out


def timing_from_quote_hist(quote: dict, hist: pd.DataFrame) -> tuple[float, float] | None:
    """S3-compatible timing inputs from live quote + cached daily history.

    Returns (pullback_5d, volume_ratio_20d) using the same definitions as the
    frozen S3 evaluation: pullback vs the close 5 cached sessions back, today's
    cumulative volume vs the 20-session full-day average.
    """
    hist = hist.sort_values("date")
    if len(hist) < 25:
        return None
    close_5d = float(hist["close"].iloc[-6])
    volume_ma20 = float(hist["volume"].tail(20).mean())
    if volume_ma20 <= 0 or close_5d <= 0:
        return None
    pullback = quote["price"] / close_5d - 1
    ratio = quote["volume"] / volume_ma20
    return pullback, ratio


def load_universe_file_symbols(path: Path) -> tuple[list[str], str]:
    """Explicit TOML universe/watchlist input -> (symbols, name)."""
    uni = load_config(path)
    symbols = [str(s).strip() for s in uni["symbols"]]
    return symbols, str(uni.get("name", path.stem))


def load_active_symbols(path: Path) -> tuple[list[str], str]:
    """Candidate handoff (active_symbols.json) -> (symbols, as_of).

    Empty list, missing keys or unreadable JSON raise UniverseError — the
    handoff is never silently accepted as an empty universe.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UniverseError(f"candidate handoff unreadable ({path}): {exc}") from exc
    symbols = data.get("symbols")
    if not isinstance(symbols, list) or not symbols:
        raise UniverseError(f"candidate handoff has no symbols ({path})")
    return [str(s).strip() for s in symbols], str(data.get("as_of", ""))


def resolve_universe(
    explicit_file: Path | None,
    active_path: Path = ACTIVE_SYMBOLS_PATH,
    subset_meta_path: Path = SUBSET_META_PATH,
) -> dict:
    """Deterministic universe resolution with loud empty/failed failure modes."""
    if explicit_file is not None:
        symbols, name = load_universe_file_symbols(explicit_file)
        if not symbols:
            raise UniverseError(f"universe file {explicit_file} has no symbols")
        return {
            "symbols": symbols,
            "source": name,
            "source_path": str(explicit_file),
            "as_of": "",
        }
    if active_path.exists():
        try:
            symbols, as_of = load_active_symbols(active_path)
        except UniverseError as exc:
            # a present-but-broken handoff must not silently fall through
            raise UniverseError(
                f"{exc}; remove the file or rerun tools/quant_build_candidates.py"
            ) from exc
        return {
            "symbols": symbols,
            "source": "candidate_pool_active",
            "source_path": str(active_path),
            "as_of": as_of,
        }
    if subset_meta_path.exists():
        meta = json.loads(subset_meta_path.read_text(encoding="utf-8"))
        symbols = [str(s).strip() for s in meta.get("symbols", [])]
        if not symbols:
            raise UniverseError(f"frozen subset manifest has no symbols ({subset_meta_path})")
        return {
            "symbols": symbols,
            "source": "csi500_subset",
            "source_path": str(subset_meta_path),
            "as_of": str(meta.get("generated_at", "")),
        }
    raise UniverseError(
        "no universe resolvable: no --universe-file, no candidate handoff "
        f"({active_path}), no frozen subset manifest ({subset_meta_path}). "
        "Run tools/quant_build_candidates.py first."
    )


def load_volume_semantics(evidence_dir: Path = SEMANTIC_DIR) -> dict:
    """Latest P0.1 semantic proof -> status block consumed by the scan.

    Only a proven FAIL suppresses triggers. Missing or unreadable evidence
    is UNKNOWN — surfaced, never silently treated as PASS.
    """
    proofs = sorted(evidence_dir.glob("semantic_proof_*.json"))
    if not proofs:
        return {"status": "UNKNOWN", "evidence": None, "reason": "no semantic proof run yet"}
    latest = proofs[-1]
    try:
        proof = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "UNKNOWN", "evidence": str(latest), "reason": "semantic proof unreadable"}
    return {
        "status": str(proof.get("status", "UNKNOWN")),
        "evidence": str(latest),
        "reason": str(proof.get("reason", "")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strategy",
        type=Path,
        default=Path("benchmarks/quant/gen1/active.toml"),
        help="active strategy (host-owned freeze)",
    )
    parser.add_argument(
        "--universe-file",
        type=Path,
        default=None,
        help="explicit universe/watchlist TOML (e.g. legacy_watchlist.toml); "
        "default: candidate handoff -> frozen subset fallback",
    )
    parser.add_argument("--max-triggers", type=int, default=10)
    args = parser.parse_args()

    active_cfg = load_config(args.strategy)
    volume_semantics = load_volume_semantics()
    try:
        resolved = resolve_universe(args.universe_file)
    except UniverseError as exc:
        print(json.dumps({"error": "UNIVERSE_UNRESOLVED", "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    symbols = resolved["symbols"]
    universe_source = resolved["source"]

    cons_500, _ = read_cache("universe", "csi500_cons", CACHE_DIR)
    cons_300, _ = read_cache("universe", "csi300_cons", CACHE_DIR)
    name_by_symbol: dict = {}
    for cons in (cons_500, cons_300):
        if cons is not None:
            name_by_symbol.update(dict(zip(cons["constituent_code"], cons["constituent_name"])))

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
        if hist is None:
            quotes_detail.append(
                {
                    **base,
                    "quote": True,
                    "price": round(quote["price"], 2),
                    "reason": "insufficient_history",
                }
            )
            continue
        timing = timing_from_quote_hist(quote, hist)
        if timing is None:
            quotes_detail.append(
                {
                    **base,
                    "quote": True,
                    "price": round(quote["price"], 2),
                    "reason": "insufficient_history",
                }
            )
            continue
        pullback, ratio = timing
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

    suppressed_count = 0
    if volume_semantics["status"] == "FAIL":
        # spec P0.1: no canonical volume unit -> the volume clause cannot be
        # trusted; fail closed instead of manufacturing entry evidence.
        suppressed_count = len(triggers)
        triggers = []
        for q in quotes_detail:
            if q.get("trigger"):
                q["trigger"] = False
                q["trigger_suppressed"] = True

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
        "universe_source_path": resolved["source_path"],
        "universe_as_of": resolved["as_of"],
        "universe_size": len(symbols),
        "quotes_fetched": len(quotes),
        "volume_semantics": volume_semantics,
        "triggers_suppressed": suppressed_count,
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
            + (
                "; VOLUME SEMANTICS FAIL: cached volume unit not canonical, triggers "
                "suppressed fail closed (spec P0.1)"
                if suppressed_count
                else ""
            )
        ),
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
