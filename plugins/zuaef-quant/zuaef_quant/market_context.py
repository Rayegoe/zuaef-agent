"""Bounded market-wide context adapter (ZUAEF Task Boundary Repair v0.1).

Production authority lives here (P5.9-A).  The historical root script is a
thin compatibility wrapper only; production calls this module directly in the
quant side environment.


This is a read-only evidence surface for questions about the A-share market as
a whole: major index quotes, advance/decline breadth, turnover, industry
sector leaders/laggards, selected external markets, oil, US rates, the US
dollar and a bounded macro headline list.

It is NOT a crawler and NOT a browser.  It collects bounded, structured data
from the existing akshare side environment, records what is observed, and
returns ``null`` / ``missing`` for unavailable layers.  It never substitutes
the candidate pool, watchlist or positions for market-wide evidence, and it
never emits causal conclusions: the host proves facts; the LLM interprets
them.

Runs in the .venv-quant side environment via ``python -m zuaef_quant.market_context``;
output is one JSON line on stdout.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import re
from typing import Any
from zoneinfo import ZoneInfo

TZ_SH = ZoneInfo("Asia/Shanghai")
EVIDENCE_SCOPE = "A_SHARE_MARKET_WIDE"
DEFAULT_NEWS_LIMIT = 10
MAX_NEWS = 12
MAX_INDICES = 8
MAX_SECTORS_PER_SIDE = 5
MAX_ASIA_INDICES = 8

# Target index names are matched against source-provided labels/aliases.
_INDEX_TARGETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("上证指数", ("上证指数", "上证综指")),
    ("深证成指", ("深证成指", "深证指数")),
    ("创业板指", ("创业板指", "创业板指数")),
    ("沪深300", ("沪深300",)),
    ("科创50", ("科创50", "科创综指", "科创板50")),
)

_ASIA_TARGETS: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    ("恒生指数", ("恒生指数", "恒生中国企业指数"), True),
    ("日经225", ("日经225", "日经指数", "日经平均"), True),
    ("韩国KOSPI", ("韩国KOSPI", "KOSPI", "韩国综合"), True),
    ("台湾加权", ("台湾加权", "台湾指数"), False),
    ("富时新加坡", ("新加坡", "富时新加坡"), False),
    ("澳洲标普200", ("澳洲", "标普/ASX", "ASX 200"), False),
)


def _now_sh() -> str:
    return _dt.datetime.now(TZ_SH).isoformat(timespec="seconds")


def _to_float(value: Any) -> float | None:
    """Best-effort numeric conversion; unparsable/missing stays ``None``."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text or text in {"-", "--", "None", "nan", "NaN"}:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _to_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    if match is None:
        return None
    try:
        return int(float(match.group(0)))
    except ValueError:
        return None


def _clean_str(value: Any, *, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"-", "--", "None", "nan", "NaN"}:
        return None
    return text[:limit]


def _get(row: dict, *keys: str) -> Any:
    for key in keys:
        if key in row:
            value = row[key]
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
    return None


def _records(table: Any) -> list[dict]:
    """Normalize an akshare/pandas DataFrame to a list of plain dict records.

    ``to_dict("records")`` is the stable pandas interface; keeping the helper
    duck-typed also lets tests use a tiny stand-in without importing pandas.
    """
    if table is None:
        return []
    if isinstance(table, list):
        return [row for row in table if isinstance(row, dict)]
    try:
        data = table.to_dict("records")
    except Exception:  # noqa: BLE001 - missing/odd table becomes missing evidence
        try:
            data = table.to_dict(orient="records")
        except Exception:  # noqa: BLE001
            return []
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def _call(ak: Any, name: str, *args: Any, **kwargs: Any) -> Any:
    """Best-effort side-feed call: an unavailable provider yields ``None``."""
    function = getattr(ak, name, None)
    if not callable(function):
        return None
    try:
        return function(*args, **kwargs)
    except Exception:  # noqa: BLE001 - unavailable feed is evidence, not a crash
        return None


def _match_name(text: str, aliases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(alias.lower() in lowered for alias in aliases)


def _first_index_value(records: list[dict], *keys: str) -> Any:
    for row in records:
        value = _get(row, *keys)
        if value is not None:
            return value
    return None


def _collect_a_share_indices(
    ak: Any,
) -> tuple[list[dict], list[str], list[dict]]:
    """Return bounded major-index observations, missing labels and raw rows."""
    missing: list[str] = []
    table = _call(ak, "stock_zh_index_spot_em", symbol="沪深重要指数")
    records = _records(table)
    if not records:
        # Some deployments/tests expose the default-argument form only.
        table = _call(ak, "stock_zh_index_spot_em")
        records = _records(table)
    if not records:
        records = _records(_call(ak, "stock_zh_index_spot_sina"))
    if not records:
        return [], ["a_share.indices"], []

    found: list[dict] = []
    for display_name, aliases in _INDEX_TARGETS:
        match = None
        for row in records:
            name = str(_get(row, "名称", "name", "指数名称") or "")
            code = str(_get(row, "代码", "code", "symbol") or "")
            if _match_name(name, aliases) or _match_name(code, aliases):
                match = row
                break
        if match is None:
            missing.append(f"a_share.indices.{display_name}")
            continue
        found.append(
            {
                "name": display_name,
                "code": _clean_str(_get(match, "代码", "code", "symbol"), limit=32),
                "level": _to_float(
                    _get(match, "最新价", "最新", "trade", "price", "close")
                ),
                "change_pct": _to_float(
                    _get(match, "涨跌幅", "change_pct", "changepercent", "涨幅")
                ),
                "turnover_cny": _to_float(
                    _get(match, "成交额", "amount", "turnover")
                ),
                "observed_at": _clean_str(
                    _get(match, "最新行情时间", "时间", "trade_time", "date"), limit=40
                ),
            }
        )
        if len(found) >= MAX_INDICES:
            break
    return found, missing, records


def _index_turnover_sum(records: list[dict]) -> tuple[float | None, list[str]]:
    """Fallback A-share turnover from the SSE + SZSE total index proxies.

    The index feed carries 成交额 for 上证指数 and 深证综指/深证成指.  We take
    one row per exchange and sum them; a missing exchange leaves the total
    missing rather than reporting a partial sum as if it were whole-market.
    """
    groups = (
        ("上证", ("上证指数", "上证综指", "000001")),
        ("深证", ("深证综指", "深证成指", "399106", "399001")),
    )
    parts: list[float] = []
    missing: list[str] = []
    for label, aliases in groups:
        value = None
        for row in records:
            name = str(_get(row, "名称", "name") or "")
            code = str(_get(row, "代码", "code", "symbol") or "")
            if not (_match_name(name, aliases) or _match_name(code, aliases)):
                continue
            amount = _to_float(_get(row, "成交额", "amount", "turnover"))
            if amount is not None:
                value = amount
                break
        if value is None:
            missing.append(f"a_share.turnover.{label}")
        else:
            parts.append(value)
    if len(parts) != len(groups):
        return None, missing
    return sum(parts), []


def _collect_breadth_and_turnover(
    ak: Any, index_records: list[dict]
) -> tuple[dict, dict, list[str]]:
    """Compute breadth/turnover from the A-share spot feed when available.

    Falls back to the market-activity feed for breadth.  Turnover remains null
    if the only available source cannot prove it; missing never becomes zero.
    """
    missing: list[str] = []
    table = _records(_call(ak, "stock_zh_a_spot_em"))
    up = down = flat = None
    turnover_cny = None
    turnover_basis = None
    if table:
        changes = [
            _to_float(_get(row, "涨跌幅", "change_pct", "changepercent"))
            for row in table
        ]
        observed = [value for value in changes if value is not None]
        if observed:
            up = sum(1 for value in observed if value > 0)
            down = sum(1 for value in observed if value < 0)
            flat = sum(1 for value in observed if value == 0)
        amounts = [
            _to_float(_get(row, "成交额", "amount", "turnover"))
            for row in table
        ]
        observed_amounts = [value for value in amounts if value is not None]
        if observed_amounts:
            turnover_cny = sum(observed_amounts)
            turnover_basis = "stock_zh_a_spot_em"

    if turnover_cny is None:
        turnover_cny, turnover_missing = _index_turnover_sum(index_records)
        if turnover_cny is not None:
            turnover_basis = "main_index_sum_SSE_SZSE"
        else:
            missing.extend(turnover_missing)

    if up is None or down is None:
        activity = _records(_call(ak, "stock_market_activity_legu"))
        for row in activity:
            item = str(_get(row, "item", "项目", "名称") or "").strip()
            value = _get(row, "value", "数值", "数量")
            if item in {"上涨", "上涨家数"} and up is None:
                up = _to_int(value)
            elif item in {"下跌", "下跌家数"} and down is None:
                down = _to_int(value)
            elif item in {"平盘", "平盘家数"} and flat is None:
                flat = _to_int(value)
        if up is None or down is None:
            missing.append("a_share.breadth")

    breadth: dict[str, Any] = {
        "up": up,
        "down": down,
        "flat": flat,
        "advance_decline_ratio": (
            round(up / down, 4) if isinstance(up, int) and isinstance(down, int) and down else None
        ),
    }
    if turnover_cny is None:
        missing.append("a_share.turnover")
    return (
        breadth,
        {"total_cny": turnover_cny, "basis": turnover_basis},
        missing,
    )


def _collect_sectors(ak: Any) -> tuple[dict, list[str]]:
    sectors: list[dict] = []
    # EastMoney is the canonical first choice.  The THS summary is a bounded
    # structured fallback used when the EastMoney push endpoint is unavailable
    # in this deployment's network (the same failure class seen by live ops).
    for function_name in (
        "stock_board_industry_name_em",
        "stock_board_industry_summary_ths",
    ):
        records = _records(_call(ak, function_name))
        for row in records:
            name = _clean_str(_get(row, "板块名称", "板块", "名称", "name"), limit=40)
            change_pct = _to_float(_get(row, "涨跌幅", "change_pct", "changepercent"))
            if name is None or change_pct is None:
                continue
            sectors.append({"name": name, "change_pct": change_pct})
        if sectors:
            break
    missing: list[str] = []
    if not sectors:
        missing.append("a_share.sectors")
        return {"leaders": [], "laggards": [], "count": 0}, missing
    sectors.sort(key=lambda item: item["change_pct"], reverse=True)
    leaders = sectors[:MAX_SECTORS_PER_SIDE]
    laggards = list(reversed(sectors[-MAX_SECTORS_PER_SIDE:]))
    return {
        "leaders": leaders,
        "laggards": laggards,
        "count": len(sectors),
    }, missing


def _global_index_row(records: list[dict], aliases: tuple[str, ...]) -> dict | None:
    for row in records:
        name = str(_get(row, "名称", "name") or "")
        code = str(_get(row, "代码", "code", "symbol") or "")
        if _match_name(name, aliases) or _match_name(code, aliases):
            return row
    return None


def _quote_payload(row: dict, *, name: str | None = None) -> dict[str, Any]:
    return {
        "name": name
        or _clean_str(_get(row, "名称", "name"), limit=40),
        "code": _clean_str(_get(row, "代码", "code", "symbol"), limit=32),
        "level": _to_float(
            _get(row, "最新价", "最新", "trade", "price", "close")
        ),
        "change_pct": _to_float(
            _get(row, "涨跌幅", "change_pct", "changepercent", "涨幅")
        ),
        "observed_at": _clean_str(
            _get(row, "最新行情时间", "时间", "trade_time", "date"), limit=40
        ),
    }


def _global_hist_quote(
    ak: Any, display_name: str, sina_symbol: str
) -> dict | None:
    """Sina global-index history fallback for one index.

    The last row is the latest observed close; a host-computed prior-close
    change is provided only when two closes are available.
    """
    rows = _records(_call(ak, "index_global_hist_sina", symbol=sina_symbol))
    if not rows:
        return None
    latest = rows[-1]
    close = _to_float(_get(latest, "close", "收盘", "最新价"))
    if close is None:
        return None
    change_pct = None
    if len(rows) >= 2:
        previous = _to_float(_get(rows[-2], "close", "收盘", "最新价"))
        if previous:
            change_pct = round((close / previous - 1) * 100, 4)
    return {
        "name": display_name,
        "code": sina_symbol,
        "level": close,
        "change_pct": change_pct,
        "observed_at": _clean_str(
            _get(latest, "date", "日期", "时间"), limit=40
        ),
        "proxy": "index_global_hist_sina",
    }


def _asia_fallback_quotes(
    ak: Any, needed: set[str] | None = None
) -> dict[str, dict]:
    """Bounded non-EastMoney fallbacks for the requested Asian indices."""
    if needed is None:
        needed = {name for name, _, required in _ASIA_TARGETS if required}
    out: dict[str, dict] = {}

    if "恒生指数" in needed:
        hk_rows = _records(_call(ak, "stock_hk_index_spot_sina"))
        for row in hk_rows:
            name = str(_get(row, "名称", "name") or "")
            code = str(_get(row, "代码", "code", "symbol") or "")
            if name == "恒生指数" or code == "HSI":
                out["恒生指数"] = _quote_payload(row, name="恒生指数")
                break
    for display_name, sina_symbol in (
        ("日经225", "日经225指数"),
        ("韩国KOSPI", "首尔综合指数"),
        ("台湾加权", "中国台湾加权指数"),
        ("澳洲标普200", "澳大利亚标准普尔200指数"),
    ):
        if display_name not in needed or display_name in out:
            continue
        quote = _global_hist_quote(ak, display_name, sina_symbol)
        if quote is not None:
            out[display_name] = quote
    return out


def _dollar_fallback_quote(ak: Any) -> dict | None:
    """USD/CNY proxy when the DXY feed is unavailable.

    The spec permits an available dollar proxy; this is explicitly labelled
    with its own name and proxy field, so it can never be mistaken for DXY.
    """
    end = _dt.datetime.now(TZ_SH).strftime("%Y%m%d")
    start = (_dt.datetime.now(TZ_SH) - _dt.timedelta(days=20)).strftime("%Y%m%d")
    rows = _records(
        _call(
            ak,
            "currency_boc_sina",
            symbol="美元",
            start_date=start,
            end_date=end,
        )
    )
    if not rows:
        return None
    usable = []
    for row in rows:
        value = _to_float(
            _get(row, "央行中间价", "中行折算价", "中行汇买价", "最新价")
        )
        if value is not None:
            # BOC USD quotes are per 100 USD; normalise to one USD when the
            # source is in that form, while leaving test/alternate direct
            # USD/CNY values untouched.
            if value > 20:
                value = round(value / 100.0, 6)
            usable.append((value, _clean_str(_get(row, "日期", "date"), limit=20)))
    if not usable:
        return None
    latest_value, latest_date = usable[-1]
    change_pct = None
    if len(usable) >= 2 and usable[-2][0]:
        change_pct = round((latest_value / usable[-2][0] - 1) * 100, 4)
    return {
        "name": "USD/CNY proxy",
        "code": "USDCNY",
        "level": latest_value,
        "change_pct": change_pct,
        "observed_at": latest_date,
        "proxy": "currency_boc_sina",
    }


def _collect_external(ak: Any) -> tuple[dict, list[str]]:
    missing: list[str] = []
    raw_global = _records(_call(ak, "index_global_spot_em"))

    energy: dict[str, Any] = {"brent": None, "wti": None, "proxy": None}
    futures = _records(_call(ak, "futures_global_spot_em"))

    def _usable(row: dict) -> bool:
        return _to_float(_get(row, "最新价", "最新", "price", "close")) is not None

    def _pick_oil(kind: str) -> dict | None:
        candidates: list[tuple[int, float, dict]] = []
        for row in futures:
            if not _usable(row):
                continue
            name = str(_get(row, "名称", "name") or "")
            code = str(_get(row, "代码", "code", "symbol") or "").upper()
            if kind == "wti":
                if code == "CL00Y" or name.upper() == "NYMEX原油":
                    score = 3
                elif "NYMEX原油" in name or "WTI" in name.upper() or "美原油" in name:
                    score = 2
                elif "原油" in name and code.endswith("00Y"):
                    score = 1
                else:
                    continue
            else:
                if code == "B00Y" or name == "布伦特原油":
                    score = 3
                elif "布伦特" in name and code.endswith("00Y"):
                    score = 2
                elif "布伦特" in name or "Brent" in name:
                    score = 1
                else:
                    continue
            volume = _to_float(_get(row, "成交量", "volume")) or 0.0
            candidates.append((score, volume, row))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return _quote_payload(candidates[0][2])

    energy["brent"] = _pick_oil("brent")
    energy["wti"] = _pick_oil("wti")
    if energy["brent"] is None and energy["wti"] is None:
        for row in futures:
            if not _usable(row):
                continue
            name = str(_get(row, "名称", "name") or "")
            if "原油" in name or "欧佩克" in name:
                energy["proxy"] = _quote_payload(row, name=name)
                break
        if energy["proxy"] is None:
            missing.append("external.energy")
    if energy["brent"] is None:
        missing.append("external.energy.brent")
    if energy["wti"] is None:
        missing.append("external.energy.wti")

    us_10y = None
    recent_start = (_dt.datetime.now(TZ_SH) - _dt.timedelta(days=30)).strftime(
        "%Y%m%d"
    )
    rate_rows = _records(_call(ak, "bond_zh_us_rate", start_date=recent_start))
    if not rate_rows:
        rate_rows = _records(_call(ak, "bond_zh_us_rate"))
    for row in reversed(rate_rows):
        value = _to_float(
            _get(
                row,
                "美国国债收益率10年",
                "美国10年期国债收益率",
                "US10Y",
                "us_10y",
            )
        )
        if value is not None:
            us_10y = {
                "name": "US 10Y",
                "value_pct": value,
                "as_of": _clean_str(_get(row, "日期", "date"), limit=20),
            }
            break
    rates = {"us_10y": us_10y}
    if us_10y is None:
        missing.append("external.rates.us_10y")

    dollar_row = _global_index_row(raw_global, ("美元指数", "USDX", "DXY", "UDI"))
    dollar_quote = _quote_payload(dollar_row) if dollar_row is not None else None
    if dollar_quote is None:
        dollar_quote = _dollar_fallback_quote(ak)
    fx = {"dollar_index": dollar_quote}
    if dollar_quote is None:
        missing.append("external.fx.dollar_index")

    em_asia: dict[str, dict] = {}
    for display_name, aliases, _required in _ASIA_TARGETS:
        row = _global_index_row(raw_global, aliases)
        if row is not None:
            em_asia[display_name] = _quote_payload(row, name=display_name)
    missing_required = {
        display_name
        for display_name, _aliases, required in _ASIA_TARGETS
        if required and display_name not in em_asia
    }
    # Only spend network calls on fallbacks when an EastMoney gap exists; then
    # fetch the full bounded Asian target list for the best available context.
    fallback_asia = (
        _asia_fallback_quotes(ak, {name for name, _, _ in _ASIA_TARGETS})
        if missing_required
        else {}
    )
    asia_indices = []
    required_asia_missing: list[str] = []
    for display_name, _aliases, required in _ASIA_TARGETS:
        payload = em_asia.get(display_name) or fallback_asia.get(display_name)
        if payload is not None:
            asia_indices.append(payload)
        elif required:
            required_asia_missing.append(f"external.asia_indices.{display_name}")
        if len(asia_indices) >= MAX_ASIA_INDICES:
            break
    if not asia_indices:
        missing.append("external.asia_indices")
    else:
        missing.extend(required_asia_missing)

    return {
        "energy": energy,
        "rates": rates,
        "fx": fx,
        "asia_indices": asia_indices,
    }, missing


def _collect_news(ak: Any, limit: int) -> tuple[list[dict], list[str]]:
    limit = max(1, min(int(limit), MAX_NEWS))
    items: list[dict] = []
    missing: list[str] = []

    em_records = _records(_call(ak, "stock_info_global_em"))
    for row in em_records[:limit]:
        title = _clean_str(_get(row, "标题", "title"), limit=160)
        if title is None:
            continue
        items.append(
            {
                "title": title,
                "published_at": _clean_str(
                    _get(row, "发布时间", "时间", "published_at"), limit=40
                ),
                "source": "东方财富",
                "url": _clean_str(_get(row, "链接", "url", "code"), limit=500),
            }
        )
        if len(items) >= limit:
            break

    if len(items) < limit:
        cls_records = _records(_call(ak, "stock_info_global_cls", "重点"))
        if not cls_records:
            cls_records = _records(_call(ak, "stock_info_global_cls"))
        for row in cls_records:
            title = _clean_str(_get(row, "标题", "title"), limit=160)
            if title is None:
                continue
            date_text = _clean_str(_get(row, "发布日期", "date"), limit=20)
            time_text = _clean_str(_get(row, "发布时间", "time"), limit=20)
            published_at = " ".join(part for part in (date_text, time_text) if part) or None
            items.append(
                {
                    "title": title,
                    "published_at": published_at,
                    "source": "财联社",
                    "url": None,
                }
            )
            if len(items) >= limit:
                break

    if not items:
        missing.append("news")
    return items[:limit], missing


def collect(limit: int = DEFAULT_NEWS_LIMIT) -> dict:
    """Collect the bounded market-wide evidence packet.

    Never raises for feed failures: unavailable layers are reported through
    ``missing`` and remain ``null`` (never zero-filled or substituted with
    candidate-pool/account data).
    """
    missing: list[str] = []
    a_share: dict[str, Any] = {
        "indices": [],
        "breadth": {"up": None, "down": None, "flat": None, "advance_decline_ratio": None},
        "turnover": {"total_cny": None},
        "sectors": {"leaders": [], "laggards": [], "count": 0},
    }
    external: dict[str, Any] = {
        "energy": {"brent": None, "wti": None, "proxy": None},
        "rates": {"us_10y": None},
        "fx": {"dollar_index": None},
        "asia_indices": [],
    }
    news: list[dict] = []

    try:
        import akshare as ak
    except Exception as exc:  # noqa: BLE001 - missing side env is structured evidence
        return {
            "as_of": _now_sh(),
            "evidence_scope": EVIDENCE_SCOPE,
            "a_share": a_share,
            "external": external,
            "news": news,
            "missing": [
                "akshare",
                "a_share.indices",
                "a_share.breadth",
                "a_share.turnover",
                "a_share.sectors",
                "external.energy",
                "external.rates",
                "external.fx",
                "external.asia_indices",
                "news",
            ],
            "limitations": [
                "market-wide evidence unavailable: akshare side environment failed to import",
                "bounded read-only evidence surface, not a crawler or browser",
                "host reports facts only; causal interpretation belongs to the model",
            ],
            "error": f"{type(exc).__name__}: {str(exc)[-200:]}",
        }

    indices, index_missing, index_records = _collect_a_share_indices(ak)
    a_share["indices"] = indices
    missing.extend(index_missing)

    breadth, turnover, breadth_missing = _collect_breadth_and_turnover(
        ak, index_records
    )
    a_share["breadth"] = breadth
    a_share["turnover"] = turnover
    missing.extend(breadth_missing)

    sectors, sector_missing = _collect_sectors(ak)
    a_share["sectors"] = sectors
    missing.extend(sector_missing)

    external, external_missing = _collect_external(ak)
    missing.extend(external_missing)

    news, news_missing = _collect_news(ak, limit)
    missing.extend(news_missing)

    # De-duplicate while preserving diagnostic order (a broken source can add
    # the same target from more than one path).
    seen_missing = set()
    deduped_missing = []
    for item in missing:
        if item not in seen_missing:
            seen_missing.add(item)
            deduped_missing.append(item)

    return {
        "as_of": _now_sh(),
        "evidence_scope": EVIDENCE_SCOPE,
        "a_share": a_share,
        "external": external,
        "news": news,
        "missing": deduped_missing,
        "limitations": [
            "bounded structured feeds; not exhaustive market research",
            "facts only: observed values never carry causal conclusions",
            "unavailable fields stay null/missing; narrower universe or account data is never substituted for market-wide evidence",
            "feed values may be delayed by the provider; observed_at/as_of stay present",
            "news items are bounded titles with source/time/url when available, never full article bodies",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=DEFAULT_NEWS_LIMIT,
                        help=f"bounded news item count (1-{MAX_NEWS})")
    args = parser.parse_args()
    print(json.dumps(collect(args.limit), ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
