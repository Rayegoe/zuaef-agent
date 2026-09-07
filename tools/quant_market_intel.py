"""Bounded structured market-intelligence adapter (research service v0.2, T008).

One structured feed per call — recent stock-specific company news — with
bounded item count and truncated content. This is NOT a crawler, a search
engine or a browser: open-ended public research belongs to the Harness
WebSearch/WebFetch capabilities (ADR-04); this tool only exposes the
structured finance evidence the side environment already owns.

Runs in the .venv-quant side environment (akshare lives there); the agent
toolset calls it via subprocess. Output is one JSON line on stdout.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
from zoneinfo import ZoneInfo

TZ_SH = ZoneInfo("Asia/Shanghai")
DEFAULT_LIMIT = 8
MAX_LIMIT = 20
SUMMARY_MAX_CHARS = 200


def collect(symbol: str, limit: int = DEFAULT_LIMIT) -> dict:
    """Fetch bounded structured news evidence for one symbol.

    Never raises: failures come back as ``{"error": ...}`` evidence so the
    caller can degrade gracefully (research PARTIAL) instead of crashing.
    """
    limit = max(1, min(int(limit), MAX_LIMIT))
    try:
        import akshare as ak

        raw = ak.stock_news_em(symbol=symbol)
    except Exception as exc:  # noqa: BLE001 — failure is structured evidence
        return {"error": f"structured news fetch failed: {str(exc)[-200:]}"}
    items = []
    for _, row in raw.head(limit).iterrows():
        summary = str(row.get("新闻内容", "") or "").strip()
        items.append(
            {
                "title": str(row.get("新闻标题", "") or "").strip(),
                "summary": summary[:SUMMARY_MAX_CHARS],
                "published_at": str(row.get("发布时间", "") or "").strip() or None,
                "source": str(row.get("文章来源", "") or "").strip() or None,
                "url": str(row.get("新闻链接", "") or "").strip() or None,
            }
        )
    return {
        "symbol": symbol,
        "as_of": _dt.datetime.now(TZ_SH).isoformat(timespec="seconds"),
        "count": len(items),
        "requested_limit": limit,
        "items": items,
        "source": "akshare.stock_news_em",
        "limitations": [
            "structured single feed, bounded items — not exhaustive market research",
            "open-ended questions go through Harness WebSearch/WebFetch, not this tool",
            "truncated summaries; open the url for full content",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True, help="6-digit A-share code")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"bounded item count (1-{MAX_LIMIT})")
    args = parser.parse_args()
    symbol = str(args.symbol).strip()
    if not (symbol.isdigit() and len(symbol) == 6):
        print(json.dumps({"error": f"{symbol!r} is not a valid 6-digit A-share code"},
                         ensure_ascii=False))
        return 2
    print(json.dumps(collect(symbol, args.limit), ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
